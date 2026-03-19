import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { useToast } from "../components/Toast";
import { api } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { PerformanceOverview, Selection, SquadPlayer, SquadResponse } from "../lib/types";

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

type SortKey = "name" | "primary_position" | "overall_rating" | "morale" | "fitness" | "fatigue" | "age" | "contract_years_remaining";
type SortDir = "asc" | "desc";

function eligibleForSlot(players: SquadPlayer[], slot: string, selectedId: number) {
  return players.filter(
    (player) =>
      player.id === selectedId || player.primary_position === slot || player.secondary_positions.includes(slot),
  );
}

function sortPlayers(players: SquadPlayer[], key: SortKey, dir: SortDir): SquadPlayer[] {
  return [...players].sort((a, b) => {
    const aVal = a[key];
    const bVal = b[key];
    if (typeof aVal === "string" && typeof bVal === "string") {
      return dir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }
    if (typeof aVal === "number" && typeof bVal === "number") {
      return dir === "asc" ? aVal - bVal : bVal - aVal;
    }
    return 0;
  });
}

function SortHeader({ label, sortKey, currentKey, currentDir, onSort }: {
  label: string;
  sortKey: SortKey;
  currentKey: SortKey;
  currentDir: SortDir;
  onSort: (key: SortKey) => void;
}) {
  const active = currentKey === sortKey;
  return (
    <th
      className="cursor-pointer select-none pb-3 transition hover:text-accent"
      onClick={() => onSort(sortKey)}
    >
      {label}{" "}
      {active ? (
        <span className="text-accent">{currentDir === "asc" ? "\u25B2" : "\u25BC"}</span>
      ) : (
        <span className="opacity-30">\u25BC</span>
      )}
    </th>
  );
}

export function SquadPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [squad, setSquad] = useState<SquadResponse | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [performance, setPerformance] = useState<PerformanceOverview | null>(null);
  const [saving, setSaving] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("overall_rating");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [filterText, setFilterText] = useState("");

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  async function loadData() {
    const [squadResponse, selectionResponse, performanceResponse] = await Promise.all([
      api.squad(),
      api.selection(),
      api.performance(),
    ]);
    setSquad(squadResponse);
    setSelection(selectionResponse);
    setPerformance(performanceResponse);
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

  const sortedPlayers = useMemo(() => {
    let players = squad?.players ?? [];
    if (filterText) {
      const lower = filterText.toLowerCase();
      players = players.filter(
        (p) => p.name.toLowerCase().includes(lower) || p.primary_position.toLowerCase().includes(lower),
      );
    }
    return sortPlayers(players, sortKey, sortDir);
  }, [squad, sortKey, sortDir, filterText]);

  async function saveSelection() {
    if (!selection) return;
    setSaving(true);
    try {
      const response = await api.updateSelection(selection);
      setSelection(response);
      toast("Selection saved successfully.", "success");
    } catch (reason) {
      toast(reason instanceof Error ? reason.message : "Failed to save selection", "error");
    } finally {
      setSaving(false);
    }
  }

  async function renewContract(playerId: number, wage: number) {
    try {
      const response = await api.renewContract(playerId, 3, Math.round(wage * 1.08));
      toast(response.message, "success");
      await loadData();
    } catch (reason) {
      toast(reason instanceof Error ? reason.message : "Failed to renew contract", "error");
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
                      {player.name} \u00B7 {player.primary_position} \u00B7 OVR {player.overall_rating}
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
                        {player.name} \u00B7 {player.primary_position} \u00B7 OVR {player.overall_rating}
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

        <SectionCard
          title="Full Squad"
          subtitle="Availability, contract, and condition data across the roster."
          actions={
            <input
              type="text"
              className="field max-w-[200px]"
              placeholder="Filter players..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
            />
          }
        >
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-muted">
                <tr>
                  <SortHeader label="Player" sortKey="name" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortHeader label="Pos" sortKey="primary_position" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortHeader label="OVR" sortKey="overall_rating" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortHeader label="Mor" sortKey="morale" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortHeader label="Fit" sortKey="fitness" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortHeader label="Fat" sortKey="fatigue" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortHeader label="Age" sortKey="age" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortHeader label="Contract" sortKey="contract_years_remaining" currentKey={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {sortedPlayers.map((player) => (
                  <tr key={player.id} className="border-t border-border">
                    <td className="py-3">
                      <div className="font-medium">{player.name}</div>
                      <div className="text-xs text-muted">{player.nationality} \u00B7 {formatMoney(player.wage)}</div>
                    </td>
                    <td className="py-3">{player.primary_position}</td>
                    <td className="py-3 font-semibold text-accent">{player.overall_rating}</td>
                    <td className="py-3">
                      <span className={player.morale >= 70 ? "text-success" : player.morale >= 50 ? "text-warn" : "text-danger"}>
                        {player.morale}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className={player.fitness >= 75 ? "text-success" : player.fitness >= 60 ? "text-warn" : "text-danger"}>
                        {player.fitness}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className={player.fatigue <= 35 ? "text-success" : player.fatigue <= 55 ? "text-warn" : "text-danger"}>
                        {player.fatigue}
                      </span>
                    </td>
                    <td className="py-3">{player.age}</td>
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
    </div>
  );
}
