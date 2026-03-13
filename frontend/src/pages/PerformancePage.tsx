import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { api } from "../lib/api";
import type { MedicalBoardPlayer, PerformanceOverview, PerformancePlan } from "../lib/types";

const FOCUS_OPTIONS = ["fitness", "attack", "defense", "set_piece", "recovery"];
const INTENSITY_OPTIONS = ["light", "balanced", "heavy"];
const CONTACT_OPTIONS = ["low", "balanced", "high"];
const REHAB_OPTIONS = ["standard", "physio", "accelerated"];
const CLEARANCE_OPTIONS = ["out", "managed", "full"];

function medicalTone(player: MedicalBoardPlayer) {
  if (player.clearance_status === "out" || player.injury_weeks_remaining > 0) {
    return "text-danger";
  }
  if (player.clearance_status === "managed" || player.group === "fatigue") {
    return "text-warn";
  }
  return "text-success";
}

export function PerformancePage() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<PerformanceOverview | null>(null);
  const [draftPlan, setDraftPlan] = useState<PerformancePlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingPlan, setSavingPlan] = useState(false);
  const [busyPlayerId, setBusyPlayerId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadOverview() {
    setLoading(true);
    try {
      const response = await api.performance();
      setOverview(response);
      setDraftPlan(response.plan);
      setMessage(null);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Failed to load performance hub");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadOverview();
  }, []);

  async function savePlan() {
    if (!draftPlan) {
      return;
    }
    setSavingPlan(true);
    try {
      const response = await api.updatePerformancePlan(draftPlan);
      setOverview(response);
      setDraftPlan(response.plan);
      setMessage("Weekly performance plan saved.");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Failed to update performance plan");
    } finally {
      setSavingPlan(false);
    }
  }

  async function updateMedical(playerId: number, payload: { rehab_mode?: string; clearance_status?: string }) {
    setBusyPlayerId(playerId);
    try {
      const response = await api.updateMedicalAssignment(playerId, payload);
      setOverview(response);
      setDraftPlan(response.plan);
      setMessage("Medical assignment updated.");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Failed to update medical assignment");
    } finally {
      setBusyPlayerId(null);
    }
  }

  if (loading) {
    return <LoadingPanel label="Loading performance hub" className="min-h-[60vh]" />;
  }

  if (!overview || !draftPlan) {
    return <EmptyState title="No performance data" body={message ?? "The performance hub could not be loaded."} />;
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={`Week ${overview.save.current_week} · Weekly Performance`}
        title="Performance Hub"
        description="Set the weekly training load, manage rehab, and clear returning players before selection and kickoff."
        actions={
          <>
            <button className="btn-secondary" onClick={() => navigate("/squad")}>
              Open Squad
            </button>
            <button className="btn-primary" onClick={() => void savePlan()} disabled={savingPlan}>
              {savingPlan ? "Saving..." : "Save Weekly Plan"}
            </button>
          </>
        }
      />

      {message ? <div className="rounded-2xl bg-accentSoft px-4 py-3 text-sm">{message}</div> : null}

      <div className="data-grid">
        <StatCard label="Training Focus" value={overview.plan.focus} detail="Mirrored into the tactical training-focus field." />
        <StatCard label="Intensity" value={overview.plan.intensity} detail="Balances match sharpness against fatigue carry-over." />
        <StatCard label="Contact Level" value={overview.plan.contact_level} detail="Changes weekly injury exposure and set-piece edge." />
        <StatCard
          label="Injury Risk"
          value={`${overview.staff_effects.injury_risk_multiplier}x`}
          detail={`Fitness staff ${overview.staff_effects.fitness_staff_rating} · Rehab bonus ${overview.staff_effects.rehab_bonus}`}
          accent={overview.staff_effects.injury_risk_multiplier > 1 ? "warn" : "success"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Weekly Plan" subtitle="This replaces the old single training-focus dial with a fuller weekly load plan.">
          <div className="grid gap-4 md:grid-cols-3">
            <label className="block">
              <div className="mb-2 text-sm font-medium">Focus</div>
              <select
                className="field"
                value={draftPlan.focus}
                onChange={(event) => setDraftPlan({ ...draftPlan, focus: event.target.value })}
              >
                {FOCUS_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <div className="mb-2 text-sm font-medium">Intensity</div>
              <select
                className="field"
                value={draftPlan.intensity}
                onChange={(event) => setDraftPlan({ ...draftPlan, intensity: event.target.value })}
              >
                {INTENSITY_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <div className="mb-2 text-sm font-medium">Contact</div>
              <select
                className="field"
                value={draftPlan.contact_level}
                onChange={(event) => setDraftPlan({ ...draftPlan, contact_level: event.target.value })}
              >
                {CONTACT_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">
              Recovery bonus: +{overview.staff_effects.recovery_bonus} on light and balanced recovery weeks.
            </div>
            <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">
              Low contact reduces injury exposure; high contact raises it for extra set-piece edge.
            </div>
            <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">
              Managed returns stay selectable, but they take extra load if you use them immediately.
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Fatigue Watch" subtitle="Players already carrying heavy load into the current week.">
          <div className="space-y-3">
            {overview.fatigue_watch.length ? (
              overview.fatigue_watch.map((player) => (
                <div key={player.player_id} className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-medium">{player.player_name}</div>
                      <div className="mt-1 text-xs text-muted">
                        {player.primary_position} · OVR {player.overall_rating} · Fatigue {player.fatigue}
                      </div>
                    </div>
                    <div className={`font-medium ${medicalTone(player)}`}>{player.group}</div>
                  </div>
                  <p className="mt-3 text-sm text-muted">{player.note}</p>
                </div>
              ))
            ) : (
              <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">No players are above the fatigue alert line right now.</div>
            )}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Medical Board" subtitle="Rehab mode and clearance controls for injured and recently recovered players.">
        {overview.medical_board.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-muted">
                <tr>
                  <th className="pb-3">Player</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Rehab</th>
                  <th className="pb-3">Clearance</th>
                  <th className="pb-3">Condition</th>
                  <th className="pb-3">Note</th>
                </tr>
              </thead>
              <tbody>
                {overview.medical_board.map((player) => (
                  <tr key={player.player_id} className="border-t border-border align-top">
                    <td className="py-3">
                      <div className="font-medium">{player.player_name}</div>
                      <div className="text-xs text-muted">
                        {player.primary_position} · OVR {player.overall_rating}
                      </div>
                    </td>
                    <td className={`py-3 font-medium ${medicalTone(player)}`}>
                      {player.injury_weeks_remaining > 0 ? `${player.injury_status} (${player.injury_weeks_remaining}w)` : player.clearance_status}
                    </td>
                    <td className="py-3">
                      <select
                        className="field min-w-[150px]"
                        value={player.rehab_mode}
                        disabled={busyPlayerId === player.player_id}
                        onChange={(event) => void updateMedical(player.player_id, { rehab_mode: event.target.value })}
                      >
                        {REHAB_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-3">
                      <select
                        className="field min-w-[150px]"
                        value={player.clearance_status}
                        disabled={busyPlayerId === player.player_id || player.injury_weeks_remaining > 0}
                        onChange={(event) => void updateMedical(player.player_id, { clearance_status: event.target.value })}
                      >
                        {CLEARANCE_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-3 text-muted">
                      Fit {player.fitness} · Fat {player.fatigue} · Mor {player.morale}
                    </td>
                    <td className="py-3 text-muted">{player.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">No active rehab or managed-return cases right now.</div>
        )}
      </SectionCard>
    </div>
  );
}
