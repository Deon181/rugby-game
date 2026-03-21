type DualStatBarProps = {
  label: string;
  homeValue: number;
  awayValue: number;
  homeLabel: string;
  awayLabel: string;
  unit?: string;
};

export function DualStatBar({ label, homeValue, awayValue, homeLabel, awayLabel, unit = "%" }: DualStatBarProps) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-2 text-xs text-muted">
        <span className="font-medium text-text">
          {homeValue}
          {unit}
        </span>
        <span className="uppercase tracking-[0.18em]">{label}</span>
        <span className="font-medium text-text">
          {awayValue}
          {unit}
        </span>
      </div>
      <div className="metric-track">
        <div className="flex h-full">
          <div className="bg-accent transition-all duration-700" style={{ width: `${homeValue}%` }} />
          <div className="bg-sky-400 transition-all duration-700" style={{ width: `${awayValue}%` }} />
        </div>
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-muted">
        <span>{homeLabel}</span>
        <span>{awayLabel}</span>
      </div>
    </div>
  );
}
