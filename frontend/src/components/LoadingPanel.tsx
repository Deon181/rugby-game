type LoadingPanelProps = {
  label: string;
  className?: string;
};

export function LoadingPanel({ label, className = "" }: LoadingPanelProps) {
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className="panel-alt flex min-w-[280px] items-center gap-4 px-6 py-5">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        <div>
          <div className="font-display text-2xl font-semibold">{label}</div>
          <div className="text-sm text-muted">Preparing the rugby world state.</div>
        </div>
      </div>
    </div>
  );
}
