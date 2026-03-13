import { useEffect, useState } from "react";

import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { api } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { FinanceOverview, SeasonHistoryResponse, TeamOverview } from "../lib/types";

export function ClubOverviewPage() {
  const [club, setClub] = useState<TeamOverview | null>(null);
  const [history, setHistory] = useState<SeasonHistoryResponse | null>(null);
  const [finance, setFinance] = useState<FinanceOverview | null>(null);

  useEffect(() => {
    void api.club().then(setClub);
    void api.seasonHistory().then(setHistory);
    void api.finance().then(setFinance);
  }, []);

  if (!club) {
    return <LoadingPanel label="Loading club overview" className="min-h-[60vh]" />;
  }

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="Club Overview" title={club.name} description="Board expectations, resource picture, and staff profile for your current career." />
      <div className="data-grid">
        <StatCard label="Reputation" value={club.reputation} />
        <StatCard label="Transfer Budget" value={formatMoney(club.budget)} />
        <StatCard label="Wage Budget" value={formatMoney(club.wage_budget)} />
        <StatCard label="Board Objective" value={club.objective} detail="The board’s minimum expectation for this season." />
        {finance ? (
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
        ) : null}
      </div>
      <SectionCard title="Staff Summary" subtitle="High-level quality across the support setup.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Object.entries(club.staff_summary).map(([key, value]) => (
            <div key={key} className="rounded-2xl bg-slate-950/30 p-4">
              <div className="stat-label">{key}</div>
              <div className="mt-2 font-display text-4xl font-semibold text-accent">{value}</div>
            </div>
          ))}
        </div>
      </SectionCard>
      {finance ? (
        <SectionCard title="Board and Cash Trend" subtitle="Compact confidence and cash-flow context for the current season.">
          <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-2xl bg-slate-950/30 p-4">
              <div className="stat-label">Operating Focus</div>
              <div className="mt-2 font-display text-3xl font-semibold capitalize">{finance.board.operating_focus}</div>
              <p className="mt-2 text-sm text-muted">
                Projection in 4 weeks: {formatMoney(finance.summary.projected_balance_4_weeks)}
              </p>
              <div className="mt-4">
                <div className="mb-2 flex justify-between text-xs uppercase tracking-[0.18em] text-muted">
                  <span>Confidence</span>
                  <span>{finance.board.confidence}</span>
                </div>
                <div className="metric-track">
                  <div
                    className={`h-full ${finance.board.pressure_state === "critical" ? "bg-rose-400" : finance.board.pressure_state === "watch" ? "bg-amber-400" : "bg-emerald-400"}`}
                    style={{ width: `${finance.board.confidence}%` }}
                  />
                </div>
              </div>
            </div>
            <div className="space-y-3">
              {finance.board.drivers.map((driver) => (
                <div key={driver} className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">
                  {driver}
                </div>
              ))}
            </div>
          </div>
        </SectionCard>
      ) : null}
      <SectionCard title="Season History" subtitle="Recent completed campaigns for the current club.">
        <div className="space-y-3">
          {history?.seasons.length ? (
            history.seasons.map((season) => (
              <div key={season.season_number} className="rounded-2xl bg-slate-950/30 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="font-medium">{season.season_label}</div>
                  <div className="text-sm text-accent">#{season.final_position}</div>
                </div>
                <p className="mt-2 text-sm text-muted">
                  {season.board_verdict} · {season.wins}-{season.draws}-{season.losses} · {season.table_points} points
                </p>
              </div>
            ))
          ) : (
            <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">No completed seasons recorded yet.</div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
