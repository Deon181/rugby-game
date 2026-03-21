import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { PerformanceOverview, Selection, SquadPlayer, SquadResponse, SquadStats } from "../lib/types";

const lineupSlots = [
  "Loosehead Prop",
  "Hooker",
  "Tighthead Prop",
  "Lock",
  "Lock",
  "Blindside Flanker",
  "Openside Flanker",
  "Number 8",
  "Scrumhalf",
  "Flyhalf",
  "Wing",
  "Inside Centre",
  "Outside Centre",
  "Wing",
  "Fullback",
];

function eligibleForSlot(players: SquadPlayer[], slot: string, selectedId: number) {
  return players.filter(
    (player) =>
      player.id === selectedId || player.primary_position === slot || player.secondary_positions.includes(slot),
  );
}

export function SquadPage() {
  const navigate = useNavigate();
  const [squad, setSquad] = useState<SquadResponse | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [performance, setPerformance] = useState<PerformanceOverview | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [squadStats, setSquadStats] = useState<SquadStats | null>(null);

  async function loadData() {
    const [squadResponse, selectionResponse, performanceResponse] = await Promise.all([
      api.squad(),
      api.selection(),
      api.performance(),
    ]);
    setSquad(squadResponse);
    setSelection(selectionResponse);
    setPerformance(performanceResponse);
    api.squadStats().then(setSquadStats).catch(() => {});
  }

  useEffect(() => {
    void loadData();
  }, []);

  const playersById = useMemo(() => new Map((squad?.players ?? []).map((player) => [player.id, player])), [squad]);
  const matchdayIds = useMemo(
    () => new Set([...(selection?.starting_lineup.map((slot) => slot.player_id) ?? []), ...(selection?.bench_player_ids ?? [])]),
    [selection],
  );
  const medicalByPlayerId = useMemo(() => {
    const map = new Map<number, PerformanceOverview["medical_board"][number]>();
    for (const entry of [...(performance?.medical_board ?? []), ...(performance?.fatigue_watch ?? [])]) {
      map.set(entry.player_id, entry);
    }
    return map;
  }, [performance]);

  async function saveSelection() {
    if (!selection) {
      return;
    }
    setSaving(true);
    try {
      const response = await api.updateSelection(selection);
      setSelection(response);
      setMessage("Selection saved.");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Failed to save selection");
    } finally {
      setSaving(false);
    }
  }

  async function renewContract(playerId: number, wage: number) {
    try {
      const response = await api.renewContract(playerId, 3, Math.round(wage * 1.08));
      setMessage(response.message);
      await loadData();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Failed to renew contract");
    }
  }

  if (!squad || !selection) {
    return <LoadingPanel label="Loading squad" className="min-h-[60vh]" />;
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Squad Management"
        title={`${squad.team.name} Squad`}
        description="Shape the starting XV, bench, captaincy, and contract picture while monitoring fitness, fatigue, morale, and injuries."
        actions={
          <>
            <button className="btn-secondary" onClick={() => navigate("/performance")}>
              Performance Hub
            </button>
            <button className="btn-primary" onClick={() => void saveSelection()} disabled={saving}>
              {saving ? "Saving..." : "Save Matchday Squad"}
            </button>
          </>
        }
      />
      {message ? <div className="rounded-2xl bg-accentSoft px-4 py-3 text-sm">{message}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title="Matchday 23" subtitle="Starting XV, bench, captain, and goal kicker.">
          <div className="space-y-4">
            {selection.starting_lineup.map((slot, index) => (
              <div key={`${slot.slot}-${index}`} className="grid gap-2 md:grid-cols-[180px_1fr] md:items-center">
                <div className="text-sm font-medium">{lineupSlots[index]}</div>
                <select
                  className="field"
                  value={slot.player_id}
                  onChange={(event) => {
                    const next = [...selection.starting_lineup];
                    next[index] = { ...next[index], player_id: Number(event.target.value) };
                    setSelection({ ...selection, starting_lineup: next });
                  }}
                >
                  {eligibleForSlot(squad.players, lineupSlots[index], slot.player_id).map((player) => (
                    <option key={player.id} value={player.id}>
                      {player.name} · {player.primary_position} · OVR {player.overall_rating}
                    </option>
                  ))}
                </select>
              </div>
            ))}

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <div className="mb-2 text-sm font-medium">Bench (select 8)</div>
                <div className="grid gap-2">
                  {squad.players.map((player) => {
                    const starter = selection.starting_lineup.some((slot) => slot.player_id === player.id);
                    return (
                      <label key={player.id} className={`rounded-2xl border border-border p-3 text-sm ${starter ? "opacity-40" : ""}`}>
                        <input
                          type="checkbox"
                          className="mr-2"
                          disabled={starter}
                          checked={selection.bench_player_ids.includes(player.id)}
                          onChange={(event) => {
                            const bench = event.target.checked
                              ? [...selection.bench_player_ids, player.id].slice(0, 8)
                              : selection.bench_player_ids.filter((id) => id !== player.id);
                            setSelection({ ...selection, bench_player_ids: bench });
                          }}
                        />
                        {player.name} · {player.primary_position} · OVR {player.overall_rating}
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-4">
                <label className="block">
                  <div className="mb-2 text-sm font-medium">Captain</div>
                  <select
                    className="field"
                    value={selection.captain_id}
                    onChange={(event) => setSelection({ ...selection, captain_id: Number(event.target.value) })}
                  >
                    {[...matchdayIds].map((playerId) => {
                      const player = playersById.get(playerId)!;
                      return (
                        <option key={playerId} value={playerId}>
                          {player.name}
                        </option>
                      );
                    })}
                  </select>
                </label>
                <label className="block">
                  <div className="mb-2 text-sm font-medium">Goal Kicker</div>
                  <select
                    className="field"
                    value={selection.goal_kicker_id}
                    onChange={(event) => setSelection({ ...selection, goal_kicker_id: Number(event.target.value) })}
                  >
                    {[...matchdayIds].map((playerId) => {
                      const player = playersById.get(playerId)!;
                      return (
                        <option key={playerId} value={playerId}>
                          {player.name}
                        </option>
                      );
                    })}
                  </select>
                </label>
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Full Squad" subtitle="Availability, contract, and condition data across the roster.">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-muted">
                <tr>
                  <th className="pb-3">Player</th>
                  <th className="pb-3">Pos</th>
                  <th className="pb-3">OVR</th>
                  <th className="pb-3">Mor</th>
                  <th className="pb-3">Fit</th>
                  <th className="pb-3">Fat</th>
                  <th className="pb-3">Contract</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {squad.players.map((player) => (
                  <tr key={player.id} className="border-t border-border">
                    <td className="py-3">
                      <Link to={`/players/${player.id}`} className="font-medium text-accent hover:underline">{player.name}</Link>
                      <div className="text-xs text-muted">{player.nationality} · {formatMoney(player.wage)}</div>
                    </td>
                    <td className="py-3">{player.primary_position}</td>
                    <td className="py-3 font-semibold text-accent">{player.overall_rating}</td>
                    <td className="py-3">{player.morale}</td>
                    <td className="py-3">{player.fitness}</td>
                    <td className="py-3">{player.fatigue}</td>
                    <td className="py-3">{player.contract_years_remaining}y</td>
                    <td className="py-3 text-muted">
                      {player.injury_weeks_remaining > 0
                        ? `${player.injury_status} (${player.injury_weeks_remaining}w)`
                        : medicalByPlayerId.get(player.id)?.clearance_status === "managed"
                          ? "Managed return"
                          : medicalByPlayerId.get(player.id)?.clearance_status === "out"
                            ? "Medically held out"
                            : medicalByPlayerId.get(player.id)?.group === "fatigue"
                              ? "Fatigue watch"
                              : "Available"}
                    </td>
                    <td className="py-3">
                      {player.contract_years_remaining <= 2 ? (
                        <button className="btn-secondary px-3 py-2 text-xs" onClick={() => void renewContract(player.id, player.wage)}>
                          Renew
                        </button>
                      ) : (
                        <span className="text-muted">Stable</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </div>

      {/* Season Leaderboards */}
      {squadStats && squadStats.players.some((p) => p.stats) && (
        <SectionCard title="Season Leaderboards" subtitle="Top performers across the squad this season.">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <LeaderboardColumn
              title="Top Try Scorers"
              players={squadStats.players
                .filter((p) => p.stats && p.stats.tries_scored > 0)
                .sort((a, b) => (b.stats?.tries_scored ?? 0) - (a.stats?.tries_scored ?? 0))
                .slice(0, 5)}
              statKey="tries_scored"
              statLabel="tries"
            />
            <LeaderboardColumn
              title="Top Tacklers"
              players={squadStats.players
                .filter((p) => p.stats && p.stats.tackles_made > 0)
                .sort((a, b) => (b.stats?.tackles_made ?? 0) - (a.stats?.tackles_made ?? 0))
                .slice(0, 5)}
              statKey="tackles_made"
              statLabel="tackles"
            />
            <LeaderboardColumn
              title="Most Appearances"
              players={squadStats.players
                .filter((p) => p.stats && p.stats.appearances > 0)
                .sort((a, b) => (b.stats?.appearances ?? 0) - (a.stats?.appearances ?? 0))
                .slice(0, 5)}
              statKey="appearances"
              statLabel="apps"
            />
            <LeaderboardColumn
              title="Highest Rated"
              players={squadStats.players
                .filter((p) => p.stats && p.stats.appearances >= 3)
                .sort((a, b) => (b.stats?.average_rating ?? 0) - (a.stats?.average_rating ?? 0))
                .slice(0, 5)}
              statKey="average_rating"
              statLabel="avg"
              isFloat
            />
          </div>
        </SectionCard>
      )}
    </div>
  );
}

type LeaderboardColumnProps = {
  title: string;
  players: SquadStats["players"];
  statKey: string;
  statLabel: string;
  isFloat?: boolean;
};

function LeaderboardColumn({ title, players, statKey, statLabel, isFloat }: LeaderboardColumnProps) {
  if (players.length === 0) return null;
  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-muted">{title}</h3>
      <div className="space-y-2">
        {players.map((p, i) => {
          const value = (p.stats as Record<string, number> | null)?.[statKey] ?? 0;
          return (
            <div key={p.id} className="flex items-center gap-2 text-sm">
              <span className="w-5 text-muted">{i + 1}.</span>
              <Link to={`/players/${p.id}`} className="flex-1 truncate text-accent hover:underline">
                {p.name}
              </Link>
              <span className="text-xs text-muted">{p.primary_position}</span>
              <span className="font-semibold">{isFloat ? value.toFixed(1) : value}</span>
              <span className="text-xs text-muted">{statLabel}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
