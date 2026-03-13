import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "../components/EmptyState";
import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { api } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { FinanceOverview } from "../lib/types";

const FOCUS_OPTIONS = [
  { value: "balanced", label: "Balanced", detail: "Neutral running costs and neutral squad support." },
  { value: "performance", label: "Performance", detail: "Higher running cost with a small weekly squad-condition boost." },
  { value: "commercial", label: "Commercial", detail: "Leaner running cost with stronger recurring income resilience." },
];

function pressureTone(pressureState: string) {
  if (pressureState === "critical") {
    return "text-danger";
  }
  if (pressureState === "watch") {
    return "text-warn";
  }
  return "text-success";
}

function formatCategory(category: string) {
  return category.replaceAll("_", " ");
}

export function FinancePage() {
  const navigate = useNavigate();
  const [finance, setFinance] = useState<FinanceOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingFocus, setSavingFocus] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadFinance() {
    setLoading(true);
    setError(null);
    try {
      setFinance(await api.finance());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to load finance view");
    } finally {
      setLoading(false);
    }
  }

  async function updateFocus(operatingFocus: string) {
    setSavingFocus(true);
    setError(null);
    try {
      setFinance(await api.updateFinanceSettings({ operating_focus: operatingFocus }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to update operating focus");
    } finally {
      setSavingFocus(false);
    }
  }

  useEffect(() => {
    void loadFinance();
  }, []);

  if (loading) {
    return <LoadingPanel label="Loading finance room" className="min-h-[60vh]" />;
  }

  if (!finance) {
    return <EmptyState title="No finance data" body={error ?? "The finance room could not be loaded."} />;
  }

  const weeklyNet =
    finance.summary.weekly_sponsor_income - finance.summary.current_wages - finance.summary.weekly_operating_cost;
  const runwayWeeks =
    weeklyNet < 0 ? Math.max(0, Math.floor(finance.summary.transfer_budget / Math.abs(weeklyNet || 1))) : null;

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={`${finance.save.league_name} · Week ${finance.save.current_week}`}
        title="Finance Room"
        description="Weekly cash flow, board confidence, and club operating focus in one management surface."
        actions={
          <>
            <button className="btn-secondary" onClick={() => navigate("/club")}>
              Club Overview
            </button>
            <button className="btn-primary" onClick={() => navigate("/")}>
              Return to Dashboard
            </button>
          </>
        }
      />

      {error ? <div className="rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}

      <div className="data-grid">
        <StatCard label="Transfer Budget" value={formatMoney(finance.summary.transfer_budget)} detail="Live transfer cash after weekly processing." />
        <StatCard
          label="Board Confidence"
          value={`${finance.board.confidence}/100`}
          detail={`${finance.board.pressure_state} pressure · ${finance.board.objective}`}
          accent={
            finance.board.pressure_state === "critical"
              ? "danger"
              : finance.board.pressure_state === "watch"
                ? "warn"
                : "success"
          }
        />
        <StatCard
          label="Weekly Run Rate"
          value={formatMoney(weeklyNet)}
          detail={`${formatMoney(finance.summary.weekly_sponsor_income)} in sponsor cash against wages and operations.`}
          accent={weeklyNet >= 0 ? "success" : "danger"}
        />
        <StatCard
          label="4-Week Projection"
          value={formatMoney(finance.summary.projected_balance_4_weeks)}
          detail={runwayWeeks !== null ? `${runwayWeeks} weeks of runway at the current burn.` : "Positive run rate if home gates hold."}
          accent={finance.summary.projected_balance_4_weeks >= finance.summary.transfer_budget ? "success" : "warn"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <SectionCard title="Board Room" subtitle="Pressure state, confidence drivers, and the active club operating posture.">
          <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-[28px] border border-border bg-slate-950/35 p-5">
              <div className="stat-label">Current Pressure</div>
              <div className={`mt-3 font-display text-4xl font-semibold capitalize ${pressureTone(finance.board.pressure_state)}`}>
                {finance.board.pressure_state}
              </div>
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
              <div className="mt-5 rounded-2xl border border-border bg-white/5 p-4 text-sm text-muted">
                Objective: {finance.board.objective}
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-2xl bg-slate-950/30 p-4">
                <div className="stat-label">Confidence Drivers</div>
                <div className="mt-3 space-y-3 text-sm">
                  {finance.board.drivers.map((driver) => (
                    <div key={driver} className="rounded-2xl bg-white/5 px-4 py-3 text-muted">
                      {driver}
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-2xl bg-slate-950/30 p-4">
                <div className="stat-label">Operating Focus</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {FOCUS_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      className={`chip ${finance.board.operating_focus === option.value ? "chip-active" : ""}`}
                      onClick={() => void updateFocus(option.value)}
                      disabled={savingFocus}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                <p className="mt-4 text-sm text-muted">
                  {FOCUS_OPTIONS.find((option) => option.value === finance.board.operating_focus)?.detail}
                </p>
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Cash Flow" subtitle="Weekly inflow and outflow across the last recorded weeks.">
          {finance.weekly_breakdown.length ? (
            <>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={finance.weekly_breakdown}>
                    <CartesianGrid stroke="rgba(127,153,188,0.12)" vertical={false} />
                    <XAxis dataKey="week" stroke="#92a4bb" />
                    <YAxis stroke="#92a4bb" />
                    <Tooltip
                      contentStyle={{
                        background: "#08111f",
                        border: "1px solid rgba(127,153,188,0.18)",
                        borderRadius: 16,
                      }}
                    />
                    <Bar dataKey="income" fill="#34d399" radius={[8, 8, 0, 0]} />
                    <Bar dataKey="expenses" fill="#fb7185" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="stat-label">Sponsor Base</div>
                  <div className="mt-2 font-display text-3xl font-semibold">{formatMoney(finance.summary.weekly_sponsor_income)}</div>
                </div>
                <div className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="stat-label">Weekly Operations</div>
                  <div className="mt-2 font-display text-3xl font-semibold">{formatMoney(finance.summary.weekly_operating_cost)}</div>
                </div>
                <div className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="stat-label">Average Home Gate</div>
                  <div className="mt-2 font-display text-3xl font-semibold">{formatMoney(finance.summary.average_home_gate)}</div>
                </div>
              </div>
            </>
          ) : (
            <EmptyState title="Ledger warming up" body="Complete the first week and the finance room will start plotting real cash flow." />
          )}
        </SectionCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <SectionCard title="Recent Ledger" subtitle="Latest recorded budget movements and management events.">
          <div className="space-y-3">
            {finance.recent_transactions.length ? (
              finance.recent_transactions.map((transaction) => (
                <div key={transaction.id} className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="stat-label">
                        Week {transaction.week} · {formatCategory(transaction.category)}
                      </div>
                      <div className="mt-2 font-medium">{transaction.note}</div>
                    </div>
                    <div className={transaction.amount >= 0 ? "text-success" : "text-danger"}>
                      {transaction.amount >= 0 ? "+" : ""}
                      {formatMoney(transaction.amount)}
                    </div>
                  </div>
                  <div className="mt-3 text-sm text-muted">Balance after entry: {formatMoney(transaction.balance_after)}</div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">No finance transactions have been logged yet.</div>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Forward View" subtitle="A short projection rather than a full spreadsheet.">
          <div className="space-y-4">
            <div className="rounded-2xl bg-slate-950/30 p-4">
              <div className="stat-label">Current Wage Space</div>
              <div className="mt-2 font-display text-3xl font-semibold">{formatMoney(finance.summary.remaining_wage_budget)}</div>
              <p className="mt-2 text-sm text-muted">
                {formatMoney(finance.summary.current_wages)} committed against a {formatMoney(finance.summary.wage_budget)} ceiling.
              </p>
            </div>
            <div className="rounded-2xl bg-slate-950/30 p-4">
              <div className="stat-label">Net Trend</div>
              {finance.weekly_breakdown.length ? (
                <div className="mt-4 h-[180px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={finance.weekly_breakdown}>
                      <CartesianGrid stroke="rgba(127,153,188,0.12)" vertical={false} />
                      <XAxis dataKey="week" stroke="#92a4bb" />
                      <YAxis stroke="#92a4bb" />
                      <Tooltip
                        contentStyle={{
                          background: "#08111f",
                          border: "1px solid rgba(127,153,188,0.18)",
                          borderRadius: 16,
                        }}
                      />
                      <Line type="monotone" dataKey="net" stroke="#f59e0b" strokeWidth={3} dot={{ r: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="mt-2 text-sm text-muted">No weekly trend recorded yet.</p>
              )}
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
