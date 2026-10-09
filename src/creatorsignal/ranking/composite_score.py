"""CompositeScore(x) = w1*CreatorFit + w2*AudienceDemand + w3*TrendMomentum
+ w4*Novelty + w5*ExpectedEngagement — a normalized weighted sum (B8), deliberately
over a multiplicative formula: decomposable (each factor's contribution is visible
to the creator in the Evidence Receipt) and doesn't misbehave near zero.

Pure, no LLM call — unit-testable and ablation-friendly per spec (B8.1 step 2).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FactorScores:
    creator_fit: float
    audience_demand: float
    trend_momentum: float
    novelty: float
    expected_engagement: float


@dataclass(frozen=True)
class CompositeWeights:
    creator_fit: float
    audience_demand: float
    trend_momentum: float
    novelty: float
    expected_engagement: float


def composite_score(factors: FactorScores, weights: CompositeWeights) -> float:
    return (
        weights.creator_fit * factors.creator_fit
        + weights.audience_demand * factors.audience_demand
        + weights.trend_momentum * factors.trend_momentum
        + weights.novelty * factors.novelty
        + weights.expected_engagement * factors.expected_engagement
    )


def weights_from_settings() -> CompositeWeights:
    from creatorsignal.config import get_settings

    s = get_settings()
    return CompositeWeights(
        creator_fit=s.weight_creator_fit,
        audience_demand=s.weight_audience_demand,
        trend_momentum=s.weight_trend_momentum,
        novelty=s.weight_novelty,
        expected_engagement=s.weight_expected_engagement,
    )
