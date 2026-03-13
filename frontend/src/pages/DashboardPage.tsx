import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState } from "../components/EmptyState";
import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { api } from "../lib/api";
import { formatMoney } from "../lib/format";
import { buildFormSnapshot, getFixtureOpponentName, getTableRow } from "../lib/insights";
import type { Dashboard, FinanceOverview, LiveMatchSnapshot, TableResponse } from "../lib/types";

type DashboardBundle = {
  dashboard: Dashboard;
  finance: FinanceOverview;
  table: TableResponse;
  liveMatch: LiveMatchSnapshot | null;
};

function metricTone(value: number, inverted = false) {
  if (inverted) {
    if (value <= 35) {
      return "text-success";
    }
    if (value <= 55) {
      return "text-accent";
    }
    return "text-danger";
  }

  if (value >= 75) {
    return "text-success";
  }
  if (value >= 60) {
    return "text-accent";
  }
  return "text-danger";
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [bundle, setBundle] = useState<DashboardBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      const [dashboard, finance, table, liveMatch] = await Promise.all([
        api.dashboard(),
        api.finance(),
        api.table(),
        api.currentLiveMatch(),
      ]);
      setBundle({ dashboard, finance, table, liveMatch });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  if (loading) {
    return <LoadingPanel label="Loading dashboard" className="min-h-[60vh]" />;
  }

  if (!bundle) {
    return <EmptyState title="No dashboard data" body={error ?? "The dashboard could not be loaded."} />;
  }

  const { dashboard, finance, table, liveMatch } = bundle;
  const formSnapshot = buildFormSnapshot(dashboard.recent_results, dashboard.save.user_team_id);
  const opponentId =
    dashboard.next_fixture?.home_team_id === dashboard.save.user_team_id
      ? dashboard.next_fixture.away_team_id
      : dashboard.next_fixture?.away_team_id;
  const opponentRow = opponentId ? getTableRow(table, opponentId) : null;
  const userRow = getTableRow(table, dashboard.save.user_team_id);
  const conditionChart = [
    { name: "Morale", value: dashboard.morale_summary.average_morale },
    { name: "Fitness", value: dashboard.morale_summary.average_fitness },
    { name: "Fatigue", value: dashboard.morale_summary.average_fatigue },
  ];
  const opponentName = dashboard.next_fixture
    ? getFixtureOpponentName(dashboard.next_fixture, dashboard.save.user_team_id)
    : null;

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={`${dashboard.save.league_name} · ${dashboard.save.season_label}`}
        title={`${dashboard.team.name} Dashboard`}
        description="Drive the season from a proper control room: upcoming opposition, current squad trend, and live-week context all in one place."
        actions={
          <>
            <button className="btn-secondary" onClick={() => navigate("/fixtures")}>
              Review Schedule
            </button>
            <button
              className="btn-primary"
              onClick={() => {
                if (dashboard.save.phase !== "in_season") {
                  navigate("/offseason");
                  return;
                }
                navigate("/match-centre");
              }}
              disabled={dashboard.save.phase === "in_season" && !dashboard.next_fixture && !liveMatch}
            >
              {dashboard.save.phase !== "in_season"
                ? "Open Offseason"
                : liveMatch
                  ? `Resume Live Match ${liveMatch.minute}'`
                  : dashboard.next_fixture
                    ? `Play Week ${dashboard.save.current_week} Live`
                    : "Season Complete"}
            </button>
          </>
        }
      />

      {liveMatch ? (
        <div className="rounded-3xl border border-accent/20 bg-accentSoft px-5 py-4">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="stat-label text-accent">Live Match Active</div>
              <div className="mt-1 font-display text-2xl font-semibold">
                {liveMatch.home.team_name} {liveMatch.home.score} - {liveMatch.away.score} {liveMatch.away.team_name}
              </div>
              <p className="mt-2 text-sm text-muted">
                The match is already in progress at {liveMatch.minute}'. Resume from the coaching box instead of starting a new simulation.
              </p>
            </div>
            <button className="btn-primary" onClick={() => navigate("/match-centre")}>
              Resume Match
            </button>
          </div>
        </div>
      ) : null}

      {dashboard.phase_message ? <div className="rounded-2xl bg-accentSoft px-4 py-3 text-sm">{dashboard.phase_message}</div> : null}
      {error ? <div className="rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}

      <div className="data-grid">
        <StatCard label="League Position" value={`#${dashboard.league_position}`} detail={userRow ? `${userRow.table_points} pts · PD ${userRow.points_difference}` : "Table rank after played fixtures."} />
        <StatCard
          label="Recent Form"
          value={`${formSnapshot.wins}-${formSnapshot.draws}-${formSnapshot.losses}`}
          detail={`Last ${formSnapshot.played || 0} played matches · Streak ${formSnapshot.streakLabel}`}
          accent={formSnapshot.losses > formSnapshot.wins ? "warn" : "success"}
        />
        <StatCard
          label="Scoring Trend"
          value={`${formSnapshot.averageScored} / ${formSnapshot.averageConceded}`}
          detail="Average points scored and conceded."
          accent={formSnapshot.averageScored >= formSnapshot.averageConceded ? "success" : "danger"}
        />
        <StatCard
          label="Injuries"
          value={dashboard.injury_summary.count}
          detail={dashboard.injury_summary.players.join(", ") || "No current injury concerns."}
          accent={dashboard.injury_summary.count > 0 ? "danger" : "success"}
        />
        <StatCard
          label="Board Confidence"
          value={`${finance.board.confidence}/100`}
          detail={`${finance.board.pressure_state} pressure · ${finance.board.operating_focus} focus`}
          accent={
            finance.board.pressure_state === "critical"
              ? "danger"
              : finance.board.pressure_state === "watch"
                ? "warn"
                : "success"
          }
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <SectionCard
          title="Matchday Briefing"
          subtitle="Opponent context, league stakes, and the decision points that matter before kickoff."
          actions={
            <button className="btn-ghost" onClick={() => navigate("/tactics")}>
              Adjust Tactics
            </button>
          }
        >
          {dashboard.next_fixture ? (
            <div className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
              <div className="rounded-[28px] border border-border bg-slate-950/35 p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="chip chip-active">{dashboard.next_fixture.round_name}</span>
                  <span className="chip">{dashboard.next_fixture.kickoff_label}</span>
                  <span className="chip">
                    {dashboard.next_fixture.home_team_id === dashboard.save.user_team_id ? "Home" : "Away"}
                  </span>
                </div>
                <div className="mt-5 font-display text-4xl font-bold">
                  {dashboard.next_fixture.home_team_name} vs {dashboard.next_fixture.away_team_name}
                </div>
                <p className="mt-3 max-w-xl text-sm text-muted">{dashboard.board_objective}</p>
                {opponentRow && opponentName ? (
                  <div className="mt-6 grid gap-3 md:grid-cols-3">
                    <div className="rounded-2xl bg-white/5 p-4">
                      <div className="stat-label">Opponent Rank</div>
                      <div className="mt-2 font-display text-3xl font-semibold">#{opponentRow.position}</div>
                      <div className="mt-2 text-sm text-muted">{opponentName}</div>
                    </div>
                    <div className="rounded-2xl bg-white/5 p-4">
                      <div className="stat-label">League Record</div>
                      <div className="mt-2 font-display text-3xl font-semibold">
                        {opponentRow.wins}-{opponentRow.draws}-{opponentRow.losses}
                      </div>
                      <div className="mt-2 text-sm text-muted">{opponentRow.table_points} table points</div>
                    </div>
                    <div className="rounded-2xl bg-white/5 p-4">
                      <div className="stat-label">Scoring Profile</div>
                      <div className="mt-2 font-display text-3xl font-semibold">
                        {opponentRow.points_for}-{opponentRow.points_against}
                      </div>
                      <div className="mt-2 text-sm text-muted">For vs against this season</div>
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="space-y-3">
                <div className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="stat-label">Club Objective</div>
                  <div className="mt-2 text-sm text-muted">{dashboard.board_objective}</div>
                </div>
                <div className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="stat-label">Budget Snapshot</div>
                  <div className="mt-3 space-y-2 text-sm">
                    <div className="flex justify-between gap-4"><span className="text-muted">Transfer</span><span>{formatMoney(dashboard.budget_snapshot.transfer_budget)}</span></div>
                    <div className="flex justify-between gap-4"><span className="text-muted">Wage Budget</span><span>{formatMoney(dashboard.budget_snapshot.wage_budget)}</span></div>
                    <div className="flex justify-between gap-4"><span className="text-muted">Current Wages</span><span>{formatMoney(dashboard.budget_snapshot.current_wages)}</span></div>
                    <div className="flex justify-between gap-4"><span className="text-muted">Remaining Wage Space</span><span>{formatMoney(dashboard.budget_snapshot.remaining_wage_budget)}</span></div>
                  </div>
                </div>
                <div className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="stat-label">Decision Queue</div>
                  <div className="mt-3 grid gap-2 text-sm">
                    <button className="btn-ghost justify-between" onClick={() => navigate("/squad")}>
                      <span>Review selection depth</span>
                      <span className="text-muted">{dashboard.injury_summary.count} unavailable</span>
                    </button>
                    <button className="btn-ghost justify-between" onClick={() => navigate("/transfers")}>
                      <span>Open recruitment hub</span>
                      <span className="text-muted">{formatMoney(dashboard.budget_snapshot.transfer_budget)}</span>
                    </button>
                    <button className="btn-ghost justify-between" onClick={() => navigate("/finance")}>
                      <span>Open finance room</span>
                      <span className="text-muted">{finance.board.confidence}/100</span>
                    </button>
                    <button className="btn-ghost justify-between" onClick={() => navigate("/performance")}>
                      <span>Open performance hub</span>
                      <span className="text-muted">{dashboard.morale_summary.average_fitness} fit</span>
                    </button>
                    <button className="btn-ghost justify-between" onClick={() => navigate("/inbox")}>
                      <span>Open inbox</span>
                      <span className="text-muted">{dashboard.inbox_preview.length} recent items</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <EmptyState title="No fixture remaining" body="The schedule is complete for the current season." />
          )}
        </SectionCard>

        <SectionCard title="Performance Trend" subtitle="Recent scoring shape over your last five played matches.">
          {formSnapshot.chartData.length ? (
            <>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={formSnapshot.chartData}>
                    <CartesianGrid stroke="rgba(127,153,188,0.12)" vertical={false} />
                    <XAxis dataKey="round" stroke="#92a4bb" />
                    <YAxis stroke="#92a4bb" />
                    <Tooltip
                      contentStyle={{
                        background: "#08111f",
                        border: "1px solid rgba(127,153,188,0.18)",
                        borderRadius: 16,
                      }}
                    />
                    <Line type="monotone" dataKey="scored" stroke="#34d399" strokeWidth={3} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="conceded" stroke="#fb7185" strokeWidth={3} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="stat-label">Trendline</div>
                  <div className="mt-2 font-display text-3xl font-semibold">{formSnapshot.streakLabel}</div>
                  <div className="mt-2 text-sm text-muted">Current result streak.</div>
                </div>
                <div className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="stat-label">Attack</div>
                  <div className="mt-2 font-display text-3xl font-semibold">{formSnapshot.averageScored}</div>
                  <div className="mt-2 text-sm text-muted">Average points scored.</div>
                </div>
                <div className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="stat-label">Defense</div>
                  <div className="mt-2 font-display text-3xl font-semibold">{formSnapshot.averageConceded}</div>
                  <div className="mt-2 text-sm text-muted">Average points conceded.</div>
                </div>
              </div>
            </>
          ) : (
            <EmptyState title="Trendline pending" body="Play a few fixtures and this panel will start surfacing your scoring pattern." />
          )}
        </SectionCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title="Squad Condition" subtitle="Current readiness across the dressing room.">
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={conditionChart}>
                <CartesianGrid stroke="rgba(127,153,188,0.12)" vertical={false} />
                <XAxis dataKey="name" stroke="#92a4bb" />
                <YAxis stroke="#92a4bb" domain={[0, 100]} />
                <Tooltip
                  contentStyle={{
                    background: "#08111f",
                    border: "1px solid rgba(127,153,188,0.18)",
                    borderRadius: 16,
                  }}
                />
                <Bar dataKey="value" fill="#f59e0b" radius={[10, 10, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>

        <SectionCard title="Executive View" subtitle="League standing, squad condition, and board pressure in one strip.">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl bg-slate-950/30 p-4">
              <div className="stat-label">League Trajectory</div>
              <div className="mt-4 space-y-4">
                <div>
                  <div className="mb-2 flex justify-between text-xs uppercase tracking-[0.18em] text-muted">
                    <span>Morale</span>
                    <span className={metricTone(dashboard.morale_summary.average_morale)}>{dashboard.morale_summary.average_morale}</span>
                  </div>
                  <div className="metric-track">
                    <div className="h-full bg-emerald-400" style={{ width: `${dashboard.morale_summary.average_morale}%` }} />
                  </div>
                </div>
                <div>
                  <div className="mb-2 flex justify-between text-xs uppercase tracking-[0.18em] text-muted">
                    <span>Fitness</span>
                    <span className={metricTone(dashboard.morale_summary.average_fitness)}>{dashboard.morale_summary.average_fitness}</span>
                  </div>
                  <div className="metric-track">
                    <div className="h-full bg-sky-400" style={{ width: `${dashboard.morale_summary.average_fitness}%` }} />
                  </div>
                </div>
                <div>
                  <div className="mb-2 flex justify-between text-xs uppercase tracking-[0.18em] text-muted">
                    <span>Fatigue</span>
                    <span className={metricTone(dashboard.morale_summary.average_fatigue, true)}>{dashboard.morale_summary.average_fatigue}</span>
                  </div>
                  <div className="metric-track">
                    <div className="h-full bg-rose-400" style={{ width: `${dashboard.morale_summary.average_fatigue}%` }} />
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl bg-slate-950/30 p-4">
              <div className="stat-label">Board Pressure</div>
              <div
                className={`mt-3 font-display text-3xl font-semibold capitalize ${
                  finance.board.pressure_state === "critical"
                    ? "text-danger"
                    : finance.board.pressure_state === "watch"
                      ? "text-warn"
                      : "text-success"
                }`}
              >
                {finance.board.pressure_state}
              </div>
              <p className="mt-2 text-sm text-muted">
                {finance.board.drivers[0] ?? "Board messaging is not available right now."}
              </p>
              <div className="mt-5 space-y-3">
                <div className="rounded-2xl border border-border bg-white/5 p-4 text-sm text-muted">
                  {finance.board.objective}
                </div>
                <div className="rounded-2xl border border-border bg-white/5 p-4 text-sm text-muted">
                  Projection: {formatMoney(finance.summary.projected_balance_4_weeks)} · Focus {finance.board.operating_focus}
                </div>
              </div>
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <SectionCard title="Recent Results" subtitle="Latest matches involving your club.">
          <div className="space-y-3">
            {dashboard.recent_results.length ? (
              dashboard.recent_results.map((fixture) => {
                const opponent = getFixtureOpponentName(fixture, dashboard.save.user_team_id);
                return (
                  <button
                    key={fixture.id}
                    className="w-full rounded-2xl bg-slate-950/30 p-4 text-left transition hover:bg-slate-950/45"
                    onClick={() => navigate(`/match-centre/${fixture.id}`)}
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <div className="stat-label">{fixture.round_name}</div>
                        <div className="mt-2 font-medium">
                          {fixture.home_team_name} vs {fixture.away_team_name}
                        </div>
                        <div className="mt-2 text-sm text-muted">{opponent ? `Opponent: ${opponent}` : "Club fixture review"}</div>
                      </div>
                      <div className="rounded-full border border-border px-3 py-1 text-xs uppercase tracking-[0.18em] text-muted">
                        View Report
                      </div>
                    </div>
                  </button>
                );
              })
            ) : (
              <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">No results recorded yet.</div>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Inbox Preview" subtitle="Latest club messages.">
          <div className="space-y-3">
            {dashboard.inbox_preview.length ? (
              dashboard.inbox_preview.map((message) => (
                <div key={message.id} className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="stat-label">{message.type}</div>
                  <div className="mt-2 font-medium">{message.title}</div>
                  <p className="mt-2 text-sm text-muted">{message.body}</p>
                </div>
              ))
            ) : (
              <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">No fresh inbox items.</div>
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
