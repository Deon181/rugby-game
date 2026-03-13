from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlmodel import Session, select

from backend.app.core.constants import ATTRIBUTE_NAMES, TACTIC_VALUES, TRAINING_FOCUSES
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
    TeamTactics,
    TransferListing,
    YouthProspect,
)
from backend.app.schemas.api import (
    ClubOption,
    DashboardResponse,
    FixtureDetail,
    FixtureListResponse,
    FixtureResultRead,
    InboxMessageRead,
    InboxResponse,
    MatchResultRead,
    NewSaveFeaturedPlayer,
    NewSaveOnboarding,
    NewSaveResponse,
    NewSaveSquadSummary,
    OffseasonStatusResponse,
    SaveSummary,
    SeasonHistoryResponse,
    SeasonHistoryRow,
    SeasonReviewResponse,
    SelectionRead,
    SelectionSlotRead,
    SelectionUpdateRequest,
    SquadPlayerRead,
    SquadResponse,
    TableResponse,
    TacticsRead,
    TacticsUpdateRequest,
    TeamOverviewRead,
    TransferListResponse,
    YouthIntakeResponse,
    YouthProspectRead,
)
from backend.app.seed.generator import create_save_world, list_club_options
from backend.app.services.ratings import compute_derived_ratings
from backend.app.services.selection import SelectionValidationError, validate_selection


def get_active_save(session: Session) -> SaveGame:
    save = session.exec(select(SaveGame).where(SaveGame.active.is_(True)).order_by(SaveGame.id.desc())).first()
    if not save:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active save found.")
    return save


def get_active_save_optional(session: Session) -> SaveGame | None:
    return session.exec(select(SaveGame).where(SaveGame.active.is_(True)).order_by(SaveGame.id.desc())).first()


def get_user_team(session: Session, save: SaveGame) -> Team:
    team = session.get(Team, save.user_team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User team not found.")
    return team


def get_league(session: Session, save: SaveGame) -> League:
    league = session.exec(select(League).where(League.save_game_id == save.id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found.")
    return league


def build_save_summary(session: Session, save: SaveGame) -> SaveSummary:
    team = get_user_team(session, save)
    return SaveSummary(
        id=save.id,
        league_name=save.league_name,
        season_label=save.season_label,
        season_number=save.season_number,
        current_week=save.current_week,
        total_weeks=save.total_weeks,
        phase=save.phase,
        offseason_step=save.offseason_step,
        user_team_id=team.id,
        user_team_name=team.name,
    )


def serialize_team(team: Team) -> TeamOverviewRead:
    return TeamOverviewRead(
        id=team.id,
        name=team.name,
        short_name=team.short_name,
        reputation=team.reputation,
        budget=team.budget,
        wage_budget=team.wage_budget,
        objective=team.board_objective,
        staff_summary={
            "attack": team.staff_attack,
            "defense": team.staff_defense,
            "fitness": team.staff_fitness,
            "set_piece": team.staff_set_piece,
        },
    )


def serialize_player(player: Player) -> SquadPlayerRead:
    return SquadPlayerRead(
        id=player.id,
        name=f"{player.first_name} {player.last_name}",
        age=player.age,
        nationality=player.nationality,
        primary_position=player.primary_position,
        secondary_positions=player.secondary_positions,
        overall_rating=player.overall_rating,
        potential=player.potential,
        wage=player.wage,
        contract_years_remaining=player.contract_years_remaining,
        morale=player.morale,
        fitness=player.fitness,
        fatigue=player.fatigue,
        injury_status=player.injury_status,
        injury_weeks_remaining=player.injury_weeks_remaining,
        form=player.form,
        transfer_value=player.transfer_value,
        attributes={attribute: getattr(player, attribute) for attribute in ATTRIBUTE_NAMES},
        derived_ratings=compute_derived_ratings(player),
        is_free_agent=player.team_id is None,
    )


def serialize_selection(selection: TeamSelection) -> SelectionRead:
    return SelectionRead(
        starting_lineup=[SelectionSlotRead(**entry) for entry in selection.starting_lineup],
        bench_player_ids=selection.bench_player_ids,
        captain_id=selection.captain_id,
        goal_kicker_id=selection.goal_kicker_id,
    )


def serialize_tactics(tactics: TeamTactics) -> TacticsRead:
    return TacticsRead(
        attacking_style=tactics.attacking_style,
        kicking_approach=tactics.kicking_approach,
        defensive_system=tactics.defensive_system,
        ruck_commitment=tactics.ruck_commitment,
        set_piece_intent=tactics.set_piece_intent,
        goal_choice=tactics.goal_choice,
        training_focus=tactics.training_focus,
    )


def serialize_fixture(session: Session, fixture: Fixture) -> FixtureDetail:
    home_team = session.get(Team, fixture.home_team_id)
    away_team = session.get(Team, fixture.away_team_id)
    result = session.get(MatchResult, fixture.result_id) if fixture.result_id else None
    return FixtureDetail(
        id=fixture.id,
        season_number=fixture.season_number,
        week=fixture.week,
        round_name=fixture.round_name,
        home_team_id=home_team.id,
        home_team_name=home_team.name,
        away_team_id=away_team.id,
        away_team_name=away_team.name,
        kickoff_label=fixture.kickoff_label,
        played=fixture.played,
        result=FixtureResultRead(home_score=result.home_score, away_score=result.away_score) if result else None,
    )


def serialize_match_result(session: Session, result: MatchResult) -> MatchResultRead:
    home_team = session.get(Team, result.home_team_id)
    away_team = session.get(Team, result.away_team_id)
    return MatchResultRead(
        fixture_id=result.fixture_id,
        season_number=result.season_number,
        home_team_id=result.home_team_id,
        away_team_id=result.away_team_id,
        home_team_name=home_team.name,
        away_team_name=away_team.name,
        home_score=result.home_score,
        away_score=result.away_score,
        home_tries=result.home_tries,
        away_tries=result.away_tries,
        home_penalties=result.home_penalties,
        away_penalties=result.away_penalties,
        home_conversions=result.home_conversions,
        away_conversions=result.away_conversions,
        summary=result.summary,
        stats=result.stats,
        commentary=result.commentary,
    )


def serialize_inbox_message(message: InboxMessage) -> InboxMessageRead:
    return InboxMessageRead(
        id=message.id,
        type=message.type,
        title=message.title,
        body=message.body,
        related_fixture_id=message.related_fixture_id,
        related_player_id=message.related_player_id,
        created_at=message.created_at,
        is_read=message.is_read,
    )


def serialize_season_history(summary: TeamSeasonSummary) -> SeasonHistoryRow:
    return SeasonHistoryRow(
        season_number=summary.season_number,
        season_label=summary.season_label,
        final_position=summary.final_position,
        played=summary.played,
        wins=summary.wins,
        draws=summary.draws,
        losses=summary.losses,
        points_for=summary.points_for,
        points_against=summary.points_against,
        points_difference=summary.points_difference,
        table_points=summary.table_points,
        board_objective=summary.board_objective,
        board_verdict=summary.board_verdict,
        budget_delta=summary.budget_delta,
    )


def serialize_youth_prospect(prospect: YouthProspect) -> YouthProspectRead:
    return YouthProspectRead(
        id=prospect.id,
        name=f"{prospect.first_name} {prospect.last_name}",
        nationality=prospect.nationality,
        age=prospect.age,
        primary_position=prospect.primary_position,
        secondary_positions=prospect.secondary_positions,
        overall_rating=prospect.overall_rating,
        potential=prospect.potential,
        readiness=prospect.readiness,
        wage=prospect.wage,
        attributes={attribute: getattr(prospect, attribute) for attribute in ATTRIBUTE_NAMES},
    )


def _current_season_filter(save: SaveGame):
    return save.season_number


def _get_next_fixture(session: Session, save: SaveGame, team: Team) -> Fixture | None:
    return session.exec(
        select(Fixture)
        .where(Fixture.save_game_id == save.id)
        .where(Fixture.season_number == _current_season_filter(save))
        .where(or_(Fixture.home_team_id == team.id, Fixture.away_team_id == team.id))
        .where(Fixture.played.is_(False))
        .order_by(Fixture.week, Fixture.id)
    ).first()


def _build_new_save_onboarding(session: Session, save: SaveGame) -> NewSaveOnboarding:
    team = get_user_team(session, save)
    players = session.exec(
        select(Player).where(Player.team_id == team.id).order_by(Player.primary_position, Player.overall_rating.desc(), Player.age)
    ).all()
    selection = session.exec(select(TeamSelection).where(TeamSelection.team_id == team.id)).first()
    featured_player_ids = [
        ("Captain", selection.captain_id),
        ("Primary Kicker", selection.goal_kicker_id),
        ("Star Player", max(players, key=lambda candidate: candidate.overall_rating).id),
        ("Top Prospect", max(players, key=lambda candidate: candidate.potential).id),
    ]
    highlights_by_player_id: dict[int, list[str]] = {}
    for label, player_id in featured_player_ids:
        highlights_by_player_id.setdefault(player_id, [])
        if label not in highlights_by_player_id[player_id]:
            highlights_by_player_id[player_id].append(label)

    position_counts = Counter(player.primary_position for player in players)
    next_fixture = _get_next_fixture(session, save, team)
    player_lookup = {player.id: player for player in players}

    return NewSaveOnboarding(
        team=serialize_team(team),
        squad_summary=NewSaveSquadSummary(
            player_count=len(players),
            average_age=round(sum(player.age for player in players) / len(players)),
            average_overall=round(sum(player.overall_rating for player in players) / len(players)),
            total_wages=sum(player.wage for player in players),
            position_counts=dict(sorted(position_counts.items())),
        ),
        featured_players=[
            NewSaveFeaturedPlayer(
                id=player_lookup[player_id].id,
                name=f"{player_lookup[player_id].first_name} {player_lookup[player_id].last_name}",
                primary_position=player_lookup[player_id].primary_position,
                overall_rating=player_lookup[player_id].overall_rating,
                age=player_lookup[player_id].age,
                highlight=" & ".join(labels),
            )
            for player_id, labels in highlights_by_player_id.items()
        ],
        players=[serialize_player(player) for player in players],
        next_fixture=serialize_fixture(session, next_fixture) if next_fixture else None,
    )


def list_available_clubs() -> list[ClubOption]:
    return list_club_options()


def create_new_save(
    session: Session,
    team_template_id: int,
    name: str,
    club_name: str,
    club_short_name: str,
) -> NewSaveResponse:
    club_options = list_club_options()
    if team_template_id < 1 or team_template_id > len(club_options):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid club choice.")
    name_conflict = {option.name.lower() for option in club_options}
    short_name_conflict = {option.short_name.lower() for option in club_options}
    if club_name.lower() in name_conflict:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Club name must be unique in the league.")
    if club_short_name.lower() in short_name_conflict:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Club short name must be unique in the league.")

    save = create_save_world(
        session,
        chosen_template_team_id=team_template_id,
        save_name=name,
        club_name=club_name,
        club_short_name=club_short_name,
    )
    return NewSaveResponse(save=build_save_summary(session, save), onboarding=_build_new_save_onboarding(session, save))


def _phase_message(save: SaveGame) -> str | None:
    if save.phase == "season_review":
        return "The season has ended. Enter the offseason flow to review the campaign and prepare the next year."
    if save.phase == "offseason":
        return f"The club is in offseason mode. Current step: {save.offseason_step.replace('_', ' ')}."
    return None


def _prepare_in_season_week(session: Session, save: SaveGame) -> SaveGame:
    if save.phase != "in_season":
        return save
    from backend.app.services.progression import apply_between_week_recovery

    if apply_between_week_recovery(session, save):
        session.commit()
        session.refresh(save)
    return save


def get_dashboard(session: Session) -> DashboardResponse:
    save = get_active_save(session)
    save = _prepare_in_season_week(session, save)
    user_team = get_user_team(session, save)
    table = build_table(session, save)
    next_fixture = None
    if save.phase == "in_season":
        next_fixture = _get_next_fixture(session, save, user_team)
    recent_fixtures = session.exec(
        select(Fixture)
        .where(Fixture.save_game_id == save.id)
        .where(Fixture.season_number == _current_season_filter(save))
        .where(or_(Fixture.home_team_id == user_team.id, Fixture.away_team_id == user_team.id))
        .where(Fixture.played.is_(True))
        .order_by(Fixture.week.desc(), Fixture.id.desc())
    ).all()[:3]
    players = session.exec(select(Player).where(Player.team_id == user_team.id).order_by(Player.overall_rating.desc())).all()
    avg_morale = round(sum(player.morale for player in players) / len(players))
    avg_fitness = round(sum(player.fitness for player in players) / len(players))
    avg_fatigue = round(sum(player.fatigue for player in players) / len(players))
    injuries = [player for player in players if player.injury_weeks_remaining > 0]
    wages = sum(player.wage for player in players)
    messages = session.exec(
        select(InboxMessage)
        .where(InboxMessage.team_id == user_team.id)
        .where(InboxMessage.season_number == _current_season_filter(save))
        .order_by(InboxMessage.created_at.desc())
    ).all()[:5]
    latest_result = session.exec(
        select(MatchResult)
        .where(MatchResult.save_game_id == save.id)
        .where(MatchResult.season_number == _current_season_filter(save))
        .where(or_(MatchResult.home_team_id == user_team.id, MatchResult.away_team_id == user_team.id))
        .order_by(MatchResult.created_at.desc())
    ).first()
    league_position = next((row.position for row in table.rows if row.team_id == user_team.id), len(table.rows))
    return DashboardResponse(
        save=build_save_summary(session, save),
        team=serialize_team(user_team),
        next_fixture=serialize_fixture(session, next_fixture) if next_fixture else None,
        recent_results=[serialize_fixture(session, fixture) for fixture in recent_fixtures],
        league_position=league_position,
        morale_summary={
            "average_morale": avg_morale,
            "average_fitness": avg_fitness,
            "average_fatigue": avg_fatigue,
        },
        injury_summary={
            "count": len(injuries),
            "players": [f"{player.first_name} {player.last_name}" for player in injuries[:5]],
        },
        budget_snapshot={
            "transfer_budget": user_team.budget,
            "wage_budget": user_team.wage_budget,
            "current_wages": wages,
            "remaining_wage_budget": max(0, user_team.wage_budget - wages),
        },
        board_objective=user_team.board_objective,
        phase_message=_phase_message(save),
        inbox_preview=[serialize_inbox_message(message) for message in messages],
        latest_match=serialize_match_result(session, latest_result) if latest_result else None,
    )


def get_club_overview(session: Session) -> TeamOverviewRead:
    save = get_active_save(session)
    return serialize_team(get_user_team(session, save))


def get_squad(session: Session) -> SquadResponse:
    save = get_active_save(session)
    save = _prepare_in_season_week(session, save)
    team = get_user_team(session, save)
    players = session.exec(select(Player).where(Player.team_id == team.id).order_by(Player.primary_position, Player.overall_rating.desc())).all()
    return SquadResponse(
        team=serialize_team(team),
        players=[serialize_player(player) for player in players],
        total_wages=sum(player.wage for player in players),
        injured_count=sum(1 for player in players if player.injury_weeks_remaining > 0),
    )


def get_tactics(session: Session) -> TacticsRead:
    save = get_active_save(session)
    save = _prepare_in_season_week(session, save)
    team = get_user_team(session, save)
    tactics = session.exec(select(TeamTactics).where(TeamTactics.team_id == team.id)).first()
    return serialize_tactics(tactics)


def update_tactics(session: Session, request: TacticsUpdateRequest) -> TacticsRead:
    save = get_active_save(session)
    save = _prepare_in_season_week(session, save)
    team = get_user_team(session, save)
    for field_name, allowed_values in TACTIC_VALUES.items():
        value = getattr(request, field_name)
        if value not in allowed_values:
            raise HTTPException(status_code=400, detail=f"Invalid value for {field_name}.")
    if request.training_focus not in TRAINING_FOCUSES:
        raise HTTPException(status_code=400, detail="Invalid training focus.")
    tactics = session.exec(select(TeamTactics).where(TeamTactics.team_id == team.id)).first()
    for key, value in request.model_dump().items():
        setattr(tactics, key, value)
    if save.phase == "in_season":
        from backend.app.services.performance import ensure_weekly_performance_plan

        plan = ensure_weekly_performance_plan(session, save, team)
        plan.focus = request.training_focus
        plan.updated_at = datetime.now(timezone.utc)
        session.add(plan)
    session.add(tactics)
    session.commit()
    session.refresh(tactics)
    return serialize_tactics(tactics)


def get_selection(session: Session) -> SelectionRead:
    save = get_active_save(session)
    save = _prepare_in_season_week(session, save)
    team = get_user_team(session, save)
    selection = session.exec(select(TeamSelection).where(TeamSelection.team_id == team.id)).first()
    return serialize_selection(selection)


def update_selection(session: Session, request: SelectionUpdateRequest) -> SelectionRead:
    save = get_active_save(session)
    save = _prepare_in_season_week(session, save)
    team = get_user_team(session, save)
    players = session.exec(select(Player).where(Player.team_id == team.id)).all()
    blocked_player_ids: set[int] = set()
    if save.phase == "in_season":
        from backend.app.services.performance import selection_blocked_player_ids

        blocked_player_ids = selection_blocked_player_ids(session, save, team)
    try:
        validate_selection(players, request, blocked_player_ids=blocked_player_ids)
    except SelectionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    selection = session.exec(select(TeamSelection).where(TeamSelection.team_id == team.id)).first()
    selection.starting_lineup = [slot.model_dump() for slot in request.starting_lineup]
    selection.bench_player_ids = request.bench_player_ids
    selection.captain_id = request.captain_id
    selection.goal_kicker_id = request.goal_kicker_id
    session.add(selection)
    session.commit()
    session.refresh(selection)
    return serialize_selection(selection)


def get_fixtures(session: Session) -> FixtureListResponse:
    save = get_active_save(session)
    fixtures = session.exec(
        select(Fixture)
        .where(Fixture.save_game_id == save.id)
        .where(Fixture.season_number == _current_season_filter(save))
        .order_by(Fixture.week, Fixture.id)
    ).all()
    recent_results = session.exec(
        select(MatchResult)
        .where(MatchResult.save_game_id == save.id)
        .where(MatchResult.season_number == _current_season_filter(save))
        .order_by(MatchResult.created_at.desc())
    ).all()[:5]
    return FixtureListResponse(
        current_week=save.current_week,
        fixtures=[serialize_fixture(session, fixture) for fixture in fixtures],
        recent_matches=[serialize_match_result(session, result) for result in recent_results],
    )


def build_table(session: Session, save: SaveGame, season_number: int | None = None) -> TableResponse:
    target_season = save.season_number if season_number is None else season_number
    league = get_league(session, save)
    teams = session.exec(select(Team).where(Team.save_game_id == save.id)).all()
    results = session.exec(
        select(MatchResult).where(MatchResult.save_game_id == save.id).where(MatchResult.season_number == target_season)
    ).all()
    table_map = {
        team.id: {
            "team": team,
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "points_for": 0,
            "points_against": 0,
            "tries_for": 0,
            "tries_against": 0,
            "table_points": 0,
        }
        for team in teams
    }
    for result in results:
        home = table_map[result.home_team_id]
        away = table_map[result.away_team_id]
        home["played"] += 1
        away["played"] += 1
        home["points_for"] += result.home_score
        home["points_against"] += result.away_score
        away["points_for"] += result.away_score
        away["points_against"] += result.home_score
        home["tries_for"] += result.home_tries
        home["tries_against"] += result.away_tries
        away["tries_for"] += result.away_tries
        away["tries_against"] += result.home_tries
        if result.home_score > result.away_score:
            home["wins"] += 1
            away["losses"] += 1
            home["table_points"] += 4
            if result.away_score >= result.home_score - 7:
                away["table_points"] += 1
        elif result.home_score < result.away_score:
            away["wins"] += 1
            home["losses"] += 1
            away["table_points"] += 4
            if result.home_score >= result.away_score - 7:
                home["table_points"] += 1
        else:
            home["draws"] += 1
            away["draws"] += 1
            home["table_points"] += 2
            away["table_points"] += 2
        if result.home_tries >= 4:
            home["table_points"] += 1
        if result.away_tries >= 4:
            away["table_points"] += 1
    rows = sorted(
        table_map.values(),
        key=lambda row: (
            row["table_points"],
            row["points_for"] - row["points_against"],
            row["tries_for"] - row["tries_against"],
            row["team"].reputation,
        ),
        reverse=True,
    )
    return TableResponse(
        league_name=league.name,
        season_number=target_season,
        current_week=save.current_week if target_season == save.season_number else save.total_weeks,
        rows=[
            {
                "position": index,
                "team_id": row["team"].id,
                "team_name": row["team"].name,
                "played": row["played"],
                "wins": row["wins"],
                "draws": row["draws"],
                "losses": row["losses"],
                "points_for": row["points_for"],
                "points_against": row["points_against"],
                "tries_for": row["tries_for"],
                "tries_against": row["tries_against"],
                "points_difference": row["points_for"] - row["points_against"],
                "table_points": row["table_points"],
            }
            for index, row in enumerate(rows, start=1)
        ],
    )


def get_table(session: Session) -> TableResponse:
    return build_table(session, get_active_save(session))


def get_transfer_listings(session: Session) -> TransferListResponse:
    save = get_active_save(session)
    team = get_user_team(session, save)
    listings = session.exec(
        select(TransferListing)
        .where(TransferListing.save_game_id == save.id)
        .where(TransferListing.season_number == _current_season_filter(save))
        .where(TransferListing.is_active.is_(True))
    ).all()
    players = {player.id: player for player in session.exec(select(Player).where(Player.save_game_id == save.id)).all()}
    teams = {candidate.id: candidate for candidate in session.exec(select(Team).where(Team.save_game_id == save.id)).all()}
    listing_reads = []
    for listing in listings:
        player = players[listing.player_id]
        owner = teams.get(player.team_id) if player.team_id is not None else None
        listing_reads.append(
            {
                "id": listing.id,
                "player_id": player.id,
                "player_name": f"{player.first_name} {player.last_name}",
                "current_team": owner.name if owner else "Free Agent",
                "is_free_agent": owner is None,
                "primary_position": player.primary_position,
                "overall_rating": player.overall_rating,
                "age": player.age,
                "asking_price": listing.asking_price,
                "wage": player.wage,
                "value": player.transfer_value,
                "form": player.form,
                "morale": player.morale,
            }
        )
    listing_reads.sort(key=lambda item: (item["overall_rating"], item["age"]), reverse=True)
    return TransferListResponse(listings=listing_reads, budget=team.budget, wage_budget=team.wage_budget)


def get_inbox(session: Session) -> InboxResponse:
    save = get_active_save(session)
    team = get_user_team(session, save)
    messages = session.exec(
        select(InboxMessage)
        .where(InboxMessage.team_id == team.id)
        .where(InboxMessage.season_number == _current_season_filter(save))
        .order_by(InboxMessage.created_at.desc())
    ).all()
    return InboxResponse(messages=[serialize_inbox_message(message) for message in messages])


def get_match_result(session: Session, fixture_id: int) -> MatchResultRead:
    save = get_active_save(session)
    fixture = session.exec(select(Fixture).where(Fixture.save_game_id == save.id).where(Fixture.id == fixture_id)).first()
    if not fixture or not fixture.result_id:
        raise HTTPException(status_code=404, detail="Match result not found.")
    result = session.get(MatchResult, fixture.result_id)
    return serialize_match_result(session, result)


def get_career_status(session: Session) -> SaveSummary:
    return build_save_summary(session, get_active_save(session))


def get_season_history(session: Session) -> SeasonHistoryResponse:
    save = get_active_save(session)
    team = get_user_team(session, save)
    seasons = session.exec(
        select(TeamSeasonSummary)
        .where(TeamSeasonSummary.save_game_id == save.id)
        .where(TeamSeasonSummary.team_id == team.id)
        .order_by(TeamSeasonSummary.season_number.desc())
    ).all()
    return SeasonHistoryResponse(seasons=[serialize_season_history(summary) for summary in seasons])


def get_season_review(session: Session) -> SeasonReviewResponse:
    save = get_active_save(session)
    if save.phase == "in_season":
        raise HTTPException(status_code=400, detail="Season review is only available after the season ends.")
    user_team = get_user_team(session, save)
    summary = session.exec(
        select(TeamSeasonSummary)
        .where(TeamSeasonSummary.save_game_id == save.id)
        .where(TeamSeasonSummary.team_id == user_team.id)
        .where(TeamSeasonSummary.season_number == save.season_number)
    ).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Season review not found.")
    retirement_messages = session.exec(
        select(InboxMessage)
        .where(InboxMessage.team_id == user_team.id)
        .where(InboxMessage.season_number == save.season_number)
        .where(InboxMessage.type == "retirement")
    ).all()
    expiring_players = session.exec(
        select(Player).where(Player.team_id == user_team.id).where(Player.contract_years_remaining <= 1)
    ).all()
    return SeasonReviewResponse(
        save=build_save_summary(session, save),
        table=build_table(session, save, save.season_number),
        club_summary=serialize_season_history(summary),
        next_objective=user_team.board_objective,
        projected_transfer_budget=user_team.budget,
        projected_wage_budget=user_team.wage_budget,
        retiring_players=[message.title.replace("Retirement: ", "") for message in retirement_messages],
        expiring_players=[f"{player.first_name} {player.last_name}" for player in expiring_players],
    )


def get_youth_intake(session: Session) -> YouthIntakeResponse:
    save = get_active_save(session)
    team = get_user_team(session, save)
    prospects = session.exec(
        select(YouthProspect)
        .where(YouthProspect.save_game_id == save.id)
        .where(YouthProspect.team_id == team.id)
        .where(YouthProspect.season_number == save.season_number)
        .where(YouthProspect.promoted.is_(False))
        .order_by(YouthProspect.potential.desc(), YouthProspect.overall_rating.desc())
    ).all()
    return YouthIntakeResponse(season_number=save.season_number, prospects=[serialize_youth_prospect(prospect) for prospect in prospects])


def get_offseason_status(session: Session) -> OffseasonStatusResponse:
    save = get_active_save(session)
    if save.phase == "in_season":
        raise HTTPException(status_code=400, detail="Offseason status is only available outside the season.")
    user_team = get_user_team(session, save)
    expiring = session.exec(
        select(Player)
        .where(Player.team_id == user_team.id)
        .where(Player.contract_years_remaining <= 1)
        .order_by(Player.overall_rating.desc())
    ).all()
    retirements = session.exec(
        select(InboxMessage)
        .where(InboxMessage.team_id == user_team.id)
        .where(InboxMessage.season_number == save.season_number)
        .where(InboxMessage.type == "retirement")
        .order_by(InboxMessage.created_at.desc())
    ).all()
    promoted_count = session.exec(
        select(YouthProspect)
        .where(YouthProspect.team_id == user_team.id)
        .where(YouthProspect.season_number == save.season_number)
        .where(YouthProspect.promoted.is_(True))
    ).all()
    return OffseasonStatusResponse(
        save=build_save_summary(session, save),
        next_objective=user_team.board_objective,
        projected_transfer_budget=user_team.budget,
        projected_wage_budget=user_team.wage_budget,
        expiring_contracts=[serialize_player(player) for player in expiring],
        retirements=[message.title.replace("Retirement: ", "") for message in retirements],
        promoted_count=len(promoted_count),
    )
