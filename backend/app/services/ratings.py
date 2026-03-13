from __future__ import annotations

from typing import TypedDict

from backend.app.models.entities import Player


class DerivedRatings(TypedDict):
    attack_rating: int
    defense_rating: int
    set_piece_rating: int
    game_management_rating: int


def _clamp_rating(value: float) -> int:
    return max(1, min(99, round(value)))


def compute_derived_ratings(player: Player) -> DerivedRatings:
    attack = (
        player.speed * 0.18
        + player.handling * 0.16
        + player.passing * 0.14
        + player.kicking_hand * 0.08
        + player.decision_making * 0.12
        + player.composure * 0.1
        + player.strength * 0.12
        + player.breakdown * 0.1
    )
    defense = (
        player.tackling * 0.28
        + player.strength * 0.16
        + player.endurance * 0.12
        + player.breakdown * 0.14
        + player.discipline * 0.14
        + player.decision_making * 0.16
    )
    set_piece = (
        player.scrum * 0.35
        + player.lineout * 0.28
        + player.strength * 0.17
        + player.handling * 0.08
        + player.leadership * 0.12
    )
    management = (
        player.kicking_hand * 0.2
        + player.goal_kicking * 0.16
        + player.passing * 0.14
        + player.decision_making * 0.2
        + player.composure * 0.16
        + player.leadership * 0.14
    )
    return {
        "attack_rating": _clamp_rating(attack),
        "defense_rating": _clamp_rating(defense),
        "set_piece_rating": _clamp_rating(set_piece),
        "game_management_rating": _clamp_rating(management),
    }


def compute_overall(player: Player) -> int:
    ratings = compute_derived_ratings(player)
    overall = (
        ratings["attack_rating"] * 0.29
        + ratings["defense_rating"] * 0.29
        + ratings["set_piece_rating"] * 0.2
        + ratings["game_management_rating"] * 0.12
        + player.endurance * 0.1
    )
    return _clamp_rating(overall)
