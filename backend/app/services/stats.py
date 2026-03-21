from __future__ import annotations

from sqlmodel import Session, select

from backend.app.models.entities import Player, PlayerSeasonStats, SaveGame, Team
from backend.app.simulation.engine import PlayerMatchStats, SimulationResult


def _compute_match_rating(ps: PlayerMatchStats, team_won: bool) -> float:
    rating = 6.0
    rating += ps.tries_scored * 1.5
    rating += ps.conversions * 0.3
    rating += ps.penalty_goals * 0.3
    rating += ps.drop_goals * 0.5
    rating += ps.tackles_made * 0.02
    rating -= ps.yellow_cards * 0.5
    rating -= ps.red_cards * 1.0
    if team_won:
        rating += 0.5
    return max(1.0, min(10.0, round(rating, 1)))


def record_player_match_stats(
    session: Session,
    save: SaveGame,
    home_team_id: int,
    away_team_id: int,
    simulation: SimulationResult,
) -> None:
    home_won = simulation.home.score > simulation.away.score

    best_rating = 0.0
    best_player_id: int | None = None

    for team_id, team_state, won in [
        (home_team_id, simulation.home, home_won),
        (away_team_id, simulation.away, not home_won),
    ]:
        for player_id, ps in team_state.player_stats.items():
            rating = _compute_match_rating(ps, won)

            row = session.exec(
                select(PlayerSeasonStats).where(
                    PlayerSeasonStats.save_game_id == save.id,
                    PlayerSeasonStats.player_id == player_id,
                    PlayerSeasonStats.season_number == save.season_number,
                )
            ).first()

            if not row:
                row = PlayerSeasonStats(
                    save_game_id=save.id,
                    player_id=player_id,
                    team_id=team_id,
                    season_number=save.season_number,
                )
                session.add(row)

            row.appearances += 1
            if ps.started:
                row.starts += 1
            row.minutes_played += ps.minutes_played
            row.tries_scored += ps.tries_scored
            row.conversions += ps.conversions
            row.penalty_goals += ps.penalty_goals
            row.drop_goals += ps.drop_goals
            row.tackles_made += ps.tackles_made
            row.tackles_missed += ps.tackles_missed
            row.carries += ps.carries
            row.line_breaks += ps.line_breaks
            row.yellow_cards += ps.yellow_cards
            row.red_cards += ps.red_cards
            row.injuries_sustained += ps.injuries_sustained
            row.total_match_rating += rating

            if rating > best_rating:
                best_rating = rating
                best_player_id = player_id

    if best_player_id is not None:
        mom_row = session.exec(
            select(PlayerSeasonStats).where(
                PlayerSeasonStats.save_game_id == save.id,
                PlayerSeasonStats.player_id == best_player_id,
                PlayerSeasonStats.season_number == save.season_number,
            )
        ).first()
        if mom_row:
            mom_row.man_of_match += 1


def _season_stats_to_dict(row: PlayerSeasonStats) -> dict:
    apps = max(1, row.appearances)
    total_points = row.tries_scored * 5 + row.conversions * 2 + row.penalty_goals * 3 + row.drop_goals * 3
    total_tackles = row.tackles_made + row.tackles_missed
    return {
        "season_number": row.season_number,
        "appearances": row.appearances,
        "starts": row.starts,
        "minutes_played": row.minutes_played,
        "tries_scored": row.tries_scored,
        "conversions": row.conversions,
        "penalty_goals": row.penalty_goals,
        "drop_goals": row.drop_goals,
        "total_points": total_points,
        "tackles_made": row.tackles_made,
        "tackles_missed": row.tackles_missed,
        "tackle_success": round(100 * row.tackles_made / max(1, total_tackles), 1),
        "carries": row.carries,
        "line_breaks": row.line_breaks,
        "yellow_cards": row.yellow_cards,
        "red_cards": row.red_cards,
        "injuries_sustained": row.injuries_sustained,
        "man_of_match": row.man_of_match,
        "average_rating": round(row.total_match_rating / apps, 1),
    }


def get_player_detail(session: Session, save: SaveGame, player_id: int) -> dict:
    from backend.app.services.game import serialize_player

    player = session.get(Player, player_id)
    if not player:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Player not found.")

    team = session.get(Team, player.team_id) if player.team_id else None

    stats_rows = session.exec(
        select(PlayerSeasonStats)
        .where(
            PlayerSeasonStats.save_game_id == save.id,
            PlayerSeasonStats.player_id == player_id,
        )
        .order_by(PlayerSeasonStats.season_number)
    ).all()

    career = [_season_stats_to_dict(row) for row in stats_rows]
    current = next((s for s in career if s["season_number"] == save.season_number), None)

    return {
        "player": serialize_player(player),
        "team_name": team.name if team else "Free Agent",
        "current_season": current,
        "career": career,
    }


def get_squad_season_stats(session: Session, save: SaveGame, team_id: int) -> dict:
    from backend.app.services.game import serialize_player

    players = session.exec(select(Player).where(Player.team_id == team_id)).all()
    stats_rows = session.exec(
        select(PlayerSeasonStats).where(
            PlayerSeasonStats.save_game_id == save.id,
            PlayerSeasonStats.team_id == team_id,
            PlayerSeasonStats.season_number == save.season_number,
        )
    ).all()

    stats_by_player = {row.player_id: _season_stats_to_dict(row) for row in stats_rows}

    result = []
    for player in players:
        entry = {
            "id": player.id,
            "name": f"{player.first_name} {player.last_name}",
            "primary_position": player.primary_position,
            "overall_rating": player.overall_rating,
            "age": player.age,
        }
        if player.id in stats_by_player:
            entry["stats"] = stats_by_player[player.id]
        else:
            entry["stats"] = None
        result.append(entry)

    return {
        "season_number": save.season_number,
        "players": result,
    }
