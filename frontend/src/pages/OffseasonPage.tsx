import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { api } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { OffseasonStatusResponse, SeasonReviewResponse, YouthIntakeResponse } from "../lib/types";
import { useGameStore } from "../store/useGameStore";

export function OffseasonPage() {
  const navigate = useNavigate();
  const currentSave = useGameStore((state) => state.currentSave);
  const advanceOffseason = useGameStore((state) => state.advanceOffseason);
  const refreshSave = useGameStore((state) => state.refreshSave);
  const [review, setReview] = useState<SeasonReviewResponse | null>(null);
  const [status, setStatus] = useState<OffseasonStatusResponse | null>(null);
  const [youth, setYouth] = useState<YouthIntakeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    try {
      const [statusResponse, reviewResponse] = await Promise.all([api.offseasonStatus(), api.seasonReview()]);
      setStatus(statusResponse);
      setReview(reviewResponse);
      if (statusResponse.save.offseason_step === "youth_intake" || statusResponse.save.offseason_step === "rollover") {
        setYouth(await api.youthIntake());
      } else {
        setYouth(null);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, [currentSave?.phase, currentSave?.offseason_step]);

  async function handleAdvance() {
    setBusy(true);
    setMessage(null);
    try {
      const save = await advanceOffseason();
      if (save.phase === "in_season") {
        await refreshSave();
        navigate("/");
        return;
      }
      await loadData();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Failed to advance offseason");
    } finally {
      setBusy(false);
    }
  }

  async function handleRenew(playerId: number, wage: number) {
    setBusy(true);
    setMessage(null);
    try {
      const response = await api.renewContract(playerId, 3, Math.round(wage * 1.08));
      setMessage(response.message);
      await loadData();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Failed to renew contract");
    } finally {
      setBusy(false);
    }
  }

  async function handlePromote(prospectId: number) {
    setBusy(true);
    setMessage(null);
    try {
      const response = await api.promoteYouth(prospectId);
      setMessage(response.message);
      await loadData();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Failed to promote prospect");
    } finally {
      setBusy(false);
    }
  }

  if (!currentSave || currentSave.phase === "in_season") {
    return <Navigate to="/" replace />;
  }

  if (loading || !status || !review) {
    return <LoadingPanel label="Loading offseason" className="min-h-[60vh]" />;
  }

  const actionLabel =
    currentSave.offseason_step === "review"
      ? "Continue To Contracts"
      : currentSave.offseason_step === "contracts"
        ? "Finalize Contract Decisions"
        : currentSave.offseason_step === "youth_intake"
          ? "Continue To Rollover"
          : "Start New Season";

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={`${currentSave.season_label} Offseason`}
        title={`${currentSave.user_team_name} Career Review`}
        description="Review the finished campaign, manage expiring deals, assess the youth intake, and roll into the next season."
        actions={
          <button className="btn-primary" onClick={() => void handleAdvance()} disabled={busy}>
            {busy ? "Processing..." : actionLabel}
          </button>
        }
      />
      {message ? <div className="rounded-2xl bg-accentSoft px-4 py-3 text-sm">{message}</div> : null}

      <div className="data-grid">
        <StatCard label="Final Position" value={`#${review.club_summary.final_position}`} />
        <StatCard label="Board Verdict" value={review.club_summary.board_verdict} detail={`Objective: ${review.club_summary.board_objective}`} />
        <StatCard label="Next Budget" value={formatMoney(status.projected_transfer_budget)} />
        <StatCard label="Next Wage Budget" value={formatMoney(status.projected_wage_budget)} />
      </div>

      <SectionCard title="Season Review" subtitle="Final table and board summary from the completed campaign.">
        <div className="grid gap-4 xl:grid-cols-[0.7fr_1.3fr]">
          <div className="space-y-3">
            <div className="rounded-2xl bg-slate-950/30 p-4">
              <div className="stat-label">Record</div>
              <div className="mt-2 font-display text-3xl font-semibold">
                {review.club_summary.wins}-{review.club_summary.draws}-{review.club_summary.losses}
              </div>
              <p className="mt-2 text-sm text-muted">
                {review.club_summary.table_points} points, {review.club_summary.points_difference >= 0 ? "+" : ""}
                {review.club_summary.points_difference} difference.
              </p>
            </div>
            <div className="rounded-2xl bg-slate-950/30 p-4">
              <div className="stat-label">Next Objective</div>
              <div className="mt-2 text-sm font-medium">{review.next_objective}</div>
            </div>
            <div className="rounded-2xl bg-slate-950/30 p-4">
              <div className="stat-label">Retirements</div>
              <div className="mt-2 text-sm text-muted">{review.retiring_players.join(", ") || "No retirements announced."}</div>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-muted">
                <tr>
                  <th className="pb-3">#</th>
                  <th className="pb-3">Team</th>
                  <th className="pb-3">P</th>
                  <th className="pb-3">W</th>
                  <th className="pb-3">D</th>
                  <th className="pb-3">L</th>
                  <th className="pb-3">PD</th>
                  <th className="pb-3">Pts</th>
                </tr>
              </thead>
              <tbody>
                {review.table.rows.map((row) => (
                  <tr key={row.team_id} className="border-t border-border">
                    <td className="py-3 font-medium text-accent">{row.position}</td>
                    <td className="py-3">{row.team_name}</td>
                    <td className="py-3">{row.played}</td>
                    <td className="py-3">{row.wins}</td>
                    <td className="py-3">{row.draws}</td>
                    <td className="py-3">{row.losses}</td>
                    <td className="py-3">{row.points_difference}</td>
                    <td className="py-3 font-semibold">{row.table_points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Contract Decisions" subtitle="Expiring players can be renewed now before rollover finalizes departures.">
        <div className="space-y-3">
          {status.expiring_contracts.length ? (
            status.expiring_contracts.map((player) => (
              <div key={player.id} className="grid gap-3 rounded-2xl bg-slate-950/30 p-4 md:grid-cols-[1fr_auto] md:items-center">
                <div>
                  <div className="font-medium">{player.name}</div>
                  <div className="mt-1 text-sm text-muted">
                    {player.primary_position} · OVR {player.overall_rating} · Wage {formatMoney(player.wage)}
                  </div>
                </div>
                <button className="btn-secondary" onClick={() => void handleRenew(player.id, player.wage)} disabled={busy}>
                  Renew 3 Years
                </button>
              </div>
            ))
          ) : (
            <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">No expiring senior contracts require action.</div>
          )}
        </div>
      </SectionCard>

      <SectionCard title="Youth Intake" subtitle="Simple academy intake for the coming year. Promote ready prospects before the new season begins.">
        <div className="space-y-3">
          {youth?.prospects.length ? (
            youth.prospects.map((prospect) => (
              <div key={prospect.id} className="grid gap-3 rounded-2xl bg-slate-950/30 p-4 md:grid-cols-[1fr_auto] md:items-center">
                <div>
                  <div className="font-medium">{prospect.name}</div>
                  <div className="mt-1 text-sm text-muted">
                    {prospect.primary_position} · OVR {prospect.overall_rating} · POT {prospect.potential} · Readiness {prospect.readiness}
                  </div>
                </div>
                <button className="btn-secondary" onClick={() => void handlePromote(prospect.id)} disabled={busy || currentSave.offseason_step !== "youth_intake"}>
                  Promote
                </button>
              </div>
            ))
          ) : (
            <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">
              {currentSave.offseason_step === "review" || currentSave.offseason_step === "contracts"
                ? "Youth intake unlocks after contract decisions."
                : "No remaining unpromoted prospects in this intake."}
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
