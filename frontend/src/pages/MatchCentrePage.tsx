import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { api } from "../lib/api";
import type {
  Dashboard,
  LiveMatchHalftimePayload,
  LiveMatchSnapshot,
  MatchResult,
  Tactics,
} from "../lib/types";
import { useGameStore } from "../store/useGameStore";

const tacticFields: Array<{
  key: keyof Tactics;
  label: string;
  options: string[];
}> = [
  { key: "attacking_style", label: "Attacking Style", options: ["forward-oriented", "balanced", "expansive"] },
  { key: "kicking_approach", label: "Kicking Approach", options: ["low", "balanced", "high"] },
  { key: "defensive_system", label: "Defensive System", options: ["drift", "balanced", "rush"] },
  { key: "ruck_commitment", label: "Ruck Commitment", options: ["low", "balanced", "high"] },
  { key: "set_piece_intent", label: "Set Piece Intent", options: ["safe", "balanced", "aggressive"] },
  { key: "goal_choice", label: "Goal Choice", options: ["go for posts", "balanced", "kick to corner"] },
];

function MatchSummary({ match }: { match: MatchResult }) {
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Match Centre"
        title={`${match.home_team_name} ${match.home_score} - ${match.away_score} ${match.away_team_name}`}
        description={match.summary}
      />

      <div className="data-grid">
        <StatCard label={match.home_team_name} value={match.home_score} detail={`${match.home_tries} tries · ${match.home_penalties} penalties`} />
        <StatCard label={match.away_team_name} value={match.away_score} detail={`${match.away_tries} tries · ${match.away_penalties} penalties`} />
        <StatCard label="Possession" value={`${match.stats.home.possession}% / ${match.stats.away.possession}%`} detail="Home / away share." />
        <StatCard label="Territory" value={`${match.stats.home.territory}% / ${match.stats.away.territory}%`} detail="Home / away share." />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <SectionCard title="Match Stats" subtitle="Key performance markers from the simulation.">
          <div className="space-y-3 text-sm">
            {[
              ["Penalties conceded", match.stats.home.penalties_conceded, match.stats.away.penalties_conceded],
              ["Turnovers", match.stats.home.turnovers, match.stats.away.turnovers],
              ["Tackles made", match.stats.home.tackles_made, match.stats.away.tackles_made],
              ["Tackles missed", match.stats.home.tackles_missed, match.stats.away.tackles_missed],
              ["Line breaks", match.stats.home.line_breaks, match.stats.away.line_breaks],
              ["Scrum success", `${match.stats.home.scrum_success}%`, `${match.stats.away.scrum_success}%`],
              ["Lineout success", `${match.stats.home.lineout_success}%`, `${match.stats.away.lineout_success}%`],
            ].map(([label, home, away]) => (
              <div key={String(label)} className="grid grid-cols-[1fr_auto_auto] gap-4 rounded-2xl bg-slate-950/30 px-4 py-3">
                <div className="text-muted">{label}</div>
                <div>{home}</div>
                <div>{away}</div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Commentary" subtitle="Generated match timeline.">
          <div className="space-y-3">
            {match.commentary.map((event, index) => (
              <div key={`${event.minute}-${index}`} className="rounded-2xl border border-border bg-slate-950/25 px-4 py-3">
                <div className="flex items-center justify-between gap-4">
                  <div className="font-medium">{event.team}</div>
                  <div className="rounded-full bg-accentSoft px-3 py-1 text-xs font-semibold text-accent">{event.minute}'</div>
                </div>
                <p className="mt-2 text-sm text-muted">{event.text}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}

function PitchView({ live }: { live: LiveMatchSnapshot }) {
  return (
    <SectionCard title="Live Pitch" subtitle="Accelerated field position and recent match pressure.">
      <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(34,197,94,0.18),rgba(4,120,87,0.24))] px-5 py-8">
        <div className="absolute inset-0 bg-[repeating-linear-gradient(90deg,rgba(255,255,255,0.06)_0px,rgba(255,255,255,0.06)_1px,transparent_1px,transparent_12.5%)]" />
        <div className="absolute inset-y-0 left-1/2 w-px bg-white/30" />
        <div className="absolute inset-y-6 left-[22%] w-px border-l border-dashed border-white/20" />
        <div className="absolute inset-y-6 right-[22%] w-px border-l border-dashed border-white/20" />
        <div className="relative h-52">
          <div className="flex justify-between text-xs font-semibold uppercase tracking-[0.25em] text-white/70">
            <span>{live.home.team_name}</span>
            <span>Halfway</span>
            <span>{live.away.team_name}</span>
          </div>
          <div
            className="absolute top-1/2 z-10 h-5 w-5 -translate-y-1/2 rounded-full border-2 border-slate-950 bg-amber-300 shadow-[0_0_18px_rgba(245,158,11,0.8)] transition-all duration-700"
            style={{ left: `calc(${live.ball_position}% - 10px)` }}
          />
          {live.recent_events.slice(-3).map((event, index) => (
            <div
              key={`${event.minute}-${event.type}-${index}`}
              className="absolute z-20 -translate-x-1/2 rounded-full bg-slate-950/85 px-3 py-1 text-[11px] font-medium text-white shadow-lg"
              style={{ left: `${event.field_position}%`, top: `${24 + index * 18}%` }}
            >
              {event.type.replace("-", " ")}
            </div>
          ))}
          <div className="absolute inset-x-0 bottom-0 flex justify-between text-xs text-white/70">
            <span>Home 22</span>
            <span>Kick battle</span>
            <span>Away 22</span>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}

export function MatchCentrePage() {
  const params = useParams<{ fixtureId?: string }>();
  const storedLatestMatch = useGameStore((state) => state.latestMatch);
  const setLatestMatch = useGameStore((state) => state.setLatestMatch);
  const setCurrentSave = useGameStore((state) => state.setCurrentSave);
  const [match, setMatch] = useState<MatchResult | null>(storedLatestMatch);
  const [live, setLive] = useState<LiveMatchSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tickPending, setTickPending] = useState(false);
  const [substitutions, setSubstitutions] = useState<Record<number, number>>({});
  const [halftime, setHalftime] = useState<LiveMatchHalftimePayload | null>(null);
  const [savingHalftime, setSavingHalftime] = useState(false);

  function applyLiveSnapshot(snapshot: LiveMatchSnapshot) {
    setLive(snapshot);
    setMatch(snapshot.result);
    setCurrentSave(snapshot.save);
    if (snapshot.result) {
      setLatestMatch(snapshot.result);
    }
  }

  useEffect(() => {
    async function loadMatchCentre() {
      setLoading(true);
      setError(null);
      try {
        if (params.fixtureId) {
          setLive(null);
          setMatch(await api.match(Number(params.fixtureId)));
          return;
        }

        const currentLive = await api.currentLiveMatch();
        if (currentLive) {
          applyLiveSnapshot(currentLive);
          return;
        }

        const dashboard: Dashboard = await api.dashboard();
        setCurrentSave(dashboard.save);
        if (dashboard.save.phase === "in_season" && dashboard.next_fixture) {
          applyLiveSnapshot(await api.startLiveMatch());
          return;
        }
        setLive(null);
        setMatch(dashboard.latest_match);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Failed to load match centre");
      } finally {
        setLoading(false);
      }
    }

    void loadMatchCentre();
  }, [params.fixtureId, setCurrentSave, setLatestMatch]);

  useEffect(() => {
    if (!live || params.fixtureId || !["first_half", "second_half"].includes(live.status) || tickPending) {
      return undefined;
    }
    const timer = window.setTimeout(async () => {
      setTickPending(true);
      try {
        applyLiveSnapshot(await api.tickLiveMatch());
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Failed to progress live match");
      } finally {
        setTickPending(false);
      }
    }, 900);
    return () => window.clearTimeout(timer);
  }, [live, params.fixtureId, tickPending]);

  useEffect(() => {
    if (!live || live.status !== "halftime") {
      return;
    }
    setSubstitutions({});
    setHalftime({
      tactics: live.user_tactics,
      substitutions: [],
      captain_id: live.user_selection.captain_id,
      goal_kicker_id: live.user_selection.goal_kicker_id,
    });
  }, [live?.session_id, live?.status]);

  const starters = useMemo(() => live?.user_matchday_players.filter((player) => player.on_field) ?? [], [live]);
  const bench = useMemo(() => live?.user_matchday_players.filter((player) => !player.on_field) ?? [], [live]);

  async function handleHalftimeSubmit() {
    if (!halftime) {
      return;
    }
    setSavingHalftime(true);
    setError(null);
    try {
      applyLiveSnapshot(
        await api.submitHalftime({
          ...halftime,
          substitutions: Object.entries(substitutions).map(([playerOutId, playerInId]) => ({
            player_out_id: Number(playerOutId),
            player_in_id: Number(playerInId),
          })),
        }),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to submit halftime changes");
    } finally {
      setSavingHalftime(false);
    }
  }

  if (loading) {
    return <LoadingPanel label="Loading match centre" className="min-h-[60vh]" />;
  }

  if (live?.result && live.status === "full_time") {
    return <MatchSummary match={live.result} />;
  }

  if (match && !live) {
    return <MatchSummary match={match} />;
  }

  if (!live) {
    return (
      <EmptyState
        title="No live match available"
        body={error ?? "There is no active fixture to play right now. Return after scheduling a new week or review the last completed result."}
      />
    );
  }

  const homePossession = live.home.stats.possession;
  const homeTerritory = live.home.stats.territory;

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Live Match Centre"
        title={`${live.home.team_name} ${live.home.score} - ${live.away.score} ${live.away.team_name}`}
        description={
          live.status === "halftime"
            ? "Halftime. Adjust tactics, reshuffle the bench, and send the side back out."
            : live.status === "full_time"
              ? "Full time."
              : `Accelerated live simulation · ${live.minute}'`
        }
        actions={
          <div className="rounded-full bg-accentSoft px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent">
            {live.status.replace("_", " ")}
          </div>
        }
      />
      {error ? <div className="rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}

      <div className="data-grid">
        <StatCard label={live.home.team_name} value={live.home.score} detail={`${live.home.tries} tries · ${live.home.penalties} penalties`} />
        <StatCard label={live.away.team_name} value={live.away.score} detail={`${live.away.tries} tries · ${live.away.penalties} penalties`} />
        <StatCard label="Possession" value={`${homePossession}% / ${live.away.stats.possession}%`} detail="Home / away share." />
        <StatCard label="Territory" value={`${homeTerritory}% / ${live.away.stats.territory}%`} detail="Home / away share." />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <PitchView live={live} />
        <SectionCard title="Match Pulse" subtitle="Current balance of the contest.">
          <div className="space-y-4">
            <div>
              <div className="mb-2 flex justify-between text-xs uppercase tracking-[0.2em] text-muted">
                <span>Possession</span>
                <span>{homePossession}% / {live.away.stats.possession}%</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-950/40">
                <div className="h-full bg-amber-400 transition-all duration-700" style={{ width: `${homePossession}%` }} />
              </div>
            </div>
            <div>
              <div className="mb-2 flex justify-between text-xs uppercase tracking-[0.2em] text-muted">
                <span>Territory</span>
                <span>{homeTerritory}% / {live.away.stats.territory}%</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-950/40">
                <div className="h-full bg-emerald-400 transition-all duration-700" style={{ width: `${homeTerritory}%` }} />
              </div>
            </div>
            <div className="grid gap-3 text-sm">
              {[
                ["Turnovers", live.home.stats.turnovers, live.away.stats.turnovers],
                ["Line breaks", live.home.stats.line_breaks, live.away.stats.line_breaks],
                ["Scrum success", `${live.home.stats.scrum_success}%`, `${live.away.stats.scrum_success}%`],
                ["Lineout success", `${live.home.stats.lineout_success}%`, `${live.away.stats.lineout_success}%`],
                ["Cards", live.home.stats.cards, live.away.stats.cards],
              ].map(([label, home, away]) => (
                <div key={String(label)} className="grid grid-cols-[1fr_auto_auto] gap-4 rounded-2xl bg-slate-950/30 px-4 py-3">
                  <div className="text-muted">{label}</div>
                  <div>{home}</div>
                  <div>{away}</div>
                </div>
              ))}
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Commentary Feed" subtitle="Live commentary updates as each accelerated block resolves.">
          <div className="space-y-3">
            {live.commentary.map((event, index) => (
              <div key={`${event.minute}-${event.type}-${index}`} className="rounded-2xl border border-border bg-slate-950/25 px-4 py-3">
                <div className="flex items-center justify-between gap-4">
                  <div className="font-medium">{event.team}</div>
                  <div className="rounded-full bg-accentSoft px-3 py-1 text-xs font-semibold text-accent">{event.minute}'</div>
                </div>
                <p className="mt-2 text-sm text-muted">{event.text}</p>
              </div>
            ))}
          </div>
        </SectionCard>

        {live.status === "halftime" && halftime ? (
          <SectionCard title="Halftime Adjustments" subtitle="Change match tactics and reshuffle the bench before the second half.">
            <div className="space-y-5">
              <div className="grid gap-3 md:grid-cols-2">
                {tacticFields.map((field) => (
                  <label key={field.key} className="space-y-2 text-sm">
                    <span className="stat-label">{field.label}</span>
                    <select
                      className="w-full rounded-2xl border border-border bg-slate-950/40 px-4 py-3"
                      value={halftime.tactics[field.key]}
                      onChange={(event) =>
                        setHalftime({
                          ...halftime,
                          tactics: { ...halftime.tactics, [field.key]: event.target.value },
                        })
                      }
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

              <div className="grid gap-3">
                {starters.map((player) => (
                  <div key={player.player_id} className="rounded-2xl bg-slate-950/30 p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <div className="font-medium">{player.starter_slot} · {player.name}</div>
                        <div className="mt-1 text-xs text-muted">Fitness {player.fitness} · Fatigue {player.fatigue}{player.injury_status ? ` · ${player.injury_status}` : ""}</div>
                      </div>
                      <select
                        className="rounded-2xl border border-border bg-slate-950/40 px-4 py-3 text-sm"
                        value={substitutions[player.player_id] ?? ""}
                        onChange={(event) => {
                          const next = { ...substitutions };
                          if (!event.target.value) {
                            delete next[player.player_id];
                          } else {
                            next[player.player_id] = Number(event.target.value);
                          }
                          setSubstitutions(next);
                        }}
                      >
                        <option value="">Keep on field</option>
                        {bench
                          .filter((option) => !Object.entries(substitutions).some(([starterId, benchId]) => Number(starterId) !== player.player_id && benchId === option.player_id))
                          .map((option) => (
                            <option key={option.player_id} value={option.player_id}>
                              {option.name} · {option.primary_position} · Fit {option.fitness}
                            </option>
                          ))}
                      </select>
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-2 text-sm">
                  <span className="stat-label">Captain</span>
                  <select
                    className="w-full rounded-2xl border border-border bg-slate-950/40 px-4 py-3"
                    value={halftime.captain_id}
                    onChange={(event) => setHalftime({ ...halftime, captain_id: Number(event.target.value) })}
                  >
                    {live.user_matchday_players.map((player) => (
                      <option key={player.player_id} value={player.player_id}>
                        {player.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2 text-sm">
                  <span className="stat-label">Goal Kicker</span>
                  <select
                    className="w-full rounded-2xl border border-border bg-slate-950/40 px-4 py-3"
                    value={halftime.goal_kicker_id}
                    onChange={(event) => setHalftime({ ...halftime, goal_kicker_id: Number(event.target.value) })}
                  >
                    {live.user_matchday_players.map((player) => (
                      <option key={player.player_id} value={player.player_id}>
                        {player.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <button className="btn-primary" onClick={() => void handleHalftimeSubmit()} disabled={savingHalftime}>
                {savingHalftime ? "Sending team talk..." : "Resume second half"}
              </button>
            </div>
          </SectionCard>
        ) : (
          <SectionCard title="Matchday 23" subtitle="Current on-field group and bench conditions.">
            <div className="space-y-3">
              {live.user_matchday_players.map((player) => (
                <div key={player.player_id} className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-medium">{player.name}</div>
                      <div className="mt-1 text-xs text-muted">
                        {player.on_field ? `${player.starter_slot} starter` : "Bench"} · {player.primary_position}
                        {player.injury_status ? ` · ${player.injury_status}` : ""}
                        {player.card_status ? ` · ${player.card_status}` : ""}
                      </div>
                    </div>
                    <div className="text-right text-xs text-muted">
                      <div>Fit {player.fitness}</div>
                      <div>Fatigue {player.fatigue}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>
        )}
      </div>
    </div>
  );
}
