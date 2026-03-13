from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SaveGame(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(default="Career Save")
    league_name: str = Field(default="Crown Isles Premiership")
    season_label: str = Field(default="2031/32")
    season_number: int = Field(default=1)
    user_team_id: int | None = Field(default=None, foreign_key="team.id")
    current_week: int = Field(default=1)
    total_weeks: int = Field(default=18)
    phase: str = Field(default="in_season")
    offseason_step: str = Field(default="review")
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class League(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    name: str
    season_label: str
    teams_count: int = Field(default=10)
    current_week: int = Field(default=1)


class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    league_id: int = Field(foreign_key="league.id", index=True)
    name: str = Field(index=True)
    short_name: str
    reputation: int
    budget: int
    wage_budget: int
    board_objective: str
    staff_attack: int
    staff_defense: int
    staff_fitness: int
    staff_set_piece: int
    is_user_team: bool = Field(default=False)


class Player(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    team_id: int | None = Field(default=None, foreign_key="team.id", index=True)
    first_name: str
    last_name: str
    nationality: str
    age: int
    primary_position: str
    secondary_positions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    overall_rating: int
    potential: int
    wage: int
    contract_years_remaining: int
    contract_last_renewed_season: int = Field(default=0)
    morale: int
    fitness: int
    fatigue: int
    form: int
    injury_status: str = Field(default="Healthy")
    injury_weeks_remaining: int = Field(default=0)
    suspended_matches: int = Field(default=0)
    retiring_after_season: bool = Field(default=False)
    transfer_value: int = Field(default=0)
    speed: int
    strength: int
    endurance: int
    handling: int
    passing: int
    tackling: int
    kicking_hand: int
    goal_kicking: int
    breakdown: int
    scrum: int
    lineout: int
    decision_making: int
    composure: int
    discipline: int
    leadership: int


class Fixture(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    league_id: int = Field(foreign_key="league.id", index=True)
    season_number: int = Field(default=1, index=True)
    week: int = Field(index=True)
    round_name: str
    home_team_id: int = Field(foreign_key="team.id")
    away_team_id: int = Field(foreign_key="team.id")
    played: bool = Field(default=False)
    result_id: int | None = Field(default=None, foreign_key="matchresult.id")
    kickoff_label: str = Field(default="Saturday 15:00")


class MatchResult(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    fixture_id: int = Field(foreign_key="fixture.id", index=True)
    season_number: int = Field(default=1, index=True)
    home_team_id: int = Field(foreign_key="team.id")
    away_team_id: int = Field(foreign_key="team.id")
    home_score: int
    away_score: int
    home_tries: int
    away_tries: int
    home_penalties: int
    away_penalties: int
    home_conversions: int
    away_conversions: int
    summary: str
    stats: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    commentary: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class LiveMatchSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    fixture_id: int = Field(foreign_key="fixture.id", index=True)
    season_number: int = Field(default=1, index=True)
    home_team_id: int = Field(foreign_key="team.id")
    away_team_id: int = Field(foreign_key="team.id")
    user_team_id: int = Field(foreign_key="team.id")
    status: str = Field(default="first_half", index=True)
    current_block: int = Field(default=0)
    minute: int = Field(default=0)
    seed: int
    ball_position: int = Field(default=50)
    commentary: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    recent_events: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    home_selection: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    away_selection: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    home_tactics: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    away_tactics: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    home_state: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    away_state: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    player_conditions: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class TeamTactics(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    attacking_style: str = Field(default="balanced")
    kicking_approach: str = Field(default="balanced")
    defensive_system: str = Field(default="balanced")
    ruck_commitment: str = Field(default="balanced")
    set_piece_intent: str = Field(default="balanced")
    goal_choice: str = Field(default="balanced")
    training_focus: str = Field(default="attack")


class TeamSelection(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    starting_lineup: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    bench_player_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    captain_id: int
    goal_kicker_id: int


class TransferListing(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    season_number: int = Field(default=1, index=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    listed_by_team_id: int | None = Field(default=None, foreign_key="team.id")
    asking_price: int
    is_active: bool = Field(default=True)


class RecruitmentTarget(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    season_number: int = Field(default=1, index=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    listing_id: int | None = Field(default=None, foreign_key="transferlisting.id", index=True)
    weeks_scouted: int = Field(default=0)
    shortlisted: bool = Field(default=False)
    status: str = Field(default="active", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class InboxMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    season_number: int = Field(default=1, index=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    type: str
    title: str
    body: str
    related_fixture_id: int | None = Field(default=None, foreign_key="fixture.id")
    related_player_id: int | None = Field(default=None, foreign_key="player.id")
    created_at: datetime = Field(default_factory=utcnow)
    is_read: bool = Field(default=False)


class TeamSeasonSummary(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    season_number: int = Field(index=True)
    season_label: str
    final_position: int
    played: int
    wins: int
    draws: int
    losses: int
    points_for: int
    points_against: int
    points_difference: int
    table_points: int
    board_objective: str
    board_verdict: str
    budget_delta: int


class YouthProspect(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    save_game_id: int = Field(foreign_key="savegame.id", index=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    season_number: int = Field(index=True)
    first_name: str
    last_name: str
    nationality: str
    age: int = Field(default=18)
    primary_position: str
    secondary_positions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    overall_rating: int
    potential: int
    readiness: int
    wage: int
    speed: int
    strength: int
    endurance: int
    handling: int
    passing: int
    tackling: int
    kicking_hand: int
    goal_kicking: int
    breakdown: int
    scrum: int
    lineout: int
    decision_making: int
    composure: int
    discipline: int
    leadership: int
    promoted: bool = Field(default=False)
