from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import cycle

from sqlmodel import Session, select

from backend.app.core.constants import (
    ATTRIBUTE_NAMES,
    CLUB_IDENTITIES,
    LINEUP_SLOTS,
    POSITION_PROFILES,
    ROSTER_TEMPLATE,
    SECONDARY_POSITION_MAP,
)
from backend.app.models.entities import (
    Fixture,
    InboxMessage,
    League,
    Player,
    SaveGame,
    Team,
    TeamSelection,
    TeamTactics,
    TransferListing,
)
from backend.app.schemas.api import ClubOption, SelectionUpdateRequest
from backend.app.services.ratings import compute_overall
from backend.app.services.selection import build_best_selection, validate_selection


REGION_POOLS = {
    "South Africa": {
        "first": [
            "Luan",
            "Siyam",
            "Jaco",
            "Mpho",
            "Ruan",
            "Thabo",
            "Kagiso",
            "Nico",
            "Andre",
            "Jaden",
        ],
        "last": [
            "Mbeki",
            "Venter",
            "Janse",
            "Nxumalo",
            "Duvenage",
            "Botha",
            "Masondo",
            "Steyn",
            "Mokoena",
            "Van Wyk",
        ],
    },
    "New Zealand": {
        "first": ["Tama", "Ariki", "Lachlan", "Kieran", "Taine", "Mika", "Rory", "Pita", "Finn", "Mason"],
        "last": ["Tupaea", "McLeod", "Raukawa", "Wanoa", "Sullivan", "Fraser", "Te Kahu", "Rangitira", "Iosefa", "Dalton"],
    },
    "Australia": {
        "first": ["Bailey", "Kai", "Hugh", "Elliot", "Cooper", "Jarrah", "Noah", "Tom", "Marlon", "Riley"],
        "last": ["Dempsey", "Rennie", "Muir", "Latu", "Callaghan", "Keating", "Marsters", "O'Donnell", "Brennan", "Tuala"],
    },
    "Pacific Isles": {
        "first": ["Sione", "Manu", "Tavita", "Ilaisa", "Niko", "Semi", "Loto", "Vili", "Josefa", "Aisea"],
        "last": ["Nadolo", "Mafi", "Vakacegu", "Talakai", "Mataele", "Tuisova", "Moli", "Foketi", "Luatua", "Tuilagi"],
    },
    "British Isles": {
        "first": ["Owen", "Rhys", "Callum", "Hamish", "Fraser", "Euan", "Tomos", "Dylan", "Morgan", "Finlay"],
        "last": ["Penrose", "McIntyre", "Davies", "Kerr", "Redpath", "Boyle", "Fenwick", "Kinsella", "Drummond", "Llewellyn"],
    },
    "France": {
        "first": ["Louis", "Mathis", "Clement", "Theo", "Bastien", "Jules", "Adrien", "Raphael", "Maxime", "Nolan"],
        "last": ["Dubois", "Mercier", "Aubry", "Lafitte", "Bourdon", "Garnier", "Roche", "Pelissier", "Faure", "Meyer"],
    },
    "Argentina": {
        "first": ["Tomas", "Ignacio", "Facundo", "Lucio", "Santiago", "Matias", "Bautista", "Ramiro", "Juan", "Agustin"],
        "last": ["Moyano", "Carrizo", "Ibarra", "Benitez", "Navarro", "Quiroga", "Figueroa", "Borda", "Aguirre", "Suarez"],
    },
}


TEAM_REGION_ROTATION = {
    0: ["South Africa", "British Isles", "Pacific Isles"],
    1: ["France", "South Africa", "British Isles"],
    2: ["New Zealand", "Pacific Isles", "Australia"],
    3: ["British Isles", "France", "South Africa"],
    4: ["Pacific Isles", "New Zealand", "South Africa"],
    5: ["Argentina", "South Africa", "British Isles"],
    6: ["Australia", "British Isles", "Pacific Isles"],
    7: ["South Africa", "Argentina", "New Zealand"],
    8: ["British Isles", "Australia", "France"],
    9: ["Pacific Isles", "Argentina", "South Africa"],
}


ATTACKING_BY_TEAM = [
    "balanced",
    "forward-oriented",
    "expansive",
    "balanced",
    "expansive",
    "forward-oriented",
    "balanced",
    "expansive",
    "balanced",
    "forward-oriented",
]


@dataclass(frozen=True)
class ClubTemplate:
    name: str
    short_name: str
    reputation: int
    budget: int
    wage_budget: int
    objective: str


def list_club_options() -> list[ClubOption]:
    options: list[ClubOption] = []
    for index, club in enumerate(CLUB_IDENTITIES, start=1):
        reputation = club[2]
        options.append(
            ClubOption(
                team_id=index,
                name=club[0],
                short_name=club[1],
                reputation=reputation,
                budget=club[3],
                wage_budget=club[4],
                objective=club[5],
                staff_summary={
                    "attack": max(60, reputation + (index % 5) - 2),
                    "defense": max(60, reputation + ((index + 2) % 5) - 2),
                    "fitness": max(60, reputation - 3 + (index % 4)),
                    "set_piece": max(60, reputation - 2 + ((index + 1) % 4)),
                },
            )
        )
    return options


def _club_templates() -> list[ClubTemplate]:
    return [ClubTemplate(*club) for club in CLUB_IDENTITIES]


def _player_name(region: str, team_index: int, player_index: int) -> tuple[str, str]:
    pool = REGION_POOLS[region]
    first = pool["first"][(team_index * 3 + player_index) % len(pool["first"])]
    last = pool["last"][(team_index * 5 + player_index * 2) % len(pool["last"])]
    return first, last


def _position_variation(position: str, team_rep: int, rng: random.Random) -> dict[str, int]:
    profile = POSITION_PROFILES[position]
    rating_delta = (team_rep - 72) / 2.8
    values: dict[str, int] = {}
    for attr in ATTRIBUTE_NAMES:
        base_value = getattr(profile, attr)
        values[attr] = max(25, min(95, round(base_value + rating_delta + rng.randint(-6, 6))))
    return values


def _create_player(
    *,
    save_id: int,
    team_id: int,
    team_rep: int,
    team_index: int,
    position: str,
    player_index: int,
    region_cycle: cycle[str],
    rng: random.Random,
) -> Player:
    region = next(region_cycle)
    first_name, last_name = _player_name(region, team_index, player_index)
    age = rng.randint(20, 34)
    secondary_positions = SECONDARY_POSITION_MAP[position][: 1 + (player_index % 2)]
    attributes = _position_variation(position, team_rep, rng)
    player = Player(
        save_game_id=save_id,
        team_id=team_id,
        first_name=first_name,
        last_name=last_name,
        nationality=region,
        age=age,
        primary_position=position,
        secondary_positions=secondary_positions,
        overall_rating=0,
        potential=max(55, min(92, team_rep + rng.randint(-8, 10) + max(0, 25 - age) // 2)),
        wage=max(1_800, int((team_rep * 90 + rng.randint(-1200, 1200)))),
        contract_years_remaining=rng.randint(1, 5),
        morale=rng.randint(62, 84),
        fitness=rng.randint(78, 96),
        fatigue=rng.randint(5, 22),
        form=rng.randint(58, 80),
        transfer_value=max(45_000, int(team_rep * 11_500 + rng.randint(-70_000, 95_000))),
        **attributes,
    )
    player.overall_rating = compute_overall(player)
    if age < 24:
        player.potential = max(player.potential, player.overall_rating + rng.randint(3, 9))
    return player


def _generate_schedule(team_ids: list[int]) -> list[list[tuple[int, int]]]:
    teams = team_ids[:]
    rounds: list[list[tuple[int, int]]] = []
    for round_index in range(len(teams) - 1):
        pairings: list[tuple[int, int]] = []
        for index in range(len(teams) // 2):
            home = teams[index]
            away = teams[-(index + 1)]
            if round_index % 2 == 0:
                pairings.append((home, away))
            else:
                pairings.append((away, home))
        rounds.append(pairings)
        teams = [teams[0], teams[-1], *teams[1:-1]]
    reverse_rounds = [[(away, home) for home, away in round_pairings] for round_pairings in rounds]
    return rounds + reverse_rounds


def _default_tactics(team_index: int) -> TeamTactics:
    return TeamTactics(
        save_game_id=0,
        team_id=0,
        attacking_style=ATTACKING_BY_TEAM[team_index],
        kicking_approach="high" if team_index in {0, 1, 5, 9} else "balanced",
        defensive_system="rush" if team_index in {1, 4, 7} else "balanced",
        ruck_commitment="high" if team_index in {0, 2, 4, 9} else "balanced",
        set_piece_intent="aggressive" if team_index in {0, 1, 5} else "balanced",
        goal_choice="kick to corner" if team_index in {2, 4, 7} else "balanced",
        training_focus="recovery" if team_index in {7, 8, 9} else "attack",
    )


def _lineup_request(players: list[Player]) -> SelectionUpdateRequest:
    request = build_best_selection(players)
    validate_selection(players, request)
    return request


def create_transfer_listings_for_season(
    session: Session,
    save_id: int,
    season_number: int,
    user_team_id: int | None = None,
) -> None:
    players = session.exec(select(Player).where(Player.save_game_id == save_id)).all()
    candidates = sorted(
        [
            player
            for player in players
            if player.team_id != user_team_id and (player.team_id is None or player.contract_years_remaining <= 2)
        ],
        key=lambda player: (player.overall_rating, player.potential, -player.age),
        reverse=True,
    )
    for player in candidates[:24]:
        session.add(
            TransferListing(
                save_game_id=save_id,
                season_number=season_number,
                player_id=player.id,
                listed_by_team_id=player.team_id,
                asking_price=int(player.transfer_value * (1.02 if player.team_id is None else 1.1)),
            )
        )


def create_save_world(session: Session, chosen_template_team_id: int, save_name: str) -> SaveGame:
    existing = session.exec(select(SaveGame).where(SaveGame.active.is_(True))).all()
    for save in existing:
        save.active = False
        save.updated_at = datetime.now(timezone.utc)

    save = SaveGame(name=save_name)
    session.add(save)
    session.flush()

    league = League(save_game_id=save.id, name=save.league_name, season_label=save.season_label)
    session.add(league)
    session.flush()

    team_records: list[Team] = []
    for index, template in enumerate(_club_templates()):
        team = Team(
            save_game_id=save.id,
            league_id=league.id,
            name=template.name,
            short_name=template.short_name,
            reputation=template.reputation,
            budget=template.budget,
            wage_budget=template.wage_budget,
            board_objective=template.objective,
            staff_attack=max(62, template.reputation + (index % 5) - 2),
            staff_defense=max(62, template.reputation + ((index + 2) % 5) - 2),
            staff_fitness=max(60, template.reputation - 3 + (index % 4)),
            staff_set_piece=max(60, template.reputation - 2 + ((index + 1) % 4)),
            is_user_team=index + 1 == chosen_template_team_id,
        )
        session.add(team)
        team_records.append(team)
    session.flush()

    save.user_team_id = next(team.id for team in team_records if team.is_user_team)
    session.add(save)

    all_players_by_team: dict[int, list[Player]] = {}
    for team_index, team in enumerate(team_records):
        rng = random.Random((save.id * 10_000) + team_index * 173)
        region_cycle = cycle(TEAM_REGION_ROTATION[team_index])
        team_players: list[Player] = []
        player_index = 0
        for position, count in ROSTER_TEMPLATE.items():
            for _ in range(count):
                player = _create_player(
                    save_id=save.id,
                    team_id=team.id,
                    team_rep=team.reputation,
                    team_index=team_index,
                    position=position,
                    player_index=player_index,
                    region_cycle=region_cycle,
                    rng=rng,
                )
                session.add(player)
                team_players.append(player)
                player_index += 1
        session.flush()
        all_players_by_team[team.id] = team_players

        tactics = _default_tactics(team_index)
        tactics.save_game_id = save.id
        tactics.team_id = team.id
        session.add(tactics)

    session.flush()

    for team in team_records:
        selection_request = _lineup_request(all_players_by_team[team.id])
        session.add(
            TeamSelection(
                save_game_id=save.id,
                team_id=team.id,
                starting_lineup=[slot.model_dump() for slot in selection_request.starting_lineup],
                bench_player_ids=selection_request.bench_player_ids,
                captain_id=selection_request.captain_id,
                goal_kicker_id=selection_request.goal_kicker_id,
            )
        )

    schedule = _generate_schedule([team.id for team in team_records])
    for week, round_pairings in enumerate(schedule, start=1):
        for home_id, away_id in round_pairings:
            session.add(
                Fixture(
                    save_game_id=save.id,
                    league_id=league.id,
                    season_number=save.season_number,
                    week=week,
                    round_name=f"Round {week}",
                    home_team_id=home_id,
                    away_team_id=away_id,
                )
            )

    create_transfer_listings_for_season(session, save.id, save.season_number, save.user_team_id)

    user_team = next(team for team in team_records if team.id == save.user_team_id)
    session.add(
        InboxMessage(
            save_game_id=save.id,
            season_number=save.season_number,
            team_id=user_team.id,
            type="board",
            title="Board expectations confirmed",
            body=f"The board expects {user_team.name} to {user_team.board_objective.lower()}.",
        )
    )
    session.commit()
    session.refresh(save)
    return save
