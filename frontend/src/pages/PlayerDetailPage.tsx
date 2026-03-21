import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { api } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { PlayerDetail, PlayerSeasonStats } from "../lib/types";

const ATTRIBUTE_LABELS: Record<string, string> = {
  speed: "Speed",
  strength: "Strength",
  stamina: "Stamina",
  tackling: "Tackling",
  handling: "Handling",
  kicking: "Kicking",
  discipline: "Discipline",
  game_sense: "Game Sense",
  leadership: "Leadership",
  scrummaging: "Scrummaging",
  lineout: "Lineout",
  breakdown: "Breakdown",
  passing: "Passing",
  creativity: "Creativity",
  aerial: "Aerial",
};

function conditionColor(value: number): string {
  if (value >= 75) return "text-success";
  if (value >= 50) return "text-warn";
  return "text-danger";
}

function ratingColor(rating: number): string {
  if (rating >= 8.0) return "text-success";
  if (rating >= 6.5) return "text-accent";
  if (rating >= 5.0) return "text-warn";
  return "text-danger";
}

function computeTotalPoints(stats: PlayerSeasonStats): number {
  return stats.tries_scored * 5 + stats.conversions * 2 + stats.penalty_goals * 3 + stats.drop_goals * 3;
}

export function PlayerDetailPage() {
  const { playerId } = useParams<{ playerId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<PlayerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!playerId) return;
    setLoading(true);
    api
      .playerDetail(Number(playerId))
      .then(setData)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Failed to load player"))
      .finally(() => setLoading(false));
  }, [playerId]);

  if (loading) return <LoadingPanel label="Loading player" className="min-h-[60vh]" />;
  if (error || !data) {
    return (
      <div className="space-y-4">
        <PageHeader eyebrow="Player" title="Not Found" description={error ?? "Player could not be loaded."} />
        <Link to="/squad" className="btn-secondary inline-block">
          Back to Squad
        </Link>
      </div>
    );
  }

  const { player, team_name, current_season, career } = data;
  const attributes = Object.entries(player.attributes);

  const careerChartData = career.map((s) => ({
    season: `S${s.season_number}`,
    tries: s.tries_scored,
    points: computeTotalPoints(s),
    rating: s.average_rating,
    appearances: s.appearances,
  }));

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={team_name}
        title={player.name}
        description={`${player.primary_position} · Age ${player.age} · OVR ${player.overall_rating} / POT ${player.potential}`}
        actions={
          <button className="btn-secondary" onClick={() => navigate("/squad")}>
            Back to Squad
          </button>
        }
      />

      {/* Condition & Contract */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Form" value={player.form} accent={player.form >= 70 ? "success" : player.form >= 40 ? "warn" : "danger"} />
        <StatCard label="Morale" value={player.morale} accent={player.morale >= 70 ? "success" : player.morale >= 40 ? "warn" : "danger"} />
        <StatCard label="Fitness" value={player.fitness} accent={player.fitness >= 70 ? "success" : player.fitness >= 40 ? "warn" : "danger"} />
        <StatCard label="Fatigue" value={player.fatigue} accent={player.fatigue <= 30 ? "success" : player.fatigue <= 60 ? "warn" : "danger"} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Weekly Wage" value={formatMoney(player.wage)} />
        <StatCard label="Contract" value={`${player.contract_years_remaining}y`} accent={player.contract_years_remaining <= 1 ? "danger" : "default"} />
        <StatCard label="Transfer Value" value={formatMoney(player.transfer_value)} />
        <StatCard
          label="Injury"
          value={player.injury_weeks_remaining > 0 ? `${player.injury_status} (${player.injury_weeks_remaining}w)` : "Fit"}
          accent={player.injury_weeks_remaining > 0 ? "danger" : "success"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {/* Attributes */}
        <SectionCard title="Attributes" subtitle="Core physical and technical abilities.">
          <div className="grid gap-3 sm:grid-cols-2">
            {attributes.map(([key, value]) => (
              <div key={key} className="flex items-center gap-3">
                <span className="w-24 text-sm text-muted">{ATTRIBUTE_LABELS[key] ?? key}</span>
                <div className="metric-track flex-1">
                  <div className="metric-fill" style={{ width: `${value}%` }} />
                </div>
                <span className="w-8 text-right text-sm font-semibold">{value}</span>
              </div>
            ))}
          </div>
        </SectionCard>

        {/* Current Season Stats */}
        <SectionCard title="Current Season" subtitle={current_season ? `${current_season.appearances} appearances this season.` : "No appearances yet."}>
          {current_season ? (
            <div className="space-y-4">
              <div className="grid gap-3 grid-cols-2 sm:grid-cols-3">
                <div className="text-center">
                  <div className="stat-label">Tries</div>
                  <div className="mt-1 font-display text-2xl font-bold text-accent">{current_season.tries_scored}</div>
                </div>
                <div className="text-center">
                  <div className="stat-label">Points</div>
                  <div className="mt-1 font-display text-2xl font-bold text-accent">{computeTotalPoints(current_season)}</div>
                </div>
                <div className="text-center">
                  <div className="stat-label">Avg Rating</div>
                  <div className={`mt-1 font-display text-2xl font-bold ${ratingColor(current_season.average_rating)}`}>
                    {current_season.average_rating.toFixed(1)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="stat-label">Tackle %</div>
                  <div className="mt-1 font-display text-2xl font-bold text-accent">{current_season.tackle_success.toFixed(0)}%</div>
                </div>
                <div className="text-center">
                  <div className="stat-label">Appearances</div>
                  <div className="mt-1 font-display text-2xl font-bold text-accent">{current_season.appearances}</div>
                </div>
                <div className="text-center">
                  <div className="stat-label">Man of Match</div>
                  <div className="mt-1 font-display text-2xl font-bold text-accent">{current_season.man_of_match}</div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="text-muted">
                    <tr>
                      <th className="pb-2">Stat</th>
                      <th className="pb-2 text-right">Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ["Starts", current_season.starts],
                      ["Minutes", current_season.minutes_played],
                      ["Tries", current_season.tries_scored],
                      ["Conversions", current_season.conversions],
                      ["Penalty Goals", current_season.penalty_goals],
                      ["Drop Goals", current_season.drop_goals],
                      ["Total Points", computeTotalPoints(current_season)],
                      ["Tackles Made", current_season.tackles_made],
                      ["Tackles Missed", current_season.tackles_missed],
                      ["Carries", current_season.carries],
                      ["Line Breaks", current_season.line_breaks],
                      ["Yellow Cards", current_season.yellow_cards],
                      ["Red Cards", current_season.red_cards],
                      ["Injuries", current_season.injuries_sustained],
                    ].map(([label, value]) => (
                      <tr key={label as string} className="border-t border-border">
                        <td className="py-2">{label}</td>
                        <td className="py-2 text-right font-semibold">{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted">No match appearances recorded this season.</p>
          )}
        </SectionCard>
      </div>

      {/* Career History */}
      {career.length > 0 && (
        <SectionCard title="Career History" subtitle="Season-by-season performance.">
          <div className="space-y-6">
            {career.length > 1 && (
              <div className="grid gap-4 lg:grid-cols-2">
                <div>
                  <h3 className="mb-2 text-sm font-medium text-muted">Tries per Season</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={careerChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="season" stroke="rgba(255,255,255,0.4)" fontSize={12} />
                      <YAxis stroke="rgba(255,255,255,0.4)" fontSize={12} allowDecimals={false} />
                      <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                      <Bar dataKey="tries" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div>
                  <h3 className="mb-2 text-sm font-medium text-muted">Average Rating Trend</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={careerChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="season" stroke="rgba(255,255,255,0.4)" fontSize={12} />
                      <YAxis domain={[0, 10]} stroke="rgba(255,255,255,0.4)" fontSize={12} />
                      <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                      <Line type="monotone" dataKey="rating" stroke="#f59e0b" strokeWidth={2} dot={{ fill: "#f59e0b" }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-muted">
                  <tr>
                    <th className="pb-2">Season</th>
                    <th className="pb-2 text-right">Apps</th>
                    <th className="pb-2 text-right">Tries</th>
                    <th className="pb-2 text-right">Points</th>
                    <th className="pb-2 text-right">Tackle %</th>
                    <th className="pb-2 text-right">Avg Rating</th>
                    <th className="pb-2 text-right">MoM</th>
                  </tr>
                </thead>
                <tbody>
                  {career.map((s) => (
                    <tr key={s.season_number} className="border-t border-border">
                      <td className="py-2">Season {s.season_number}</td>
                      <td className="py-2 text-right">{s.appearances}</td>
                      <td className="py-2 text-right">{s.tries_scored}</td>
                      <td className="py-2 text-right">{computeTotalPoints(s)}</td>
                      <td className="py-2 text-right">{s.tackle_success.toFixed(0)}%</td>
                      <td className={`py-2 text-right font-semibold ${ratingColor(s.average_rating)}`}>{s.average_rating.toFixed(1)}</td>
                      <td className="py-2 text-right">{s.man_of_match}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </SectionCard>
      )}
    </div>
  );
}
