import random

from creatoros.evaluation import baselines


def _candidates():
    return [
        {
            "topic": "AI coding agents",
            "angle": "productivity",
            "creator_fit": 0.5,
            "audience_demand": 0.9,
            "trend_momentum": 0.95,
        },
        {
            "topic": "cooking recipes",
            "angle": "weeknight dinners",
            "creator_fit": 0.9,
            "audience_demand": 0.2,
            "trend_momentum": 0.1,
        },
        {
            "topic": "startup fundraising",
            "angle": "seed round tips",
            "creator_fit": 0.3,
            "audience_demand": 0.4,
            "trend_momentum": 0.5,
        },
    ]


def test_trending_only_picks_highest_trend_momentum():
    result = baselines.trending_only_baseline(_candidates())
    assert result["topic"] == "AI coding agents"


def test_popularity_only_picks_highest_audience_demand():
    result = baselines.popularity_only_baseline(_candidates())
    assert result["topic"] == "AI coding agents"


def test_random_baseline_uses_injected_rng():
    candidates = _candidates()
    rng = random.Random(0)
    result = baselines.random_baseline(candidates, rng=rng)
    assert result in candidates


def test_historical_top_topic_baseline_matches_label_keywords():
    candidates = _candidates()
    result = baselines.historical_top_topic_baseline(
        candidates, creator_dna_winning_topics=[{"label": "cooking recipes"}]
    )
    assert result["topic"] == "cooking recipes"


def test_historical_top_topic_baseline_falls_back_when_no_dna():
    candidates = _candidates()
    result = baselines.historical_top_topic_baseline(candidates, creator_dna_winning_topics=[])
    assert result["topic"] == "cooking recipes"  # highest creator_fit


def test_most_recent_successful_topic_baseline_matches_label_keywords():
    candidates = _candidates()
    result = baselines.most_recent_successful_topic_baseline(
        candidates, creator_dna_recent_fatigue_topics=[{"label": "startup fundraising"}]
    )
    assert result["topic"] == "startup fundraising"


def test_llm_only_baseline_matches_generated_topic_to_candidate_pool():
    candidates = _candidates()
    result = baselines.llm_only_baseline(
        candidates, generate=lambda niche: "cooking recipes for beginners", niche="food"
    )
    assert result["topic"] == "cooking recipes"
