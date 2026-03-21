from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


def _normalize_name(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError("Value cannot be blank.")
    return cleaned


class ClubOption(BaseModel):
    template_team_id: int
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


class NewSaveSquadSummary(BaseModel):
    player_count: int
    average_age: int
    average_overall: int
    total_wages: int
    position_counts: dict[str, int]


class NewSaveFeaturedPlayer(BaseModel):
    id: int
    name: str
    primary_position: str
    overall_rating: int
    age: int
    highlight: str


class NewSaveOnboarding(BaseModel):
    team: TeamOverviewRead
    squad_summary: NewSaveSquadSummary
    featured_players: list[NewSaveFeaturedPlayer]
    players: list[SquadPlayerRead]
    next_fixture: "FixtureDetail | None" = None


class NewSaveRequest(BaseModel):
    template_team_id: int
    club_name: str = Field(min_length=2, max_length=40)
    club_short_name: str = Field(min_length=2, max_length=18)
    name: str = Field(default="Career Save", min_length=1, max_length=40)

    @field_validator("club_name", "club_short_name", "name")
    @classmethod
    def normalize_names(cls, value: str) -> str:
        return _normalize_name(value)


class NewSaveResponse(BaseModel):
    save: SaveSummary
    onboarding: NewSaveOnboarding


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


class ScoutingReportRead(BaseModel):
    stage: str
    weeks_scouted: int
    weeks_to_complete: int
    fit_score: int | None = None
    fit_label: str | None = None
    risk_label: str | None = None
    estimated_value_low: int | None = None
    estimated_value_high: int | None = None
    estimated_weekly_wage_low: int | None = None
    estimated_weekly_wage_high: int | None = None
    potential_low: int | None = None
    potential_high: int | None = None
    contract_years_hint: str | None = None
    recommendation: str | None = None


class RecruitmentListingRead(BaseModel):
    listing_id: int
    player_id: int
    player_name: str
    current_team: str
    is_free_agent: bool
    primary_position: str
    overall_rating: int
    age: int
    asking_price: int
    shortlisted: bool = False
    scouting: ScoutingReportRead


class ContractWatchPlayerRead(BaseModel):
    player_id: int
    player_name: str
    primary_position: str
    overall_rating: int
    age: int
    contract_years_remaining: int
    current_wage: int
    desired_years: int
    minimum_years: int
    desired_weekly_wage: int
    recommended_max_wage: int
    retention_priority: str
    willingness: str
    morale: int


class RecruitmentSummaryRead(BaseModel):
    active_reports: int
    completed_reports: int
    shortlisted_targets: int
    max_active_reports: int


class RecruitmentResponse(BaseModel):
    market: list[RecruitmentListingRead]
    shortlist: list[RecruitmentListingRead]
    contract_watch: list[ContractWatchPlayerRead]
    summary: RecruitmentSummaryRead
    budget: int
    wage_budget: int
    current_wages: int


class BoardStatusRead(BaseModel):
    objective: str
    confidence: int
    pressure_state: str
    operating_focus: str
    drivers: list[str]


class FinanceSummaryRead(BaseModel):
    transfer_budget: int
    wage_budget: int
    current_wages: int
    remaining_wage_budget: int
    weekly_sponsor_income: int
    weekly_operating_cost: int
    average_home_gate: int
    projected_balance_4_weeks: int


class FinanceTransactionRead(BaseModel):
    id: int
    week: int
    category: str
    amount: int
    balance_after: int
    note: str
    created_at: datetime


class FinanceWeekBreakdownRead(BaseModel):
    week: int
    income: int
    expenses: int
    net: int


class FinanceOverviewResponse(BaseModel):
    save: SaveSummary
    board: BoardStatusRead
    summary: FinanceSummaryRead
    recent_transactions: list[FinanceTransactionRead]
    weekly_breakdown: list[FinanceWeekBreakdownRead]


class FinanceSettingsUpdateRequest(BaseModel):
    operating_focus: str


class PerformancePlanRead(BaseModel):
    focus: str
    intensity: str
    contact_level: str


class PerformancePlanUpdateRequest(BaseModel):
    focus: str
    intensity: str
    contact_level: str


class MedicalAssignmentUpdateRequest(BaseModel):
    rehab_mode: str | None = None
    clearance_status: str | None = None


class StaffEffectSummaryRead(BaseModel):
    fitness_staff_rating: int
    recovery_bonus: int
    injury_risk_multiplier: float
    rehab_bonus: int


class MedicalBoardPlayerRead(BaseModel):
    player_id: int
    player_name: str
    primary_position: str
    overall_rating: int
    fitness: int
    fatigue: int
    morale: int
    injury_status: str
    injury_weeks_remaining: int
    rehab_mode: str
    clearance_status: str
    return_watch_weeks: int
    group: str
    note: str


class PerformanceOverviewResponse(BaseModel):
    save: SaveSummary
    plan: PerformancePlanRead
    fatigue_watch: list[MedicalBoardPlayerRead]
    medical_board: list[MedicalBoardPlayerRead]
    staff_effects: StaffEffectSummaryRead


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


class PlayerSeasonStatsRead(BaseModel):
    season_number: int
    appearances: int
    starts: int
    minutes_played: int
    tries_scored: int
    conversions: int
    penalty_goals: int
    drop_goals: int
    total_points: int
    tackles_made: int
    tackles_missed: int
    tackle_success: float
    carries: int
    line_breaks: int
    yellow_cards: int
    red_cards: int
    injuries_sustained: int
    man_of_match: int
    average_rating: float


class PlayerDetailResponse(BaseModel):
    player: SquadPlayerRead
    team_name: str
    current_season: PlayerSeasonStatsRead | None
    career: list[PlayerSeasonStatsRead]


class SquadStatsResponse(BaseModel):
    season_number: int
    players: list[dict[str, Any]]


class OffseasonStatusResponse(BaseModel):
    save: SaveSummary
    next_objective: str
    projected_transfer_budget: int
    projected_wage_budget: int
    expiring_contracts: list[SquadPlayerRead]
    retirements: list[str]
    promoted_count: int
