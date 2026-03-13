import { useEffect, useState } from "react";

import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import type { InboxResponse } from "../lib/types";

export function InboxPage() {
  const [inbox, setInbox] = useState<InboxResponse | null>(null);

  useEffect(() => {
    void api.inbox().then(setInbox);
  }, []);

  if (!inbox) {
    return <LoadingPanel label="Loading inbox" className="min-h-[60vh]" />;
  }

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="Club Communications" title="Inbox" description="A simple news feed for board notes, injury reports, transfer confirmations, and match summaries." />
      <SectionCard title="Messages" subtitle="Newest first.">
        <div className="space-y-3">
          {inbox.messages.map((message) => (
            <div key={message.id} className="rounded-2xl bg-slate-950/30 p-4">
              <div className="flex items-center justify-between gap-4">
                <div className="stat-label">{message.type}</div>
                <div className="text-xs text-muted">{new Date(message.created_at).toLocaleString()}</div>
              </div>
              <div className="mt-2 font-medium">{message.title}</div>
              <p className="mt-2 text-sm text-muted">{message.body}</p>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
