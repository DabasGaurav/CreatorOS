import pytest

from creatoros.ranking import factors


def test_audience_demand_averages_inputs():
    result = factors.audience_demand(normalized_search_volume=0.8, community_engagement_score=0.4)
    assert result == pytest.approx(0.6)


def test_audience_demand_clamped_to_unit_interval():
    assert (
        factors.audience_demand(normalized_search_volume=1.5, community_engagement_score=1.5) == 1.0
    )


def test_trend_momentum_averages_inputs():
    assert factors.trend_momentum(trend_slope=0.2, discussion_velocity=0.6) == 0.4


def test_niche_saturation_zero_with_no_niche_signal():
    assert factors.niche_saturation(candidate_vector=[1.0, 0.0], niche_vectors=[]) == 0.0


def test_niche_saturation_high_for_similar_topic():
    score = factors.niche_saturation(candidate_vector=[1.0, 0.0], niche_vectors=[[1.0, 0.0]])
    assert score == 1.0


def test_niche_saturation_low_for_dissimilar_topic():
    score = factors.niche_saturation(candidate_vector=[1.0, 0.0], niche_vectors=[[0.0, 1.0]])
    assert score == 0.5  # orthogonal vectors remap to the midpoint


def test_novelty_combines_personal_novelty_and_saturation():
    # High personal novelty + low saturation => high novelty.
    assert factors.novelty(personal_novelty=1.0, niche_saturation_score=0.0) == 1.0
    # Low personal novelty + high saturation => low novelty.
    assert factors.novelty(personal_novelty=0.0, niche_saturation_score=1.0) == 0.0
    # Mixed signal averages.
    assert factors.novelty(personal_novelty=1.0, niche_saturation_score=1.0) == 0.5
