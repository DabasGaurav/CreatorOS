"""The five CompositeScore ranking factors (B8), each an independent, unit-testable
pure function returning a [0,1] float. CreatorFit and PersonalNovelty already exist
in embeddings/qdrant_client.py (Build Doc 1) — this module covers the remaining
factors the spec assigns to Build Doc 2: AudienceDemand, TrendMomentum, Novelty
(which composes PersonalNovelty with niche saturation), and niche saturation itself.

AudienceDemand and TrendMomentum take pre-normalized [0,1] inputs rather than raw
evidence, so they stay decoupled from the Market Researcher agent that produces
those inputs — the combination formula for each (spec doesn't specify one) is a
simple mean, documented as an assumption, not a spec-given rule.
"""

from creatoros.embeddings.qdrant_client import cosine_similarity
from creatoros.embeddings.voyage_client import embed_text, embed_texts


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _remap_cosine_to_unit(cosine_score: float) -> float:
    return _clamp01((cosine_score + 1.0) / 2.0)


def audience_demand(*, normalized_search_volume: float, community_engagement_score: float) -> float:
    """Evidence the audience wants this topic. Both inputs are already normalized
    to [0,1] by the Market Researcher's evidence extraction (search-volume
    percentile, community engagement percentile)."""
    return _clamp01((normalized_search_volume + community_engagement_score) / 2)


def trend_momentum(*, trend_slope: float, discussion_velocity: float) -> float:
    """Whether demand is accelerating, not just large. Both inputs pre-normalized
    to [0,1] (e.g. a Google Trends slope percentile, a Reddit/YouTube post-velocity
    percentile) by the Market Researcher."""
    return _clamp01((trend_slope + discussion_velocity) / 2)


def niche_saturation(*, candidate_text: str, niche_signal_texts: list[str]) -> float:
    """High similarity to recently observed niche-wide topics (niche_signal, Build
    Doc 1 — manually curated, never scraped) means the topic is saturated in the
    creator's niche right now. Returns saturation in [0,1]; 0.0 (unsaturated) when
    there's no niche_signal data yet to compare against."""
    if not niche_signal_texts:
        return 0.0

    candidate_vector = embed_text(candidate_text, input_type="query")
    niche_vectors = embed_texts(niche_signal_texts, input_type="document")
    max_similarity = max(cosine_similarity(candidate_vector, v) for v in niche_vectors)
    return _remap_cosine_to_unit(max_similarity)


def novelty(*, personal_novelty: float, niche_saturation_score: float) -> float:
    """Avoids over-repetition — two sub-scores kept separate per spec (personal
    novelty vs. niche saturation), combined here as a simple mean: genuinely novel
    means both 'new for this creator' and 'not oversaturated in the niche'."""
    return _clamp01((personal_novelty + (1.0 - niche_saturation_score)) / 2)
