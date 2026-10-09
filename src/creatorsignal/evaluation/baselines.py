"""Baselines CreatorSignal.ai must be shown to beat (B13) — implemented now as callable
functions over the same candidate pool the real ranking pipeline scores, so later
offline A/B comparison is a query, not a re-run. Each baseline picks one candidate
from the pool using a simpler heuristic than the full CompositeScore pipeline;
"real evaluation happens after outcome data exists" (spec) — these exist now so
that data can be logged from day one.

Assumption, not spec-given: "most recent successful topic" is approximated via
Creator DNA's recency-weighted recent_fatigue_notes top entry (Build Doc 1) rather
than a separate history scan — recent_fatigue_notes' exponential decay already
weights true recency heavily, and reusing it avoids a second aggregation pass.
"""

import random
from typing import Protocol, TypedDict


class Candidate(TypedDict, total=False):
    topic: str
    angle: str
    creator_fit: float
    audience_demand: float
    trend_momentum: float
    novelty: float
    expected_engagement: float
    composite_score: float


class _SupportsGenerate(Protocol):
    def __call__(self, niche: str) -> str: ...


def _best_by(candidates: list[Candidate], key: str) -> Candidate:
    return max(candidates, key=lambda c: c.get(key, 0.0))


def _best_matching_label(candidates: list[Candidate], label: str) -> Candidate:
    """Keyword-overlap match between a candidate's topic+angle text and a target
    label — deliberately cheap (no embedding call) since baselines exist to be a
    fast, always-available comparison point, not another use of the real pipeline's
    retrieval machinery."""
    label_words = set(label.lower().split())
    return max(
        candidates,
        key=lambda c: len(
            label_words & set(f"{c.get('topic', '')} {c.get('angle', '')}".lower().split())
        ),
    )


def trending_only_baseline(candidates: list[Candidate]) -> Candidate:
    """Picks the candidate with the highest TrendMomentum alone — ignores fit,
    demand, novelty, and predicted engagement entirely."""
    return _best_by(candidates, "trend_momentum")


def popularity_only_baseline(candidates: list[Candidate]) -> Candidate:
    """Picks the candidate with the highest AudienceDemand alone."""
    return _best_by(candidates, "audience_demand")


def random_baseline(candidates: list[Candidate], *, rng: random.Random | None = None) -> Candidate:
    rng = rng or random.Random()
    return rng.choice(candidates)


def historical_top_topic_baseline(
    candidates: list[Candidate], *, creator_dna_winning_topics: list[dict]
) -> Candidate:
    """Picks the candidate whose topic/angle text best matches the creator's
    all-time top-performing topic cluster label — a keyword-overlap proxy, not the
    full composite ranking. Falls back to best CreatorFit when there's no DNA yet
    (e.g. a brand-new creator with no winning_topics)."""
    if not creator_dna_winning_topics:
        return _best_by(candidates, "creator_fit")
    return _best_matching_label(candidates, creator_dna_winning_topics[0]["label"])


def most_recent_successful_topic_baseline(
    candidates: list[Candidate], *, creator_dna_recent_fatigue_topics: list[dict]
) -> Candidate:
    """Approximated via Creator DNA's recency-weighted fatigue notes (see module
    docstring) rather than a fresh history scan — its top entry is the topic
    cluster most heavily weighted toward true recency. Falls back to best
    CreatorFit when there's no fatigue data yet."""
    if not creator_dna_recent_fatigue_topics:
        return _best_by(candidates, "creator_fit")
    return _best_matching_label(candidates, creator_dna_recent_fatigue_topics[0]["label"])


def llm_only_baseline(
    candidates: list[Candidate], *, generate: _SupportsGenerate, niche: str
) -> Candidate:
    """LLM-only idea generation with no ranking at all — the counterfactual
    CreatorSignal.ai must beat to justify the ranking/retrieval machinery's existence.
    `generate` is injected so this stays unit-testable without a live API call;
    the real implementation calls the Anthropic API with no evidence, no ranking,
    just 'give me a Reel idea for this niche.'"""
    suggested_topic = generate(niche)
    return _best_matching_label(candidates, suggested_topic)
