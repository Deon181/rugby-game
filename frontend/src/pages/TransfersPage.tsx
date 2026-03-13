import { useEffect, useState } from "react";

import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { TransferListResponse } from "../lib/types";

export function TransfersPage() {
  const [data, setData] = useState<TransferListResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [bidValues, setBidValues] = useState<Record<number, number>>({});

  async function loadTransfers() {
    setData(await api.transfers());
  }

  useEffect(() => {
    void loadTransfers();
  }, []);

  async function handleBid(listingId: number, amount: number) {
    try {
      const response = await api.bidTransfer(listingId, amount);
      setMessage(response.message);
      await loadTransfers();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Bid failed");
    }
  }

  if (!data) {
    return <LoadingPanel label="Loading transfer market" className="min-h-[60vh]" />;
  }

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="Transfer Market" title="Listed Players" description="Target immediate upgrades and depth using a lightweight MVP market with budget and wage checks." />
      {message ? <div className="rounded-2xl bg-accentSoft px-4 py-3 text-sm">{message}</div> : null}
      <div className="data-grid">
        <div className="panel p-5">
          <div className="stat-label">Budget</div>
          <div className="mt-2 font-display text-4xl font-semibold text-accent">{formatMoney(data.budget)}</div>
        </div>
        <div className="panel p-5">
          <div className="stat-label">Wage Budget</div>
          <div className="mt-2 font-display text-4xl font-semibold text-accent">{formatMoney(data.wage_budget)}</div>
        </div>
      </div>
      <SectionCard title="Market Board" subtitle="Bids at or above the asking range will complete immediately in the MVP.">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-muted">
              <tr>
                <th className="pb-3">Player</th>
                <th className="pb-3">Club</th>
                <th className="pb-3">Pos</th>
                <th className="pb-3">OVR</th>
                <th className="pb-3">Age</th>
                <th className="pb-3">Fee</th>
                <th className="pb-3">Bid</th>
              </tr>
            </thead>
            <tbody>
              {data.listings.map((listing) => (
                <tr key={listing.id} className="border-t border-border">
                  <td className="py-3">{listing.player_name}</td>
                  <td className="py-3 text-muted">{listing.current_team}</td>
                  <td className="py-3">{listing.primary_position}</td>
                  <td className="py-3 font-semibold text-accent">{listing.overall_rating}</td>
                  <td className="py-3">{listing.age}</td>
                  <td className="py-3">{formatMoney(listing.asking_price)}</td>
                  <td className="py-3">
                    <div className="flex flex-col gap-2 md:flex-row">
                      <input
                        className="field min-w-[140px]"
                        type="number"
                        value={bidValues[listing.id] ?? listing.asking_price}
                        onChange={(event) =>
                          setBidValues((current) => ({ ...current, [listing.id]: Number(event.target.value) }))
                        }
                      />
                      <button className="btn-secondary" onClick={() => void handleBid(listing.id, bidValues[listing.id] ?? listing.asking_price)}>
                        Submit Bid
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}
