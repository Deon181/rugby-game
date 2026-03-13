import { useEffect, useState } from "react";

import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import type { TableResponse } from "../lib/types";

export function TablePage() {
  const [table, setTable] = useState<TableResponse | null>(null);

  useEffect(() => {
    void api.table().then(setTable);
  }, []);

  if (!table) {
    return <LoadingPanel label="Loading league table" className="min-h-[60vh]" />;
  }

  return (
    <div className="space-y-4">
      <PageHeader eyebrow={table.league_name} title="League Table" description="Standings update automatically after each completed week, including rugby bonus-point scoring." />
      <SectionCard title="Standings" subtitle={`After week ${table.current_week - 1}`}>
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
                <th className="pb-3">PF</th>
                <th className="pb-3">PA</th>
                <th className="pb-3">PD</th>
                <th className="pb-3">BPts</th>
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row) => (
                <tr key={row.team_id} className="border-t border-border">
                  <td className="py-3 font-medium text-accent">{row.position}</td>
                  <td className="py-3">{row.team_name}</td>
                  <td className="py-3">{row.played}</td>
                  <td className="py-3">{row.wins}</td>
                  <td className="py-3">{row.draws}</td>
                  <td className="py-3">{row.losses}</td>
                  <td className="py-3">{row.points_for}</td>
                  <td className="py-3">{row.points_against}</td>
                  <td className="py-3">{row.points_difference}</td>
                  <td className="py-3 font-semibold">{row.table_points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}
