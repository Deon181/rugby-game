import type {
  AdvanceWeekResponse,
  ClubOption,
  Dashboard,
  FinanceOverview,
  FixtureList,
  InboxResponse,
  LiveMatchHalftimePayload,
  LiveMatchSnapshot,
  MatchResult,
  NewSaveResponse,
  OffseasonStatusResponse,
  PerformanceOverview,
  PlayerDetail,
  RecruitmentResponse,
  SaveSummary,
  SeasonHistoryResponse,
  SeasonReviewResponse,
  Selection,
  SquadResponse,
  SquadStats,
  TableResponse,
  Tactics,
  TeamOverview,
  TransferListResponse,
  YouthIntakeResponse,
} from "./types";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail ?? "Request failed");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  currentSave: () => request<SaveSummary | null>("/api/save/current"),
  saveOptions: () => request<ClubOption[]>("/api/saves/options"),
  createSave: (payload: { template_team_id: number; club_name: string; club_short_name: string; name: string }) =>
    request<NewSaveResponse>("/api/saves", { method: "POST", body: JSON.stringify(payload) }),
  careerStatus: () => request<SaveSummary>("/api/career/status"),
  dashboard: () => request<Dashboard>("/api/dashboard"),
  finance: () => request<FinanceOverview>("/api/finance"),
  updateFinanceSettings: (payload: { operating_focus: string }) =>
    request<FinanceOverview>("/api/finance/settings", { method: "PUT", body: JSON.stringify(payload) }),
  performance: () => request<PerformanceOverview>("/api/performance"),
  updatePerformancePlan: (payload: { focus: string; intensity: string; contact_level: string }) =>
    request<PerformanceOverview>("/api/performance/plan", { method: "PUT", body: JSON.stringify(payload) }),
  updateMedicalAssignment: (playerId: number, payload: { rehab_mode?: string; clearance_status?: string }) =>
    request<PerformanceOverview>(`/api/performance/medical/${playerId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  club: () => request<TeamOverview>("/api/club"),
  squad: () => request<SquadResponse>("/api/squad"),
  tactics: () => request<Tactics>("/api/tactics"),
  updateTactics: (payload: Tactics) => request<Tactics>("/api/tactics", { method: "PUT", body: JSON.stringify(payload) }),
  selection: () => request<Selection>("/api/selection"),
  updateSelection: (payload: Selection) =>
    request<Selection>("/api/selection", { method: "PUT", body: JSON.stringify(payload) }),
  fixtures: () => request<FixtureList>("/api/fixtures"),
  table: () => request<TableResponse>("/api/table"),
  transfers: () => request<TransferListResponse>("/api/transfers"),
  recruitment: () => request<RecruitmentResponse>("/api/recruitment"),
  startScouting: (playerId: number) =>
    request<{ status: string; message: string }>(`/api/recruitment/scouting/${playerId}`, { method: "POST" }),
  toggleShortlist: (playerId: number) =>
    request<{ status: string; message: string }>(`/api/recruitment/shortlist/${playerId}`, { method: "POST" }),
  bidTransfer: (listingId: number, amount: number) =>
    request<{ status: string; message: string }>(`/api/transfers/${listingId}/bid`, {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  renewContract: (playerId: number, years: number, weeklyWage: number) =>
    request<{ status: string; message: string }>(`/api/contracts/${playerId}/renew`, {
      method: "POST",
      body: JSON.stringify({ years, weekly_wage: weeklyWage }),
    }),
  inbox: () => request<InboxResponse>("/api/inbox"),
  advanceWeek: () => request<AdvanceWeekResponse>("/api/advance-week", { method: "POST" }),
  currentLiveMatch: () => request<LiveMatchSnapshot | null>("/api/live-match/current"),
  startLiveMatch: () => request<LiveMatchSnapshot>("/api/live-match/start", { method: "POST" }),
  tickLiveMatch: () => request<LiveMatchSnapshot>("/api/live-match/tick", { method: "POST" }),
  submitHalftime: (payload: LiveMatchHalftimePayload) =>
    request<LiveMatchSnapshot>("/api/live-match/halftime", { method: "POST", body: JSON.stringify(payload) }),
  seasonReview: () => request<SeasonReviewResponse>("/api/season/review"),
  offseasonStatus: () => request<OffseasonStatusResponse>("/api/offseason/status"),
  advanceOffseason: () => request<SaveSummary>("/api/offseason/advance", { method: "POST" }),
  youthIntake: () => request<YouthIntakeResponse>("/api/youth-intake"),
  promoteYouth: (prospectId: number) =>
    request<{ status: string; message: string }>(`/api/youth-intake/${prospectId}/promote`, { method: "POST" }),
  seasonHistory: () => request<SeasonHistoryResponse>("/api/history/seasons"),
  match: (fixtureId: number) => request<MatchResult>(`/api/matches/${fixtureId}`),
  playerDetail: (playerId: number) => request<PlayerDetail>(`/api/players/${playerId}`),
  squadStats: () => request<SquadStats>("/api/squad/stats"),
};
