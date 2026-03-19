import { useEffect, useState, type PropsWithChildren } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useGameStore } from "../store/useGameStore";
import { api } from "../lib/api";

const baseNavItems = [
  { to: "/", label: "Dashboard", icon: "\u25A3", shortcut: "1" },
  { to: "/squad", label: "Squad", icon: "\u2694", shortcut: "2" },
  { to: "/performance", label: "Performance", icon: "\u2665", shortcut: "3" },
  { to: "/tactics", label: "Tactics", icon: "\u2699", shortcut: "4" },
  { to: "/fixtures", label: "Fixtures", icon: "\u2637", shortcut: "5" },
  { to: "/table", label: "League Table", icon: "\u2630", shortcut: "6" },
  { to: "/finance", label: "Finance", icon: "\u20AC", shortcut: "7" },
  { to: "/transfers", label: "Recruitment", icon: "\u21C4", shortcut: "8" },
  { to: "/club", label: "Club Overview", icon: "\u2691", shortcut: "9" },
  { to: "/match-centre", label: "Match Centre", icon: "\u26BD", shortcut: "0" },
  { to: "/inbox", label: "Inbox", icon: "\u2709", shortcut: null },
];

type AppShellProps = PropsWithChildren<{
  bootstrapError: string | null;
}>;

export function AppShell({ children, bootstrapError }: AppShellProps) {
  const currentSave = useGameStore((state) => state.currentSave);
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    api.inbox().then((res) => {
      setUnreadCount(res.messages.filter((m) => !m.is_read).length);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const items = currentSave?.phase !== "in_season"
        ? [{ to: "/offseason", shortcut: null }, ...baseNavItems]
        : baseNavItems;

      const match = items.find((item) => item.shortcut === e.key);
      if (match) {
        e.preventDefault();
        navigate(match.to);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [currentSave?.phase, navigate]);

  const navItems = currentSave?.phase !== "in_season"
    ? [{ to: "/offseason", label: "Offseason", icon: "\u23F3", shortcut: null }, ...baseNavItems]
    : baseNavItems;

  return (
    <div className="min-h-screen px-4 py-4 md:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-4 lg:flex-row">
        <aside className="panel-alt w-full shrink-0 p-5 lg:sticky lg:top-4 lg:h-[calc(100vh-2rem)] lg:w-[280px]">
          <div className="border-b border-border pb-4">
            <div className="stat-label">Rugby Director</div>
            <div className="mt-2 font-display text-4xl font-bold">Season Room</div>
            <p className="mt-3 text-sm text-muted">
              {currentSave
                ? `${currentSave.user_team_name} \u00B7 ${currentSave.season_label} \u00B7 ${
                    currentSave.phase === "in_season"
                      ? `Week ${currentSave.current_week}/${currentSave.total_weeks}`
                      : currentSave.offseason_step.replace("_", " ")
                  }`
                : "No active save"}
            </p>
          </div>
          <nav className="mt-4 grid gap-2 lg:overflow-y-auto lg:max-h-[calc(100vh-14rem)]">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition ${
                    isActive ? "bg-accent text-slate-950" : "bg-slate-950/20 text-text hover:bg-slate-950/40 hover:text-accent"
                  }`
                }
              >
                <span className="w-5 text-center text-base">{item.icon}</span>
                <span className="flex-1">{item.label}</span>
                {item.to === "/inbox" && unreadCount > 0 ? (
                  <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-rose-500 px-1.5 text-[10px] font-bold text-white">
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                ) : null}
                {item.shortcut ? <span className="kbd">{item.shortcut}</span> : null}
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
