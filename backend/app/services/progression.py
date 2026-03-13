from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from backend.app.models.entities import Fixture, InboxMessage, MatchResult, Player, SaveGame, Team, TeamSelection, TeamTactics
from backend.app.schemas.api import AdvanceWeekResponse, SelectionSlotRead, SelectionUpdateRequest
from backend.app.services.career import enter_season_review
from backend.app.services.game import (
    build_save_summary,
    get_active_save,
    get_match_result,
    get_user_team,
    serialize_inbox_message,
)
from backend.app.services.recruitment import progress_scouting_targets
from backend.app.services.selection import SelectionValidationError, build_best_selection, validate_selection
from backend.app.simulation.engine import SimulationResult, build_team_profile, simulate_match


@dataclass
class WeekContext:
    fixtures: list[Fixture]
    teams_by_id: dict[int, Team]
    players_by_team: dict[int, list[Player]]
    tactics_by_team: dict[int, TeamTactics]
    selections_by_team: dict[int, TeamSelection]


def _apply_between_week_recovery(players: list[Player]) -> None:
    for player in players:
        if player.injury_weeks_remaining > 0:
            player.injury_weeks_remaining = max(0, player.injury_weeks_remaining - 1)
            if player.injury_weeks_remaining == 0:
                player.injury_status = "Healthy"
                player.fitness = min(98, player.fitness + 8)
        if player.suspended_matches > 0:
            player.suspended_matches = max(0, player.suspended_matches - 1)
        if player.injury_weeks_remaining == 0:
            player.fatigue = max(0, player.fatigue - 5)
            player.fitness = min(99, player.fitness + 3)


def _apply_post_match_effects(
    team_players: list[Player],
    selection: TeamSelection,
    tactics: TeamTactics,
    outcomes: dict[int, object],
    won: bool,
    drew: bool,
) -> None:
    starter_ids = {slot["player_id"] for slot in selection.starting_lineup}
    bench_ids = set(selection.bench_player_ids)
    matchday_ids = starter_ids | bench_ids
    for player in team_players:
        if player.id in starter_ids:
            player.fatigue = min(95, player.fatigue + 16)
            player.fitness = max(45, player.fitness - 6)
        elif player.id in bench_ids:
            player.fatigue = min(95, player.fatigue + 9)
            player.fitness = max(50, player.fitness - 4)
        else:
            recovery = 8 if tactics.training_focus == "recovery" else 5
            player.fatigue = max(0, player.fatigue - recovery)
            player.fitness = min(99, player.fitness + (6 if tactics.training_focus == "fitness" else 3))
        if tactics.training_focus == "fitness":
            player.fitness = min(99, player.fitness + 2)
        if tactics.training_focus == "recovery":
            player.fatigue = max(0, player.fatigue - 2)

        if won:
            player.morale = min(99, player.morale + (3 if player.id in matchday_ids else 1))
            player.form = min(99, player.form + (3 if player.id in starter_ids else 1))
        elif drew:
            player.morale = min(99, max(40, player.morale + 1))
            player.form = min(99, max(40, player.form + 1))
        else:
            player.morale = max(35, player.morale - (3 if player.id in matchday_ids else 1))
            player.form = max(35, player.form - (2 if player.id in starter_ids else 1))

        outcome = outcomes.get(player.id) if outcomes else None
        if outcome:
            player.fatigue = min(99, player.fatigue + outcome.fatigue_delta)
            player.fitness = max(35, min(99, player.fitness + outcome.fitness_delta))
            player.morale = max(25, min(99, player.morale + outcome.morale_delta))
            player.form = max(25, min(99, player.form + outcome.form_delta))
            if outcome.injury_status:
                player.injury_status = outcome.injury_status
                player.injury_weeks_remaining = outcome.injury_weeks_remaining
            player.suspended_matches = max(0, player.suspended_matches + outcome.suspended_matches_delta)


def _create_contract_warnings(session: Session, save: SaveGame, team: Team, players: list[Player]) -> None:
    expiring = [player for player in players if player.contract_years_remaining <= 1][:2]
    for player in expiring:
        session.add(
            InboxMessage(
                save_game_id=save.id,
                season_number=save.season_number,
                team_id=team.id,
                type="contract",
                title="Contract running down",
                body=f"{player.first_name} {player.last_name} has only {player.contract_years_remaining} year(s) left on the deal.",
                related_player_id=player.id,
                created_at=datetime.now(timezone.utc),
            )
        )


def _repair_selection_if_needed(players: list[Player], selection: TeamSelection) -> SelectionUpdateRequest:
    current = SelectionUpdateRequest(
        starting_lineup=[SelectionSlotRead(**slot) for slot in selection.starting_lineup],
        bench_player_ids=selection.bench_player_ids,
        captain_id=selection.captain_id,
        goal_kicker_id=selection.goal_kicker_id,
    )
    try:
        validate_selection(players, current)
        return current
    except SelectionValidationError:
        return build_best_selection(players)


def apply_between_week_recovery(session: Session, save: SaveGame) -> None:
    all_players = session.exec(select(Player).where(Player.save_game_id == save.id)).all()
    _apply_between_week_recovery(all_players)
    for player in all_players:
        session.add(player)
    session.flush()


def load_week_context(session: Session, save: SaveGame) -> WeekContext:
    fixtures = session.exec(
        select(Fixture)
        .where(Fixture.save_game_id == save.id)
        .where(Fixture.season_number == save.season_number)
        .where(Fixture.week == save.current_week)
        .order_by(Fixture.id)
    ).all()
    teams_by_id = {team.id: team for team in session.exec(select(Team).where(Team.save_game_id == save.id)).all()}
    players_by_team: dict[int, list[Player]] = {}
    tactics_by_team: dict[int, TeamTactics] = {}
    selections_by_team: dict[int, TeamSelection] = {}

    for team in teams_by_id.values():
        players_by_team[team.id] = session.exec(select(Player).where(Player.team_id == team.id)).all()
        tactics_by_team[team.id] = session.exec(select(TeamTactics).where(TeamTactics.team_id == team.id)).first()
        selections_by_team[team.id] = session.exec(select(TeamSelection).where(TeamSelection.team_id == team.id)).first()
        repaired = _repair_selection_if_needed(players_by_team[team.id], selections_by_team[team.id])
        selections_by_team[team.id].starting_lineup = [slot.model_dump() for slot in repaired.starting_lineup]
        selections_by_team[team.id].bench_player_ids = repaired.bench_player_ids
        selections_by_team[team.id].captain_id = repaired.captain_id
        selections_by_team[team.id].goal_kicker_id = repaired.goal_kicker_id
        session.add(selections_by_team[team.id])

    session.flush()
    return WeekContext(
        fixtures=fixtures,
        teams_by_id=teams_by_id,
        players_by_team=players_by_team,
        tactics_by_team=tactics_by_team,
        selections_by_team=selections_by_team,
    )


def simulate_fixture(context: WeekContext, fixture: Fixture, *, seed: int) -> SimulationResult:
    home_team = context.teams_by_id[fixture.home_team_id]
    away_team = context.teams_by_id[fixture.away_team_id]
    home_profile = build_team_profile(
        home_team,
        context.players_by_team[home_team.id],
        context.selections_by_team[home_team.id],
        context.tactics_by_team[home_team.id],
    )
    away_profile = build_team_profile(
        away_team,
        context.players_by_team[away_team.id],
        context.selections_by_team[away_team.id],
        context.tactics_by_team[away_team.id],
    )
    return simulate_match(home_profile, away_profile, seed=seed)


def record_fixture_result(
    session: Session,
    save: SaveGame,
    fixture: Fixture,
    simulation: SimulationResult,
    context: WeekContext,
) -> MatchResult:
    home_team = context.teams_by_id[fixture.home_team_id]
    away_team = context.teams_by_id[fixture.away_team_id]
    result = MatchResult(
        save_game_id=save.id,
        fixture_id=fixture.id,
        season_number=save.season_number,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        home_score=simulation.home.score,
        away_score=simulation.away.score,
        home_tries=simulation.home.tries,
        away_tries=simulation.away.tries,
        home_penalties=simulation.home.penalties,
        away_penalties=simulation.away.penalties,
        home_conversions=simulation.home.conversions,
        away_conversions=simulation.away.conversions,
        summary=simulation.summary,
        stats=simulation.stats,
        commentary=simulation.commentary,
    )
    session.add(result)
    session.flush()
    fixture.played = True
    fixture.result_id = result.id
    session.add(fixture)

    home_win = result.home_score > result.away_score
    away_win = result.away_score > result.home_score
    drew = result.home_score == result.away_score
    _apply_post_match_effects(
        context.players_by_team[home_team.id],
        context.selections_by_team[home_team.id],
        context.tactics_by_team[home_team.id],
        simulation.home.outcomes,
        won=home_win,
        drew=drew,
    )
    _apply_post_match_effects(
        context.players_by_team[away_team.id],
        context.selections_by_team[away_team.id],
        context.tactics_by_team[away_team.id],
        simulation.away.outcomes,
        won=away_win,
        drew=drew,
    )
    return result


def create_user_fixture_messages(
    session: Session,
    save: SaveGame,
    user_team: Team,
    fixture: Fixture,
    simulation: SimulationResult,
) -> None:
    home_team = session.get(Team, fixture.home_team_id)
    away_team = session.get(Team, fixture.away_team_id)
    home_score = simulation.home.score
    away_score = simulation.away.score
    session.add(
        InboxMessage(
            save_game_id=save.id,
            season_number=save.season_number,
            team_id=user_team.id,
            type="match",
            title=f"Match report: {home_team.short_name} {home_score}-{away_score} {away_team.short_name}",
            body=simulation.summary,
            related_fixture_id=fixture.id,
            created_at=datetime.now(timezone.utc),
        )
    )
    user_team_state = simulation.home if home_team.id == user_team.id else simulation.away
    for player_id, outcome in user_team_state.outcomes.items():
        if outcome.injury_status:
            player = session.get(Player, player_id)
            session.add(
                InboxMessage(
                    save_game_id=save.id,
                    season_number=save.season_number,
                    team_id=user_team.id,
                    type="injury",
                    title=f"Injury update: {player.first_name} {player.last_name}",
                    body=f"{player.first_name} {player.last_name} suffered {outcome.injury_status.lower()} and will miss around {outcome.injury_weeks_remaining} week(s).",
                    related_fixture_id=fixture.id,
                    related_player_id=player.id,
                    created_at=datetime.now(timezone.utc),
                )
            )


def finalize_current_week(
    session: Session,
    save: SaveGame,
    user_team: Team,
    *,
    completed_ids: list[int],
    user_result_fixture_id: int | None,
) -> AdvanceWeekResponse:
    user_players = session.exec(select(Player).where(Player.team_id == user_team.id)).all()
    for player in user_players:
        if player.contract_years_remaining > 0 and save.current_week in {6, 12, 17} and player.contract_years_remaining == 1:
            player.contract_years_remaining = 1
        session.add(player)
    if save.current_week in {6, 12, 17}:
        _create_contract_warnings(session, save, user_team, user_players)

    progress_scouting_targets(session, save)
    save.current_week += 1
    save.updated_at = datetime.now(timezone.utc)
    session.add(save)
    session.commit()

    season_complete = save.current_week > save.total_weeks
    if season_complete:
        enter_season_review(session)
        save = get_active_save(session)
    messages = session.exec(
        select(InboxMessage)
        .where(InboxMessage.team_id == user_team.id)
        .where(InboxMessage.season_number == save.season_number)
        .order_by(InboxMessage.created_at.desc())
    ).all()[:8]
    return AdvanceWeekResponse(
        save=build_save_summary(session, save),
        advanced_to_week=min(save.current_week, save.total_weeks),
        completed_fixture_ids=completed_ids,
        user_match=get_match_result(session, user_result_fixture_id) if user_result_fixture_id else None,
        inbox_messages=[serialize_inbox_message(message) for message in messages],
        season_complete=season_complete,
    )


def simulate_remaining_week(
    session: Session,
    save: SaveGame,
    context: WeekContext,
    *,
    skip_fixture_ids: set[int] | None = None,
) -> tuple[list[int], int | None]:
    skip_fixture_ids = skip_fixture_ids or set()
    user_team = get_user_team(session, save)
    completed_ids: list[int] = []
    user_result_fixture_id: int | None = None
    for fixture in context.fixtures:
        if fixture.id in skip_fixture_ids or fixture.played:
            continue
        simulation = simulate_fixture(session_context := context, fixture, seed=(save.id * 10_000 + fixture.id * 37 + save.current_week))
        record_fixture_result(session, save, fixture, simulation, session_context)
        completed_ids.append(fixture.id)
        if user_team.id in {fixture.home_team_id, fixture.away_team_id}:
            create_user_fixture_messages(session, save, user_team, fixture, simulation)
            user_result_fixture_id = fixture.id
    return completed_ids, user_result_fixture_id


def advance_week(session: Session) -> AdvanceWeekResponse:
    save = get_active_save(session)
    if save.phase != "in_season":
        raise HTTPException(status_code=400, detail="Cannot advance the week while the save is in offseason flow.")

    user_team = get_user_team(session, save)
    fixtures = session.exec(
        select(Fixture)
        .where(Fixture.save_game_id == save.id)
        .where(Fixture.season_number == save.season_number)
        .where(Fixture.week == save.current_week)
        .order_by(Fixture.id)
    ).all()
    user_fixture = next((fixture for fixture in fixtures if user_team.id in {fixture.home_team_id, fixture.away_team_id}), None)
    if user_fixture and not user_fixture.played:
        raise HTTPException(status_code=400, detail="Start the live match from Match Centre to play the user fixture.")

    context = load_week_context(session, save)
    completed_ids, user_result_fixture_id = simulate_remaining_week(session, save, context)
    return finalize_current_week(
        session,
        save,
        user_team,
        completed_ids=completed_ids,
        user_result_fixture_id=user_result_fixture_id,
    )
