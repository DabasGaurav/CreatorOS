import type { EvidenceBreakdown } from "@/lib/types";

interface Factor {
  label: string;
  value: number | null;
}

function formatPct(value: number | null): string {
  if (value === null) return "--";
  return `${Math.round(value * 100)}%`;
}

export default function EvidenceReceipt({
  evidence,
  accentClassName,
}: {
  evidence: EvidenceBreakdown;
  accentClassName: string;
}) {
  const factors: Factor[] = [
    { label: "CreatorFit", value: evidence.creator_fit },
    { label: "AudienceDemand", value: evidence.audience_demand },
    { label: "TrendMomentum", value: evidence.trend_momentum },
    { label: "Novelty", value: evidence.novelty },
    { label: "ExpectedEngagement", value: evidence.expected_engagement },
  ];

  return (
    <div
      className="rounded-md border border-surface-raised bg-surface p-4 font-utility text-[13px] tabular-nums"
      aria-label="Evidence breakdown"
    >
      <ul className="space-y-2.5">
        {factors.map((factor, i) => {
          const pct = factor.value ?? 0;
          return (
            <li
              key={factor.label}
              className="receipt-line flex items-center gap-3"
              style={{ "--line-index": i } as React.CSSProperties}
            >
              <span className="w-36 shrink-0 text-ink-muted">{factor.label}</span>
              <span className="h-1 flex-1 overflow-hidden rounded-full bg-surface-raised">
                <span
                  className={`block h-full rounded-full ${accentClassName}`}
                  style={{ width: `${Math.max(0, Math.min(100, pct * 100))}%` }}
                />
              </span>
              <span className="w-10 shrink-0 text-right text-ink">
                {formatPct(factor.value)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
