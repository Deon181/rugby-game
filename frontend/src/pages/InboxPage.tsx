import { useEffect, useMemo, useState } from "react";

import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { api } from "../lib/api";
import type { InboxResponse } from "../lib/types";

type InboxFilter = "all" | "unread" | "match_report" | "injury" | "transfer" | "contract" | "board";

const filterOptions: Array<{ key: InboxFilter; label: string }> = [
  { key: "all", label: "All" },
  { key: "unread", label: "Unread" },
  { key: "match_report", label: "Match Reports" },
  { key: "injury", label: "Injuries" },
  { key: "transfer", label: "Transfers" },
  { key: "contract", label: "Contracts" },
  { key: "board", label: "Board" },
];

function messageTypeIcon(type: string) {
  if (type.includes("match") || type.includes("result")) return "\u26BD";
  if (type.includes("injury")) return "\u2695";
  if (type.includes("transfer")) return "\u21C4";
  if (type.includes("contract")) return "\u270D";
  if (type.includes("board")) return "\u2691";
  return "\u2709";
}

export function InboxPage() {
  const [inbox, setInbox] = useState<InboxResponse | null>(null);
  const [filter, setFilter] = useState<InboxFilter>("all");

  useEffect(() => {
    void api.inbox().then(setInbox);
  }, []);

  const unreadCount = useMemo(() => inbox?.messages.filter((m) => !m.is_read).length ?? 0, [inbox]);

  const filteredMessages = useMemo(() => {
    if (!inbox) return [];
    return inbox.messages.filter((m) => {
      if (filter === "all") return true;
      if (filter === "unread") return !m.is_read;
      return m.type.toLowerCase().includes(filter);
    });
  }, [inbox, filter]);

  if (!inbox) {
    return <LoadingPanel label="Loading inbox" className="min-h-[60vh]" />;
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Club Communications"
        title="Inbox"
        description="A simple news feed for board notes, injury reports, transfer confirmations, and match summaries."
      />

      <div className="data-grid">
        <StatCard label="Total Messages" value={inbox.messages.length} detail="All-time inbox items." />
        <StatCard
          label="Unread"
          value={unreadCount}
          detail={unreadCount === 0 ? "All caught up." : `${unreadCount} message${unreadCount > 1 ? "s" : ""} need attention.`}
          accent={unreadCount > 0 ? "warn" : "success"}
        />
      </div>

      <SectionCard
        title="Messages"
        subtitle="Newest first."
        actions={
          <div className="flex flex-wrap gap-2">
            {filterOptions.map((opt) => (
              <button
                key={opt.key}
                className={`chip ${filter === opt.key ? "chip-active" : ""}`}
                onClick={() => setFilter(opt.key)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        }
      >
        <div className="space-y-3">
          {filteredMessages.length ? (
            filteredMessages.map((message) => (
              <div
                key={message.id}
                className={`rounded-2xl p-4 transition ${
                  message.is_read ? "bg-slate-950/30" : "border border-accent/20 bg-accentSoft"
                }`}
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-base">{messageTypeIcon(message.type)}</span>
                    <div className="stat-label">{message.type}</div>
                    {!message.is_read ? (
                      <span className="h-2 w-2 rounded-full bg-accent" />
                    ) : null}
                  </div>
                  <div className="text-xs text-muted">{new Date(message.created_at).toLocaleString()}</div>
                </div>
                <div className="mt-2 font-medium">{message.title}</div>
                <p className="mt-2 text-sm text-muted">{message.body}</p>
              </div>
            ))
          ) : (
            <div className="rounded-2xl bg-slate-950/30 p-4 text-sm text-muted">
              No messages match the current filter.
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
