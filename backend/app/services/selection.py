from __future__ import annotations

from collections import Counter

from backend.app.core.constants import LINEUP_SLOTS
from backend.app.models.entities import Player
from backend.app.schemas.api import SelectionSlotRead, SelectionUpdateRequest


class SelectionValidationError(ValueError):
    pass


def player_can_cover_slot(player: Player, slot: str) -> bool:
    if player.primary_position == slot:
        return True
    return slot in player.secondary_positions


def validate_selection(
    players: list[Player],
    request: SelectionUpdateRequest,
    *,
    blocked_player_ids: set[int] | None = None,
) -> None:
    blocked_player_ids = blocked_player_ids or set()
    players_by_id = {player.id: player for player in players}

    if len(request.starting_lineup) != len(LINEUP_SLOTS):
        raise SelectionValidationError("Starting lineup must contain exactly 15 slot assignments.")

    if len(request.bench_player_ids) != 8:
        raise SelectionValidationError("Bench must contain exactly 8 players.")

    slots = [assignment.slot for assignment in request.starting_lineup]
    if Counter(slots) != Counter(LINEUP_SLOTS):
        raise SelectionValidationError("Starting lineup must fill the standard XV slots.")

    starter_ids = [assignment.player_id for assignment in request.starting_lineup]
    matchday_ids = starter_ids + request.bench_player_ids
    if len(set(matchday_ids)) != 23:
        raise SelectionValidationError("Matchday squad must contain 23 unique players.")

    for assignment in request.starting_lineup:
        player = players_by_id.get(assignment.player_id)
        if player is None:
            raise SelectionValidationError(f"Unknown player {assignment.player_id} in lineup.")
        if player.injury_weeks_remaining > 0 or player.suspended_matches > 0 or player.id in blocked_player_ids:
            raise SelectionValidationError(f"{player.first_name} {player.last_name} is unavailable.")
        if not player_can_cover_slot(player, assignment.slot):
            raise SelectionValidationError(
                f"{player.first_name} {player.last_name} cannot reasonably start at {assignment.slot}."
            )

    bench = [players_by_id.get(player_id) for player_id in request.bench_player_ids]
    if any(player is None for player in bench):
        raise SelectionValidationError("Bench contains an unknown player.")

    front_row_cover = sum(
        player.primary_position in {"Loosehead Prop", "Hooker", "Tighthead Prop"} or
        any(pos in {"Loosehead Prop", "Hooker", "Tighthead Prop"} for pos in player.secondary_positions)
        for player in bench
        if player
    )
    pack_cover = sum(
        player.primary_position in {"Lock", "Blindside Flanker", "Openside Flanker", "Number 8"}
        for player in bench
        if player
    )
    spine_cover = sum(
        player.primary_position in {"Scrumhalf", "Flyhalf", "Inside Centre", "Fullback"}
        or any(pos in {"Scrumhalf", "Flyhalf", "Inside Centre", "Fullback"} for pos in player.secondary_positions)
        for player in bench
        if player
    )
    if front_row_cover < 2 or pack_cover < 1 or spine_cover < 2:
        raise SelectionValidationError("Bench composition is not positionally coherent for an MVP matchday squad.")

    if request.captain_id not in matchday_ids:
        raise SelectionValidationError("Captain must be part of the matchday 23.")
    if request.goal_kicker_id not in matchday_ids:
        raise SelectionValidationError("Goal kicker must be part of the matchday 23.")


def build_best_selection(players: list[Player], *, blocked_player_ids: set[int] | None = None) -> SelectionUpdateRequest:
    blocked_player_ids = blocked_player_ids or set()
    available = [
        player
        for player in players
        if player.injury_weeks_remaining == 0 and player.suspended_matches == 0 and player.id not in blocked_player_ids
    ]
    chosen_ids: set[int] = set()
    starting_lineup = []
    for slot in LINEUP_SLOTS:
        eligible = [
            player for player in available
            if player.id not in chosen_ids and (player.primary_position == slot or slot in player.secondary_positions)
        ]
        if not eligible:
            eligible = [player for player in available if player.id not in chosen_ids]
        player = sorted(
            eligible,
            key=lambda candidate: (
                candidate.primary_position != slot,
                -candidate.overall_rating,
                -candidate.fitness,
                candidate.fatigue,
            ),
        )[0]
        starting_lineup.append(SelectionSlotRead(slot=slot, player_id=player.id))
        chosen_ids.add(player.id)

    remaining = [player for player in available if player.id not in chosen_ids]
    front_rows = sorted(
        [
            player
            for player in remaining
            if player.primary_position in {"Loosehead Prop", "Hooker", "Tighthead Prop"}
            or any(position in {"Loosehead Prop", "Hooker", "Tighthead Prop"} for position in player.secondary_positions)
        ],
        key=lambda player: (-player.overall_rating, -player.fitness),
    )[:2]
    chosen_bench = {player.id for player in front_rows}
    bench = front_rows[:]
    pack_cover = next(
        (
            player
            for player in sorted(remaining, key=lambda candidate: (-candidate.overall_rating, -candidate.fitness))
            if player.id not in chosen_bench
            and player.primary_position in {"Lock", "Blindside Flanker", "Openside Flanker", "Number 8"}
        ),
        None,
    )
    if pack_cover:
        bench.append(pack_cover)
        chosen_bench.add(pack_cover.id)
    spine_candidates = [
        player
        for player in sorted(remaining, key=lambda candidate: (-candidate.overall_rating, -candidate.fitness))
        if player.id not in chosen_bench
        and (
            player.primary_position in {"Scrumhalf", "Flyhalf", "Inside Centre", "Fullback"}
            or any(position in {"Scrumhalf", "Flyhalf", "Inside Centre", "Fullback"} for position in player.secondary_positions)
        )
    ][:2]
    for player in spine_candidates:
        bench.append(player)
        chosen_bench.add(player.id)
    for player in sorted(remaining, key=lambda candidate: (-candidate.overall_rating, -candidate.fitness)):
        if player.id in chosen_bench:
            continue
        bench.append(player)
        chosen_bench.add(player.id)
        if len(bench) == 8:
            break

    matchday = [player for player in available if player.id in {slot.player_id for slot in starting_lineup} | {player.id for player in bench[:8]}]
    captain = max(matchday, key=lambda player: (player.leadership, player.overall_rating))
    kicker = max(matchday, key=lambda player: (player.goal_kicking, player.kicking_hand, player.overall_rating))
    request = SelectionUpdateRequest(
        starting_lineup=starting_lineup,
        bench_player_ids=[player.id for player in bench[:8]],
        captain_id=captain.id,
        goal_kicker_id=kicker.id,
    )
    validate_selection(players, request, blocked_player_ids=blocked_player_ids)
    return request
