from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from backend.app.core.constants import TACTIC_VALUES, TRAINING_FOCUSES
from backend.app.models.entities import Fixture, LiveMatchSession, Player, SaveGame, Team, TeamSelection, TeamTactics
from backend.app.schemas.api import (
    LiveMatchHalftimeRequest,
    LiveMatchPlayerRead,
    LiveMatchSnapshotRead,
    LiveMatchTeamStateRead,
    SelectionRead,
    SelectionSlotRead,
    TacticsRead,
)
from backend.app.services.performance import ensure_weekly_performance_plan, medical_assignment_map
from backend.app.services.game import (
    build_save_summary,
    get_active_save,
    get_match_result,
    get_user_team,
    serialize_fixture,
    serialize_match_result,
)
from backend.app.services.progression import (
    WeekContext,
    apply_between_week_recovery,
    create_user_fixture_messages,
    finalize_current_week,
    load_week_context,
    record_fixture_result,
    simulate_remaining_week,
)
from backend.app.services.selection import player_can_cover_slot
from backend.app.simulation.config import CONFIG
from backend.app.simulation.engine import (
    build_simulation_result,
    build_stats,
    build_team_profile,
    hydrate_team_state,
    initialize_team_state,
    serialize_team_state,
    simulate_block,
)


LIVE_ACTIVE_STATUSES = {"first_half", "second_half", "halftime"}


def _active_session_query(session: Session, save: SaveGame):
    return (
        select(LiveMatchSession)
        .where(LiveMatchSession.save_game_id == save.id)
        .where(LiveMatchSession.is_active.is_(True))
        .order_by(LiveMatchSession.id.desc())
    )


def _get_active_live_session_optional(session: Session, save: SaveGame) -> LiveMatchSession | None:
    return session.exec(_active_session_query(session, save)).first()


def _get_active_live_session(session: Session, save: SaveGame) -> LiveMatchSession:
    live_session = _get_active_live_session_optional(session, save)
    if not live_session:
        raise HTTPException(status_code=404, detail="No active live match found.")
    return live_session


def _selection_payload(selection: TeamSelection) -> dict[str, Any]:
    return {
        "starting_lineup": list(selection.starting_lineup),
        "bench_player_ids": list(selection.bench_player_ids),
        "captain_id": selection.captain_id,
        "goal_kicker_id": selection.goal_kicker_id,
    }


def _copy_selection_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "starting_lineup": [dict(slot) for slot in payload["starting_lineup"]],
        "bench_player_ids": list(payload["bench_player_ids"]),
        "captain_id": payload["captain_id"],
        "goal_kicker_id": payload["goal_kicker_id"],
    }


def _tactics_payload(tactics: TeamTactics) -> dict[str, Any]:
    return {
        "attacking_style": tactics.attacking_style,
        "kicking_approach": tactics.kicking_approach,
        "defensive_system": tactics.defensive_system,
        "ruck_commitment": tactics.ruck_commitment,
        "set_piece_intent": tactics.set_piece_intent,
        "goal_choice": tactics.goal_choice,
        "training_focus": tactics.training_focus,
    }


def _copy_tactics_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return dict(payload)


def _selection_read(payload: dict[str, Any]) -> SelectionRead:
    return SelectionRead(
        starting_lineup=[SelectionSlotRead(**slot) for slot in payload["starting_lineup"]],
        bench_player_ids=list(payload["bench_player_ids"]),
        captain_id=payload["captain_id"],
        goal_kicker_id=payload["goal_kicker_id"],
    )


def _tactics_read(payload: dict[str, Any]) -> TacticsRead:
    return TacticsRead(**payload)


def _selection_model(save_id: int, team_id: int, payload: dict[str, Any]) -> TeamSelection:
    return TeamSelection(
        save_game_id=save_id,
        team_id=team_id,
        starting_lineup=list(payload["starting_lineup"]),
        bench_player_ids=list(payload["bench_player_ids"]),
        captain_id=payload["captain_id"],
        goal_kicker_id=payload["goal_kicker_id"],
    )


def _tactics_model(save_id: int, team_id: int, payload: dict[str, Any]) -> TeamTactics:
    return TeamTactics(save_game_id=save_id, team_id=team_id, **payload)


def _user_side(live_session: LiveMatchSession) -> str:
    return "home" if live_session.user_team_id == live_session.home_team_id else "away"


def _opponent_side(side: str) -> str:
    return "away" if side == "home" else "home"


def _session_fixture(session: Session, save: SaveGame, user_team: Team) -> Fixture:
    fixture = session.exec(
        select(Fixture)
        .where(Fixture.save_game_id == save.id)
        .where(Fixture.season_number == save.season_number)
        .where(Fixture.week == save.current_week)
        .where((Fixture.home_team_id == user_team.id) | (Fixture.away_team_id == user_team.id))
        .order_by(Fixture.id)
    ).first()
    if not fixture:
        raise HTTPException(status_code=400, detail="No pending user fixture found for the current week.")
    if fixture.played:
        raise HTTPException(status_code=400, detail="The user fixture for this week has already been completed.")
    return fixture


def _condition_key(player_id: int) -> str:
    return str(player_id)


def _build_initial_conditions(context: WeekContext, home_team_id: int, away_team_id: int) -> dict[str, dict[str, int]]:
    conditions: dict[str, dict[str, int]] = {}
    for team_id in (home_team_id, away_team_id):
        selection = context.selections_by_team[team_id]
        player_ids = {slot["player_id"] for slot in selection.starting_lineup} | set(selection.bench_player_ids)
        for player in context.players_by_team[team_id]:
            if player.id in player_ids:
                conditions[_condition_key(player.id)] = {
                    "fatigue": player.fatigue,
                    "fitness": player.fitness,
                    "morale": player.morale,
                    "form": player.form,
                }
    return conditions


def _clone_players(players: list[Player], conditions: dict[str, dict[str, int]]) -> list[Player]:
    adjusted: list[Player] = []
    for player in players:
        clone = Player.model_validate(player.model_dump())
        override = conditions.get(_condition_key(player.id))
        if override:
            clone.fatigue = override["fatigue"]
            clone.fitness = override["fitness"]
            clone.morale = override["morale"]
            clone.form = override["form"]
        adjusted.append(clone)
    return adjusted


def _validate_tactics(request: TacticsRead) -> None:
    for field_name, allowed_values in TACTIC_VALUES.items():
        value = getattr(request, field_name)
        if value not in allowed_values:
            raise HTTPException(status_code=400, detail=f"Invalid value for {field_name}.")
    if request.training_focus not in TRAINING_FOCUSES:
        raise HTTPException(status_code=400, detail="Invalid training focus.")


def _load_session_profiles(
    session: Session,
    save: SaveGame,
    live_session: LiveMatchSession,
) -> tuple[dict[int, Team], dict[str, list[Player]], dict[str, TeamSelection], dict[str, TeamTactics]]:
    teams_by_id = {
        live_session.home_team_id: session.get(Team, live_session.home_team_id),
        live_session.away_team_id: session.get(Team, live_session.away_team_id),
    }
    players_by_side = {
        "home": _clone_players(
            session.exec(select(Player).where(Player.team_id == live_session.home_team_id)).all(),
            live_session.player_conditions,
        ),
        "away": _clone_players(
            session.exec(select(Player).where(Player.team_id == live_session.away_team_id)).all(),
            live_session.player_conditions,
        ),
    }
    selections = {
        "home": _selection_model(save.id, live_session.home_team_id, live_session.home_selection),
        "away": _selection_model(save.id, live_session.away_team_id, live_session.away_selection),
    }
    tactics = {
        "home": _tactics_model(save.id, live_session.home_team_id, live_session.home_tactics),
        "away": _tactics_model(save.id, live_session.away_team_id, live_session.away_tactics),
    }
    return teams_by_id, players_by_side, selections, tactics


def _team_state_read(team: Team, stats: dict[str, int], payload: dict[str, Any]) -> LiveMatchTeamStateRead:
    return LiveMatchTeamStateRead(
        team_id=team.id,
        team_name=team.name,
        score=payload["score"],
        tries=payload["tries"],
        penalties=payload["penalties"],
        conversions=payload["conversions"],
        drop_goals=payload["drop_goals"],
        stats=stats,
    )


def _user_matchday_players(
    team_players: list[Player],
    selection_payload: dict[str, Any],
    state_payload: dict[str, Any],
    conditions: dict[str, dict[str, int]],
) -> list[LiveMatchPlayerRead]:
    starters = {entry["player_id"]: entry["slot"] for entry in selection_payload["starting_lineup"]}
    bench_ids = set(selection_payload["bench_player_ids"])
    outcomes = {int(player_id): outcome for player_id, outcome in state_payload.get("outcomes", {}).items()}
    players_by_id = {player.id: player for player in team_players}
    matchday_players = []
    for player_id in [entry["player_id"] for entry in selection_payload["starting_lineup"]] + selection_payload["bench_player_ids"]:
        player = players_by_id[player_id]
        condition = conditions.get(_condition_key(player_id), {})
        outcome = outcomes.get(player_id, {})
        matchday_players.append(
            LiveMatchPlayerRead(
                player_id=player.id,
                name=f"{player.first_name} {player.last_name}",
                primary_position=player.primary_position,
                secondary_positions=player.secondary_positions,
                overall_rating=player.overall_rating,
                starter_slot=starters.get(player.id),
                on_field=player.id in starters,
                fatigue=condition.get("fatigue", player.fatigue),
                fitness=condition.get("fitness", player.fitness),
                morale=condition.get("morale", player.morale),
                form=condition.get("form", player.form),
                injury_status=outcome.get("injury_status"),
                card_status="red" if outcome.get("suspended_matches_delta", 0) > 0 else None,
            )
        )
    return matchday_players


def _snapshot_from_session(
    session: Session,
    save: SaveGame,
    live_session: LiveMatchSession,
    *,
    result_fixture_id: int | None = None,
) -> LiveMatchSnapshotRead:
    fixture = session.get(Fixture, live_session.fixture_id)
    teams_by_id, players_by_side, _, _ = _load_session_profiles(session, save, live_session)
    blocks_played = max(1, live_session.current_block)
    stats = build_stats(
        hydrate_team_state(build_team_profile(teams_by_id[live_session.home_team_id], players_by_side["home"], _selection_model(save.id, live_session.home_team_id, live_session.home_selection), _tactics_model(save.id, live_session.home_team_id, live_session.home_tactics)), live_session.home_state),
        hydrate_team_state(build_team_profile(teams_by_id[live_session.away_team_id], players_by_side["away"], _selection_model(save.id, live_session.away_team_id, live_session.away_selection), _tactics_model(save.id, live_session.away_team_id, live_session.away_tactics)), live_session.away_state),
        blocks_played=blocks_played,
    )
    user_side = _user_side(live_session)
    user_team_players = players_by_side[user_side]
    user_selection = live_session.home_selection if user_side == "home" else live_session.away_selection
    user_tactics = live_session.home_tactics if user_side == "home" else live_session.away_tactics
    user_state = live_session.home_state if user_side == "home" else live_session.away_state
    result = get_match_result(session, result_fixture_id) if result_fixture_id else None
    return LiveMatchSnapshotRead(
        session_id=live_session.id,
        save=build_save_summary(session, save),
        fixture=serialize_fixture(session, fixture),
        status=live_session.status,
        minute=live_session.minute,
        current_block=live_session.current_block,
        total_blocks=CONFIG.blocks,
        user_team_id=live_session.user_team_id,
        home=_team_state_read(teams_by_id[live_session.home_team_id], stats["home"], live_session.home_state),
        away=_team_state_read(teams_by_id[live_session.away_team_id], stats["away"], live_session.away_state),
        commentary=list(live_session.commentary),
        recent_events=list(live_session.recent_events),
        ball_position=live_session.ball_position,
        user_selection=_selection_read(user_selection),
        user_tactics=_tactics_read(user_tactics),
        user_matchday_players=_user_matchday_players(user_team_players, user_selection, user_state, live_session.player_conditions),
        result=result,
    )


def _persist_session(session: Session, live_session: LiveMatchSession) -> None:
    live_session.updated_at = datetime.now(timezone.utc)
    session.add(live_session)
    session.commit()
    session.refresh(live_session)


def _apply_match_fatigue(
    live_session: LiveMatchSession,
    selection_payload: dict[str, Any],
    *,
    block_index: int,
) -> None:
    starter_fatigue = 3 if block_index < 4 else 4
    starter_fitness = -1 if block_index < 4 else -2
    for slot in selection_payload["starting_lineup"]:
        condition = live_session.player_conditions[_condition_key(slot["player_id"])]
        condition["fatigue"] = min(95, condition["fatigue"] + starter_fatigue)
        condition["fitness"] = max(42, condition["fitness"] + starter_fitness)
    for player_id in selection_payload["bench_player_ids"]:
        condition = live_session.player_conditions[_condition_key(player_id)]
        condition["fatigue"] = max(0, condition["fatigue"] - 1)
        condition["fitness"] = min(99, condition["fitness"] + 1)


def _apply_ai_halftime(live_session: LiveMatchSession, session: Session, save: SaveGame) -> None:
    ai_side = _opponent_side(_user_side(live_session))
    ai_selection = live_session.home_selection if ai_side == "home" else live_session.away_selection
    ai_tactics = live_session.home_tactics if ai_side == "home" else live_session.away_tactics
    ai_state = live_session.home_state if ai_side == "home" else live_session.away_state
    opp_state = live_session.away_state if ai_side == "home" else live_session.home_state

    if ai_state["score"] < opp_state["score"]:
        ai_tactics["attacking_style"] = "expansive"
        ai_tactics["goal_choice"] = "kick to corner"
        ai_tactics["ruck_commitment"] = "high"
    elif ai_state["score"] > opp_state["score"]:
        ai_tactics["kicking_approach"] = "high"
        ai_tactics["goal_choice"] = "go for posts"

    players = {
        player.id: player
        for player in session.exec(select(Player).where(Player.team_id == (live_session.home_team_id if ai_side == "home" else live_session.away_team_id))).all()
    }
    highest_fatigue = max(
        ai_selection["starting_lineup"],
        key=lambda slot: live_session.player_conditions[_condition_key(slot["player_id"])]["fatigue"],
    )
    outgoing_id = highest_fatigue["player_id"]
    slot_name = highest_fatigue["slot"]
    candidates = [
        bench_id
        for bench_id in ai_selection["bench_player_ids"]
        if player_can_cover_slot(players[bench_id], slot_name)
        and live_session.player_conditions[_condition_key(bench_id)]["fitness"] > live_session.player_conditions[_condition_key(outgoing_id)]["fitness"]
    ]
    if candidates:
        incoming_id = max(candidates, key=lambda player_id: (players[player_id].overall_rating, live_session.player_conditions[_condition_key(player_id)]["fitness"]))
        ai_selection["bench_player_ids"] = [outgoing_id if player_id == incoming_id else player_id for player_id in ai_selection["bench_player_ids"]]
        highest_fatigue["player_id"] = incoming_id


def _context_with_live_overrides(session: Session, save: SaveGame, live_session: LiveMatchSession) -> WeekContext:
    context = load_week_context(session, save)
    context.selections_by_team[live_session.home_team_id] = _selection_model(save.id, live_session.home_team_id, live_session.home_selection)
    context.selections_by_team[live_session.away_team_id] = _selection_model(save.id, live_session.away_team_id, live_session.away_selection)
    context.tactics_by_team[live_session.home_team_id] = _tactics_model(save.id, live_session.home_team_id, live_session.home_tactics)
    context.tactics_by_team[live_session.away_team_id] = _tactics_model(save.id, live_session.away_team_id, live_session.away_tactics)
    return context


def start_live_match(session: Session) -> LiveMatchSnapshotRead:
    save = get_active_save(session)
    if save.phase != "in_season":
        raise HTTPException(status_code=400, detail="Live matches are only available during the season.")

    existing = _get_active_live_session_optional(session, save)
    if existing:
        return _snapshot_from_session(session, save, existing)

    user_team = get_user_team(session, save)
    fixture = _session_fixture(session, save, user_team)
    apply_between_week_recovery(session, save)
    context = load_week_context(session, save)
    home_plan = ensure_weekly_performance_plan(session, save, context.teams_by_id[fixture.home_team_id]) if fixture.home_team_id == user_team.id else None
    away_plan = ensure_weekly_performance_plan(session, save, context.teams_by_id[fixture.away_team_id]) if fixture.away_team_id == user_team.id else None
    home_medical = medical_assignment_map(session, save, context.teams_by_id[fixture.home_team_id]) if fixture.home_team_id == user_team.id else {}
    away_medical = medical_assignment_map(session, save, context.teams_by_id[fixture.away_team_id]) if fixture.away_team_id == user_team.id else {}

    live_session = LiveMatchSession(
        save_game_id=save.id,
        fixture_id=fixture.id,
        season_number=save.season_number,
        home_team_id=fixture.home_team_id,
        away_team_id=fixture.away_team_id,
        user_team_id=user_team.id,
        status="first_half",
        current_block=0,
        minute=0,
        seed=(save.id * 10_000 + fixture.id * 37 + save.current_week),
        ball_position=50,
        commentary=[],
        recent_events=[],
        home_selection=_selection_payload(context.selections_by_team[fixture.home_team_id]),
        away_selection=_selection_payload(context.selections_by_team[fixture.away_team_id]),
        home_tactics=_tactics_payload(context.tactics_by_team[fixture.home_team_id]),
        away_tactics=_tactics_payload(context.tactics_by_team[fixture.away_team_id]),
        player_conditions=_build_initial_conditions(context, fixture.home_team_id, fixture.away_team_id),
        home_state=serialize_team_state(initialize_team_state(build_team_profile(
            context.teams_by_id[fixture.home_team_id],
            context.players_by_team[fixture.home_team_id],
            context.selections_by_team[fixture.home_team_id],
            context.tactics_by_team[fixture.home_team_id],
            performance_plan=home_plan,
            medical_assignments=home_medical,
        ))),
        away_state=serialize_team_state(initialize_team_state(build_team_profile(
            context.teams_by_id[fixture.away_team_id],
            context.players_by_team[fixture.away_team_id],
            context.selections_by_team[fixture.away_team_id],
            context.tactics_by_team[fixture.away_team_id],
            performance_plan=away_plan,
            medical_assignments=away_medical,
        ))),
    )
    session.add(live_session)
    session.commit()
    session.refresh(live_session)
    return _snapshot_from_session(session, save, live_session)


def get_current_live_match(session: Session) -> LiveMatchSnapshotRead | None:
    save = get_active_save(session)
    live_session = _get_active_live_session_optional(session, save)
    if not live_session:
        return None
    return _snapshot_from_session(session, save, live_session)


def tick_live_match(session: Session) -> LiveMatchSnapshotRead:
    save = get_active_save(session)
    live_session = _get_active_live_session(session, save)
    if live_session.status == "halftime":
        raise HTTPException(status_code=400, detail="Halftime changes are required before the match can resume.")
    if live_session.status not in {"first_half", "second_half"}:
        raise HTTPException(status_code=400, detail="The live match is not in a playable state.")

    teams_by_id, players_by_side, selections, tactics = _load_session_profiles(session, save, live_session)
    home_plan = ensure_weekly_performance_plan(session, save, teams_by_id[live_session.home_team_id]) if live_session.home_team_id == live_session.user_team_id else None
    away_plan = ensure_weekly_performance_plan(session, save, teams_by_id[live_session.away_team_id]) if live_session.away_team_id == live_session.user_team_id else None
    home_medical = medical_assignment_map(session, save, teams_by_id[live_session.home_team_id]) if live_session.home_team_id == live_session.user_team_id else {}
    away_medical = medical_assignment_map(session, save, teams_by_id[live_session.away_team_id]) if live_session.away_team_id == live_session.user_team_id else {}
    home_profile = build_team_profile(
        teams_by_id[live_session.home_team_id],
        players_by_side["home"],
        selections["home"],
        tactics["home"],
        performance_plan=home_plan,
        medical_assignments=home_medical,
    )
    away_profile = build_team_profile(
        teams_by_id[live_session.away_team_id],
        players_by_side["away"],
        selections["away"],
        tactics["away"],
        performance_plan=away_plan,
        medical_assignments=away_medical,
    )
    home_state = hydrate_team_state(home_profile, live_session.home_state)
    away_state = hydrate_team_state(away_profile, live_session.away_state)

    block = simulate_block(
        home_profile,
        away_profile,
        home_state,
        away_state,
        seed=live_session.seed,
        block_index=live_session.current_block,
    )
    live_session.commentary = [*live_session.commentary, *block.commentary]
    live_session.recent_events = block.commentary
    live_session.minute = block.minute
    completed_block = live_session.current_block
    live_session.current_block += 1
    live_session.ball_position = block.ball_position
    _apply_match_fatigue(live_session, live_session.home_selection, block_index=completed_block)
    _apply_match_fatigue(live_session, live_session.away_selection, block_index=completed_block)
    live_session.player_conditions = {
        player_id: dict(values)
        for player_id, values in live_session.player_conditions.items()
    }
    live_session.home_state = serialize_team_state(home_state)
    live_session.away_state = serialize_team_state(away_state)

    if live_session.current_block == CONFIG.blocks // 2:
        halftime_event = {
            "minute": CONFIG.block_minutes * (CONFIG.blocks // 2),
            "team": "Match Officials",
            "type": "halftime",
            "text": "Halftime. The managers head down the tunnel with the tactical picture still in motion.",
            "field_position": 50,
        }
        live_session.commentary = [*live_session.commentary, halftime_event]
        live_session.recent_events = [*block.commentary, halftime_event]
        live_session.status = "halftime"
        _persist_session(session, live_session)
        return _snapshot_from_session(session, save, live_session)

    if live_session.current_block >= CONFIG.blocks:
        final_event = {
            "minute": CONFIG.block_minutes * CONFIG.blocks,
            "team": "Match Officials",
            "type": "full-time",
            "text": "Full time. The match closes and the league round is processed around it.",
            "field_position": live_session.ball_position,
        }
        live_session.commentary = [*live_session.commentary, final_event]
        live_session.recent_events = [*block.commentary, final_event]
        live_session.status = "full_time"
        simulation = build_simulation_result(home_state, away_state, live_session.commentary)
        fixture = session.get(Fixture, live_session.fixture_id)
        user_team = get_user_team(session, save)
        context = _context_with_live_overrides(session, save, live_session)
        record_fixture_result(session, save, fixture, simulation, context)
        create_user_fixture_messages(session, save, user_team, fixture, simulation)
        remaining_ids, _ = simulate_remaining_week(session, save, context, skip_fixture_ids={fixture.id})
        live_session.is_active = False
        session.add(live_session)
        response = finalize_current_week(
            session,
            save,
            user_team,
            completed_ids=[fixture.id, *remaining_ids],
            user_result_fixture_id=fixture.id,
        )
        return LiveMatchSnapshotRead(
            session_id=live_session.id,
            save=response.save,
            fixture=serialize_fixture(session, fixture),
            status="full_time",
            minute=live_session.minute,
            current_block=live_session.current_block,
            total_blocks=CONFIG.blocks,
            user_team_id=live_session.user_team_id,
            home=_team_state_read(session.get(Team, live_session.home_team_id), simulation.stats["home"], live_session.home_state),
            away=_team_state_read(session.get(Team, live_session.away_team_id), simulation.stats["away"], live_session.away_state),
            commentary=list(live_session.commentary),
            recent_events=list(live_session.recent_events),
            ball_position=live_session.ball_position,
            user_selection=_selection_read(live_session.home_selection if _user_side(live_session) == "home" else live_session.away_selection),
            user_tactics=_tactics_read(live_session.home_tactics if _user_side(live_session) == "home" else live_session.away_tactics),
            user_matchday_players=_user_matchday_players(
                players_by_side[_user_side(live_session)],
                live_session.home_selection if _user_side(live_session) == "home" else live_session.away_selection,
                live_session.home_state if _user_side(live_session) == "home" else live_session.away_state,
                live_session.player_conditions,
            ),
            result=response.user_match,
        )

    live_session.status = "first_half" if live_session.current_block < CONFIG.blocks // 2 else "second_half"
    _persist_session(session, live_session)
    return _snapshot_from_session(session, save, live_session)


def submit_halftime_changes(session: Session, request: LiveMatchHalftimeRequest) -> LiveMatchSnapshotRead:
    save = get_active_save(session)
    live_session = _get_active_live_session(session, save)
    if live_session.status != "halftime":
        raise HTTPException(status_code=400, detail="Halftime changes are only available during the halftime break.")
    _validate_tactics(request.tactics)

    user_side = _user_side(live_session)
    team_id = live_session.home_team_id if user_side == "home" else live_session.away_team_id
    current_selection = live_session.home_selection if user_side == "home" else live_session.away_selection
    players = {player.id: player for player in session.exec(select(Player).where(Player.team_id == team_id)).all()}

    starting_lineup = [dict(slot) for slot in current_selection["starting_lineup"]]
    bench_player_ids = list(current_selection["bench_player_ids"])
    starters = {entry["player_id"]: entry for entry in starting_lineup}
    bench_ids = set(bench_player_ids)
    used_out_ids: set[int] = set()
    used_in_ids: set[int] = set()
    for substitution in request.substitutions:
        if substitution.player_out_id in used_out_ids or substitution.player_in_id in used_in_ids:
            raise HTTPException(status_code=400, detail="Each halftime substitution must use unique in/out players.")
        if substitution.player_out_id not in starters:
            raise HTTPException(status_code=400, detail="Substituted-out player must currently be on the field.")
        if substitution.player_in_id not in bench_ids:
            raise HTTPException(status_code=400, detail="Substituted-in player must currently be on the bench.")
        slot_name = starters[substitution.player_out_id]["slot"]
        if not player_can_cover_slot(players[substitution.player_in_id], slot_name):
            raise HTTPException(status_code=400, detail=f"{players[substitution.player_in_id].first_name} {players[substitution.player_in_id].last_name} cannot cover {slot_name}.")

        starters[substitution.player_out_id]["player_id"] = substitution.player_in_id
        bench_player_ids = [
            substitution.player_out_id if player_id == substitution.player_in_id else player_id
            for player_id in bench_player_ids
        ]
        used_out_ids.add(substitution.player_out_id)
        used_in_ids.add(substitution.player_in_id)
        del starters[substitution.player_out_id]
        starters[substitution.player_in_id] = next(entry for entry in starting_lineup if entry["player_id"] == substitution.player_in_id)
        bench_ids = set(bench_player_ids)

    selection_payload = {
        "starting_lineup": starting_lineup,
        "bench_player_ids": bench_player_ids,
        "captain_id": request.captain_id,
        "goal_kicker_id": request.goal_kicker_id,
    }
    matchday_ids = {entry["player_id"] for entry in selection_payload["starting_lineup"]} | set(selection_payload["bench_player_ids"])
    if request.captain_id not in matchday_ids or request.goal_kicker_id not in matchday_ids:
        raise HTTPException(status_code=400, detail="Captain and goal kicker must remain part of the current matchday squad.")
    tactics_payload = request.tactics.model_dump()

    team_tactics = session.exec(select(TeamTactics).where(TeamTactics.team_id == team_id)).first()
    for key, value in request.tactics.model_dump().items():
        setattr(team_tactics, key, value)
    session.add(team_tactics)

    if user_side == "home":
        live_session.home_selection = _copy_selection_payload(selection_payload)
        live_session.home_tactics = _copy_tactics_payload(tactics_payload)
    else:
        live_session.away_selection = _copy_selection_payload(selection_payload)
        live_session.away_tactics = _copy_tactics_payload(tactics_payload)

    _apply_ai_halftime(live_session, session, save)
    live_session.home_selection = _copy_selection_payload(live_session.home_selection)
    live_session.away_selection = _copy_selection_payload(live_session.away_selection)
    live_session.home_tactics = _copy_tactics_payload(live_session.home_tactics)
    live_session.away_tactics = _copy_tactics_payload(live_session.away_tactics)
    live_session.status = "second_half"
    live_session.recent_events = [
        {
            "minute": 40,
            "team": session.get(Team, team_id).name,
            "type": "halftime-adjustment",
            "text": "The coaching box reshapes the game plan and sends a different second-half mix back out.",
            "field_position": 50,
        }
    ]
    live_session.commentary = [*live_session.commentary, *live_session.recent_events]
    _persist_session(session, live_session)
    return _snapshot_from_session(session, save, live_session)
