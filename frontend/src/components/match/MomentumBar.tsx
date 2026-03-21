type MomentumBarProps = {
  homeValue: number;
  awayValue: number;
  homeTeamName: string;
  awayTeamName: string;
};

export function MomentumBar({ homeValue, awayValue, homeTeamName, awayTeamName }: MomentumBarProps) {
  const offset = homeValue - 50; // -50 to +50
  const fillWidth = Math.abs(offset) * 2; // 0-100%
  const fillLeft = offset >= 0 ? 50 : 50 - fillWidth;
  const fillColor = offset >= 0 ? "bg-accent" : "bg-sky-400";

  return (
    <div>
      <div className="mb-2 flex justify-between text-xs uppercase tracking-[0.18em] text-muted">
        <span>{homeTeamName}</span>
        <span>Momentum</span>
        <span>{awayTeamName}</span>
      </div>
      <div className="relative h-3 overflow-hidden rounded-full bg-slate-950/40">
        <div className="absolute inset-y-0 left-1/2 z-10 w-px bg-white/30" />
        <div
          className={`absolute h-full transition-all duration-700 ${fillColor}`}
          style={{ left: `${fillLeft}%`, width: `${fillWidth}%` }}
        />
      </div>
    </div>
  );
}
