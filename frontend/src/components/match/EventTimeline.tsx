import type { RefObject } from "react";

import { SectionCard } from "../SectionCard";
import type { LiveMatchSnapshot } from "../../lib/types";

type CommentaryEvent = LiveMatchSnapshot["commentary"][number];

const EVENT_ICONS: Record<string, { icon: string; colorClass: string }> = {
  try:           { icon: "🏉", colorClass: "" },
  "maul-try":    { icon: "🏉", colorClass: "" },
  "penalty-goal":{ icon: "●", colorClass: "text-amber-400" },
  "missed-penalty": { icon: "○", colorClass: "text-muted" },
  "drop-goal":   { icon: "◆", colorClass: "text-accent" },
  turnover:      { icon: "↺", colorClass: "text-sky-400" },
  injury:        { icon: "+", colorClass: "text-danger" },
  "red-card":    { icon: "■", colorClass: "text-danger" },
  "yellow-card": { icon: "■", colorClass: "text-amber-400" },
  territory:     { icon: "→", colorClass: "text-muted" },
  "bench-impact":{ icon: "⇅", colorClass: "text-muted" },
  halftime:      { icon: "—", colorClass: "text-accent" },
  "full-time":   { icon: "●", colorClass: "text-success" },
};

function getEventStyle(type: string) {
  return EVENT_ICONS[type] ?? { icon: "·", colorClass: "text-muted" };
}

function isScoring(type: string) {
  return type === "try" || type === "maul-try" || type === "penalty-goal" || type === "drop-goal";
}

type EventTimelineProps = {
  commentary: LiveMatchSnapshot["commentary"];
  containerRef: RefObject<HTMLDivElement | null>;
};

export function EventTimeline({ commentary, containerRef }: EventTimelineProps) {
  return (
    <SectionCard title="Match Timeline" subtitle="Live event feed with icons, timing, and context from the simulation engine.">
      <div ref={containerRef} className="max-h-[520px] space-y-2 overflow-y-auto pr-2">
        {commentary.map((event: CommentaryEvent, index: number) => {
          const { icon, colorClass } = getEventStyle(event.type);
          const scoring = isScoring(event.type);
          return (
            <div
              key={`${event.minute}-${event.type}-${index}`}
              className={`flex items-start gap-3 rounded-2xl border px-4 py-3 ${scoring ? "border-success/20 bg-success/5" : "border-border bg-slate-950/25"}`}
            >
              <span className={`mt-0.5 w-5 shrink-0 text-center text-sm ${colorClass}`}>{icon}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-medium">{event.team}</span>
                  <span className="shrink-0 rounded-full bg-accentSoft px-3 py-0.5 text-xs font-semibold text-accent">
                    {event.minute}&apos;
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted">{event.text}</p>
              </div>
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}
