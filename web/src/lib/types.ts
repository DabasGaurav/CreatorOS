// Mirrors the FastAPI backend's response shapes (src/creatorsignal/api/main.py,
// src/creatorsignal/db/models.py). Kept as plain types, not a shared codegen
// artifact — the backend is the source of truth; update both sides by hand
// when either changes.

export type RecommendationStatus = "pending" | "running" | "completed" | "failed";

// Mirrors src/creatorsignal/api/main.py's _NODE_TO_STAGE mapping.
export type RecommendationStage = "research" | "candidates" | "ranked" | "selected" | "written";

export const STAGE_ORDER: RecommendationStage[] = [
  "research",
  "candidates",
  "ranked",
  "selected",
  "written",
];

export interface EvidenceBreakdown {
  creator_fit: number | null;
  audience_demand: number | null;
  trend_momentum: number | null;
  novelty: number | null;
  expected_engagement: number | null;
  why_now: string | null;
  why_you: string | null;
}

export interface ContentPackage {
  hook: string;
  script: string;
  storyboard: string;
  caption: string;
  cta: string;
}

export interface Outcome {
  topic_match_score: number | null;
  actual_engagement_rate: number | null;
  predicted_engagement: number | null;
  detected_at: string;
}

export interface Recommendation {
  request_id: string;
  status: RecommendationStatus;
  current_stage: RecommendationStage | null;
  error: string | null;
  topic: string | null;
  angle: string | null;
  format: string | null;
  composite_score: number | null;
  evidence_breakdown: EvidenceBreakdown | null;
  selection_type: "exploit" | "explore" | null;
  content_package: ContentPackage | null;
  baseline_picks: Record<string, string | null> | null;
  created_at: string;
  completed_at: string | null;
  outcome: Outcome | null;
}

export interface CreatorDNATopic {
  cluster_id?: number;
  label: string;
  avg_engagement_rate: number;
  reel_count: number;
}

export interface CreatorDNA {
  winning_topics: CreatorDNATopic[];
  weak_topics: CreatorDNATopic[];
  primary_kpi: string;
  early_profile: boolean;
}

export interface Creator {
  id: string;
  display_name: string | null;
  niche: string;
  instagram_connected: boolean;
}
