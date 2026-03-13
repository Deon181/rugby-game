type StatCardProps = {
  label: string;
  value: string | number;
  detail?: string;
  accent?: "default" | "success" | "warn" | "danger";
};

const accentMap = {
  default: "text-accent",
  success: "text-success",
  warn: "text-warn",
  danger: "text-danger",
};

export function StatCard({ label, value, detail, accent = "default" }: StatCardProps) {
  return (
    <div className="panel p-5">
      <div className="stat-label">{label}</div>
      <div className={`mt-2 font-display text-4xl font-bold ${accentMap[accent]}`}>{value}</div>
      {detail ? <div className="mt-3 text-sm text-muted">{detail}</div> : null}
    </div>
  );
}
