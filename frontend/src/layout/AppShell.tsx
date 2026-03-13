import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";

import { useGameStore } from "../store/useGameStore";

const baseNavItems = [
  { to: "/", label: "Dashboard" },
  { to: "/squad", label: "Squad" },
  { to: "/tactics", label: "Tactics" },
  { to: "/fixtures", label: "Fixtures" },
  { to: "/table", label: "League Table" },
  { to: "/transfers", label: "Recruitment" },
  { to: "/club", label: "Club Overview" },
  { to: "/match-centre", label: "Match Centre" },
  { to: "/inbox", label: "Inbox" },
];

type AppShellProps = PropsWithChildren<{
  bootstrapError: string | null;
}>;

export function AppShell({ children, bootstrapError }: AppShellProps) {
  const currentSave = useGameStore((state) => state.currentSave);
  const navItems = currentSave?.phase !== "in_season" ? [{ to: "/offseason", label: "Offseason" }, ...baseNavItems] : baseNavItems;
  return (
    <div className="min-h-screen px-4 py-4 md:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-4 lg:flex-row">
        <aside className="panel-alt w-full shrink-0 p-5 lg:sticky lg:top-4 lg:h-[calc(100vh-2rem)] lg:w-[280px]">
          <div className="border-b border-border pb-4">
            <div className="stat-label">Rugby Director</div>
            <div className="mt-2 font-display text-4xl font-bold">Season Room</div>
            <p className="mt-3 text-sm text-muted">
              {currentSave
                ? `${currentSave.user_team_name} · ${currentSave.season_label} · ${
                    currentSave.phase === "in_season"
                      ? `Week ${currentSave.current_week}/${currentSave.total_weeks}`
                      : currentSave.offseason_step.replace("_", " ")
                  }`
                : "No active save"}
            </p>
          </div>
          <nav className="mt-4 grid gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-2xl px-4 py-3 text-sm font-medium transition ${
                    isActive ? "bg-accent text-slate-950" : "bg-slate-950/20 text-text hover:bg-slate-950/40 hover:text-accent"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          {bootstrapError ? <div className="mt-4 rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{bootstrapError}</div> : null}
        </aside>
        <main className="flex-1 space-y-4">{children}</main>
      </div>
    </div>
  );
}
