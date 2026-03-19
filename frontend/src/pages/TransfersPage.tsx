import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "../components/EmptyState";
import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { useToast } from "../components/Toast";
import { api } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { ContractWatchPlayer, RecruitmentListing, RecruitmentResponse } from "../lib/types";

function scoutingTone(stage: string) {
  if (stage === "complete") {
    return "border-emerald-400/30 bg-emerald-400/10 text-emerald-300";
  }
  if (stage === "detailed") {
    return "border-sky-400/30 bg-sky-400/10 text-sky-300";
  }
  if (stage === "regional") {
    return "border-amber-400/30 bg-amber-400/10 text-amber-300";
  }
  return "border-border bg-white/5 text-muted";
}

function retentionTone(priority: string) {
  if (priority === "Core") {
    return "text-emerald-300";
  }
  if (priority === "Important") {
    return "text-accent";
  }
  return "text-muted";
}

function formatRange(low: number | null, high: number | null) {
  if (low === null || high === null) {
    return "Unscouted";
  }
  if (low === high) {
    return formatMoney(low);
  }
  return `${formatMoney(low)} - ${formatMoney(high)}`;
}

function formatPotential(listing: RecruitmentListing) {
  const { potential_low: low, potential_high: high } = listing.scouting;
  if (low === null || high === null) {
    return "Unknown";
  }
  return low === high ? `${low}` : `${low}-${high}`;
}

export function TransfersPage() {
  const { toast } = useToast();
  const [data, setData] = useState<RecruitmentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [bidValues, setBidValues] = useState<Record<number, number>>({});
  const [renewalValues, setRenewalValues] = useState<Record<number, { years: number; weeklyWage: number }>>({});
  const [positionFilter, setPositionFilter] = useState<string>("all");
  const [busyKey, setBusyKey] = useState<string | null>(null);

  async function loadRecruitment() {
    setLoading(true);
    setError(null);
    try {
      const response = await api.recruitment();
      setData(response);
      setRenewalValues((current) => {
        const next = { ...current };
        for (const player of response.contract_watch) {
          if (!next[player.player_id]) {
            next[player.player_id] = {
              years: player.desired_years,
              weeklyWage: player.desired_weekly_wage,
            };
          }
        }
        return next;
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to load recruitment hub");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadRecruitment();
  }, []);

  const positions = useMemo(() => {
    const unique = new Set((data?.market ?? []).map((listing) => listing.primary_position));
    return ["all", ...unique];
  }, [data]);

  const visibleMarket = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.market.filter((listing) => positionFilter === "all" || listing.primary_position === positionFilter);
  }, [data, positionFilter]);

  async function handleScout(playerId: number) {
    setBusyKey(`scout-${playerId}`);
    try {
      const response = await api.startScouting(playerId);
      toast(response.message, "success");
      await loadRecruitment();
    } catch (reason) {
      toast(reason instanceof Error ? reason.message : "Scouting assignment failed", "error");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleToggleShortlist(playerId: number) {
    setBusyKey(`shortlist-${playerId}`);
    try {
      const response = await api.toggleShortlist(playerId);
      toast(response.message, "success");
      await loadRecruitment();
    } catch (reason) {
      toast(reason instanceof Error ? reason.message : "Shortlist update failed", "error");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleBid(listingId: number, amount: number) {
    setBusyKey(`bid-${listingId}`);
    try {
      const response = await api.bidTransfer(listingId, amount);
      toast(response.message, "success");
      await loadRecruitment();
    } catch (reason) {
      toast(reason instanceof Error ? reason.message : "Bid failed", "error");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleRenew(player: ContractWatchPlayer) {
    const offer = renewalValues[player.player_id] ?? {
      years: player.desired_years,
      weeklyWage: player.desired_weekly_wage,
    };

    setBusyKey(`renew-${player.player_id}`);
    try {
      const response = await api.renewContract(player.player_id, offer.years, offer.weeklyWage);
      toast(response.message, "success");
      await loadRecruitment();
    } catch (reason) {
      toast(reason instanceof Error ? reason.message : "Renewal failed", "error");
    } finally {
      setBusyKey(null);
    }
  }

  if (loading) {
    return <LoadingPanel label="Loading recruitment hub" className="min-h-[60vh]" />;
  }

  if (!data) {
    return <EmptyState title="No recruitment data" body={error ?? "The recruitment hub could not be loaded."} />;
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Recruitment Layer"
        title="Recruitment Hub"
        description="Scout targets through the season, keep a focused shortlist, and manage contract risk before core players drift into the market."
        actions={
          <select className="field min-w-[180px]" value={positionFilter} onChange={(event) => setPositionFilter(event.target.value)}>
            {positions.map((position) => (
              <option key={position} value={position}>
                {position === "all" ? "All Positions" : position}
              </option>
            ))}
          </select>
        }
      />

      {error ? <div className="rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}

      <div className="data-grid">
        <StatCard label="Transfer Budget" value={formatMoney(data.budget)} detail="Available for completed incoming deals." />
        <StatCard label="Current Wages" value={formatMoney(data.current_wages)} detail={`${formatMoney(data.wage_budget)} total wage budget`} />
        <StatCard
          label="Active Reports"
          value={`${data.summary.active_reports}/${data.summary.max_active_reports}`}
          detail={`${data.summary.completed_reports} complete reports on file.`}
          accent={data.summary.active_reports >= data.summary.max_active_reports ? "warn" : "success"}
        />
        <StatCard label="Shortlist" value={data.summary.shortlisted_targets} detail="Tracked targets ready for action." />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <SectionCard title="Market Board" subtitle="Public listings plus progressively better scouting intelligence.">
          {visibleMarket.length ? (
            <div className="space-y-3">
              {visibleMarket.map((listing) => (
                <div key={listing.player_id} className="rounded-[28px] border border-border bg-slate-950/30 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${scoutingTone(listing.scouting.stage)}`}>
                          {listing.scouting.stage}
                        </span>
                        {listing.shortlisted ? <span className="chip chip-active">Shortlisted</span> : null}
                        <span className="chip">{listing.primary_position}</span>
                      </div>
                      <div className="mt-3 font-display text-3xl font-semibold">{listing.player_name}</div>
                      <div className="mt-2 text-sm text-muted">
                        {listing.current_team} · OVR {listing.overall_rating} · Age {listing.age}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="stat-label">Asking Price</div>
                      <div className="mt-2 font-display text-3xl font-semibold text-accent">{formatMoney(listing.asking_price)}</div>
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-2xl bg-white/5 p-4">
                      <div className="stat-label">Fit</div>
                      <div className="mt-2 text-sm font-medium">{listing.scouting.fit_label ?? "Not yet profiled"}</div>
                      <div className="mt-2 text-xs text-muted">
                        {listing.scouting.fit_score !== null ? `Score ${listing.scouting.fit_score}` : "Assign scouting to unlock fit."}
                      </div>
                    </div>
                    <div className="rounded-2xl bg-white/5 p-4">
                      <div className="stat-label">Value View</div>
                      <div className="mt-2 text-sm font-medium">
                        {formatRange(listing.scouting.estimated_value_low, listing.scouting.estimated_value_high)}
                      </div>
                      <div className="mt-2 text-xs text-muted">{listing.scouting.recommendation ?? "Scouting still gathering value confidence."}</div>
                    </div>
                    <div className="rounded-2xl bg-white/5 p-4">
                      <div className="stat-label">Potential</div>
                      <div className="mt-2 text-sm font-medium">{formatPotential(listing)}</div>
                      <div className="mt-2 text-xs text-muted">{listing.scouting.contract_years_hint ?? "Contract situation unknown."}</div>
                    </div>
                    <div className="rounded-2xl bg-white/5 p-4">
                      <div className="stat-label">Risk</div>
                      <div className="mt-2 text-sm font-medium">{listing.scouting.risk_label ?? "Unknown"}</div>
                      <div className="mt-2 text-xs text-muted">
                        Wage view: {formatRange(listing.scouting.estimated_weekly_wage_low, listing.scouting.estimated_weekly_wage_high)}
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="btn-secondary"
                        onClick={() => void handleScout(listing.player_id)}
                        disabled={busyKey !== null}
                      >
                        {busyKey === `scout-${listing.player_id}` ? "Assigning..." : listing.scouting.stage === "unscouted" ? "Start Scouting" : "Refresh Focus"}
                      </button>
                      <button
                        className="btn-ghost"
                        onClick={() => void handleToggleShortlist(listing.player_id)}
                        disabled={busyKey !== null}
                      >
                        {busyKey === `shortlist-${listing.player_id}` ? "Updating..." : listing.shortlisted ? "Remove Shortlist" : "Add Shortlist"}
                      </button>
                    </div>
                    <div className="flex flex-col gap-2 md:flex-row">
                      <input
                        className="field min-w-[150px]"
                        type="number"
                        value={bidValues[listing.listing_id] ?? listing.asking_price}
                        onChange={(event) =>
                          setBidValues((current) => ({ ...current, [listing.listing_id]: Number(event.target.value) }))
                        }
                      />
                      <button
                        className="btn-primary"
                        onClick={() => void handleBid(listing.listing_id, bidValues[listing.listing_id] ?? listing.asking_price)}
                        disabled={busyKey !== null}
                      >
                        {busyKey === `bid-${listing.listing_id}` ? "Submitting..." : "Submit Bid"}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No recruitment targets" body="There are no active market entries for the current filter." />
          )}
        </SectionCard>

        <SectionCard title="Shortlist" subtitle="Tracked targets sorted by fit and scouting quality.">
          {data.shortlist.length ? (
            <div className="space-y-3">
              {data.shortlist.map((listing) => (
                <div key={listing.player_id} className="rounded-2xl bg-slate-950/30 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-medium">{listing.player_name}</div>
                      <div className="mt-1 text-sm text-muted">
                        {listing.primary_position} · OVR {listing.overall_rating} · {listing.current_team}
                      </div>
                    </div>
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${scoutingTone(listing.scouting.stage)}`}>
                      {listing.scouting.stage}
                    </span>
                  </div>
                  <div className="mt-3 text-sm text-muted">
                    {listing.scouting.recommendation ?? "Scouting is still working toward a clearer recommendation."}
                  </div>
                  <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
                    <div className="rounded-2xl bg-white/5 px-3 py-2">
                      Fit: {listing.scouting.fit_label ?? "Unknown"}
                    </div>
                    <div className="rounded-2xl bg-white/5 px-3 py-2">
                      Value: {formatRange(listing.scouting.estimated_value_low, listing.scouting.estimated_value_high)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="Shortlist is empty" body="Add targets from the market board to keep a tighter recruiting focus." />
          )}
        </SectionCard>
      </div>

      <SectionCard title="Contract Watch" subtitle="Renewal risk for players at two years or less, with visible demand targets.">
        {data.contract_watch.length ? (
          <div className="space-y-3">
            {data.contract_watch.map((player) => {
              const offer = renewalValues[player.player_id] ?? {
                years: player.desired_years,
                weeklyWage: player.desired_weekly_wage,
              };
              return (
                <div key={player.player_id} className="rounded-[28px] border border-border bg-slate-950/30 p-5">
                  <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`chip ${player.retention_priority === "Core" ? "chip-active" : ""}`}>
                          {player.retention_priority}
                        </span>
                        <span className="chip">{player.contract_years_remaining} year(s) left</span>
                      </div>
                      <div className="mt-3 font-display text-3xl font-semibold">{player.player_name}</div>
                      <div className="mt-2 text-sm text-muted">
                        {player.primary_position} · OVR {player.overall_rating} · Age {player.age} · Morale {player.morale}
                      </div>
                      <div className="mt-4 grid gap-3 md:grid-cols-3">
                        <div className="rounded-2xl bg-white/5 p-4">
                          <div className="stat-label">Current Wage</div>
                          <div className="mt-2 text-sm font-medium">{formatMoney(player.current_wage)}</div>
                        </div>
                        <div className="rounded-2xl bg-white/5 p-4">
                          <div className="stat-label">Expected Wage</div>
                          <div className="mt-2 text-sm font-medium">{formatMoney(player.desired_weekly_wage)}</div>
                        </div>
                        <div className="rounded-2xl bg-white/5 p-4">
                          <div className="stat-label">Player Mood</div>
                          <div className={`mt-2 text-sm font-medium ${retentionTone(player.retention_priority)}`}>
                            {player.willingness}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-2xl bg-white/5 p-4">
                      <div className="stat-label">Renewal Offer</div>
                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        <label className="space-y-2 text-sm">
                          <span className="text-muted">Years</span>
                          <input
                            className="field"
                            type="number"
                            min={player.minimum_years}
                            max={5}
                            value={offer.years}
                            onChange={(event) =>
                              setRenewalValues((current) => ({
                                ...current,
                                [player.player_id]: {
                                  ...offer,
                                  years: Number(event.target.value),
                                },
                              }))
                            }
                          />
                        </label>
                        <label className="space-y-2 text-sm">
                          <span className="text-muted">Weekly Wage</span>
                          <input
                            className="field"
                            type="number"
                            min={player.desired_weekly_wage}
                            value={offer.weeklyWage}
                            onChange={(event) =>
                              setRenewalValues((current) => ({
                                ...current,
                                [player.player_id]: {
                                  ...offer,
                                  weeklyWage: Number(event.target.value),
                                },
                              }))
                            }
                          />
                        </label>
                      </div>
                      <div className="mt-4 text-sm text-muted">
                        Player expectation: {player.minimum_years}-{player.desired_years} years and about {formatMoney(player.desired_weekly_wage)}.
                        Stretch ceiling: {formatMoney(player.recommended_max_wage)}.
                      </div>
                      <button className="btn-primary mt-4 w-full" onClick={() => void handleRenew(player)} disabled={busyKey !== null}>
                        {busyKey === `renew-${player.player_id}` ? "Submitting..." : "Submit Renewal"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState title="Contract watch is clear" body="No players are close enough to expiry to demand action right now." />
        )}
      </SectionCard>
    </div>
  );
}
