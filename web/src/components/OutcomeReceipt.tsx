import type { Outcome } from "@/lib/types";

function formatPct(value: number | null): string {
  if (value === null) return "--";
  return `${Math.round(value * 100)}%`;
}

// A second, smaller receipt beneath the predicted one — visually reinforcing
// the predict -> measure loop that's the product's real differentiator (C4).
export default function OutcomeReceipt({ outcome }: { outcome: Outcome }) {
  const rows = [
    { label: "Predicted engagement", value: outcome.predicted_engagement },
    { label: "Actual engagement", value: outcome.actual_engagement_rate },
    { label: "Topic match", value: outcome.topic_match_score },
  ];

  return (
    <div className="rounded-md border border-explore-teal/40 bg-surface p-3 font-utility text-xs tabular-nums">
      <p className="mb-2 text-[11px] uppercase tracking-wide text-explore-teal">Actual result</p>
      <ul className="space-y-1.5">
        {rows.map((row) => (
          <li key={row.label} className="flex items-center justify-between gap-3">
            <span className="text-ink-muted">{row.label}</span>
            <span className="text-ink">{formatPct(row.value)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
