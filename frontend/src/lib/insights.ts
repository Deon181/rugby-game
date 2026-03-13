import type {
  Fixture,
  LiveMatchPlayer,
  LiveMatchSnapshot,
  MatchResult,
  TableResponse,
} from "./types";

export type FixtureOutcome = "W" | "D" | "L";

export type FormSnapshot = {
  played: number;
  wins: number;
  draws: number;
  losses: number;
  averageScored: number;
  averageConceded: number;
  streakLabel: string;
  chartData: Array<{
    round: string;
    scored: number;
    conceded: number;
    margin: number;
    outcome: FixtureOutcome;
  }>;
};

export type LiveAlert = {
  level: "danger" | "warn" | "info";
  title: string;
  detail: string;
};

function average(values: number[]) {
  if (!values.length) {
    return 0;
  }
  return Math.round(values.reduce((total, value) => total + value, 0) / values.length);
}

function compressRoundName(roundName: string) {
  return roundName.replace(/^Round\s+/i, "R");
}

function streakLabel(outcomes: FixtureOutcome[]) {
  if (!outcomes.length) {
    return "No played matches";
  }

  const latest = outcomes[outcomes.length - 1];
  let count = 0;
  for (let index = outcomes.length - 1; index >= 0; index -= 1) {
    if (outcomes[index] !== latest) {
      break;
    }
    count += 1;
  }

  return `${latest}${count}`;
}

export function isUserFixture(fixture: Fixture, userTeamId: number) {
  return fixture.home_team_id === userTeamId || fixture.away_team_id === userTeamId;
}

export function getFixtureOpponentName(fixture: Fixture, userTeamId: number) {
  if (fixture.home_team_id === userTeamId) {
    return fixture.away_team_name;
  }
  if (fixture.away_team_id === userTeamId) {
    return fixture.home_team_name;
  }
  return null;
}

export function getFixtureVenueLabel(fixture: Fixture, userTeamId: number) {
  if (fixture.home_team_id === userTeamId) {
    return "Home";
  }
  if (fixture.away_team_id === userTeamId) {
    return "Away";
  }
  return "League";
}

export function getFixtureOutcome(fixture: Fixture, userTeamId: number): FixtureOutcome | null {
  if (!fixture.result || !isUserFixture(fixture, userTeamId)) {
    return null;
  }

  const scored = fixture.home_team_id === userTeamId ? fixture.result.home_score : fixture.result.away_score;
  const conceded = fixture.home_team_id === userTeamId ? fixture.result.away_score : fixture.result.home_score;

  if (scored > conceded) {
    return "W";
  }
  if (scored < conceded) {
    return "L";
  }
  return "D";
}

export function buildFormSnapshot(fixtures: Fixture[], userTeamId: number): FormSnapshot {
  const playedFixtures = fixtures
    .filter((fixture) => fixture.result && isUserFixture(fixture, userTeamId))
    .sort((left, right) => left.week - right.week)
    .slice(-5);

  const chartData = playedFixtures.map((fixture) => {
    const scored = fixture.home_team_id === userTeamId ? fixture.result!.home_score : fixture.result!.away_score;
    const conceded = fixture.home_team_id === userTeamId ? fixture.result!.away_score : fixture.result!.home_score;
    const outcome = getFixtureOutcome(fixture, userTeamId) ?? "D";
    return {
      round: compressRoundName(fixture.round_name),
      scored,
      conceded,
      margin: scored - conceded,
      outcome,
    };
  });

  const outcomes = chartData.map((fixture) => fixture.outcome);

  return {
    played: chartData.length,
    wins: outcomes.filter((outcome) => outcome === "W").length,
    draws: outcomes.filter((outcome) => outcome === "D").length,
    losses: outcomes.filter((outcome) => outcome === "L").length,
    averageScored: average(chartData.map((fixture) => fixture.scored)),
    averageConceded: average(chartData.map((fixture) => fixture.conceded)),
    streakLabel: streakLabel(outcomes),
    chartData,
  };
}

export function getTableRow(table: TableResponse | null, teamId: number) {
  return table?.rows.find((row) => row.team_id === teamId) ?? null;
}

export function getUserSide(live: LiveMatchSnapshot) {
  return live.home.team_id === live.user_team_id ? "home" : "away";
}

export function getUserTeamState(live: LiveMatchSnapshot) {
  return getUserSide(live) === "home" ? live.home : live.away;
}

export function getOpponentTeamState(live: LiveMatchSnapshot) {
  return getUserSide(live) === "home" ? live.away : live.home;
}

export function buildLiveAlerts(live: LiveMatchSnapshot): LiveAlert[] {
  const players = live.user_matchday_players.filter((player) => player.on_field);
  const alerts: LiveAlert[] = [];

  for (const player of players) {
    if (player.injury_status) {
      alerts.push({
        level: "danger",
        title: `${player.name} is carrying a knock`,
        detail: `${player.starter_slot ?? player.primary_position} · ${player.injury_status}`,
      });
      continue;
    }

    if (player.card_status) {
      alerts.push({
        level: "danger",
        title: `${player.name} is on a card watch`,
        detail: `${player.starter_slot ?? player.primary_position} · ${player.card_status.toUpperCase()} card`,
      });
      continue;
    }

    if (player.fatigue >= 80 || player.fitness <= 62) {
      alerts.push({
        level: "danger",
        title: `${player.name} is fading hard`,
        detail: `${player.starter_slot ?? player.primary_position} · Fitness ${player.fitness} · Fatigue ${player.fatigue}`,
      });
      continue;
    }

    if (player.fatigue >= 68 || player.fitness <= 72) {
      alerts.push({
        level: "warn",
        title: `${player.name} needs managing`,
        detail: `${player.starter_slot ?? player.primary_position} · Fitness ${player.fitness} · Fatigue ${player.fatigue}`,
      });
    }
  }

  if (!alerts.length) {
    alerts.push({
      level: "info",
      title: "Condition is stable",
      detail: "The starting group is holding up well through this phase of the match.",
    });
  }

  return alerts.slice(0, 4);
}

function sortBenchCandidates(players: LiveMatchPlayer[]) {
  return [...players]
    .filter((player) => !player.on_field)
    .sort((left, right) => {
      const leftScore = left.fitness + (100 - left.fatigue) + left.overall_rating;
      const rightScore = right.fitness + (100 - right.fatigue) + right.overall_rating;
      return rightScore - leftScore;
    });
}

export function buildCoachNotes(live: LiveMatchSnapshot) {
  const user = getUserTeamState(live);
  const opponent = getOpponentTeamState(live);
  const benchOptions = sortBenchCandidates(live.user_matchday_players);
  const notes: string[] = [];

  if (user.score < opponent.score && user.stats.territory < opponent.stats.territory) {
    notes.push("Territory is slipping away. Push the kicking game longer or raise ruck commitment to stop defending repeat phases.");
  }

  if (user.score < opponent.score && user.stats.line_breaks <= opponent.stats.line_breaks) {
    notes.push("You need a sharper attacking edge. A more expansive shape can create wider mismatches before the match gets away.");
  }

  if (user.stats.turnovers > opponent.stats.turnovers + 2) {
    notes.push("Turnovers are feeding the opposition transition game. Balance the attack and reduce the risk profile for a few phases.");
  }

  if (user.stats.penalties_conceded > opponent.stats.penalties_conceded + 2 || user.stats.cards > 0) {
    notes.push("Discipline is hurting field position. The game is gifting the opposition exits and goal chances.");
  }

  if (user.stats.scrum_success + 8 < opponent.stats.scrum_success || user.stats.lineout_success + 8 < opponent.stats.lineout_success) {
    notes.push("The set piece is losing leverage. Safer calls and fresher forwards are the cleanest way back into the match.");
  }

  if (live.minute >= 60 && user.score > opponent.score) {
    notes.push("The match is entering closeout territory. Kick long, protect field position, and avoid forcing low-value passes.");
  }

  if (benchOptions.length) {
    const benchLead = benchOptions[0];
    notes.push(
      `Best bench spark: ${benchLead.name}, ${benchLead.primary_position}, fitness ${benchLead.fitness}, overall ${benchLead.overall_rating}.`,
    );
  }

  if (!notes.length) {
    notes.push("The balance is even. Back the current plan unless fatigue or discipline starts moving against you.");
  }

  return notes.slice(0, 4);
}

export function summariseMatchResult(match: MatchResult, teamId: number) {
  const isHome = match.home_team_id === teamId;
  const scored = isHome ? match.home_score : match.away_score;
  const conceded = isHome ? match.away_score : match.home_score;
  const outcome: FixtureOutcome = scored > conceded ? "W" : scored < conceded ? "L" : "D";

  return {
    scored,
    conceded,
    margin: scored - conceded,
    outcome,
  };
}
