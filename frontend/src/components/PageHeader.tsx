import type { ReactNode } from "react";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
};

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 rounded-3xl border border-border bg-slate-950/30 px-6 py-6 md:flex-row md:items-end md:justify-between">
      <div className="space-y-2">
        <div className="stat-label">{eyebrow}</div>
        <h1 className="font-display text-4xl font-bold text-text">{title}</h1>
        <p className="max-w-3xl text-sm text-muted md:text-base">{description}</p>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
    </div>
  );
}
