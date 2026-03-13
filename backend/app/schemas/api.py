from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ClubOption(BaseModel):
    team_id: int
    name: str
    short_name: str
    reputation: int
    budget: int
    wage_budget: int
    objective: str
    staff_summary: dict[str, int]


class SaveSummary(BaseModel):
    id: int
    league_name: str
    season_label: str
    season_number: int
    current_week: int
    total_weeks: int
    phase: str
    offseason_step: str
    user_team_id: int
    user_team_name: str


class NewSaveRequest(BaseModel):
    team_id: int
    name: str = "Career Save"


class NewSaveResponse(BaseModel):
    save: SaveSummary


class TeamOverviewRead(BaseModel):
    id: int
    name: str
    short_name: str
    reputation: int
    budget: int
    wage_budget: int
    objective: str
    staff_summary: dict[str, int]


class SquadPlayerRead(BaseModel):
    id: int
    name: str
    age: int
    nationality: str
    primary_position: str
    secondary_positions: list[str]
    overall_rating: int
    potential: int
    wage: int
    contract_years_remaining: int
    morale: int
    fitness: int
    fatigue: int
    injury_status: str
    injury_weeks_remaining: int
    form: int
    transfer_value: int
    attributes: dict[str, int]
    derived_ratings: dict[str, int]
    is_free_agent: bool = False


class SquadResponse(BaseModel):
    team: TeamOverviewRead
    players: list[SquadPlayerRead]
    total_wages: int
    injured_count: int


class TacticsRead(BaseModel):
    attacking_style: str
    kicking_approach: str
    defensive_system: str
    ruck_commitment: str
    set_piece_intent: str
    goal_choice: str
    training_focus: str


class TacticsUpdateRequest(TacticsRead):
    pass


class SelectionSlotRead(BaseModel):
    slot: str
    player_id: int


class SelectionRead(BaseModel):
    starting_lineup: list[SelectionSlotRead]
    bench_player_ids: list[int]
    captain_id: int
    goal_kicker_id: int


class SelectionUpdateRequest(BaseModel):
    starting_lineup: list[SelectionSlotRead]
    bench_player_ids: list[int]
    captain_id: int
    goal_kicker_id: int


class FixtureResultRead(BaseModel):
    home_score: int
    away_score: int


class FixtureDetail(BaseModel):
    id: int
    season_number: int
    week: int
    round_name: str
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    kickoff_label: str
    played: bool
    result: FixtureResultRead | None = None


class MatchResultRead(BaseModel):
    fixture_id: int
    season_number: int
    home_team_id: int
    away_team_id: int
    home_team_name: str
    away_team_name: str
    home_score: int
    away_score: int
    home_tries: int
    away_tries: int
    home_penalties: int
    away_penalties: int
    home_conversions: int
    away_conversions: int
    summary: str
    stats: dict[str, Any]
    commentary: list[dict[str, Any]]


class LiveMatchTeamStateRead(BaseModel):
    team_id: int
    team_name: str
    score: int
    tries: int
    penalties: int
    conversions: int
    drop_goals: int
    stats: dict[str, int]


class LiveMatchPlayerRead(BaseModel):
    player_id: int
    name: str
    primary_position: str
    secondary_positions: list[str]
    overall_rating: int
    starter_slot: str | None
    on_field: bool
    fatigue: int
    fitness: int
    morale: int
    form: int
    injury_status: str | None = None
    card_status: str | None = None


class LiveSubstitutionRequest(BaseModel):
    player_out_id: int
    player_in_id: int


class LiveMatchHalftimeRequest(BaseModel):
    tactics: TacticsUpdateRequest
    substitutions: list[LiveSubstitutionRequest] = Field(default_factory=list)
    captain_id: int
    goal_kicker_id: int


class LiveMatchSnapshotRead(BaseModel):
    session_id: int
    save: SaveSummary
    fixture: FixtureDetail
    status: str
    minute: int
    current_block: int
    total_blocks: int
    user_team_id: int
    home: LiveMatchTeamStateRead
    away: LiveMatchTeamStateRead
    commentary: list[dict[str, Any]]
    recent_events: list[dict[str, Any]]
    ball_position: int
    user_selection: SelectionRead
    user_tactics: TacticsRead
    user_matchday_players: list[LiveMatchPlayerRead]
    result: MatchResultRead | None = None


class FixtureListResponse(BaseModel):
    current_week: int
    fixtures: list[FixtureDetail]
    recent_matches: list[MatchResultRead] = Field(default_factory=list)


class TableRow(BaseModel):
    position: int
    team_id: int
    team_name: str
    played: int
    wins: int
    draws: int
    losses: int
    points_for: int
    points_against: int
    tries_for: int
    tries_against: int
    points_difference: int
    table_points: int


class TableResponse(BaseModel):
    league_name: str
    season_number: int
    current_week: int
    rows: list[TableRow]


class DashboardResponse(BaseModel):
    save: SaveSummary
    team: TeamOverviewRead
    next_fixture: FixtureDetail | None
    recent_results: list[FixtureDetail]
    league_position: int
    morale_summary: dict[str, int]
    injury_summary: dict[str, int | list[str]]
    budget_snapshot: dict[str, int]
    board_objective: str
    phase_message: str | None = None
    inbox_preview: list["InboxMessageRead"]
    latest_match: MatchResultRead | None = None


class TransferListingRead(BaseModel):
    id: int
    player_id: int
    player_name: str
    current_team: str
    is_free_agent: bool
    primary_position: str
    overall_rating: int
    age: int
    asking_price: int
    wage: int
    value: int
    form: int
    morale: int


class TransferListResponse(BaseModel):
    listings: list[TransferListingRead]
    budget: int
    wage_budget: int


class TransferBidRequest(BaseModel):
    amount: int


class ContractRenewRequest(BaseModel):
    years: int = Field(ge=1, le=5)
    weekly_wage: int = Field(ge=1_000)


class InboxMessageRead(BaseModel):
    id: int
    type: str
    title: str
    body: str
    related_fixture_id: int | None
    related_player_id: int | None
    created_at: datetime
    is_read: bool


class InboxResponse(BaseModel):
    messages: list[InboxMessageRead]


class AdvanceWeekResponse(BaseModel):
    save: SaveSummary
    advanced_to_week: int
    completed_fixture_ids: list[int]
    user_match: MatchResultRead | None
    inbox_messages: list[InboxMessageRead]
    season_complete: bool


class SeasonHistoryRow(BaseModel):
    season_number: int
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


class SeasonHistoryResponse(BaseModel):
    seasons: list[SeasonHistoryRow]


class SeasonReviewResponse(BaseModel):
    save: SaveSummary
    table: TableResponse
    club_summary: SeasonHistoryRow
    next_objective: str
    projected_transfer_budget: int
    projected_wage_budget: int
    retiring_players: list[str]
    expiring_players: list[str]


class YouthProspectRead(BaseModel):
    id: int
    name: str
    nationality: str
    age: int
    primary_position: str
    secondary_positions: list[str]
    overall_rating: int
    potential: int
    readiness: int
    wage: int
    attributes: dict[str, int]


class YouthIntakeResponse(BaseModel):
    season_number: int
    prospects: list[YouthProspectRead]


class OffseasonStatusResponse(BaseModel):
    save: SaveSummary
    next_objective: str
    projected_transfer_budget: int
    projected_wage_budget: int
    expiring_contracts: list[SquadPlayerRead]
    retirements: list[str]
    promoted_count: int
