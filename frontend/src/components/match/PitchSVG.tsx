import { SectionCard } from "../SectionCard";
import type { LiveMatchSnapshot } from "../../lib/types";

type PitchSVGProps = {
  ballPosition: number;
  recentEvents: LiveMatchSnapshot["recent_events"];
  homeTeamName: string;
  awayTeamName: string;
  commentaryLength: number;
  userPressure: number;
};

function flashColor(type: string): string {
  if (type === "try" || type === "maul-try") return "#34d399";
  if (type === "penalty-goal" || type === "drop-goal") return "#f59e0b";
  if (type === "red-card") return "#fb7185";
  if (type === "yellow-card") return "#fbbf24";
  if (type === "turnover") return "#38bdf8";
  return "rgba(255,255,255,0.5)";
}

function pressureLabel(value: number) {
  if (value >= 72) return "Dominant field position";
  if (value >= 58) return "Territory edge";
  if (value >= 42) return "Even balance";
  if (value >= 28) return "Absorbing pressure";
  return "Pinned back";
}

export function PitchSVG({ ballPosition, recentEvents, homeTeamName, awayTeamName, commentaryLength, userPressure }: PitchSVGProps) {
  const lastEvent = recentEvents.at(-1);
  const pips = recentEvents.slice(-3);

  return (
    <SectionCard title="Live Pitch" subtitle="Field position, recent event map, and territorial read on the current block.">
      <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(34,197,94,0.18),rgba(4,120,87,0.24))] px-5 py-8">
        {/* Stripe pattern */}
        <div className="absolute inset-0 bg-[repeating-linear-gradient(90deg,rgba(255,255,255,0.06)_0px,rgba(255,255,255,0.06)_1px,transparent_1px,transparent_12.5%)]" />

        {/* Try zone overlays */}
        <div className="absolute inset-y-0 left-0 w-[10%] rounded-l-[28px] bg-emerald-400/10" />
        <div className="absolute inset-y-0 right-0 w-[10%] rounded-r-[28px] bg-emerald-400/10" />

        {/* Try lines at 10% */}
        <div className="absolute inset-y-0 left-[10%] w-px bg-white/20" />
        <div className="absolute inset-y-0 right-[10%] w-px bg-white/20" />

        {/* Halfway line */}
        <div className="absolute inset-y-0 left-1/2 w-px bg-white/30" />

        {/* 22m lines */}
        <div className="absolute inset-y-6 left-[22%] w-px border-l border-dashed border-white/20" />
        <div className="absolute inset-y-6 right-[22%] w-px border-l border-dashed border-white/20" />

        <div className="relative h-56">
          {/* Team name labels */}
          <div className="flex justify-between text-xs font-semibold uppercase tracking-[0.25em] text-white/70">
            <span>{homeTeamName}</span>
            <span>Halfway</span>
            <span>{awayTeamName}</span>
          </div>

          {/* Ball indicator */}
          <div
            className="absolute top-1/2 z-10 h-5 w-5 -translate-y-1/2 rounded-full border-2 border-slate-950 bg-amber-300 shadow-[0_0_18px_rgba(245,158,11,0.8)] transition-all duration-700"
            style={{ left: `calc(${ballPosition}% - 10px)` }}
          />

          {/* SVG flash ring overlay */}
          <svg
            className="pointer-events-none absolute inset-0 h-full w-full"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
          >
            {lastEvent ? (
              <circle
                key={commentaryLength}
                cx={lastEvent.field_position}
                cy={50}
                r={4}
                fill="none"
                stroke={flashColor(lastEvent.type)}
                strokeWidth={1.5}
                className="pitch-flash"
              />
            ) : null}
          </svg>

          {/* Event pips */}
          {pips.map((event, index) => (
            <div
              key={`${event.minute}-${event.type}-${index}`}
              className="absolute z-20 -translate-x-1/2 rounded-full bg-slate-950/85 px-3 py-1 text-[11px] font-medium text-white shadow-lg"
              style={{ left: `${event.field_position}%`, top: `${24 + index * 18}%` }}
            >
              {event.type.replace("-", " ")} {event.minute}&apos;
            </div>
          ))}

          {/* Bottom zone labels */}
          <div className="absolute inset-x-0 bottom-0 flex items-center justify-between text-xs text-white/70">
            <span>Home 22</span>
            <span>{pressureLabel(userPressure)}</span>
            <span>Away 22</span>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}
