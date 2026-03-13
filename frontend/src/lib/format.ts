export function formatMoney(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPercent(value: number) {
  return `${value}%`;
}

export function scoreLine(home: string, away: string, homeScore: number, awayScore: number) {
  return `${home} ${homeScore} - ${awayScore} ${away}`;
}
