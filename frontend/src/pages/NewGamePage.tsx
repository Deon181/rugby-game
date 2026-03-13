import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { ClubOption } from "../lib/types";
import { useGameStore } from "../store/useGameStore";

export function NewGamePage() {
  const navigate = useNavigate();
  const [clubs, setClubs] = useState<ClubOption[]>([]);
  const [selectedClub, setSelectedClub] = useState<number | null>(null);
  const [saveName, setSaveName] = useState("Career Save");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setCurrentSave = useGameStore((state) => state.setCurrentSave);

  useEffect(() => {
    void api
      .saveOptions()
      .then((response) => {
        setClubs(response);
        setSelectedClub(response[0]?.team_id ?? null);
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreateSave() {
    if (!selectedClub) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await api.createSave({ team_id: selectedClub, name: saveName });
      setCurrentSave(response.save);
      navigate("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to create save");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen px-4 py-6 md:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="panel-alt overflow-hidden">
          <div className="grid gap-6 p-8 lg:grid-cols-[1.3fr_0.7fr]">
            <div>
              <div className="stat-label">New Career</div>
              <h1 className="mt-2 font-display text-5xl font-bold">Rugby Director</h1>
              <p className="mt-4 max-w-3xl text-base text-muted">
                Take charge of a fictional pro club, shape the squad, and navigate a full double round-robin season with
                rugby-specific tactics, commentary-led matches, and persistent save progression.
              </p>
            </div>
            <div className="rounded-3xl border border-border bg-slate-950/30 p-6">
              <div className="stat-label">Save Setup</div>
              <label className="mt-4 block text-sm text-muted">
                Save name
                <input className="field mt-2" value={saveName} onChange={(event) => setSaveName(event.target.value)} />
              </label>
              <button className="btn-primary mt-5 w-full" onClick={() => void handleCreateSave()} disabled={!selectedClub || submitting}>
                {submitting ? "Creating Save..." : "Start Career"}
              </button>
              {error ? <div className="mt-4 rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}
            </div>
          </div>
        </section>

        {loading ? (
          <div className="panel p-6 text-sm text-muted">Loading club options...</div>
        ) : (
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {clubs.map((club) => {
              const selected = club.team_id === selectedClub;
              return (
                <button
                  key={club.team_id}
                  type="button"
                  onClick={() => setSelectedClub(club.team_id)}
                  className={`panel p-6 text-left transition ${selected ? "border-accent bg-accentSoft/40" : "hover:border-accent/60"}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-display text-3xl font-semibold">{club.name}</div>
                      <div className="mt-1 text-sm text-muted">{club.short_name}</div>
                    </div>
                    <div className="rounded-xl bg-slate-950/50 px-3 py-2 text-right">
                      <div className="stat-label">Rep</div>
                      <div className="font-display text-2xl font-semibold text-accent">{club.reputation}</div>
                    </div>
                  </div>
                  <p className="mt-5 text-sm text-muted">{club.objective}</p>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl bg-slate-950/35 p-3">
                      <div className="stat-label">Budget</div>
                      <div className="mt-2 text-sm font-semibold">{formatMoney(club.budget)}</div>
                    </div>
                    <div className="rounded-2xl bg-slate-950/35 p-3">
                      <div className="stat-label">Wage Budget</div>
                      <div className="mt-2 text-sm font-semibold">{formatMoney(club.wage_budget)}</div>
                    </div>
                  </div>
                  <div className="mt-5 flex flex-wrap gap-2 text-xs text-muted">
                    {Object.entries(club.staff_summary).map(([key, value]) => (
                      <span key={key} className="rounded-full border border-border px-3 py-1">
                        {key}: {value}
                      </span>
                    ))}
                  </div>
                </button>
              );
            })}
          </section>
        )}
      </div>
    </div>
  );
}
