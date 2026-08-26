import type { Recommendation } from "@/lib/types";
import ScoreBadge from "./ScoreBadge";
import EvidenceReceipt from "./EvidenceReceipt";
import OutcomeReceipt from "./OutcomeReceipt";
import ContentPackageSection from "./ContentPackageSection";

export default function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const isExplore = recommendation.selection_type === "explore";
  const accentClassName = isExplore ? "bg-explore-teal" : "bg-signal-amber";

  return (
    <div className="mx-auto max-w-sm space-y-4">
      {/* 9:16 frame — echoes the Reel aspect ratio */}
      <div className="relative aspect-[9/16] w-full overflow-hidden rounded-lg border border-surface-raised bg-gradient-to-br from-surface to-surface-raised">
        <div className="absolute inset-0 flex items-end bg-gradient-to-t from-canvas/90 via-canvas/10 to-transparent p-5">
          <div>
            {isExplore && (
              <span className="mb-2 inline-block rounded bg-explore-teal/15 px-2 py-0.5 font-utility text-[11px] uppercase tracking-wide text-explore-teal">
                Experiment
              </span>
            )}
            <h2 className="font-display text-2xl leading-tight font-semibold text-ink">
              {recommendation.topic}
            </h2>
            {recommendation.angle && (
              <p className="mt-1 font-body text-sm text-ink-muted">{recommendation.angle}</p>
            )}
          </div>
        </div>
        <ScoreBadge
          score={recommendation.composite_score}
          selectionType={recommendation.selection_type}
        />
      </div>

      {recommendation.evidence_breakdown && (
        <>
          <EvidenceReceipt
            evidence={recommendation.evidence_breakdown}
            accentClassName={accentClassName}
          />
          {recommendation.outcome && <OutcomeReceipt outcome={recommendation.outcome} />}
          <div className="space-y-3 px-1">
            {recommendation.evidence_breakdown.why_now && (
              <div>
                <h3 className="mb-1 font-utility text-xs uppercase tracking-wide text-ink-muted">
                  Why now
                </h3>
                <p className="font-body text-sm leading-relaxed text-ink">
                  {recommendation.evidence_breakdown.why_now}
                </p>
              </div>
            )}
            {recommendation.evidence_breakdown.why_you && (
              <div>
                <h3 className="mb-1 font-utility text-xs uppercase tracking-wide text-ink-muted">
                  Why you
                </h3>
                <p className="font-body text-sm leading-relaxed text-ink">
                  {recommendation.evidence_breakdown.why_you}
                </p>
              </div>
            )}
          </div>
        </>
      )}

      {recommendation.content_package && (
        <ContentPackageSection content={recommendation.content_package} />
      )}
    </div>
  );
}
