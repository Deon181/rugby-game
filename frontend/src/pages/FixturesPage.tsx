import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import { scoreLine } from "../lib/format";
import type { FixtureList } from "../lib/types";
import { useGameStore } from "../store/useGameStore";

export function FixturesPage() {
  const navigate = useNavigate();
  const currentSave = useGameStore((state) => state.currentSave);
  const [data, setData] = useState<FixtureList | null>(null);

  async function loadFixtures() {
    setData(await api.fixtures());
  }

  useEffect(() => {
    void loadFixtures();
  }, []);

  const currentFixtures = useMemo(
    () => data?.fixtures.filter((fixture) => fixture.week === data.current_week) ?? [],
    [data],
  );

  if (!data) {
    return <LoadingPanel label="Loading fixtures" className="min-h-[60vh]" />;
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Season Schedule"
        title="Fixtures and Results"
        description="Track the whole season calendar, from the immediate round to completed scorelines around the league."
        actions={
          <button
            className="btn-primary"
            onClick={() => (currentSave?.phase === "in_season" ? navigate("/match-centre") : navigate("/offseason"))}
            disabled={currentSave?.phase === "in_season" && currentFixtures.length === 0}
          >
            {currentSave?.phase === "in_season" ? `Play Round ${data.current_week} Live` : "Open Offseason"}
          </button>
        }
      />
      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <SectionCard title={`Round ${data.current_week}`} subtitle="Upcoming league fixtures for the active week.">
          <div className="space-y-3">
            {currentFixtures.map((fixture) => (
              <div key={fixture.id} className="rounded-2xl bg-slate-950/30 p-4">
                <div className="stat-label">{fixture.kickoff_label}</div>
                <div className="mt-2 font-medium">{fixture.home_team_name} vs {fixture.away_team_name}</div>
              </div>
            ))}
          </div>
        </SectionCard>
        <SectionCard title="Season List" subtitle="Every fixture in the double round-robin campaign.">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-muted">
                <tr>
                  <th className="pb-3">Week</th>
                  <th className="pb-3">Fixture</th>
                  <th className="pb-3">Result</th>
                </tr>
              </thead>
              <tbody>
                {data.fixtures.map((fixture) => (
                  <tr key={fixture.id} className="border-t border-border">
                    <td className="py-3">{fixture.week}</td>
                    <td className="py-3">{fixture.home_team_name} vs {fixture.away_team_name}</td>
                    <td className="py-3 text-muted">
                      {fixture.result
                        ? scoreLine(
                            fixture.home_team_name,
                            fixture.away_team_name,
                            fixture.result.home_score,
                            fixture.result.away_score,
                          )
                        : "Not played"}
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
