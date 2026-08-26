import uuid

from creatoros.graph import nodes as nodes_module
from creatoros.graph.nodes import (
    baseline_node_factory,
    explore_exploit_node,
    ranking_node_factory,
)
from creatoros.graph.pipeline import build_pipeline


class FakeQdrant:
    pass


class FakeNicheQuery:
    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return []


class FakeSession:
    def query(self, model):
        return FakeNicheQuery()


def test_pipeline_compiles_without_error():
    pipeline = build_pipeline(FakeSession(), FakeQdrant())
    assert pipeline is not None


def test_ranking_node_sorts_by_composite_score_descending(monkeypatch):
    # embed_texts is called once per cycle with all candidate texts, in order —
    # the fake returns a per-candidate marker vector so creator_fit's fake can
    # tell "bad idea" and "good idea" apart without needing real embeddings.
    monkeypatch.setattr(
        nodes_module,
        "embed_texts",
        lambda texts, input_type="query": [[0.1] if "bad" in t else [0.9] for t in texts],
    )
    monkeypatch.setattr(
        nodes_module,
        "creator_fit",
        lambda qdrant, candidate_vector, creator_id: candidate_vector[0],
    )
    monkeypatch.setattr(
        nodes_module, "personal_novelty", lambda qdrant, candidate_vector, creator_id: 0.5
    )

    ranking_node = ranking_node_factory(FakeSession(), FakeQdrant())
    state = {
        "creator_id": str(uuid.uuid4()),
        "niche": "AI/startups",
        "evidence": {"confidence": 0.5},
        "candidates": [
            {
                "topic": "bad idea",
                "angle": "meh",
                "format": "reel",
                "audience_need": "n",
                "timing": "now",
            },
            {
                "topic": "good idea",
                "angle": "great",
                "format": "reel",
                "audience_need": "n",
                "timing": "now",
            },
        ],
    }

    result = ranking_node(state)
    ranked = result["ranked"]
    assert len(ranked) == 2
    assert ranked[0]["topic"] == "good idea"
    assert ranked[0]["composite_score"] > ranked[1]["composite_score"]
    for c in ranked:
        assert "creator_fit" in c
        assert "expected_engagement" in c


def test_explore_exploit_node_populates_selection_and_type():
    state = {
        "ranked": [
            {"topic": "a", "composite_score": 0.9},
            {"topic": "b", "composite_score": 0.5},
        ]
    }
    result = explore_exploit_node(state)
    assert result["selection"]["topic"] in ("a", "b")
    assert result["selection_type"] in ("exploit", "explore")


def test_baseline_node_returns_all_expected_keys():
    baseline_node = baseline_node_factory()
    state = {
        "ranked": [
            {
                "topic": "a",
                "angle": "x",
                "creator_fit": 0.9,
                "audience_demand": 0.8,
                "trend_momentum": 0.7,
            },
            {
                "topic": "b",
                "angle": "y",
                "creator_fit": 0.3,
                "audience_demand": 0.2,
                "trend_momentum": 0.1,
            },
        ],
        "creator_dna": {
            "winning_topics": [{"label": "a"}],
            "recent_fatigue_notes": {"topics": [{"label": "b"}]},
        },
    }
    result = baseline_node(state)
    picks = result["baseline_picks"]
    assert set(picks.keys()) == {
        "trending_only",
        "popularity_only",
        "random",
        "historical_top_topic",
        "most_recent_successful_topic",
    }
