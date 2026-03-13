export type ClubOption = {
  template_team_id: number;
  name: string;
  short_name: string;
  reputation: number;
  budget: number;
  wage_budget: number;
  objective: string;
  staff_summary: Record<string, number>;
};

export type SaveSummary = {
  id: number;
  league_name: string;
  season_label: string;
  season_number: number;
  current_week: number;
  total_weeks: number;
  phase: string;
  offseason_step: string;
  user_team_id: number;
  user_team_name: string;
};

export type TeamOverview = {
  id: number;
  name: string;
  short_name: string;
  reputation: number;
  budget: number;
  wage_budget: number;
  objective: string;
  staff_summary: Record<string, number>;
};

export type SquadPlayer = {
  id: number;
  name: string;
  age: number;
  nationality: string;
  primary_position: string;
  secondary_positions: string[];
  overall_rating: number;
  potential: number;
  wage: number;
  contract_years_remaining: number;
  morale: number;
  fitness: number;
  fatigue: number;
  injury_status: string;
  injury_weeks_remaining: number;
  form: number;
  transfer_value: number;
  attributes: Record<string, number>;
  derived_ratings: Record<string, number>;
  is_free_agent: boolean;
};

export type SquadResponse = {
  team: TeamOverview;
  players: SquadPlayer[];
  total_wages: number;
  injured_count: number;
};

export type NewSaveSquadSummary = {
  player_count: number;
  average_age: number;
  average_overall: number;
  total_wages: number;
  position_counts: Record<string, number>;
};

export type NewSaveFeaturedPlayer = {
  id: number;
  name: string;
  primary_position: string;
  overall_rating: number;
  age: number;
  highlight: string;
};

export type NewSaveOnboarding = {
  team: TeamOverview;
  squad_summary: NewSaveSquadSummary;
  featured_players: NewSaveFeaturedPlayer[];
  players: SquadPlayer[];
  next_fixture: Fixture | null;
};

export type NewSaveResponse = {
  save: SaveSummary;
  onboarding: NewSaveOnboarding;
};

export type Tactics = {
  attacking_style: string;
  kicking_approach: string;
  defensive_system: string;
  ruck_commitment: string;
  set_piece_intent: string;
  goal_choice: string;
  training_focus: string;
};

export type SelectionSlot = {
  slot: string;
  player_id: number;
};

export type Selection = {
  starting_lineup: SelectionSlot[];
  bench_player_ids: number[];
  captain_id: number;
  goal_kicker_id: number;
};

export type Fixture = {
  id: number;
  season_number: number;
  week: number;
  round_name: string;
  home_team_id: number;
  home_team_name: string;
  away_team_id: number;
  away_team_name: string;
  kickoff_label: string;
  played: boolean;
  result: { home_score: number; away_score: number } | null;
};

export type MatchResult = {
  fixture_id: number;
  season_number: number;
  home_team_id: number;
  away_team_id: number;
  home_team_name: string;
  away_team_name: string;
  home_score: number;
  away_score: number;
  home_tries: number;
  away_tries: number;
  home_penalties: number;
  away_penalties: number;
  home_conversions: number;
  away_conversions: number;
  summary: string;
  stats: Record<string, Record<string, number>>;
  commentary: Array<{ minute: number; team: string; type: string; text: string }>;
};

export type LiveMatchTeamState = {
  team_id: number;
  team_name: string;
  score: number;
  tries: number;
  penalties: number;
  conversions: number;
  drop_goals: number;
  stats: Record<string, number>;
};

export type LiveMatchPlayer = {
  player_id: number;
  name: string;
  primary_position: string;
  secondary_positions: string[];
  overall_rating: number;
  starter_slot: string | null;
  on_field: boolean;
  fatigue: number;
  fitness: number;
  morale: number;
  form: number;
  injury_status: string | null;
  card_status: string | null;
};

export type LiveSubstitution = {
  player_out_id: number;
  player_in_id: number;
};

export type LiveMatchSnapshot = {
  session_id: number;
  save: SaveSummary;
  fixture: Fixture;
  status: string;
  minute: number;
  current_block: number;
  total_blocks: number;
  user_team_id: number;
  home: LiveMatchTeamState;
  away: LiveMatchTeamState;
  commentary: Array<{ minute: number; team: string; type: string; text: string; field_position: number }>;
  recent_events: Array<{ minute: number; team: string; type: string; text: string; field_position: number }>;
  ball_position: number;
  user_selection: Selection;
  user_tactics: Tactics;
  user_matchday_players: LiveMatchPlayer[];
  result: MatchResult | null;
};

export type Dashboard = {
  save: SaveSummary;
  team: TeamOverview;
  next_fixture: Fixture | null;
  recent_results: Fixture[];
  league_position: number;
  morale_summary: Record<string, number>;
  injury_summary: { count: number; players: string[] };
  budget_snapshot: Record<string, number>;
  board_objective: string;
  phase_message: string | null;
  inbox_preview: InboxMessage[];
  latest_match: MatchResult | null;
};

export type FixtureList = {
  current_week: number;
  fixtures: Fixture[];
  recent_matches: MatchResult[];
};

export type TableRow = {
  position: number;
  team_id: number;
  team_name: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  points_for: number;
  points_against: number;
  tries_for: number;
  tries_against: number;
  points_difference: number;
  table_points: number;
};

export type TableResponse = {
  league_name: string;
  season_number: number;
  current_week: number;
  rows: TableRow[];
};

export type TransferListing = {
  id: number;
  player_id: number;
  player_name: string;
  current_team: string;
  is_free_agent: boolean;
  primary_position: string;
  overall_rating: number;
  age: number;
  asking_price: number;
  wage: number;
  value: number;
  form: number;
  morale: number;
};

export type TransferListResponse = {
  listings: TransferListing[];
  budget: number;
  wage_budget: number;
};

export type ScoutingReport = {
  stage: string;
  weeks_scouted: number;
  weeks_to_complete: number;
  fit_score: number | null;
  fit_label: string | null;
  risk_label: string | null;
  estimated_value_low: number | null;
  estimated_value_high: number | null;
  estimated_weekly_wage_low: number | null;
  estimated_weekly_wage_high: number | null;
  potential_low: number | null;
  potential_high: number | null;
  contract_years_hint: string | null;
  recommendation: string | null;
};

export type RecruitmentListing = {
  listing_id: number;
  player_id: number;
  player_name: string;
  current_team: string;
  is_free_agent: boolean;
  primary_position: string;
  overall_rating: number;
  age: number;
  asking_price: number;
  shortlisted: boolean;
  scouting: ScoutingReport;
};

export type ContractWatchPlayer = {
  player_id: number;
  player_name: string;
  primary_position: string;
  overall_rating: number;
  age: number;
  contract_years_remaining: number;
  current_wage: number;
  desired_years: number;
  minimum_years: number;
  desired_weekly_wage: number;
  recommended_max_wage: number;
  retention_priority: string;
  willingness: string;
  morale: number;
};

export type RecruitmentSummary = {
  active_reports: number;
  completed_reports: number;
  shortlisted_targets: number;
  max_active_reports: number;
};

export type RecruitmentResponse = {
  market: RecruitmentListing[];
  shortlist: RecruitmentListing[];
  contract_watch: ContractWatchPlayer[];
  summary: RecruitmentSummary;
  budget: number;
  wage_budget: number;
  current_wages: number;
};

export type BoardStatus = {
  objective: string;
  confidence: number;
  pressure_state: string;
  operating_focus: string;
  drivers: string[];
};

export type FinanceSummary = {
  transfer_budget: number;
  wage_budget: number;
  current_wages: number;
  remaining_wage_budget: number;
  weekly_sponsor_income: number;
  weekly_operating_cost: number;
  average_home_gate: number;
  projected_balance_4_weeks: number;
};

export type FinanceTransaction = {
  id: number;
  week: number;
  category: string;
  amount: number;
  balance_after: number;
  note: string;
  created_at: string;
};

export type FinanceWeekBreakdown = {
  week: number;
  income: number;
  expenses: number;
  net: number;
};

export type FinanceOverview = {
  save: SaveSummary;
  board: BoardStatus;
  summary: FinanceSummary;
  recent_transactions: FinanceTransaction[];
  weekly_breakdown: FinanceWeekBreakdown[];
};

export type PerformancePlan = {
  focus: string;
  intensity: string;
  contact_level: string;
};

export type MedicalBoardPlayer = {
  player_id: number;
  player_name: string;
  primary_position: string;
  overall_rating: number;
  fitness: number;
  fatigue: number;
  morale: number;
  injury_status: string;
  injury_weeks_remaining: number;
  rehab_mode: string;
  clearance_status: string;
  return_watch_weeks: number;
  group: string;
  note: string;
};

export type StaffEffectSummary = {
  fitness_staff_rating: number;
  recovery_bonus: number;
  injury_risk_multiplier: number;
  rehab_bonus: number;
};

export type PerformanceOverview = {
  save: SaveSummary;
  plan: PerformancePlan;
  fatigue_watch: MedicalBoardPlayer[];
  medical_board: MedicalBoardPlayer[];
  staff_effects: StaffEffectSummary;
};

export type InboxMessage = {
  id: number;
  type: string;
  title: string;
  body: string;
  related_fixture_id: number | null;
  related_player_id: number | null;
  created_at: string;
  is_read: boolean;
};

export type InboxResponse = {
  messages: InboxMessage[];
};

export type AdvanceWeekResponse = {
  save: SaveSummary;
  advanced_to_week: number;
  completed_fixture_ids: number[];
  user_match: MatchResult | null;
  inbox_messages: InboxMessage[];
  season_complete: boolean;
};

export type LiveMatchHalftimePayload = {
  tactics: Tactics;
  substitutions: LiveSubstitution[];
  captain_id: number;
  goal_kicker_id: number;
};

export type SeasonHistoryRow = {
  season_number: number;
  season_label: string;
  final_position: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  points_for: number;
  points_against: number;
  points_difference: number;
  table_points: number;
  board_objective: string;
  board_verdict: string;
  budget_delta: number;
};

export type SeasonHistoryResponse = {
  seasons: SeasonHistoryRow[];
};

export type SeasonReviewResponse = {
  save: SaveSummary;
  table: TableResponse;
  club_summary: SeasonHistoryRow;
  next_objective: string;
  projected_transfer_budget: number;
  projected_wage_budget: number;
  retiring_players: string[];
  expiring_players: string[];
};

export type YouthProspect = {
  id: number;
  name: string;
  nationality: string;
  age: number;
  primary_position: string;
  secondary_positions: string[];
  overall_rating: number;
  potential: number;
  readiness: number;
  wage: number;
  attributes: Record<string, number>;
};

export type YouthIntakeResponse = {
  season_number: number;
  prospects: YouthProspect[];
};

export type OffseasonStatusResponse = {
  save: SaveSummary;
  next_objective: string;
  projected_transfer_budget: number;
  projected_wage_budget: number;
  expiring_contracts: SquadPlayer[];
  retirements: string[];
  promoted_count: number;
};
