import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import { scoreLine } from "../lib/format";
import {
  getFixtureOpponentName,
  getFixtureOutcome,
  getFixtureVenueLabel,
  isUserFixture,
  summariseMatchResult,
} from "../lib/insights";
import type { Fixture, FixtureList, LiveMatchSnapshot } from "../lib/types";
import { useGameStore } from "../store/useGameStore";

type FixtureFilter = "round" | "club" | "completed" | "upcoming" | "all";

const filterOptions: Array<{ key: FixtureFilter; label: string }> = [
  { key: "round", label: "Selected Round" },
  { key: "club", label: "My Club" },
  { key: "completed", label: "Completed" },
  { key: "upcoming", label: "Upcoming" },
  { key: "all", label: "All Fixtures" },
];

function fixtureBadgeClasses(outcome: "W" | "D" | "L" | null) {
  if (outcome === "W") {
    return "border-emerald-400/30 bg-emerald-400/10 text-emerald-300";
  }
  if (outcome === "L") {
    return "border-rose-400/30 bg-rose-400/10 text-rose-300";
  }
  if (outcome === "D") {
    return "border-amber-400/30 bg-amber-400/10 text-amber-300";
  }
  return "border-border bg-white/5 text-muted";
}

export function FixturesPage() {
  const navigate = useNavigate();
  const currentSave = useGameStore((state) => state.currentSave);
  const [data, setData] = useState<FixtureList | null>(null);
  const [liveMatch, setLiveMatch] = useState<LiveMatchSnapshot | null>(null);
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<FixtureFilter>("round");
  const [error, setError] = useState<string | null>(null);

  async function loadFixtures() {
    setError(null);
    try {
      const [fixtures, currentLive] = await Promise.all([api.fixtures(), api.currentLiveMatch()]);
      setData(fixtures);
      setLiveMatch(currentLive);
      setSelectedWeek((current) => current ?? fixtures.current_week);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to load fixtures");
    }
  }

  useEffect(() => {
    void loadFixtures();
  }, []);

  const weeks = useMemo(() => {
    const uniqueWeeks = new Set((data?.fixtures ?? []).map((fixture) => fixture.week));
    return [...uniqueWeeks].sort((left, right) => left - right);
  }, [data]);

  const fixturesForWeek = useMemo(
    () => data?.fixtures.filter((fixture) => fixture.week === selectedWeek) ?? [],
    [data, selectedWeek],
  );

  const visibleFixtures = useMemo(() => {
    if (!data || !currentSave) {
      return [];
    }

    const predicates: Record<FixtureFilter, (fixture: Fixture) => boolean> = {
      round: (fixture) => fixture.week === selectedWeek,
      club: (fixture) => isUserFixture(fixture, currentSave.user_team_id),
      completed: (fixture) => fixture.played,
      upcoming: (fixture) => !fixture.played,
      all: () => true,
    };

    return data.fixtures.filter(predicates[selectedFilter]);
  }, [currentSave, data, selectedFilter, selectedWeek]);

  const userRoundFixture = useMemo(() => {
    if (!currentSave) {
      return null;
    }
    return fixturesForWeek.find((fixture) => isUserFixture(fixture, currentSave.user_team_id)) ?? null;
  }, [currentSave, fixturesForWeek]);

  if (!data) {
    return <LoadingPanel label="Loading fixtures" className="min-h-[60vh]" />;
  }

  const playedInWeek = fixturesForWeek.filter((fixture) => fixture.played).length;
  const roundProgress = fixturesForWeek.length ? Math.round((playedInWeek / fixturesForWeek.length) * 100) : 0;

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Season Schedule"
        title="Fixtures and Results"
        description="Navigate the campaign by round, track your own match path, and jump straight into live play or post-match review."
        actions={
          <>
            <select
              className="field min-w-[150px]"
              value={selectedWeek ?? data.current_week}
              onChange={(event) => {
                setSelectedWeek(Number(event.target.value));
                setSelectedFilter("round");
              }}
            >
              {weeks.map((week) => (
                <option key={week} value={week}>
                  Week {week}
                </option>
              ))}
            </select>
            <button
              className="btn-primary"
              onClick={() => {
                if (currentSave?.phase !== "in_season") {
                  navigate("/offseason");
                  return;
                }
                navigate("/match-centre");
              }}
              disabled={currentSave?.phase === "in_season" && !userRoundFixture && !liveMatch}
            >
              {currentSave?.phase === "in_season"
                ? liveMatch
                  ? `Resume Live Match ${liveMatch.minute}'`
                  : `Play Round ${data.current_week} Live`
                : "Open Offseason"}
            </button>
          </>
        }
      />

      {error ? <div className="rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title={`Week ${selectedWeek ?? data.current_week} Focus`} subtitle="Current round state, including your club's direct touchpoint.">
          <div className="space-y-4">
            <div className="rounded-[28px] border border-border bg-slate-950/35 p-5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="chip chip-active">{playedInWeek}/{fixturesForWeek.length || 0} played</span>
                <span className="chip">{roundProgress}% processed</span>
                {userRoundFixture ? (
                  <span className="chip">{getFixtureVenueLabel(userRoundFixture, currentSave?.user_team_id ?? 0)} fixture</span>
                ) : null}
              </div>
              <div className="mt-5 text-sm text-muted">
                {userRoundFixture
                  ? `Your club is facing ${getFixtureOpponentName(userRoundFixture, currentSave?.user_team_id ?? 0)} in this round.`
                  : "Your club does not have a highlighted fixture in this view."}
              </div>
              <div className="mt-4 metric-track">
                <div className="h-full bg-accent" style={{ width: `${roundProgress}%` }} />
              </div>
            </div>

            <div className="space-y-3">
              {fixturesForWeek.length ? (
                fixturesForWeek.map((fixture) => {
                  const isClubFixture = currentSave ? isUserFixture(fixture, currentSave.user_team_id) : false;
                  const outcome = currentSave ? getFixtureOutcome(fixture, currentSave.user_team_id) : null;
                  const isLiveFixture = liveMatch?.fixture.id === fixture.id;
                  return (
                    <button
                      key={fixture.id}
                      className={`w-full rounded-2xl border p-4 text-left transition ${
                        isClubFixture ? "border-accent/30 bg-accentSoft" : "border-border bg-slate-950/30 hover:bg-slate-950/45"
                      }`}
                      onClick={() => {
                        if (isLiveFixture || (!fixture.played && isClubFixture)) {
                          navigate("/match-centre");
                          return;
                        }
                        if (fixture.played) {
                          navigate(`/match-centre/${fixture.id}`);
                        }
                      }}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="stat-label">{fixture.kickoff_label}</div>
                          <div className="mt-2 font-medium">
                            {fixture.home_team_name} vs {fixture.away_team_name}
                          </div>
                          <div className="mt-2 text-sm text-muted">
                            {fixture.result
                              ? scoreLine(
                                  fixture.home_team_name,
                                  fixture.away_team_name,
                                  fixture.result.home_score,
                                  fixture.result.away_score,
                                )
                              : "Awaiting kickoff"}
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {isClubFixture ? (
                            <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${fixtureBadgeClasses(outcome)}`}>
                              {outcome ? `${outcome} result` : "My match"}
                            </span>
                          ) : null}
                          {isLiveFixture ? <span className="chip chip-active">Live</span> : null}
                          {fixture.played ? <span className="chip">Report</span> : <span className="chip">Pending</span>}
                        </div>
                      </div>
                    </button>
                  );
                })
              ) : (
                <EmptyState title="No fixtures in this round" body="Select another week to inspect the broader season schedule." />
              )}
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Fixture Matrix" subtitle="Filter the season list by club, round state, or full competition view.">
          <div className="flex flex-wrap gap-2">
            {filterOptions.map((option) => (
              <button
                key={option.key}
                className={`chip ${selectedFilter === option.key ? "chip-active" : ""}`}
                onClick={() => setSelectedFilter(option.key)}
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-muted">
                <tr>
                  <th className="pb-3 pr-4">Week</th>
                  <th className="pb-3 pr-4">Round</th>
                  <th className="pb-3 pr-4">Fixture</th>
                  <th className="pb-3 pr-4">Context</th>
                  <th className="pb-3 pr-4">Result</th>
                  <th className="pb-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {visibleFixtures.map((fixture) => {
                  const isClubFixture = currentSave ? isUserFixture(fixture, currentSave.user_team_id) : false;
                  const opponent = currentSave ? getFixtureOpponentName(fixture, currentSave.user_team_id) : null;
                  const outcome = currentSave ? getFixtureOutcome(fixture, currentSave.user_team_id) : null;
                  const isLiveFixture = liveMatch?.fixture.id === fixture.id;
                  return (
                    <tr key={fixture.id} className={`border-t border-border ${isClubFixture ? "bg-white/[0.03]" : ""}`}>
                      <td className="py-3 pr-4">{fixture.week}</td>
                      <td className="py-3 pr-4">{fixture.round_name}</td>
                      <td className="py-3 pr-4">
                        <div className="font-medium">{fixture.home_team_name} vs {fixture.away_team_name}</div>
                        <div className="mt-1 text-xs text-muted">{fixture.kickoff_label}</div>
                      </td>
                      <td className="py-3 pr-4 text-muted">
                        {isClubFixture ? `${getFixtureVenueLabel(fixture, currentSave?.user_team_id ?? 0)} vs ${opponent}` : "League fixture"}
                      </td>
                      <td className="py-3 pr-4">
                        {fixture.result ? (
                          <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${fixtureBadgeClasses(outcome)}`}>
                            {scoreLine(
                              fixture.home_team_name,
                              fixture.away_team_name,
                              fixture.result.home_score,
                              fixture.result.away_score,
                            )}
                          </span>
                        ) : (
                          <span className="text-muted">Not played</span>
                        )}
                      </td>
                      <td className="py-3">
                        <button
                          className="btn-ghost"
                          onClick={() => {
                            if (isLiveFixture || (!fixture.played && isClubFixture)) {
                              navigate("/match-centre");
                              return;
                            }
                            if (fixture.played) {
                              navigate(`/match-centre/${fixture.id}`);
                            }
                          }}
                          disabled={!fixture.played && !isClubFixture}
                        >
                          {isLiveFixture ? "Resume Live" : fixture.played ? "Review" : isClubFixture ? "Play Live" : "Unavailable"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <SectionCard title="League Latest" subtitle="Recent completed matches from around the division.">
          <div className="space-y-3">
            {data.recent_matches.length ? (
              data.recent_matches.slice(0, 6).map((match) => {
                const summary = currentSave ? summariseMatchResult(match, currentSave.user_team_id) : null;
                return (
                  <button
                    key={match.fixture_id}
                    className="w-full rounded-2xl bg-slate-950/30 p-4 text-left transition hover:bg-slate-950/45"
                    onClick={() => navigate(`/match-centre/${match.fixture_id}`)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="stat-label">Season {match.season_number}</div>
                        <div className="mt-2 font-medium">
                          {match.home_team_name} {match.home_score} - {match.away_score} {match.away_team_name}
                        </div>
                        <p className="mt-2 text-sm text-muted">{match.summary}</p>
                      </div>
                      {summary ? (
                        <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${fixtureBadgeClasses(summary.outcome)}`}>
                          {summary.outcome}
                        </span>
                      ) : (
                        <span className="chip">Report</span>
                      )}
                    </div>
                  </button>
                );
              })
            ) : (
              <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">No completed league matches to review yet.</div>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Club Run-In" subtitle="Your season path at a glance, including every played and pending league date.">
          <div className="grid gap-3 md:grid-cols-2">
            {currentSave ? (
              data.fixtures
                .filter((fixture) => isUserFixture(fixture, currentSave.user_team_id))
                .map((fixture) => {
                  const outcome = getFixtureOutcome(fixture, currentSave.user_team_id);
                  const opponent = getFixtureOpponentName(fixture, currentSave.user_team_id);
                  return (
                    <button
                      key={fixture.id}
                      className="rounded-2xl bg-slate-950/30 p-4 text-left transition hover:bg-slate-950/45"
                      onClick={() => {
                        if (!fixture.played) {
                          navigate("/match-centre");
                          return;
                        }
                        navigate(`/match-centre/${fixture.id}`);
                      }}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <div className="stat-label">
                            Week {fixture.week} · {getFixtureVenueLabel(fixture, currentSave.user_team_id)}
                          </div>
                          <div className="mt-2 font-medium">{opponent}</div>
                        </div>
                        <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${fixtureBadgeClasses(outcome)}`}>
                          {outcome ?? "Next"}
                        </span>
                      </div>
                      <div className="mt-3 text-sm text-muted">
                        {fixture.result
                          ? scoreLine(
                              fixture.home_team_name,
                              fixture.away_team_name,
                              fixture.result.home_score,
                              fixture.result.away_score,
                            )
                          : fixture.kickoff_label}
                      </div>
                    </button>
                  );
                })
            ) : (
              <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">No active club save.</div>
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
