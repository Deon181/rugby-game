type EmptyStateProps = {
  title: string;
  body: string;
};

export function EmptyState({ title, body }: EmptyStateProps) {
  return (
    <div className="panel-alt flex min-h-[220px] flex-col items-center justify-center px-6 py-10 text-center">
      <div className="font-display text-3xl font-semibold">{title}</div>
      <p className="mt-3 max-w-xl text-sm text-muted">{body}</p>
    </div>
  );
}
