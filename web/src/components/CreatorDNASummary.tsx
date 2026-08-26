import type { Creator, CreatorDNA } from "@/lib/types";

export default function CreatorDNASummary({
  creator,
  dna,
}: {
  creator: Creator;
  dna: CreatorDNA | null;
}) {
  const topTopic = dna?.winning_topics?.[0]?.label;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-surface-raised bg-surface px-4 py-3">
      <div>
        <p className="font-display text-sm font-medium text-ink">{creator.display_name}</p>
        <p className="font-body text-xs text-ink-muted">{creator.niche}</p>
      </div>
      <div className="flex items-center gap-4 font-utility text-xs text-ink-muted">
        {dna?.early_profile && (
          <span className="rounded bg-alert-coral/15 px-2 py-0.5 text-alert-coral">
            Early profile
          </span>
        )}
        {topTopic && (
          <span>
            Top topic: <span className="text-ink">{topTopic}</span>
          </span>
        )}
        {dna?.primary_kpi && (
          <span>
            KPI: <span className="text-ink">{dna.primary_kpi}</span>
          </span>
        )}
      </div>
    </div>
  );
}
