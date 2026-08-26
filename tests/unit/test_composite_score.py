from creatoros.ranking.composite_score import CompositeWeights, FactorScores, composite_score


def test_composite_score_weighted_sum():
    factors_ = FactorScores(
        creator_fit=0.8,
        audience_demand=0.6,
        trend_momentum=0.4,
        novelty=0.9,
        expected_engagement=0.7,
    )
    weights = CompositeWeights(
        creator_fit=0.3,
        audience_demand=0.2,
        trend_momentum=0.2,
        novelty=0.1,
        expected_engagement=0.2,
    )
    expected = 0.3 * 0.8 + 0.2 * 0.6 + 0.2 * 0.4 + 0.1 * 0.9 + 0.2 * 0.7
    assert composite_score(factors_, weights) == expected


def test_composite_score_equal_weights_equals_average_when_weights_sum_to_one():
    factors_ = FactorScores(0.5, 0.5, 0.5, 0.5, 0.5)
    weights = CompositeWeights(0.2, 0.2, 0.2, 0.2, 0.2)
    assert composite_score(factors_, weights) == 0.5
