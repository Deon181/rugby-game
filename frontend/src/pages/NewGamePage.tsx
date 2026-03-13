import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LoadingPanel } from "../components/LoadingPanel";
import { api } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { ClubOption } from "../lib/types";
import { useGameStore } from "../store/useGameStore";

const creationSteps = [
  { id: 1, label: "League Slot" },
  { id: 2, label: "Club Identity" },
] as const;

function normalizeValue(value: string) {
  return value.trim().replace(/\s+/g, " ");
}

function buildSuggestedShortName(name: string) {
  const words = normalizeValue(name)
    .split(" ")
    .filter(Boolean);
  if (words.length >= 2) {
    return words
      .slice(0, 3)
      .map((word) => word[0]!.toUpperCase())
      .join("");
  }
  return normalizeValue(name).slice(0, 18);
}

function validateClubName(value: string, clubs: ClubOption[]) {
  const normalized = normalizeValue(value);
  if (!normalized) {
    return "Enter a club name.";
  }
  if (normalized.length < 2) {
    return "Club name must be at least 2 characters.";
  }
  if (normalized.length > 40) {
    return "Club name must be 40 characters or fewer.";
  }
  if (clubs.some((club) => club.name.toLowerCase() === normalized.toLowerCase())) {
    return "Club name must be unique in this league.";
  }
  return null;
}

function validateShortName(value: string, clubs: ClubOption[]) {
  const normalized = normalizeValue(value);
  if (!normalized) {
    return "Enter a short name.";
  }
  if (normalized.length < 2) {
    return "Short name must be at least 2 characters.";
  }
  if (normalized.length > 18) {
    return "Short name must be 18 characters or fewer.";
  }
  if (clubs.some((club) => club.short_name.toLowerCase() === normalized.toLowerCase())) {
    return "Short name must be unique in this league.";
  }
  return null;
}

export function NewGamePage() {
  const navigate = useNavigate();
  const [clubs, setClubs] = useState<ClubOption[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [clubName, setClubName] = useState("");
  const [clubShortName, setClubShortName] = useState("");
  const [saveName, setSaveName] = useState("Career Save");
  const [currentStep, setCurrentStep] = useState<1 | 2>(1);
  const [shortNameTouched, setShortNameTouched] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setCurrentSave = useGameStore((state) => state.setCurrentSave);
  const setPendingOnboarding = useGameStore((state) => state.setPendingOnboarding);

  useEffect(() => {
    void api
      .saveOptions()
      .then((response) => {
        setClubs(response);
        setSelectedTemplateId(response[0]?.template_team_id ?? null);
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (shortNameTouched) {
      return;
    }
    const suggested = buildSuggestedShortName(clubName);
    setClubShortName(suggested);
  }, [clubName, shortNameTouched]);

  const selectedClub = useMemo(
    () => clubs.find((club) => club.template_team_id === selectedTemplateId) ?? null,
    [clubs, selectedTemplateId],
  );
  const normalizedClubName = normalizeValue(clubName);
  const normalizedShortName = normalizeValue(clubShortName);
  const normalizedSaveName = normalizeValue(saveName);
  const clubNameError = validateClubName(clubName, clubs);
  const shortNameError = validateShortName(clubShortName, clubs);
  const saveNameError = normalizedSaveName ? null : "Enter a save name.";

  async function handleCreateSave() {
    if (!selectedClub || clubNameError || shortNameError || saveNameError) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await api.createSave({
        template_team_id: selectedClub.template_team_id,
        club_name: normalizedClubName,
        club_short_name: normalizedShortName,
        name: normalizedSaveName,
      });
      setCurrentSave(response.save);
      setPendingOnboarding(response.save.id, response.onboarding);
      navigate("/new-game/reveal");
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
          <div className="grid gap-8 p-8 lg:grid-cols-[1.1fr_0.9fr]">
            <div>
              <div className="stat-label">New Club Journey</div>
              <h1 className="mt-2 font-display text-5xl font-bold">Build your entry into the premiership</h1>
              <p className="mt-4 max-w-3xl text-base text-muted">
                Pick the league slot you want to inherit, stamp your own club identity onto it, and take over a seeded
                30-player squad built for a full season from week one.
              </p>
            </div>

            <div className="grid gap-3 rounded-3xl border border-border bg-slate-950/30 p-6">
              <div className="stat-label">Journey</div>
              {creationSteps.map((step) => {
                const active = step.id === currentStep;
                const complete = step.id < currentStep;
                return (
                  <div
                    key={step.id}
                    className={`rounded-2xl border px-4 py-3 text-sm transition ${
                      active
                        ? "border-accent bg-accentSoft/40"
                        : complete
                          ? "border-success/30 bg-success/10"
                          : "border-border bg-slate-950/25"
                    }`}
                  >
                    <div className="stat-label">{`Step ${step.id}`}</div>
                    <div className="mt-1 font-medium text-text">{step.label}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {loading ? (
          <LoadingPanel label="Loading league slots" className="min-h-[40vh]" />
        ) : (
          <>
            {currentStep === 1 ? (
              <section className="space-y-4">
                <div className="flex flex-col gap-2">
                  <div className="stat-label">Step 1</div>
                  <h2 className="font-display text-3xl font-semibold">Choose the league slot to take over</h2>
                  <p className="max-w-3xl text-sm text-muted">
                    You are replacing one existing club identity, not changing league structure. The selected slot
                    provides your budget, reputation, staff quality, and board expectations for year one.
                  </p>
                </div>

                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {clubs.map((club) => {
                    const selected = club.template_team_id === selectedTemplateId;
                    return (
                      <button
                        key={club.template_team_id}
                        type="button"
                        onClick={() => setSelectedTemplateId(club.template_team_id)}
                        className={`panel p-6 text-left transition ${
                          selected ? "border-accent bg-accentSoft/40" : "hover:border-accent/60"
                        }`}
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
                </div>

                <div className="panel flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="stat-label">Selected Slot</div>
                    <div className="mt-2 font-display text-3xl font-semibold">
                      {selectedClub ? selectedClub.name : "Choose a club slot"}
                    </div>
                    <p className="mt-2 text-sm text-muted">
                      {selectedClub
                        ? `You will replace ${selectedClub.name} but keep this slot's budget, staff, and board target.`
                        : "Pick the league package you want to inherit."}
                    </p>
                  </div>
                  <button
                    className="btn-primary"
                    disabled={!selectedClub}
                    onClick={() => setCurrentStep(2)}
                  >
                    Continue to Club Identity
                  </button>
                </div>
              </section>
            ) : null}

            {currentStep === 2 && selectedClub ? (
              <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
                <div className="panel p-6">
                  <div className="stat-label">Step 2</div>
                  <h2 className="mt-2 font-display text-3xl font-semibold">Name your club</h2>
                  <p className="mt-2 text-sm text-muted">
                    Your club will enter the league in place of {selectedClub.name}. Identity is yours; year-one
                    balance comes from the inherited slot.
                  </p>

                  <div className="mt-6 space-y-4">
                    <label className="block text-sm text-muted">
                      Club name
                      <input
                        className="field mt-2"
                        value={clubName}
                        onChange={(event) => setClubName(event.target.value)}
                        placeholder="Harbour City RFC"
                      />
                      {clubNameError ? <div className="mt-2 text-xs text-danger">{clubNameError}</div> : null}
                    </label>

                    <label className="block text-sm text-muted">
                      Short name
                      <input
                        className="field mt-2"
                        value={clubShortName}
                        onChange={(event) => {
                          setShortNameTouched(true);
                          setClubShortName(event.target.value);
                        }}
                        placeholder="HCR"
                      />
                      {shortNameError ? <div className="mt-2 text-xs text-danger">{shortNameError}</div> : null}
                    </label>

                    <label className="block text-sm text-muted">
                      Save name
                      <input
                        className="field mt-2"
                        value={saveName}
                        onChange={(event) => setSaveName(event.target.value)}
                      />
                      {saveNameError ? <div className="mt-2 text-xs text-danger">{saveNameError}</div> : null}
                    </label>
                  </div>

                  <div className="mt-6 flex flex-wrap gap-3">
                    <button className="btn-secondary" onClick={() => setCurrentStep(1)} disabled={submitting}>
                      Back to League Slots
                    </button>
                    <button
                      className="btn-primary"
                      onClick={() => void handleCreateSave()}
                      disabled={Boolean(clubNameError || shortNameError || saveNameError || submitting)}
                    >
                      {submitting ? "Generating Club..." : "Create Club and Reveal Squad"}
                    </button>
                  </div>

                  {error ? <div className="mt-4 rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}
                </div>

                <div className="space-y-4">
                  <section className="panel-alt overflow-hidden p-6">
                    <div className="stat-label">Identity Preview</div>
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                      <span className="chip chip-active">{normalizedShortName || "SHORT NAME"}</span>
                      <span className="chip">{selectedClub.objective}</span>
                    </div>
                    <div className="mt-5 font-display text-4xl font-bold">{normalizedClubName || "Your Club Name"}</div>
                    <p className="mt-3 max-w-2xl text-sm text-muted">
                      Enter the competition with {formatMoney(selectedClub.budget)} in transfer budget,{" "}
                      {formatMoney(selectedClub.wage_budget)} in wage budget, and a board demand to {selectedClub.objective.toLowerCase()}.
                    </p>
                    <div className="mt-6 grid gap-3 md:grid-cols-2">
                      <div className="rounded-2xl bg-slate-950/35 p-4">
                        <div className="stat-label">Replacing</div>
                        <div className="mt-2 text-lg font-semibold">{selectedClub.name}</div>
                        <div className="mt-1 text-sm text-muted">League slot stays intact; only the club identity changes.</div>
                      </div>
                      <div className="rounded-2xl bg-slate-950/35 p-4">
                        <div className="stat-label">Seeded Squad</div>
                        <div className="mt-2 text-lg font-semibold">30 players on arrival</div>
                        <div className="mt-1 text-sm text-muted">Auto-selected matchday 23, ready to tweak after the reveal.</div>
                      </div>
                    </div>
                  </section>

                  <section className="panel p-6">
                    <div className="stat-label">Inherited Football Package</div>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <div className="rounded-2xl bg-slate-950/30 p-4">
                        <div className="stat-label">Reputation</div>
                        <div className="mt-2 font-display text-3xl font-semibold text-accent">{selectedClub.reputation}</div>
                      </div>
                      <div className="rounded-2xl bg-slate-950/30 p-4">
                        <div className="stat-label">Board Target</div>
                        <div className="mt-2 text-sm font-semibold">{selectedClub.objective}</div>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted">
                      {Object.entries(selectedClub.staff_summary).map(([key, value]) => (
                        <span key={key} className="rounded-full border border-border px-3 py-1">
                          {key}: {value}
                        </span>
                      ))}
                    </div>
                  </section>
                </div>
              </section>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
