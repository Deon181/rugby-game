import { useEffect, useState } from "react";

import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import type { Tactics } from "../lib/types";

const fields: Array<{ key: keyof Tactics; label: string; options: string[] }> = [
  { key: "attacking_style", label: "Attacking Style", options: ["forward-oriented", "balanced", "expansive"] },
  { key: "kicking_approach", label: "Kicking Approach", options: ["low", "balanced", "high"] },
  { key: "defensive_system", label: "Defensive System", options: ["drift", "balanced", "rush"] },
  { key: "ruck_commitment", label: "Ruck Commitment", options: ["low", "balanced", "high"] },
  { key: "set_piece_intent", label: "Set Piece Intent", options: ["safe", "balanced", "aggressive"] },
  { key: "goal_choice", label: "Goal Choice", options: ["go for posts", "balanced", "kick to corner"] },
  { key: "training_focus", label: "Training Focus", options: ["fitness", "attack", "defense", "set_piece", "recovery"] },
];

export function TacticsPage() {
  const [tactics, setTactics] = useState<Tactics | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void api.tactics().then(setTactics);
  }, []);

  async function handleSave() {
    if (!tactics) {
      return;
    }
    setSaving(true);
    try {
      const response = await api.updateTactics(tactics);
      setTactics(response);
      setMessage("Tactics saved.");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Failed to save tactics");
    } finally {
      setSaving(false);
    }
  }

  if (!tactics) {
    return <LoadingPanel label="Loading tactics" className="min-h-[60vh]" />;
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Tactical Control"
        title="Match Plan"
        description="Set the identity of your side for the coming week. These choices feed directly into territory, set-piece pressure, discipline, and attacking pattern generation."
        actions={
          <button className="btn-primary" onClick={() => void handleSave()} disabled={saving}>
            {saving ? "Saving..." : "Save Tactics"}
          </button>
        }
      />
      {message ? <div className="rounded-2xl bg-accentSoft px-4 py-3 text-sm">{message}</div> : null}
      <SectionCard title="Tactical Settings" subtitle="Every selection has a material effect on the simulation.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {fields.map((field) => (
            <label key={field.key} className="block">
              <div className="mb-2 text-sm font-medium">{field.label}</div>
              <select
                className="field"
                value={tactics[field.key]}
                onChange={(event) => setTactics({ ...tactics, [field.key]: event.target.value })}
              >
                {field.options.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
