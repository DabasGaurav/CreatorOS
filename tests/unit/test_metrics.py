from creatoros.dna.metrics import compute_engagement_rate


def test_compute_engagement_rate_basic():
    rate = compute_engagement_rate(likes=40, comments=5, shares=3, saves=2, reach=1000)
    assert rate == (40 + 5 + 3 + 2) / 1000


def test_compute_engagement_rate_treats_missing_metrics_as_zero():
    rate = compute_engagement_rate(likes=10, comments=None, shares=None, saves=None, reach=100)
    assert rate == 0.1


def test_compute_engagement_rate_none_when_reach_missing():
    assert compute_engagement_rate(likes=10, comments=1, shares=1, saves=1, reach=None) is None


def test_compute_engagement_rate_none_when_reach_zero():
    assert compute_engagement_rate(likes=10, comments=1, shares=1, saves=1, reach=0) is None
