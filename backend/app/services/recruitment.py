from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from backend.app.core.constants import ROSTER_TEMPLATE
from backend.app.models.entities import Player, RecruitmentTarget, SaveGame, Team, TeamTactics, TransferListing
from backend.app.schemas.api import (
    ContractWatchPlayerRead,
    RecruitmentListingRead,
    RecruitmentResponse,
    RecruitmentSummaryRead,
    ScoutingReportRead,
)
from backend.app.services.game import get_active_save, get_user_team


SCOUTING_WEEKS_TO_COMPLETE = 3
MAX_ACTIVE_REPORTS = 4
FORWARD_POSITIONS = {
    "Loosehead Prop",
    "Hooker",
    "Tighthead Prop",
    "Lock",
    "Blindside Flanker",
    "Openside Flanker",
    "Number 8",
}
BACK_POSITIONS = {"Scrumhalf", "Flyhalf", "Inside Centre", "Outside Centre", "Wing", "Fullback"}


def _round_to_offer(value: float) -> int:
    return max(1_000, int(round(value / 500.0) * 500))


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def _active_listing_for_player(session: Session, save: SaveGame, player_id: int) -> TransferListing | None:
    return session.exec(
        select(TransferListing)
        .where(TransferListing.save_game_id == save.id)
        .where(TransferListing.season_number == save.season_number)
        .where(TransferListing.player_id == player_id)
        .where(TransferListing.is_active.is_(True))
        .order_by(TransferListing.id.desc())
    ).first()


def _active_targets(session: Session, save: SaveGame) -> list[RecruitmentTarget]:
    return session.exec(
        select(RecruitmentTarget)
        .where(RecruitmentTarget.save_game_id == save.id)
        .where(RecruitmentTarget.season_number == save.season_number)
        .where(RecruitmentTarget.status == "active")
    ).all()


def _target_by_player(session: Session, save: SaveGame, player_id: int) -> RecruitmentTarget | None:
    return session.exec(
        select(RecruitmentTarget)
        .where(RecruitmentTarget.save_game_id == save.id)
        .where(RecruitmentTarget.season_number == save.season_number)
        .where(RecruitmentTarget.player_id == player_id)
        .order_by(RecruitmentTarget.id.desc())
    ).first()


def _ensure_target(session: Session, save: SaveGame, player_id: int) -> tuple[RecruitmentTarget, TransferListing]:
    listing = _active_listing_for_player(session, save, player_id)
    if not listing:
        raise HTTPException(status_code=404, detail="That player is not currently available on the recruitment market.")

    target = _target_by_player(session, save, player_id)
    if target:
        target.listing_id = listing.id
        target.status = "active"
        target.updated_at = datetime.now(timezone.utc)
        session.add(target)
        return target, listing

    target = RecruitmentTarget(
        save_game_id=save.id,
        season_number=save.season_number,
        player_id=player_id,
        listing_id=listing.id,
        weeks_scouted=0,
        shortlisted=False,
        status="active",
    )
    session.add(target)
    session.flush()
    return target, listing


def _player_team_name(session: Session, player: Player) -> str:
    if player.team_id is None:
        return "Free Agent"
    team = session.get(Team, player.team_id)
    return team.name if team else "Free Agent"


def _fit_score(player: Player, squad: list[Player], tactics: TeamTactics) -> int:
    same_position = [candidate for candidate in squad if candidate.primary_position == player.primary_position]
    position_best = max((candidate.overall_rating for candidate in same_position), default=0)
    position_depth = len(same_position)
    position_target = ROSTER_TEMPLATE.get(player.primary_position, 2)

    score = 54
    score += (player.overall_rating - position_best) * 4
    score += max(0, position_target - position_depth) * 5
    score += min(8, max(0, player.potential - player.overall_rating))

    if player.primary_position in FORWARD_POSITIONS and tactics.attacking_style == "forward-oriented":
        score += 7
    if player.primary_position in BACK_POSITIONS and tactics.attacking_style == "expansive":
        score += 7
    if player.primary_position in {"Loosehead Prop", "Hooker", "Tighthead Prop", "Lock"} and tactics.set_piece_intent == "aggressive":
        score += 7
    if player.primary_position in {"Blindside Flanker", "Openside Flanker", "Number 8"} and tactics.ruck_commitment == "high":
        score += 5
    if player.primary_position in {"Scrumhalf", "Flyhalf", "Fullback"} and tactics.kicking_approach == "high":
        score += 4

    if player.age <= 24:
        score += 4
    elif player.age >= 32:
        score -= 4
    if player.injury_weeks_remaining > 0:
        score -= 10

    return _clamp(score, 28, 92)


def _fit_label(score: int) -> str:
    if score >= 76:
        return "Strong fit"
    if score >= 62:
        return "Useful fit"
    if score >= 48:
        return "Depth fit"
    return "Poor fit"


def _risk_label(player: Player) -> str:
    if player.injury_weeks_remaining > 0 or player.age >= 34 or player.morale <= 50:
        return "High"
    if player.age >= 30 or player.morale <= 62:
        return "Moderate"
    return "Low"


def _contract_hint(player: Player, *, exact: bool) -> str:
    if exact:
        return f"{player.contract_years_remaining} year(s) remaining"
    if player.contract_years_remaining <= 1:
        return "Deal running down"
    if player.contract_years_remaining <= 3:
        return "Mid-term deal"
    return "Long-term deal"


def _estimate_range(actual: int, weeks_scouted: int, *, value_type: str) -> tuple[int, int] | None:
    if weeks_scouted <= 0:
        return None

    if value_type == "transfer":
        spread = 0.25 if weeks_scouted == 1 else 0.12 if weeks_scouted == 2 else 0.0
    elif value_type == "wage":
        spread = 0.18 if weeks_scouted == 1 else 0.08 if weeks_scouted == 2 else 0.0
    else:
        spread = 0.0

    if spread == 0.0:
        rounded = _round_to_offer(actual)
        return rounded, rounded

    return _round_to_offer(actual * (1 - spread)), _round_to_offer(actual * (1 + spread))


def _potential_range(player: Player, weeks_scouted: int) -> tuple[int, int] | None:
    if weeks_scouted <= 0:
        return None
    if weeks_scouted == 1:
        return max(player.overall_rating, player.potential - 6), min(95, player.potential + 6)
    if weeks_scouted == 2:
        return max(player.overall_rating, player.potential - 3), min(95, player.potential + 3)
    return player.potential, player.potential


def _report_stage(weeks_scouted: int) -> str:
    if weeks_scouted <= 0:
        return "unscouted"
    if weeks_scouted == 1:
        return "regional"
    if weeks_scouted == 2:
        return "detailed"
    return "complete"


def _recommendation(player: Player, listing: TransferListing, fit_score: int, weeks_scouted: int) -> str | None:
    if weeks_scouted < 2:
        return None
    if fit_score >= 74 and listing.asking_price <= player.transfer_value:
        return "Move early"
    if fit_score >= 62 and listing.asking_price <= int(player.transfer_value * 1.1):
        return "Shortlist"
    if fit_score >= 52:
        return "Monitor price"
    return "Depth option"


def _scouting_report(player: Player, listing: TransferListing, target: RecruitmentTarget | None, squad: list[Player], tactics: TeamTactics) -> ScoutingReportRead:
    weeks_scouted = min(target.weeks_scouted if target else 0, SCOUTING_WEEKS_TO_COMPLETE)
    if weeks_scouted <= 0:
        return ScoutingReportRead(
            stage="unscouted",
            weeks_scouted=0,
            weeks_to_complete=SCOUTING_WEEKS_TO_COMPLETE,
        )

    fit_score = _fit_score(player, squad, tactics)
    value_range = _estimate_range(player.transfer_value, weeks_scouted, value_type="transfer")
    wage_expectation = _round_to_offer(player.wage * (1.05 + max(0, player.overall_rating - 72) / 200))
    wage_range = _estimate_range(wage_expectation, weeks_scouted, value_type="wage")
    potential_range = _potential_range(player, weeks_scouted)

    return ScoutingReportRead(
        stage=_report_stage(weeks_scouted),
        weeks_scouted=weeks_scouted,
        weeks_to_complete=max(0, SCOUTING_WEEKS_TO_COMPLETE - weeks_scouted),
        fit_score=fit_score,
        fit_label=_fit_label(fit_score),
        risk_label=_risk_label(player),
        estimated_value_low=value_range[0] if value_range else None,
        estimated_value_high=value_range[1] if value_range else None,
        estimated_weekly_wage_low=wage_range[0] if wage_range else None,
        estimated_weekly_wage_high=wage_range[1] if wage_range else None,
        potential_low=potential_range[0] if potential_range else None,
        potential_high=potential_range[1] if potential_range else None,
        contract_years_hint=_contract_hint(player, exact=weeks_scouted >= SCOUTING_WEEKS_TO_COMPLETE),
        recommendation=_recommendation(player, listing, fit_score, weeks_scouted),
    )


def _listing_read(
    session: Session,
    player: Player,
    listing: TransferListing,
    target: RecruitmentTarget | None,
    squad: list[Player],
    tactics: TeamTactics,
) -> RecruitmentListingRead:
    return RecruitmentListingRead(
        listing_id=listing.id,
        player_id=player.id,
        player_name=f"{player.first_name} {player.last_name}",
        current_team=_player_team_name(session, player),
        is_free_agent=player.team_id is None,
        primary_position=player.primary_position,
        overall_rating=player.overall_rating,
        age=player.age,
        asking_price=listing.asking_price,
        shortlisted=target.shortlisted if target else False,
        scouting=_scouting_report(player, listing, target, squad, tactics),
    )


def _contract_profile(player: Player, team: Team, squad: list[Player]) -> ContractWatchPlayerRead:
    ranked = sorted(squad, key=lambda candidate: candidate.overall_rating, reverse=True)
    rank = next((index for index, candidate in enumerate(ranked, start=1) if candidate.id == player.id), len(ranked))
    if rank <= 8 or player.overall_rating >= team.reputation + 1:
        retention_priority = "Core"
    elif rank <= 18 or player.overall_rating >= team.reputation - 4:
        retention_priority = "Important"
    else:
        retention_priority = "Depth"

    if player.age <= 24 and player.potential >= player.overall_rating + 5:
        desired_years = 4
    elif player.age <= 29:
        desired_years = 3
    elif player.age <= 33:
        desired_years = 2
    else:
        desired_years = 1

    minimum_years = max(1, desired_years - 1)

    wage_multiplier = 1.03
    if player.contract_years_remaining <= 1:
        wage_multiplier += 0.02
    if retention_priority == "Core":
        wage_multiplier += 0.03
    elif retention_priority == "Important":
        wage_multiplier += 0.015
    if player.overall_rating >= team.reputation:
        wage_multiplier += 0.01
    if player.morale < 62:
        wage_multiplier += 0.01
    if player.age >= 33:
        wage_multiplier -= 0.01
    wage_multiplier = max(1.03, min(1.14, wage_multiplier))

    desired_weekly_wage = _round_to_offer(player.wage * wage_multiplier)
    recommended_max_wage = _round_to_offer(desired_weekly_wage * (1.08 if retention_priority == "Core" else 1.05))

    if player.morale >= 78:
        willingness = "Keen to stay"
    elif player.morale >= 62:
        willingness = "Open to renew"
    else:
        willingness = "Needs convincing"

    return ContractWatchPlayerRead(
        player_id=player.id,
        player_name=f"{player.first_name} {player.last_name}",
        primary_position=player.primary_position,
        overall_rating=player.overall_rating,
        age=player.age,
        contract_years_remaining=player.contract_years_remaining,
        current_wage=player.wage,
        desired_years=desired_years,
        minimum_years=minimum_years,
        desired_weekly_wage=desired_weekly_wage,
        recommended_max_wage=recommended_max_wage,
        retention_priority=retention_priority,
        willingness=willingness,
        morale=player.morale,
    )


def build_contract_watch(session: Session, save: SaveGame | None = None) -> list[ContractWatchPlayerRead]:
    save = save or get_active_save(session)
    user_team = get_user_team(session, save)
    squad = session.exec(select(Player).where(Player.team_id == user_team.id).order_by(Player.overall_rating.desc())).all()
    watch = [
        _contract_profile(player, user_team, squad)
        for player in squad
        if player.contract_years_remaining <= 2
    ]
    priority_order = {"Core": 0, "Important": 1, "Depth": 2}
    return sorted(
        watch,
        key=lambda item: (priority_order[item.retention_priority], item.contract_years_remaining, -item.overall_rating),
    )


def get_contract_watch_player(session: Session, player_id: int, save: SaveGame | None = None) -> ContractWatchPlayerRead:
    save = save or get_active_save(session)
    watch = build_contract_watch(session, save)
    for candidate in watch:
        if candidate.player_id == player_id:
            return candidate
    raise HTTPException(status_code=404, detail="Contract profile not found for that player.")


def get_recruitment_board(session: Session) -> RecruitmentResponse:
    save = get_active_save(session)
    user_team = get_user_team(session, save)
    squad = session.exec(select(Player).where(Player.team_id == user_team.id).order_by(Player.overall_rating.desc())).all()
    tactics = session.exec(select(TeamTactics).where(TeamTactics.team_id == user_team.id)).first()
    listings = session.exec(
        select(TransferListing)
        .where(TransferListing.save_game_id == save.id)
        .where(TransferListing.season_number == save.season_number)
        .where(TransferListing.is_active.is_(True))
        .order_by(TransferListing.asking_price.desc(), TransferListing.id.desc())
    ).all()
    targets = {
        target.player_id: target
        for target in _active_targets(session, save)
    }

    market: list[RecruitmentListingRead] = []
    for listing in listings:
        player = session.get(Player, listing.player_id)
        if not player or player.team_id == user_team.id:
            continue
        market.append(_listing_read(session, player, listing, targets.get(player.id), squad, tactics))

    shortlist = sorted(
        [listing for listing in market if listing.shortlisted],
        key=lambda listing: (
            listing.scouting.fit_score is None,
            -(listing.scouting.fit_score or 0),
            -listing.overall_rating,
        ),
    )
    summary = RecruitmentSummaryRead(
        active_reports=sum(
            1
            for target in targets.values()
            if target.status == "active" and target.weeks_scouted < SCOUTING_WEEKS_TO_COMPLETE
        ),
        completed_reports=sum(
            1
            for target in targets.values()
            if target.status == "active" and target.weeks_scouted >= SCOUTING_WEEKS_TO_COMPLETE
        ),
        shortlisted_targets=sum(1 for target in targets.values() if target.status == "active" and target.shortlisted),
        max_active_reports=MAX_ACTIVE_REPORTS,
    )
    current_wages = sum(player.wage for player in squad)
    return RecruitmentResponse(
        market=market,
        shortlist=shortlist,
        contract_watch=build_contract_watch(session, save),
        summary=summary,
        budget=user_team.budget,
        wage_budget=user_team.wage_budget,
        current_wages=current_wages,
    )


def start_scouting_target(session: Session, player_id: int) -> dict[str, str]:
    save = get_active_save(session)
    existing_target = _target_by_player(session, save, player_id)
    if not existing_target:
        active_reports = [
            candidate
            for candidate in _active_targets(session, save)
            if candidate.weeks_scouted < SCOUTING_WEEKS_TO_COMPLETE
        ]
        if len(active_reports) >= MAX_ACTIVE_REPORTS:
            raise HTTPException(
                status_code=400,
                detail=f"Your recruitment team can only handle {MAX_ACTIVE_REPORTS} active reports at once.",
            )

    target, _ = _ensure_target(session, save, player_id)

    target.status = "active"
    target.updated_at = datetime.now(timezone.utc)
    session.add(target)
    session.commit()

    if target.weeks_scouted >= SCOUTING_WEEKS_TO_COMPLETE:
        return {"status": "complete", "message": "That scouting report is already complete."}
    return {"status": "assigned", "message": "Scouting assignment added to the weekly recruitment queue."}


def toggle_shortlist_target(session: Session, player_id: int) -> dict[str, str]:
    save = get_active_save(session)
    target, _ = _ensure_target(session, save, player_id)
    target.shortlisted = not target.shortlisted
    target.updated_at = datetime.now(timezone.utc)
    session.add(target)
    session.commit()
    return {
        "status": "updated",
        "message": "Player added to shortlist." if target.shortlisted else "Player removed from shortlist.",
    }


def progress_scouting_targets(session: Session, save: SaveGame | None = None) -> None:
    save = save or get_active_save(session)
    for target in _active_targets(session, save):
        if target.weeks_scouted >= SCOUTING_WEEKS_TO_COMPLETE:
            continue
        if not _active_listing_for_player(session, save, target.player_id):
            target.status = "closed"
            target.updated_at = datetime.now(timezone.utc)
            session.add(target)
            continue
        target.weeks_scouted += 1
        target.updated_at = datetime.now(timezone.utc)
        session.add(target)


def close_recruitment_target(session: Session, save: SaveGame, player_id: int, *, status: str = "closed") -> None:
    target = _target_by_player(session, save, player_id)
    if not target:
        return
    target.status = status
    target.updated_at = datetime.now(timezone.utc)
    session.add(target)
