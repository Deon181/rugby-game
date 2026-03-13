import { Navigate, useNavigate } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { formatMoney } from "../lib/format";
import { useGameStore } from "../store/useGameStore";

function getOpponentName(homeTeamId: number, userTeamId: number, homeTeamName: string, awayTeamName: string) {
  return homeTeamId === userTeamId ? awayTeamName : homeTeamName;
}

function getVenueLabel(homeTeamId: number, userTeamId: number) {
  return homeTeamId === userTeamId ? "Home" : "Away";
}

export function NewTeamRevealPage() {
  const navigate = useNavigate();
  const currentSave = useGameStore((state) => state.currentSave);
  const pendingOnboarding = useGameStore((state) => state.pendingOnboarding);
  const clearPendingOnboarding = useGameStore((state) => state.clearPendingOnboarding);

  if (!currentSave) {
    return <Navigate to="/new-game" replace />;
  }

  if (!pendingOnboarding || pendingOnboarding.saveId !== currentSave.id) {
    return <Navigate to="/" replace />;
  }

  const { team, squad_summary, featured_players, players, next_fixture } = pendingOnboarding.data;
  const nextOpponent = next_fixture
    ? getOpponentName(
        next_fixture.home_team_id,
        currentSave.user_team_id,
        next_fixture.home_team_name,
        next_fixture.away_team_name,
      )
    : null;
  const nextVenue = next_fixture ? getVenueLabel(next_fixture.home_team_id, currentSave.user_team_id) : null;

  function leaveOnboarding(path: string) {
    clearPendingOnboarding();
    navigate(path);
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={`${currentSave.league_name} · Club Ready`}
        title={`Welcome to ${team.name}`}
        description="The league slot is locked in, the roster is seeded, and your staff has already built a default matchday group. Review the squad, absorb the first-week picture, then step into the season room."
        actions={
          <>
            <button className="btn-secondary" onClick={() => leaveOnboarding("/squad")}>
              Open Squad Planner
            </button>
            <button className="btn-primary" onClick={() => leaveOnboarding("/")}>
              Enter Season Room
            </button>
          </>
        }
      />

      <section className="panel-alt overflow-hidden p-6">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="chip chip-active">{team.short_name}</span>
              <span className="chip">{team.objective}</span>
              <span className="chip">{currentSave.season_label}</span>
            </div>
            <div className="mt-5 font-display text-4xl font-bold">{team.name}</div>
            <p className="mt-3 max-w-3xl text-sm text-muted">
              You inherited a reputation {team.reputation} club package, full coaching staff coverage, and a 30-player
              squad built to compete immediately.
            </p>
          </div>

          <div className="rounded-[28px] border border-border bg-slate-950/35 p-5 xl:w-[380px]">
            <div className="stat-label">First Match Brief</div>
            {next_fixture ? (
              <>
                <div className="mt-3 font-display text-3xl font-semibold">{nextOpponent}</div>
                <div className="mt-2 text-sm text-muted">
                  {nextFixtureLabel(next_fixture.round_name, nextVenue, next_fixture.kickoff_label)}
                </div>
              </>
            ) : (
              <div className="mt-3 text-sm text-muted">The fixture list is ready once you enter the season room.</div>
            )}
          </div>
        </div>
      </section>

      <div className="data-grid">
        <StatCard label="Squad Size" value={squad_summary.player_count} detail="Full senior squad generated at save start." />
        <StatCard label="Average OVR" value={squad_summary.average_overall} detail="Overall team level on day one." />
        <StatCard label="Average Age" value={squad_summary.average_age} detail="Squad age curve across the 30-man group." />
        <StatCard
          label="Weekly Wages"
          value={formatMoney(squad_summary.total_wages)}
          detail={`${formatMoney(team.wage_budget)} wage budget available`}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title="Featured Leaders" subtitle="The standout personalities and talent pillars handed to you on day one.">
          <div className="grid gap-3 md:grid-cols-2">
            {featured_players.map((player) => (
              <div key={player.id} className="rounded-[24px] border border-border bg-slate-950/30 p-4">
                <div className="stat-label text-accent">{player.highlight}</div>
                <div className="mt-2 font-display text-2xl font-semibold">{player.name}</div>
                <div className="mt-1 text-sm text-muted">
                  {player.primary_position} · Age {player.age}
                </div>
                <div className="mt-4 flex items-center justify-between rounded-2xl bg-white/5 px-4 py-3">
                  <span className="text-sm text-muted">Overall</span>
                  <span className="font-display text-3xl font-semibold text-accent">{player.overall_rating}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap gap-2 text-xs text-muted">
            {Object.entries(squad_summary.position_counts).map(([position, count]) => (
              <span key={position} className="rounded-full border border-border px-3 py-1">
                {position}: {count}
              </span>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          title="Full 30-Man Squad"
          subtitle="Your starting roster, ready for selection tweaks, contract work, and tactical decisions."
          actions={
            <button className="btn-ghost" onClick={() => leaveOnboarding("/fixtures")}>
              Review Fixtures
            </button>
          }
        >
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-muted">
                <tr>
                  <th className="pb-3">Player</th>
                  <th className="pb-3">Pos</th>
                  <th className="pb-3">Age</th>
                  <th className="pb-3">OVR</th>
                  <th className="pb-3">Potential</th>
                  <th className="pb-3">Wage</th>
                  <th className="pb-3">Morale</th>
                </tr>
              </thead>
              <tbody>
                {players.map((player) => (
                  <tr key={player.id} className="border-t border-border">
                    <td className="py-3">
                      <div className="font-medium">{player.name}</div>
                      <div className="text-xs text-muted">{player.nationality}</div>
                    </td>
                    <td className="py-3">{player.primary_position}</td>
                    <td className="py-3">{player.age}</td>
                    <td className="py-3 font-semibold text-accent">{player.overall_rating}</td>
                    <td className="py-3">{player.potential}</td>
                    <td className="py-3">{formatMoney(player.wage)}</td>
                    <td className="py-3">{player.morale}</td>
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

function nextFixtureLabel(roundName: string, nextVenue: string | null, kickoffLabel: string) {
  return [roundName, nextVenue, kickoffLabel].filter(Boolean).join(" · ");
}
