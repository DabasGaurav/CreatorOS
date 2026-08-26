import { STAGE_ORDER, type RecommendationStage } from "@/lib/types";

const STAGE_LABELS: Record<RecommendationStage, string> = {
  research: "Researching the niche",
  candidates: "Generating candidates",
  ranked: "Ranking against your evidence",
  selected: "Selecting and explaining the pick",
  written: "Writing the content package",
};

export default function LoadingState({ stage }: { stage: RecommendationStage | null }) {
  const currentIndex = stage ? STAGE_ORDER.indexOf(stage) : -1;
  // Fill through the *current* stage, not just completed ones — a stage only
  // appears once its node starts producing state, so showing it as "in
  // progress" (not empty) reflects that work is genuinely happening now.
  const fillPct = currentIndex === -1 ? 4 : ((currentIndex + 1) / STAGE_ORDER.length) * 100;

  return (
    <div className="mx-auto flex max-w-xs flex-col items-center gap-6">
      <div
        className="relative aspect-[9/16] w-full overflow-hidden rounded-lg border-2 border-signal-amber/60"
        role="progressbar"
        aria-valuenow={currentIndex + 1}
        aria-valuemin={0}
        aria-valuemax={STAGE_ORDER.length}
        aria-label="Generating recommendation"
      >
        <div
          className="absolute inset-x-0 bottom-0 bg-signal-amber/15 transition-[height] duration-700 ease-out"
          style={{ height: `${fillPct}%` }}
        />
      </div>
      <ul className="w-full space-y-2 font-utility text-xs">
        {STAGE_ORDER.map((s, i) => {
          const done = i < currentIndex;
          const active = i === currentIndex;
          return (
            <li
              key={s}
              className={`flex items-center gap-2 ${
                done || active ? "text-ink" : "text-ink-muted"
              }`}
            >
              <span
                className={`inline-block h-1.5 w-1.5 rounded-full ${
                  done ? "bg-signal-amber" : active ? "animate-pulse bg-signal-amber" : "bg-surface-raised"
                }`}
                aria-hidden="true"
              />
              {STAGE_LABELS[s]}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
