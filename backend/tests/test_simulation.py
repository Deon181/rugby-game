from statistics import mean

from sqlmodel import select

from backend.app.models.entities import Player, Team, TeamTactics
from backend.app.simulation.engine import build_team_profile, simulate_match
from backend.tests.helpers import create_test_save, team_bundle


def _score_diffs(results):
    return [result.home.score - result.away.score for result in results]


def _clone_player(player: Player) -> Player:
    return Player.model_validate(player.model_dump())


def _clone_tactics(tactics: TeamTactics) -> TeamTactics:
    return TeamTactics.model_validate(tactics.model_dump())


def test_stronger_team_generally_outperforms_weaker_team(session):
    create_test_save(session)
    teams = [team_bundle(session, team.id) for team in session.exec(select(Team)).all()]
    teams.sort(key=lambda bundle: bundle[0].reputation, reverse=True)
    strong_team, strong_players, strong_selection, strong_tactics = teams[0]
    weak_team, weak_players, weak_selection, weak_tactics = teams[-1]
    strong_profile = build_team_profile(strong_team, strong_players, strong_selection, strong_tactics)
    weak_profile = build_team_profile(weak_team, weak_players, weak_selection, weak_tactics)

    results = [simulate_match(strong_profile, weak_profile, seed=seed) for seed in range(1, 41)]
    assert mean(_score_diffs(results)) > 5


def test_expansive_tactics_increase_line_breaks(session):
    save = create_test_save(session)
    home_team, home_players, home_selection, home_tactics = team_bundle(session, save.user_team_id)
    away_team, away_players, away_selection, away_tactics = team_bundle(session, save.user_team_id + 1)

    expansive_tactics = _clone_tactics(home_tactics)
    expansive_tactics.attacking_style = "expansive"
    expansive_tactics.goal_choice = "kick to corner"
    conservative_tactics = _clone_tactics(home_tactics)
    conservative_tactics.attacking_style = "forward-oriented"
    conservative_tactics.goal_choice = "go for posts"

    expansive_profile = build_team_profile(home_team, home_players, home_selection, expansive_tactics)
    conservative_profile = build_team_profile(home_team, home_players, home_selection, conservative_tactics)
    away_profile = build_team_profile(away_team, away_players, away_selection, away_tactics)

    expansive = [simulate_match(expansive_profile, away_profile, seed=100 + seed) for seed in range(25)]
    conservative = [simulate_match(conservative_profile, away_profile, seed=100 + seed) for seed in range(25)]

    assert mean(result.home.line_breaks for result in expansive) >= mean(result.home.line_breaks for result in conservative)


def test_exhausted_team_underperforms_fresh_team(session):
    save = create_test_save(session)
    team, players, selection, tactics = team_bundle(session, save.user_team_id)
    opponent_team, opponent_players, opponent_selection, opponent_tactics = team_bundle(session, save.user_team_id + 1)

    fresh_profile = build_team_profile(team, players, selection, tactics)
    tired_players = []
    for player in players:
        clone = _clone_player(player)
        clone.fatigue = 70
        clone.fitness = 55
        tired_players.append(clone)
    tired_profile = build_team_profile(team, tired_players, selection, tactics)
    opponent_profile = build_team_profile(opponent_team, opponent_players, opponent_selection, opponent_tactics)

    fresh_results = [simulate_match(fresh_profile, opponent_profile, seed=200 + seed) for seed in range(25)]
    tired_results = [simulate_match(tired_profile, opponent_profile, seed=200 + seed) for seed in range(25)]

    assert mean(result.home.score for result in fresh_results) > mean(result.home.score for result in tired_results)


def test_low_discipline_team_concedes_more_penalties(session):
    save = create_test_save(session)
    team, players, selection, tactics = team_bundle(session, save.user_team_id)
    opponent_team, opponent_players, opponent_selection, opponent_tactics = team_bundle(session, save.user_team_id + 1)

    disciplined_players = [_clone_player(player) for player in players]
    ill_disciplined_players = []
    for player in players:
        clone = _clone_player(player)
        clone.discipline = 35
        ill_disciplined_players.append(clone)

    disciplined_profile = build_team_profile(team, disciplined_players, selection, tactics)
    ill_disciplined_profile = build_team_profile(team, ill_disciplined_players, selection, tactics)
    opponent_profile = build_team_profile(opponent_team, opponent_players, opponent_selection, opponent_tactics)

    disciplined = [simulate_match(disciplined_profile, opponent_profile, seed=300 + seed) for seed in range(25)]
    ill_disciplined = [simulate_match(ill_disciplined_profile, opponent_profile, seed=300 + seed) for seed in range(25)]

    assert mean(result.home.penalties_conceded for result in ill_disciplined) >= mean(
        result.home.penalties_conceded for result in disciplined
    )
