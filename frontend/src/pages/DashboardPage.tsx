import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "../components/EmptyState";
import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { api } from "../lib/api";
import { formatMoney, scoreLine } from "../lib/format";
import type { Dashboard } from "../lib/types";

export function DashboardPage() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      setDashboard(await api.dashboard());
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

  if (!dashboard) {
    return <EmptyState title="No dashboard data" body={error ?? "The dashboard could not be loaded."} />;
  }

  const conditionChart = [
    { name: "Morale", value: dashboard.morale_summary.average_morale },
    { name: "Fitness", value: dashboard.morale_summary.average_fitness },
    { name: "Fatigue", value: dashboard.morale_summary.average_fatigue },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={`${dashboard.save.league_name} · ${dashboard.save.season_label}`}
        title={`${dashboard.team.name} Dashboard`}
        description="Control the weekly rhythm of the club: prepare the next match, track condition, and react to form, injuries, and board pressure."
        actions={
          <button
            className="btn-primary"
            onClick={() => (dashboard.save.phase === "in_season" ? navigate("/match-centre") : navigate("/offseason"))}
            disabled={dashboard.save.phase === "in_season" && !dashboard.next_fixture}
          >
            {dashboard.save.phase === "in_season"
              ? dashboard.next_fixture
                ? `Play Week ${dashboard.save.current_week} Live`
                : "Season Complete"
              : "Open Offseason"}
          </button>
        }
      />
      {dashboard.phase_message ? <div className="rounded-2xl bg-accentSoft px-4 py-3 text-sm">{dashboard.phase_message}</div> : null}
      {error ? <div className="rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}

      <div className="data-grid">
        <StatCard label="League Position" value={`#${dashboard.league_position}`} detail="Table rank after played fixtures." />
        <StatCard label="Transfer Budget" value={formatMoney(dashboard.budget_snapshot.transfer_budget)} detail="Available for incoming bids." />
        <StatCard label="Average Morale" value={dashboard.morale_summary.average_morale} detail="Squad mood heading into the next round." />
        <StatCard
          label="Injuries"
          value={dashboard.injury_summary.count}
          detail={dashboard.injury_summary.players.join(", ") || "No current injury concerns."}
          accent={dashboard.injury_summary.count > 0 ? "danger" : "success"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <SectionCard
          title="Next Fixture"
          subtitle="Your next scheduled league match."
          actions={
            <button className="btn-secondary" onClick={() => navigate("/tactics")}>
              Adjust Tactics
            </button>
          }
        >
          {dashboard.next_fixture ? (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl bg-slate-950/30 p-5">
                <div className="stat-label">{dashboard.next_fixture.round_name}</div>
                <div className="mt-2 font-display text-3xl font-semibold">
                  {dashboard.next_fixture.home_team_name} vs {dashboard.next_fixture.away_team_name}
                </div>
                <p className="mt-3 text-sm text-muted">Kick-off: {dashboard.next_fixture.kickoff_label}</p>
                <p className="mt-5 text-sm text-muted">{dashboard.board_objective}</p>
              </div>
              <div className="rounded-2xl bg-slate-950/30 p-5">
                <div className="stat-label">Budget Snapshot</div>
                <div className="mt-3 space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-muted">Transfer</span><span>{formatMoney(dashboard.budget_snapshot.transfer_budget)}</span></div>
                  <div className="flex justify-between"><span className="text-muted">Wage Budget</span><span>{formatMoney(dashboard.budget_snapshot.wage_budget)}</span></div>
                  <div className="flex justify-between"><span className="text-muted">Current Wages</span><span>{formatMoney(dashboard.budget_snapshot.current_wages)}</span></div>
                  <div className="flex justify-between"><span className="text-muted">Remaining Wage Space</span><span>{formatMoney(dashboard.budget_snapshot.remaining_wage_budget)}</span></div>
                </div>
              </div>
            </div>
          ) : (
            <EmptyState title="No fixture remaining" body="The schedule is complete for the current season." />
          )}
        </SectionCard>

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
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <SectionCard title="Recent Results" subtitle="Latest matches involving your club.">
          <div className="space-y-3">
            {dashboard.recent_results.length ? (
              dashboard.recent_results.map((fixture) => (
                <div key={fixture.id} className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="stat-label">{fixture.round_name}</div>
                  <div className="mt-2 font-medium">
                    {fixture.result
                      ? scoreLine(
                          fixture.home_team_name,
                          fixture.away_team_name,
                          fixture.result.home_score,
                          fixture.result.away_score,
                        )
                      : `${fixture.home_team_name} vs ${fixture.away_team_name}`}
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">No results recorded yet.</div>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Inbox Preview" subtitle="Latest club messages.">
          <div className="space-y-3">
            {dashboard.inbox_preview.map((message) => (
              <div key={message.id} className="rounded-2xl bg-slate-950/30 p-4">
                <div className="stat-label">{message.type}</div>
                <div className="mt-2 font-medium">{message.title}</div>
                <p className="mt-2 text-sm text-muted">{message.body}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
