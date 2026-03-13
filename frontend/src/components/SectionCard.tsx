import type { ReactNode } from "react";

type SectionCardProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function SectionCard({ title, subtitle, actions, children }: SectionCardProps) {
  return (
    <section className="panel p-5">
      <div className="mb-4 flex flex-col gap-3 border-b border-border pb-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-display text-2xl font-semibold">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
        </div>
        {actions ? <div className="flex items-center gap-3">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}
