import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { DualStatBar } from "../components/match/DualStatBar";
import { EventTimeline } from "../components/match/EventTimeline";
import { MomentumBar } from "../components/match/MomentumBar";
import { PitchSVG } from "../components/match/PitchSVG";
import { api } from "../lib/api";
import {
  buildCoachNotes,
  buildLiveAlerts,
  getOpponentTeamState,
  getUserSide,
  getUserTeamState,
} from "../lib/insights";
import type { LiveAlert } from "../lib/insights";
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

const playbackSpeeds = [
  { label: "Slow", value: 1400 },
  { label: "Standard", value: 900 },
  { label: "Fast", value: 450 },
];

function alertClassName(alert: LiveAlert) {
  if (alert.level === "danger") {
    return "border-rose-400/25 bg-rose-400/10 text-rose-100";
  }
  if (alert.level === "warn") {
    return "border-amber-400/25 bg-amber-400/10 text-amber-100";
  }
  return "border-sky-400/25 bg-sky-400/10 text-sky-100";
}

function pressureLabel(value: number) {
  if (value >= 72) {
    return "Dominant field position";
  }
  if (value >= 58) {
    return "Territory edge";
  }
  if (value >= 42) {
    return "Even balance";
  }
  if (value >= 28) {
    return "Absorbing pressure";
  }
  return "Pinned back";
}

function AnimatedScore({ score, colorClass }: { score: number; colorClass: string }) {
  return <div className={`mt-2 font-display text-4xl font-bold score-pop ${colorClass}`}>{score}</div>;
}

function MatchSummary({ match, onBack }: { match: MatchResult; onBack: () => void }) {
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Match Centre"
        title={`${match.home_team_name} ${match.home_score} - ${match.away_score} ${match.away_team_name}`}
        description={match.summary}
        actions={<button className="btn-secondary" onClick={onBack}>Back to Fixtures</button>}
      />

      <div className="data-grid">
        <StatCard label={match.home_team_name} value={match.home_score} detail={`${match.home_tries} tries · ${match.home_penalties} penalties`} />
        <StatCard label={match.away_team_name} value={match.away_score} detail={`${match.away_tries} tries · ${match.away_penalties} penalties`} />
        <StatCard label="Possession" value={`${match.stats.home.possession}% / ${match.stats.away.possession}%`} detail="Home / away share." />
        <StatCard label="Territory" value={`${match.stats.home.territory}% / ${match.stats.away.territory}%`} detail="Home / away share." />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <SectionCard title="Score Breakdown" subtitle="Where the points and pressure came from.">
          <div className="space-y-3 text-sm">
            {[
              ["Tries", match.home_tries, match.away_tries],
              ["Conversions", match.home_conversions, match.away_conversions],
              ["Penalties", match.home_penalties, match.away_penalties],
              ["Turnovers", match.stats.home.turnovers, match.stats.away.turnovers],
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

        <SectionCard title="Commentary Archive" subtitle="Full match timeline from the simulation engine.">
          <div className="max-h-[620px] space-y-3 overflow-y-auto pr-2">
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

export function MatchCentrePage() {
  const navigate = useNavigate();
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
  const [autoPlay, setAutoPlay] = useState(true);
  const [tickDelay, setTickDelay] = useState(900);
  const commentaryRef = useRef<HTMLDivElement | null>(null);

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
          setAutoPlay(false);
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

  const tickLiveMatch = useEffectEvent(async () => {
    setTickPending(true);
    setError(null);
    try {
      applyLiveSnapshot(await api.tickLiveMatch());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to progress live match");
    } finally {
      setTickPending(false);
    }
  });

  useEffect(() => {
    if (!live || params.fixtureId || !autoPlay || !["first_half", "second_half"].includes(live.status) || tickPending) {
      return undefined;
    }
    const timer = window.setTimeout(() => {
      void tickLiveMatch();
    }, tickDelay);
    return () => window.clearTimeout(timer);
  }, [autoPlay, live, params.fixtureId, tickDelay, tickPending]);

  useEffect(() => {
    if (!live) {
      return;
    }
    if (!["first_half", "second_half"].includes(live.status)) {
      setAutoPlay(false);
    }
  }, [live?.status]);

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

  useEffect(() => {
    if (!live || !commentaryRef.current) {
      return;
    }
    commentaryRef.current.scrollTo({
      top: commentaryRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [live?.commentary.length]);

  const starters = useMemo(() => live?.user_matchday_players.filter((player) => player.on_field) ?? [], [live]);
  const bench = useMemo(() => live?.user_matchday_players.filter((player) => !player.on_field) ?? [], [live]);
  const alerts = useMemo(() => (live ? buildLiveAlerts(live) : []), [live]);
  const coachNotes = useMemo(() => (live ? buildCoachNotes(live) : []), [live]);
  const userSide = live ? getUserSide(live) : null;
  const user = live ? getUserTeamState(live) : null;
  const opponent = live ? getOpponentTeamState(live) : null;
  const userPressure = live ? (userSide === "home" ? live.ball_position : 100 - live.ball_position) : 50;
  const lastEvent = live?.recent_events.at(-1) ?? null;

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
      setAutoPlay(true);
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
    return <MatchSummary match={live.result} onBack={() => navigate("/fixtures")} />;
  }

  if (match && !live) {
    return <MatchSummary match={match} onBack={() => navigate("/fixtures")} />;
  }

  if (!live || !user || !opponent) {
    return (
      <EmptyState
        title="No live match available"
        body={error ?? "There is no active fixture to play right now. Return after scheduling a new week or review the last completed result."}
      />
    );
  }

  const playable = ["first_half", "second_half"].includes(live.status);

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
              : `Live simulation in progress at ${live.minute}'. The coaching box can pause, accelerate, or step through the blocks.`
        }
        actions={
          <>
            {playbackSpeeds.map((speed) => (
              <button
                key={speed.value}
                className={`chip ${tickDelay === speed.value ? "chip-active" : ""}`}
                onClick={() => setTickDelay(speed.value)}
                disabled={!playable}
              >
                {speed.label}
              </button>
            ))}
            <button
              className="btn-secondary"
              onClick={() => setAutoPlay((current) => !current)}
              disabled={!playable}
            >
              {autoPlay && playable ? "Pause Feed" : "Resume Feed"}
            </button>
            <button className="btn-primary" onClick={() => void tickLiveMatch()} disabled={!playable || tickPending}>
              {tickPending ? "Advancing..." : "Advance Now"}
            </button>
          </>
        }
      />

      {error ? <div className="rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}

      <div className="data-grid">
        <div className="panel p-5">
          <div className="stat-label">{user.team_name}</div>
          <AnimatedScore
            key={`home-${user.score}`}
            score={user.score}
            colorClass={user.score >= opponent.score ? "text-success" : "text-warn"}
          />
          <div className="mt-3 text-sm text-muted">{user.tries} tries · {user.penalties} penalties</div>
        </div>
        <div className="panel p-5">
          <div className="stat-label">{opponent.team_name}</div>
          <AnimatedScore
            key={`away-${opponent.score}`}
            score={opponent.score}
            colorClass={user.score >= opponent.score ? "text-warn" : "text-danger"}
          />
          <div className="mt-3 text-sm text-muted">{opponent.tries} tries · {opponent.penalties} penalties</div>
        </div>
        <StatCard label="Possession" value={`${user.stats.possession}%`} detail={`${opponent.stats.possession}% for ${opponent.team_name}`} accent={user.stats.possession >= 50 ? "success" : "warn"} />
        <StatCard label="Territory" value={`${user.stats.territory}%`} detail={`${opponent.stats.territory}% for ${opponent.team_name}`} accent={user.stats.territory >= 50 ? "success" : "warn"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <PitchSVG
          ballPosition={live.ball_position}
          recentEvents={live.recent_events}
          homeTeamName={live.home.team_name}
          awayTeamName={live.away.team_name}
          commentaryLength={live.commentary.length}
          userPressure={userPressure}
        />

        <SectionCard title="Command Deck" subtitle="Playback control, scoreboard context, and the latest swing in the match.">
          <div className="space-y-4">
            <div className="rounded-[28px] border border-border bg-slate-950/35 p-5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="chip chip-active">{live.status.replace("_", " ")}</span>
                <span className="chip">
                  {live.current_block}/{live.total_blocks} blocks
                </span>
                <span className="chip">{pressureLabel(userPressure)}</span>
              </div>
              <div className="mt-5 grid gap-4 md:grid-cols-3">
                <div>
                  <div className="stat-label">Game Clock</div>
                  <div className="mt-2 font-display text-4xl font-bold">{live.minute}'</div>
                </div>
                <div>
                  <div className="stat-label">Score Margin</div>
                  <div className="mt-2 font-display text-4xl font-bold">
                    {user.score - opponent.score > 0 ? "+" : ""}
                    {user.score - opponent.score}
                  </div>
                </div>
                <div>
                  <div className="stat-label">Last Swing</div>
                  <div className="mt-2 text-sm text-muted">{lastEvent ? `${lastEvent.minute}' ${lastEvent.text}` : "Awaiting the next event."}</div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <DualStatBar
                label="Possession"
                homeValue={live.home.stats.possession ?? 50}
                awayValue={live.away.stats.possession ?? 50}
                homeLabel={live.home.team_name}
                awayLabel={live.away.team_name}
              />
              <DualStatBar
                label="Territory"
                homeValue={live.home.stats.territory ?? 50}
                awayValue={live.away.stats.territory ?? 50}
                homeLabel={live.home.team_name}
                awayLabel={live.away.team_name}
              />
              <MomentumBar
                homeValue={Math.round(((live.home.stats.territory ?? 50) + (live.home.stats.possession ?? 50)) / 2)}
                awayValue={Math.round(((live.away.stats.territory ?? 50) + (live.away.stats.possession ?? 50)) / 2)}
                homeTeamName={live.home.team_name}
                awayTeamName={live.away.team_name}
              />
            </div>

            <div className="grid gap-3 text-sm">
              {[
                ["Turnovers", user.stats.turnovers, opponent.stats.turnovers],
                ["Line breaks", user.stats.line_breaks, opponent.stats.line_breaks],
                ["Penalties conceded", user.stats.penalties_conceded, opponent.stats.penalties_conceded],
                ["Cards", user.stats.cards, opponent.stats.cards],
                ["Scrum success", `${user.stats.scrum_success}%`, `${opponent.stats.scrum_success}%`],
                ["Lineout success", `${user.stats.lineout_success}%`, `${opponent.stats.lineout_success}%`],
              ].map(([label, teamValue, opponentValue]) => (
                <div key={String(label)} className="grid grid-cols-[1fr_auto_auto] gap-4 rounded-2xl bg-slate-950/30 px-4 py-3">
                  <div className="text-muted">{label}</div>
                  <div>{teamValue}</div>
                  <div>{opponentValue}</div>
                </div>
              ))}
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Coach Box" subtitle="Condition alerts and tactical notes generated from the live state.">
          <div className="space-y-5">
            <div>
              <div className="stat-label">Immediate Alerts</div>
              <div className="mt-3 space-y-3">
                {alerts.map((alert, index) => (
                  <div key={`${alert.title}-${index}`} className={`rounded-2xl border px-4 py-3 ${alertClassName(alert)}`}>
                    <div className="font-medium">{alert.title}</div>
                    <div className="mt-1 text-sm opacity-90">{alert.detail}</div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="stat-label">Coaching Notes</div>
              <div className="mt-3 space-y-3">
                {coachNotes.map((note, index) => (
                  <div key={`${note}-${index}`} className="rounded-2xl bg-slate-950/30 px-4 py-3 text-sm text-muted">
                    {note}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </SectionCard>

        {live.status === "halftime" && halftime ? (
          <SectionCard title="Halftime Adjustments" subtitle="Change match tactics and reshuffle the bench before the second half.">
            <div className="space-y-5">
              <div className="rounded-2xl border border-accent/25 bg-accentSoft px-4 py-3 text-sm">
                Halftime pauses autoplay. Lock in any tactical changes, set your bench, then resume the second half.
              </div>

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
                        <div className="font-medium">
                          {player.starter_slot} · {player.name}
                        </div>
                        <div className="mt-1 text-xs text-muted">
                          Fitness {player.fitness} · Fatigue {player.fatigue}
                          {player.injury_status ? ` · ${player.injury_status}` : ""}
                        </div>
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
          <SectionCard title="Matchday 23" subtitle="Current on-field group, bench readiness, and likely impact options.">
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
                      <div>Rating {player.overall_rating}</div>
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

      <EventTimeline commentary={live.commentary} containerRef={commentaryRef} />
    </div>
  );
}
