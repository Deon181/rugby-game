from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from backend.app.models.entities import Player, PlayerMedicalAssignment, Team, TeamSelection, TeamTactics, WeeklyPerformancePlan
from backend.app.services.ratings import compute_derived_ratings
from backend.app.simulation.config import CONFIG


@dataclass
class SelectedPlayer:
    player: Player
    slot: str
    is_starter: bool
    injury_risk_multiplier: float = 1.0
    managed_return: bool = False


@dataclass
class TeamProfile:
    team: Team
    tactics: TeamTactics
    starters: list[SelectedPlayer]
    bench: list[SelectedPlayer]
    captain: Player
    goal_kicker: Player
    attack: float
    defense: float
    set_piece: float
    management: float
    discipline: float
    breakdown: float
    fitness: float
    fatigue: float
    morale: float
    bench_impact: float
    tackle_efficiency: float
    scrum_success: float
    lineout_success: float
    line_break_threat: float
    position_fit: float
    injury_risk_multiplier: float


@dataclass
class PlayerOutcome:
    player_id: int
    fatigue_delta: int = 0
    fitness_delta: int = 0
    morale_delta: int = 0
    form_delta: int = 0
    injury_status: str | None = None
    injury_weeks_remaining: int = 0
    suspended_matches_delta: int = 0


@dataclass
class TeamState:
    profile: TeamProfile
    score: int = 0
    tries: int = 0
    penalties: int = 0
    conversions: int = 0
    drop_goals: int = 0
    possession_points: float = 0.0
    territory_points: float = 0.0
    penalties_conceded: int = 0
    turnovers: int = 0
    tackles_made: int = 0
    tackles_missed: int = 0
    line_breaks: int = 0
    scrum_attempts: int = 0
    scrum_wins: int = 0
    lineout_attempts: int = 0
    lineout_wins: int = 0
    cards: int = 0
    commentary: list[dict[str, Any]] = field(default_factory=list)
    outcomes: dict[int, PlayerOutcome] = field(default_factory=dict)


@dataclass
class BlockSimulation:
    minute: int
    commentary: list[dict[str, Any]]
    home_possession: float
    away_possession: float
    home_territory: float
    away_territory: float
    ball_position: int


@dataclass
class SimulationResult:
    home: TeamState
    away: TeamState
    summary: str
    commentary: list[dict[str, Any]]
    stats: dict[str, Any]


TEAM_STATE_FIELDS = (
    "score",
    "tries",
    "penalties",
    "conversions",
    "drop_goals",
    "possession_points",
    "territory_points",
    "penalties_conceded",
    "turnovers",
    "tackles_made",
    "tackles_missed",
    "line_breaks",
    "scrum_attempts",
    "scrum_wins",
    "lineout_attempts",
    "lineout_wins",
    "cards",
)


def build_team_profile(
    team: Team,
    players: list[Player],
    selection: TeamSelection,
    tactics: TeamTactics,
    performance_plan: WeeklyPerformancePlan | None = None,
    medical_assignments: dict[int, PlayerMedicalAssignment] | None = None,
) -> TeamProfile:
    players_by_id = {player.id: player for player in players}
    starters = [
        SelectedPlayer(
            player=players_by_id[entry["player_id"]],
            slot=entry["slot"],
            is_starter=True,
            injury_risk_multiplier=(
                1.25
                if medical_assignments
                and (assignment := medical_assignments.get(entry["player_id"]))
                and assignment.clearance_status == "managed"
                else 1.0
            ),
            managed_return=bool(
                medical_assignments
                and (assignment := medical_assignments.get(entry["player_id"]))
                and assignment.clearance_status == "managed"
            ),
        )
        for entry in selection.starting_lineup
    ]
    bench = [
        SelectedPlayer(
            player=players_by_id[player_id],
            slot=players_by_id[player_id].primary_position,
            is_starter=False,
            injury_risk_multiplier=(
                1.1
                if medical_assignments
                and (assignment := medical_assignments.get(player_id))
                and assignment.clearance_status == "managed"
                else 1.0
            ),
            managed_return=bool(
                medical_assignments
                and (assignment := medical_assignments.get(player_id))
                and assignment.clearance_status == "managed"
            ),
        )
        for player_id in selection.bench_player_ids
    ]
    captain = players_by_id[selection.captain_id]
    goal_kicker = players_by_id[selection.goal_kicker_id]

    attack_values = []
    defense_values = []
    set_piece_values = []
    management_values = []
    discipline_values = []
    breakdown_values = []
    fitness_values = []
    fatigue_values = []
    morale_values = []
    fit_scores = []
    tackle_scores = []
    scrum_scores = []
    lineout_scores = []
    line_break_scores = []

    for selected in starters:
        player = selected.player
        ratings = compute_derived_ratings(player)
        fit = 1.0 if player.primary_position == selected.slot else 0.93
        attack_values.append(ratings["attack_rating"] * fit)
        defense_values.append(ratings["defense_rating"] * fit)
        set_piece_values.append(ratings["set_piece_rating"] * fit)
        management_values.append(ratings["game_management_rating"] * fit)
        discipline_values.append(player.discipline)
        breakdown_values.append(player.breakdown)
        fitness_values.append(player.fitness)
        fatigue_values.append(player.fatigue)
        morale_values.append(player.morale)
        fit_scores.append(fit)
        tackle_scores.append((player.tackling + player.decision_making) / 2)
        scrum_scores.append(player.scrum)
        lineout_scores.append(player.lineout)
        line_break_scores.append((player.speed + player.handling + player.decision_making) / 3)

    bench_rating = sum(player.player.overall_rating for player in bench) / max(1, len(bench))
    intensity_bonus = 0
    contact_defense_bonus = 0
    contact_set_piece_bonus = 0
    discipline_penalty = 0
    injury_multiplier = max(0.82, 1 - (team.staff_fitness - 68) / 320)
    if performance_plan:
        if performance_plan.intensity == "heavy":
            intensity_bonus = 1
            injury_multiplier *= 1.05
        elif performance_plan.intensity == "light":
            intensity_bonus = -1
            injury_multiplier *= 0.95
        if performance_plan.contact_level == "low":
            contact_defense_bonus = -1
            contact_set_piece_bonus = -1
            injury_multiplier *= 0.85
        elif performance_plan.contact_level == "high":
            contact_defense_bonus = 1
            contact_set_piece_bonus = 1
            discipline_penalty = 1
            injury_multiplier *= 1.2

    return TeamProfile(
        team=team,
        tactics=tactics,
        starters=starters,
        bench=bench,
        captain=captain,
        goal_kicker=goal_kicker,
        attack=(sum(attack_values) / len(attack_values)) + (2 if tactics.training_focus == "attack" else 0) + intensity_bonus,
        defense=(sum(defense_values) / len(defense_values)) + (2 if tactics.training_focus == "defense" else 0) + intensity_bonus + contact_defense_bonus,
        set_piece=(sum(set_piece_values) / len(set_piece_values)) + (2 if tactics.training_focus == "set_piece" else 0) + contact_set_piece_bonus,
        management=sum(management_values) / len(management_values),
        discipline=(sum(discipline_values) / len(discipline_values)) - discipline_penalty,
        breakdown=sum(breakdown_values) / len(breakdown_values),
        fitness=(sum(fitness_values) / len(fitness_values)) + (2 if tactics.training_focus == "fitness" else 0),
        fatigue=max(0, (sum(fatigue_values) / len(fatigue_values)) - (3 if tactics.training_focus == "recovery" else 0)),
        morale=sum(morale_values) / len(morale_values),
        bench_impact=bench_rating,
        tackle_efficiency=sum(tackle_scores) / len(tackle_scores),
        scrum_success=sum(scrum_scores) / len(scrum_scores),
        lineout_success=sum(lineout_scores) / len(lineout_scores),
        line_break_threat=sum(line_break_scores) / len(line_break_scores),
        position_fit=sum(fit_scores) / len(fit_scores),
        injury_risk_multiplier=injury_multiplier,
    )


def initialize_team_state(profile: TeamProfile) -> TeamState:
    return TeamState(profile=profile)


def serialize_team_state(state: TeamState) -> dict[str, Any]:
    return {
        **{field: getattr(state, field) for field in TEAM_STATE_FIELDS},
        "commentary": state.commentary,
        "outcomes": {str(player_id): outcome.__dict__ for player_id, outcome in state.outcomes.items()},
    }


def hydrate_team_state(profile: TeamProfile, payload: dict[str, Any] | None) -> TeamState:
    state = TeamState(profile=profile)
    if not payload:
        return state
    for field in TEAM_STATE_FIELDS:
        setattr(state, field, payload.get(field, getattr(state, field)))
    state.commentary = list(payload.get("commentary", []))
    state.outcomes = {
        int(player_id): PlayerOutcome(**outcome)
        for player_id, outcome in payload.get("outcomes", {}).items()
    }
    return state


def _modifier(value: str, low: float, high: float) -> float:
    if value in {"low", "safe", "drift", "forward-oriented", "go for posts"}:
        return low
    if value in {"high", "aggressive", "rush", "expansive", "kick to corner"}:
        return high
    return 1.0


def _team_power(profile: TeamProfile, minute: int, home: bool, cards: int = 0) -> dict[str, float]:
    late_game_boost = 1 + max(0, minute - 50) / 200 * ((profile.bench_impact - 68) / 18)
    fatigue_penalty = 1 - (profile.fatigue / 300)
    fitness_boost = 1 + (profile.fitness - 75) / 250
    morale_boost = 1 + (profile.morale - 70) / 250
    home_boost = 1.02 if home else 1.0
    card_penalty = max(0.76, 1 - cards * 0.12)

    attack = profile.attack * late_game_boost * fatigue_penalty * fitness_boost * card_penalty
    defense = profile.defense * fatigue_penalty * morale_boost * card_penalty
    territory = (
        profile.management * _modifier(profile.tactics.kicking_approach, 0.94, 1.08)
        + profile.set_piece * _modifier(profile.tactics.set_piece_intent, 0.97, 1.07)
        + (CONFIG.home_advantage if home else 0)
    ) * home_boost * max(0.84, card_penalty)
    discipline = profile.discipline * _modifier(profile.tactics.ruck_commitment, 1.05, 0.93)
    return {
        "attack": attack * _modifier(profile.tactics.attacking_style, 0.98, 1.08) * profile.position_fit,
        "defense": defense * _modifier(profile.tactics.defensive_system, 0.97, 1.05),
        "territory": territory,
        "discipline": discipline,
        "set_piece": profile.set_piece * _modifier(profile.tactics.set_piece_intent, 0.98, 1.08) * card_penalty,
        "breakdown": profile.breakdown * _modifier(profile.tactics.ruck_commitment, 0.96, 1.08) * card_penalty,
        "line_break": profile.line_break_threat * _modifier(profile.tactics.attacking_style, 0.96, 1.08) * card_penalty,
        "goal": profile.goal_kicker.goal_kicking * _modifier(profile.tactics.goal_choice, 1.05, 0.95),
    }


def _choice(rng: random.Random, weighted_options: list[tuple[str, float]]) -> str:
    total = sum(weight for _, weight in weighted_options)
    roll = rng.random() * total
    cursor = 0.0
    for option, weight in weighted_options:
        cursor += weight
        if roll <= cursor:
            return option
    return weighted_options[-1][0]


def _commentary(minute: int, team_name: str, text: str, event_type: str, field_position: int) -> dict[str, Any]:
    return {
        "minute": minute,
        "team": team_name,
        "type": event_type,
        "text": text,
        "field_position": field_position,
    }


def _pick_involved_player(rng: random.Random, selected_players: list[SelectedPlayer], key: str) -> Player:
    if key == "finisher":
        sorted_players = sorted(
            selected_players,
            key=lambda selected: (selected.player.speed + selected.player.handling + selected.player.composure),
            reverse=True,
        )
    elif key == "forward":
        sorted_players = sorted(
            selected_players,
            key=lambda selected: (selected.player.strength + selected.player.breakdown + selected.player.tackling),
            reverse=True,
        )
    else:
        sorted_players = sorted(
            selected_players,
            key=lambda selected: (selected.player.goal_kicking + selected.player.kicking_hand + selected.player.decision_making),
            reverse=True,
        )
    return rng.choice(sorted_players[: max(3, len(sorted_players) // 2)]).player


def _pick_injury_target(rng: random.Random, selected_players: list[SelectedPlayer]) -> SelectedPlayer:
    weights = [selected.injury_risk_multiplier for selected in selected_players]
    return rng.choices(selected_players, weights=weights, k=1)[0]


def _ensure_outcome(state: TeamState, player: Player) -> PlayerOutcome:
    return state.outcomes.setdefault(player.id, PlayerOutcome(player_id=player.id))


def _block_rng(seed: int, block_index: int) -> random.Random:
    return random.Random(seed + block_index * 104_729)


def _field_position(rng: random.Random, home_attacking: bool, pressure: float) -> int:
    swing = 18 + pressure * 28
    centre = 50 + swing if home_attacking else 50 - swing
    return round(max(4, min(96, centre + rng.uniform(-12, 12))))


def _ball_position_from_territory(home_territory: float, home_possession: float) -> int:
    return round(max(6, min(94, home_territory * 0.72 + home_possession * 0.28)))


def simulate_block(
    home_profile: TeamProfile,
    away_profile: TeamProfile,
    home_state: TeamState,
    away_state: TeamState,
    *,
    seed: int,
    block_index: int,
) -> BlockSimulation:
    rng = _block_rng(seed, block_index)
    minute = block_index * CONFIG.block_minutes + CONFIG.block_minutes
    home_power = _team_power(home_profile, minute, home=True, cards=home_state.cards)
    away_power = _team_power(away_profile, minute, home=False, cards=away_state.cards)

    territory_total = home_power["territory"] + away_power["territory"]
    home_territory = max(35.0, min(65.0, 100 * home_power["territory"] / territory_total + rng.uniform(-5, 5)))
    home_possession = max(
        38.0,
        min(
            62.0,
            100
            * (home_power["breakdown"] + home_power["attack"])
            / (home_power["breakdown"] + away_power["breakdown"] + home_power["attack"] + away_power["attack"])
            + rng.uniform(-4, 4),
        ),
    )
    away_territory = 100 - home_territory
    away_possession = 100 - home_possession
    home_state.territory_points += home_territory
    away_state.territory_points += away_territory
    home_state.possession_points += home_possession
    away_state.possession_points += away_possession

    home_entries = max(1, round((home_power["attack"] / 36 + home_territory / 34 + rng.uniform(-0.7, 0.7))))
    away_entries = max(1, round((away_power["attack"] / 36 + away_territory / 34 + rng.uniform(-0.7, 0.7))))

    block_commentary: list[dict[str, Any]] = []

    if abs(home_territory - away_territory) > 8:
        dominant = home_state if home_territory > away_territory else away_state
        block_commentary.append(
            _commentary(
                minute - 5,
                dominant.profile.team.name,
                "They are pinning the opposition deep with a sustained territorial spell.",
                "territory",
                72 if dominant is home_state else 28,
            )
        )

    for offense_state, defense_state, entries, territory_share in (
        (home_state, away_state, home_entries, home_territory / 100),
        (away_state, home_state, away_entries, away_territory / 100),
    ):
        offense_is_home = offense_state is home_state
        offense_power = home_power if offense_is_home else away_power
        defense_power = away_power if offense_is_home else home_power
        for _ in range(entries):
            source = _choice(
                rng,
                [
                    ("set_piece", max(1.0, offense_power["set_piece"] / 20)),
                    ("phase_play", max(1.0, offense_power["attack"] / 18)),
                    ("kick_return", max(0.8, offense_power["line_break"] / 24)),
                ],
            )

            if source == "set_piece":
                offense_state.scrum_attempts += 1
                defense_state.scrum_attempts += 1
                if rng.random() < (offense_power["set_piece"] / (offense_power["set_piece"] + defense_power["set_piece"])):
                    offense_state.scrum_wins += 1
                else:
                    defense_state.scrum_wins += 1
                offense_state.lineout_attempts += 1
                defense_state.lineout_attempts += 1
                if rng.random() < (offense_power["set_piece"] / (offense_power["set_piece"] + defense_power["set_piece"])):
                    offense_state.lineout_wins += 1
                else:
                    defense_state.lineout_wins += 1

            pressure = (
                offense_power["attack"] * 0.45
                + offense_power["set_piece"] * (0.18 if source == "set_piece" else 0.08)
                + offense_power["line_break"] * 0.18
                + offense_power["breakdown"] * 0.12
            )
            resistance = defense_power["defense"] * 0.5 + defense_power["discipline"] * 0.18 + defense_power["breakdown"] * 0.16
            swing = pressure - resistance + rng.uniform(-10, 10)
            penalty_bias = max(0.04, (76 - defense_power["discipline"]) / 90)
            field_position = _field_position(rng, offense_is_home, territory_share)

            if swing > 8:
                finisher = _pick_involved_player(rng, offense_state.profile.starters, "finisher")
                offense_state.tries += 1
                offense_state.score += 5
                offense_state.line_breaks += 1
                offense_state.tackles_made += rng.randint(1, 3)
                defense_state.tackles_missed += rng.randint(1, 2)
                conversion_success = rng.random() < min(0.95, 0.45 + offense_power["goal"] / 110)
                if conversion_success:
                    offense_state.conversions += 1
                    offense_state.score += 2
                block_commentary.append(
                    _commentary(
                        max(1, minute - rng.randint(0, CONFIG.block_minutes - 1)),
                        offense_state.profile.team.name,
                        f"{finisher.first_name} {finisher.last_name} slices through for a try after sustained pressure.",
                        "try",
                        field_position,
                    )
                )
                outcome = _ensure_outcome(offense_state, finisher)
                outcome.form_delta += 4
                outcome.morale_delta += 3
            elif rng.random() < penalty_bias:
                defense_state.penalties_conceded += 1
                if rng.random() < (0.55 if offense_state.profile.tactics.goal_choice == "go for posts" else 0.28):
                    success = rng.random() < min(0.92, 0.42 + offense_power["goal"] / 105)
                    kicker = offense_state.profile.goal_kicker
                    if success:
                        offense_state.penalties += 1
                        offense_state.score += 3
                        block_commentary.append(
                            _commentary(
                                max(1, minute - rng.randint(0, CONFIG.block_minutes - 1)),
                                offense_state.profile.team.name,
                                f"{kicker.first_name} {kicker.last_name} keeps calm and knocks over the penalty.",
                                "penalty-goal",
                                field_position,
                            )
                        )
                    else:
                        block_commentary.append(
                            _commentary(
                                max(1, minute - rng.randint(0, CONFIG.block_minutes - 1)),
                                offense_state.profile.team.name,
                                "The penalty attempt drifts wide, and the pressure goes begging.",
                                "missed-penalty",
                                field_position,
                            )
                        )
                else:
                    maul_success = rng.random() < min(0.72, 0.25 + offense_power["set_piece"] / 125 + offense_power["attack"] / 180)
                    if maul_success:
                        forward = _pick_involved_player(rng, offense_state.profile.starters, "forward")
                        offense_state.tries += 1
                        offense_state.score += 5
                        conversion_success = rng.random() < min(0.92, 0.4 + offense_power["goal"] / 110)
                        if conversion_success:
                            offense_state.conversions += 1
                            offense_state.score += 2
                        block_commentary.append(
                            _commentary(
                                max(1, minute - rng.randint(0, CONFIG.block_minutes - 1)),
                                offense_state.profile.team.name,
                                f"They kick to the corner, drive the maul, and {forward.first_name} {forward.last_name} crashes over.",
                                "maul-try",
                                field_position,
                            )
                        )
                    else:
                        block_commentary.append(
                            _commentary(
                                max(1, minute - rng.randint(0, CONFIG.block_minutes - 1)),
                                offense_state.profile.team.name,
                                "They kick to the corner but the defending pack survives the maul threat.",
                                "maul-stop",
                                field_position,
                            )
                        )
            elif swing > 0:
                offense_state.line_breaks += 1 if rng.random() < 0.35 else 0
                defense_state.turnovers += 1 if rng.random() < 0.28 else 0
                offense_state.tackles_made += rng.randint(0, 1)
                defense_state.tackles_made += rng.randint(2, 5)
                if minute > 60 and rng.random() < 0.05 and offense_state.profile.tactics.kicking_approach != "low":
                    if rng.random() < 0.32 + offense_power["goal"] / 180:
                        offense_state.drop_goals += 1
                        offense_state.score += 3
                        block_commentary.append(
                            _commentary(
                                max(1, minute - rng.randint(0, CONFIG.block_minutes - 1)),
                                offense_state.profile.team.name,
                                "Space opens just outside the 22 and they slot a composed drop goal.",
                                "drop-goal",
                                field_position,
                            )
                        )
            else:
                offense_state.turnovers += 1
                offense_state.tackles_made += rng.randint(1, 3)
                defense_state.tackles_made += rng.randint(2, 5)
                if rng.random() < 0.15:
                    block_commentary.append(
                        _commentary(
                            max(1, minute - rng.randint(0, CONFIG.block_minutes - 1)),
                            defense_state.profile.team.name,
                            "A dominant tackle jars the ball loose and relieves the pressure.",
                            "turnover",
                            max(8, min(92, 100 - field_position)),
                        )
                    )

    for state in (home_state, away_state):
        injury_risk = (0.008 + max(0, state.profile.fatigue - 22) / 1600) * state.profile.injury_risk_multiplier
        if rng.random() < injury_risk:
            selected = _pick_injury_target(rng, state.profile.starters + state.profile.bench)
            injured = selected.player
            weeks = rng.randint(1, 4)
            if selected.managed_return and rng.random() < 0.45:
                weeks = min(5, weeks + 1)
            outcome = _ensure_outcome(state, injured)
            outcome.injury_status = "Hamstring strain" if injured.speed > injured.strength else "Shoulder knock"
            outcome.injury_weeks_remaining = weeks
            block_commentary.append(
                _commentary(
                    max(1, minute - rng.randint(0, 4)),
                    state.profile.team.name,
                    f"{injured.first_name} {injured.last_name} is forced off injured and may miss {weeks} week(s).",
                    "injury",
                    _field_position(rng, state is home_state, 0.45),
                )
            )

        card_risk = 0.006 + max(0, 70 - state.profile.discipline) / 1800
        if rng.random() < card_risk:
            offender = rng.choice(state.profile.starters).player
            outcome = _ensure_outcome(state, offender)
            offense_is_red = rng.random() < 0.35
            if offense_is_red:
                state.cards += 1
                outcome.suspended_matches_delta += 1
                block_commentary.append(
                    _commentary(
                        max(1, minute - rng.randint(0, 4)),
                        state.profile.team.name,
                        f"{offender.first_name} {offender.last_name} sees red after repeated indiscipline at the ruck.",
                        "red-card",
                        _field_position(rng, state is home_state, 0.42),
                    )
                )
            else:
                block_commentary.append(
                    _commentary(
                        max(1, minute - rng.randint(0, 4)),
                        state.profile.team.name,
                        f"{offender.first_name} {offender.last_name} is shown yellow for cynical play.",
                        "yellow-card",
                        _field_position(rng, state is home_state, 0.42),
                    )
                )

    if block_index == 5:
        block_commentary.append(
            _commentary(
                58,
                home_profile.team.name if home_profile.bench_impact >= away_profile.bench_impact else away_profile.team.name,
                "The benches are beginning to shape the final quarter, with fresh carriers changing the gain line.",
                "bench-impact",
                52,
            )
        )

    block_commentary.sort(key=lambda event: (event["minute"], event["team"]))
    home_state.commentary.extend(block_commentary)
    away_state.commentary.extend(block_commentary)
    return BlockSimulation(
        minute=minute,
        commentary=block_commentary,
        home_possession=home_possession,
        away_possession=away_possession,
        home_territory=home_territory,
        away_territory=away_territory,
        ball_position=_ball_position_from_territory(home_territory, home_possession),
    )


def build_summary(home_state: TeamState, away_state: TeamState) -> str:
    home_result = "beat" if home_state.score > away_state.score else "drew with" if home_state.score == away_state.score else "fell to"
    return (
        f"{home_state.profile.team.name} {home_result} {away_state.profile.team.name} "
        f"{home_state.score}-{away_state.score} after a contest shaped by territory and set-piece pressure."
    )


def build_stats(home_state: TeamState, away_state: TeamState, *, blocks_played: int) -> dict[str, Any]:
    denominator = max(1, blocks_played)
    return {
        "home": {
            "possession": round(home_state.possession_points / denominator),
            "territory": round(home_state.territory_points / denominator),
            "penalties_conceded": home_state.penalties_conceded,
            "turnovers": home_state.turnovers,
            "tackles_made": home_state.tackles_made,
            "tackles_missed": home_state.tackles_missed,
            "line_breaks": home_state.line_breaks,
            "scrum_success": round(100 * home_state.scrum_wins / max(1, home_state.scrum_attempts)),
            "lineout_success": round(100 * home_state.lineout_wins / max(1, home_state.lineout_attempts)),
            "cards": home_state.cards,
        },
        "away": {
            "possession": round(away_state.possession_points / denominator),
            "territory": round(away_state.territory_points / denominator),
            "penalties_conceded": away_state.penalties_conceded,
            "turnovers": away_state.turnovers,
            "tackles_made": away_state.tackles_made,
            "tackles_missed": away_state.tackles_missed,
            "line_breaks": away_state.line_breaks,
            "scrum_success": round(100 * away_state.scrum_wins / max(1, away_state.scrum_attempts)),
            "lineout_success": round(100 * away_state.lineout_wins / max(1, away_state.lineout_attempts)),
            "cards": away_state.cards,
        },
    }


def build_simulation_result(
    home_state: TeamState,
    away_state: TeamState,
    commentary: list[dict[str, Any]],
    *,
    blocks_played: int = CONFIG.blocks,
) -> SimulationResult:
    combined_commentary = sorted(commentary, key=lambda event: (event["minute"], event["team"]))
    return SimulationResult(
        home=home_state,
        away=away_state,
        summary=build_summary(home_state, away_state),
        commentary=combined_commentary,
        stats=build_stats(home_state, away_state, blocks_played=blocks_played),
    )


def simulate_match(
    home_profile: TeamProfile,
    away_profile: TeamProfile,
    *,
    seed: int,
) -> SimulationResult:
    home_state = initialize_team_state(home_profile)
    away_state = initialize_team_state(away_profile)
    combined_commentary: list[dict[str, Any]] = []
    for block in range(CONFIG.blocks):
        result = simulate_block(home_profile, away_profile, home_state, away_state, seed=seed, block_index=block)
        combined_commentary.extend(result.commentary)
    return build_simulation_result(home_state, away_state, combined_commentary, blocks_played=CONFIG.blocks)
