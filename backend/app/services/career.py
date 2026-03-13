from __future__ import annotations

import random
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from backend.app.core.constants import ATTRIBUTE_NAMES, POSITION_PROFILES, POSITIONS, SECONDARY_POSITION_MAP
from backend.app.models.entities import (
    Fixture,
    InboxMessage,
    League,
    MatchResult,
    Player,
    SaveGame,
    Team,
    TeamSeasonSummary,
    TeamSelection,
    TransferListing,
    YouthProspect,
)
from backend.app.schemas.api import SaveSummary
from backend.app.seed.generator import (
    REGION_POOLS,
    TEAM_REGION_ROTATION,
    _player_name,
    _position_variation,
    create_transfer_listings_for_season,
)
from backend.app.services.finance import apply_season_review_finance, ensure_board_state
from backend.app.services.performance import ensure_weekly_performance_plan
from backend.app.services.game import (
    build_save_summary,
    build_table,
    get_active_save,
    get_user_team,
)
from backend.app.services.ratings import compute_overall
from backend.app.services.selection import build_best_selection


OBJECTIVES_BY_RANK = [
    "Win the title",
    "Finish in the top three",
    "Finish in the top three",
    "Reach the top half",
    "Reach the top half",
    "Stabilise in the top half",
    "Avoid the bottom three",
    "Avoid the bottom three",
    "Avoid finishing last",
    "Avoid finishing last",
]


def next_season_label(current_label: str) -> str:
    start_year = int(current_label.split("/")[0])
    next_year = start_year + 1
    return f"{next_year}/{str((next_year + 1) % 100).zfill(2)}"


def _expected_finish_order(teams: list[Team]) -> dict[int, int]:
    ordered = sorted(teams, key=lambda team: team.reputation, reverse=True)
    return {team.id: index for index, team in enumerate(ordered, start=1)}


def _board_outcome(final_position: int, expected_position: int) -> tuple[str, int, int]:
    delta = expected_position - final_position
    if delta >= 3:
        return "Outstanding season", 1_300_000, 240_000
    if delta >= 1:
        return "Board pleased", 700_000, 120_000
    if delta == 0:
        return "Objective met", 250_000, 40_000
    if delta >= -2:
        return "Below expectations", -350_000, -60_000
    return "Major disappointment", -800_000, -140_000


def _next_objective_for_team(teams: list[Team], team: Team) -> str:
    expected = _expected_finish_order(teams)[team.id]
    return OBJECTIVES_BY_RANK[min(len(OBJECTIVES_BY_RANK) - 1, expected - 1)]


def _mark_retirements(session: Session, save: SaveGame, user_team_id: int) -> list[str]:
    rng = random.Random(save.id * 1_009 + save.season_number * 97)
    retirements: list[str] = []
    players = session.exec(select(Player).where(Player.save_game_id == save.id).where(Player.team_id.is_not(None))).all()
    for player in players:
        risk = 0.0
        if player.age >= 37:
            risk = 0.95
        elif player.age >= 35:
            risk = 0.28 + max(0, player.injury_weeks_remaining) * 0.05
        elif player.age >= 34 and player.overall_rating < 72:
            risk = 0.16
        if rng.random() < risk:
            player.retiring_after_season = True
            session.add(player)
            if player.team_id == user_team_id:
                name = f"{player.first_name} {player.last_name}"
                retirements.append(name)
                session.add(
                    InboxMessage(
                        save_game_id=save.id,
                        season_number=save.season_number,
                        team_id=user_team_id,
                        type="retirement",
                        title=f"Retirement: {name}",
                        body=f"{name} has informed the club that this was the final season of his career.",
                        related_player_id=player.id,
                        created_at=datetime.now(timezone.utc),
                    )
                )
    return retirements


def enter_season_review(session: Session) -> SaveSummary:
    save = get_active_save(session)
    if save.phase != "in_season":
        return build_save_summary(session, save)

    table = build_table(session, save, save.season_number)
    teams = session.exec(select(Team).where(Team.save_game_id == save.id)).all()
    expected_positions = _expected_finish_order(teams)
    user_team = get_user_team(session, save)

    existing = session.exec(
        select(TeamSeasonSummary)
        .where(TeamSeasonSummary.save_game_id == save.id)
        .where(TeamSeasonSummary.season_number == save.season_number)
    ).all()
    if existing:
        save.phase = "season_review"
        save.offseason_step = "review"
        session.add(save)
        session.commit()
        session.refresh(save)
        return build_save_summary(session, save)

    retirement_names = _mark_retirements(session, save, user_team.id)
    rows_by_team = {row.team_id: row for row in table.rows}
    for row in table.rows:
        team = next(team for team in teams if team.id == row.team_id)
        previous_objective = team.board_objective
        verdict, budget_delta, wage_delta = _board_outcome(row.position, expected_positions[team.id])
        if team.id == user_team.id:
            apply_season_review_finance(
                session,
                save,
                team,
                verdict=verdict,
                budget_delta=budget_delta,
                final_position=row.position,
            )
        else:
            team.budget = max(2_000_000, team.budget + budget_delta)
        team.wage_budget = max(1_500_000, team.wage_budget + wage_delta)
        team.board_objective = _next_objective_for_team(teams, team)
        session.add(team)
        session.add(
            TeamSeasonSummary(
                save_game_id=save.id,
                team_id=team.id,
                season_number=save.season_number,
                season_label=save.season_label,
                final_position=row.position,
                played=row.played,
                wins=row.wins,
                draws=row.draws,
                losses=row.losses,
                points_for=row.points_for,
                points_against=row.points_against,
                points_difference=row.points_difference,
                table_points=row.table_points,
                board_objective=previous_objective,
                board_verdict=verdict,
                budget_delta=budget_delta,
            )
        )
        if team.id == user_team.id:
            session.add(
                InboxMessage(
                    save_game_id=save.id,
                    season_number=save.season_number,
                    team_id=user_team.id,
                    type="board",
                    title=f"Season review: {verdict}",
                    body=(
                        f"You finished {row.position} in {save.league_name}. "
                        f"Next season's board objective is now '{team.board_objective}'."
                    ),
                    created_at=datetime.now(timezone.utc),
                )
            )

    save.current_week = save.total_weeks
    save.phase = "season_review"
    save.offseason_step = "review"
    save.updated_at = datetime.now(timezone.utc)
    session.add(save)
    session.commit()
    session.refresh(save)
    return build_save_summary(session, save)


def _auto_renew_ai_contracts(session: Session, save: SaveGame, user_team_id: int) -> None:
    teams = session.exec(select(Team).where(Team.save_game_id == save.id)).all()
    for team in teams:
        if team.id == user_team_id:
            continue
        squad = session.exec(select(Player).where(Player.team_id == team.id)).all()
        for player in [candidate for candidate in squad if candidate.contract_years_remaining <= 1]:
            should_renew = (
                player.overall_rating >= team.reputation - 4
                or player.potential >= player.overall_rating + 6
                or len([candidate for candidate in squad if candidate.primary_position == player.primary_position]) <= 2
            )
            if should_renew:
                player.contract_years_remaining = 2 + (1 if player.age < 28 else 0)
                player.wage = int(player.wage * 1.06)
                player.contract_last_renewed_season = save.season_number
                player.morale = min(99, player.morale + 5)
                session.add(player)
            else:
                player.team_id = None
                player.morale = max(45, player.morale - 4)
                session.add(player)


def _generate_youth_for_team(save: SaveGame, team: Team, team_index: int, count: int) -> list[YouthProspect]:
    rng = random.Random(save.id * 2_003 + save.season_number * 131 + team.id * 17)
    prospects: list[YouthProspect] = []
    region_rotation = TEAM_REGION_ROTATION[team_index]
    for index in range(count):
        region = region_rotation[index % len(region_rotation)]
        first_name, last_name = _player_name(region, team_index, 40 + index)
        position = POSITIONS[(team_index + index * 2) % len(POSITIONS)]
        attributes = _position_variation(position, team.reputation - 6, rng)
        prospect = YouthProspect(
            save_game_id=save.id,
            team_id=team.id,
            season_number=save.season_number,
            first_name=first_name,
            last_name=last_name,
            nationality=region,
            age=17 + (index % 2),
            primary_position=position,
            secondary_positions=SECONDARY_POSITION_MAP[position][:1],
            overall_rating=max(52, min(76, team.reputation - 10 + rng.randint(-4, 5))),
            potential=max(65, min(92, team.reputation + rng.randint(2, 12))),
            readiness=max(48, min(88, team.reputation - 4 + rng.randint(-6, 8))),
            wage=max(1_000, 900 + rng.randint(0, 500)),
            **attributes,
        )
        prospects.append(prospect)
    return prospects


def _ensure_youth_intake(session: Session, save: SaveGame) -> None:
    existing = session.exec(
        select(YouthProspect).where(YouthProspect.save_game_id == save.id).where(YouthProspect.season_number == save.season_number)
    ).all()
    if existing:
        return
    teams = session.exec(select(Team).where(Team.save_game_id == save.id).order_by(Team.id)).all()
    for team_index, team in enumerate(teams):
        count = 5 if team.is_user_team else 4
        for prospect in _generate_youth_for_team(save, team, team_index, count):
            session.add(prospect)


def _adjust_attributes_for_development(player: Player, team: Team | None, rng: random.Random) -> None:
    gap = player.potential - player.overall_rating
    staff_boost = 0 if team is None else (team.staff_fitness + team.staff_attack) / 50 - 2.6
    age_penalty = 0
    if player.age >= 32:
        age_penalty = 1.8
    elif player.age >= 29:
        age_penalty = 0.9
    change = round(max(-4, min(4, gap / 9 + (player.form - 65) / 18 + staff_boost - age_penalty)))
    profile = POSITION_PROFILES[player.primary_position]
    key_attributes = [attr for attr in ATTRIBUTE_NAMES if getattr(profile, attr) >= 60]
    for attr in ATTRIBUTE_NAMES:
        weight = 1.0 if attr in key_attributes else 0.5
        attr_delta = round(change * weight / 2)
        noise = rng.choice([-1, 0, 0, 1])
        setattr(player, attr, max(25, min(95, getattr(player, attr) + attr_delta + noise)))
    player.overall_rating = compute_overall(player)
    player.transfer_value = max(45_000, int(player.overall_rating * 12_500 + player.potential * 3_400 - player.age * 4_200))


def _apply_annual_player_updates(session: Session, save: SaveGame) -> None:
    teams = {team.id: team for team in session.exec(select(Team).where(Team.save_game_id == save.id)).all()}
    rng = random.Random(save.id * 3_031 + save.season_number * 181)
    players = session.exec(select(Player).where(Player.save_game_id == save.id)).all()
    for player in players:
        if player.retiring_after_season:
            session.delete(player)
            continue
        player.age += 1
        if player.contract_years_remaining <= 1 and player.contract_last_renewed_season != save.season_number:
            player.team_id = None
        elif player.contract_last_renewed_season != save.season_number:
            player.contract_years_remaining = max(1, player.contract_years_remaining - 1)
        player.contract_last_renewed_season = 0
        player.retiring_after_season = False
        player.morale = max(45, min(90, player.morale + rng.randint(-2, 3)))
        player.form = max(50, min(85, 62 + rng.randint(-6, 6)))
        player.fitness = max(72, min(96, player.fitness + rng.randint(-2, 3)))
        player.fatigue = max(0, player.fatigue - 10)
        team = teams.get(player.team_id) if player.team_id else None
        _adjust_attributes_for_development(player, team, rng)
        session.add(player)


def _auto_promote_ai_prospects(session: Session, save: SaveGame, user_team_id: int) -> None:
    teams = session.exec(select(Team).where(Team.save_game_id == save.id)).all()
    for team in teams:
        squad = session.exec(select(Player).where(Player.team_id == team.id)).all()
        prospects = session.exec(
            select(YouthProspect)
            .where(YouthProspect.team_id == team.id)
            .where(YouthProspect.season_number == save.season_number)
            .where(YouthProspect.promoted.is_(False))
            .order_by(YouthProspect.readiness.desc(), YouthProspect.potential.desc())
        ).all()
        minimum_squad_size = 30 if team.id == user_team_id else 31
        while len(squad) < minimum_squad_size and prospects:
            prospect = prospects.pop(0)
            _promote_prospect_to_player(session, save, prospect)
            squad.append(session.exec(select(Player).where(Player.team_id == team.id).order_by(Player.id.desc())).first())


def _repair_all_selections(session: Session, save: SaveGame) -> None:
    teams = session.exec(select(Team).where(Team.save_game_id == save.id)).all()
    for team in teams:
        players = session.exec(select(Player).where(Player.team_id == team.id)).all()
        selection = session.exec(select(TeamSelection).where(TeamSelection.team_id == team.id)).first()
        best = build_best_selection(players)
        selection.starting_lineup = [slot.model_dump() for slot in best.starting_lineup]
        selection.bench_player_ids = best.bench_player_ids
        selection.captain_id = best.captain_id
        selection.goal_kicker_id = best.goal_kicker_id
        session.add(selection)


def _generate_fixtures_for_new_season(session: Session, save: SaveGame) -> None:
    league = session.exec(select(League).where(League.save_game_id == save.id)).first()
    teams = session.exec(select(Team).where(Team.save_game_id == save.id).order_by(Team.id)).all()
    team_ids = [team.id for team in teams]
    rounds: list[list[tuple[int, int]]] = []
    rotation = team_ids[:]
    for round_index in range(len(rotation) - 1):
        pairings: list[tuple[int, int]] = []
        for index in range(len(rotation) // 2):
            home = rotation[index]
            away = rotation[-(index + 1)]
            pairings.append((home, away) if round_index % 2 == 0 else (away, home))
        rounds.append(pairings)
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    schedule = rounds + [[(away, home) for home, away in pairings] for pairings in rounds]
    for week, pairings in enumerate(schedule, start=1):
        for home_team_id, away_team_id in pairings:
            session.add(
                Fixture(
                    save_game_id=save.id,
                    league_id=league.id,
                    season_number=save.season_number,
                    week=week,
                    round_name=f"Round {week}",
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                )
            )


def _promote_prospect_to_player(session: Session, save: SaveGame, prospect: YouthProspect) -> Player:
    player = Player(
        save_game_id=save.id,
        team_id=prospect.team_id,
        first_name=prospect.first_name,
        last_name=prospect.last_name,
        nationality=prospect.nationality,
        age=prospect.age,
        primary_position=prospect.primary_position,
        secondary_positions=prospect.secondary_positions,
        overall_rating=prospect.overall_rating,
        potential=prospect.potential,
        wage=prospect.wage,
        contract_years_remaining=3,
        contract_last_renewed_season=save.season_number,
        morale=72,
        fitness=88,
        fatigue=6,
        form=64,
        injury_status="Healthy",
        injury_weeks_remaining=0,
        suspended_matches=0,
        retiring_after_season=False,
        transfer_value=max(35_000, int(prospect.overall_rating * 10_500 + prospect.potential * 2_800)),
        speed=prospect.speed,
        strength=prospect.strength,
        endurance=prospect.endurance,
        handling=prospect.handling,
        passing=prospect.passing,
        tackling=prospect.tackling,
        kicking_hand=prospect.kicking_hand,
        goal_kicking=prospect.goal_kicking,
        breakdown=prospect.breakdown,
        scrum=prospect.scrum,
        lineout=prospect.lineout,
        decision_making=prospect.decision_making,
        composure=prospect.composure,
        discipline=prospect.discipline,
        leadership=prospect.leadership,
    )
    session.add(player)
    prospect.promoted = True
    session.add(prospect)
    return player


def promote_youth_prospect(session: Session, prospect_id: int) -> dict[str, str]:
    save = get_active_save(session)
    user_team = get_user_team(session, save)
    if save.phase == "in_season":
        raise HTTPException(status_code=400, detail="Youth promotions are only available during the offseason.")
    prospect = session.exec(
        select(YouthProspect)
        .where(YouthProspect.id == prospect_id)
        .where(YouthProspect.team_id == user_team.id)
        .where(YouthProspect.season_number == save.season_number)
        .where(YouthProspect.promoted.is_(False))
    ).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Youth prospect not found.")
    player = _promote_prospect_to_player(session, save, prospect)
    session.add(
        InboxMessage(
            save_game_id=save.id,
            season_number=save.season_number,
            team_id=user_team.id,
            type="academy",
            title=f"Academy promotion: {player.first_name} {player.last_name}",
            body=f"{player.first_name} {player.last_name} has been promoted to the senior squad.",
            related_player_id=player.id,
            created_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    return {"status": "accepted", "message": f"Promoted {player.first_name} {player.last_name} to the senior squad."}


def advance_offseason(session: Session) -> SaveSummary:
    save = get_active_save(session)
    user_team = get_user_team(session, save)
    if save.phase == "in_season":
        raise HTTPException(status_code=400, detail="The club is still in-season.")

    if save.phase == "season_review" and save.offseason_step == "review":
        save.phase = "offseason"
        save.offseason_step = "contracts"
        session.add(save)
        session.commit()
        session.refresh(save)
        return build_save_summary(session, save)

    if save.phase == "offseason" and save.offseason_step == "contracts":
        _auto_renew_ai_contracts(session, save, user_team.id)
        _ensure_youth_intake(session, save)
        save.offseason_step = "youth_intake"
        save.updated_at = datetime.now(timezone.utc)
        session.add(save)
        session.commit()
        session.refresh(save)
        return build_save_summary(session, save)

    if save.phase == "offseason" and save.offseason_step == "youth_intake":
        save.offseason_step = "rollover"
        save.updated_at = datetime.now(timezone.utc)
        session.add(save)
        session.commit()
        session.refresh(save)
        return build_save_summary(session, save)

    if save.phase == "offseason" and save.offseason_step == "rollover":
        _apply_annual_player_updates(session, save)
        _auto_promote_ai_prospects(session, save, user_team.id)
        session.exec(
            select(TransferListing).where(TransferListing.save_game_id == save.id).where(TransferListing.is_active.is_(True))
        ).all()
        active_listings = session.exec(
            select(TransferListing).where(TransferListing.save_game_id == save.id).where(TransferListing.is_active.is_(True))
        ).all()
        for listing in active_listings:
            listing.is_active = False
            session.add(listing)

        save.season_number += 1
        save.season_label = next_season_label(save.season_label)
        save.current_week = 1
        save.phase = "in_season"
        save.offseason_step = "review"
        save.updated_at = datetime.now(timezone.utc)
        league = session.exec(select(League).where(League.save_game_id == save.id)).first()
        league.season_label = save.season_label
        league.current_week = 1
        session.add(league)
        session.add(save)
        _generate_fixtures_for_new_season(session, save)
        create_transfer_listings_for_season(session, save.id, save.season_number, user_team.id)
        _repair_all_selections(session, save)
        refreshed_user_team = get_user_team(session, save)
        ensure_board_state(session, save, refreshed_user_team)
        ensure_weekly_performance_plan(session, save, refreshed_user_team)
        session.add(
            InboxMessage(
                save_game_id=save.id,
                season_number=save.season_number,
                team_id=refreshed_user_team.id,
                type="board",
                title=f"New season ready: {save.season_label}",
                body=f"The board now expects {refreshed_user_team.name} to {refreshed_user_team.board_objective.lower()}.",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        session.refresh(save)
        return build_save_summary(session, save)

    raise HTTPException(status_code=400, detail="Offseason state is invalid.")
