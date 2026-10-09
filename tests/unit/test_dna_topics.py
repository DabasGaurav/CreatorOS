from creatorsignal.dna.topics import cluster_reels, label_cluster


def _unit_vector(dim: int, index: int) -> list[float]:
    v = [0.0] * dim
    v[index] = 1.0
    return v


def test_cluster_reels_groups_similar_vectors_together():
    ids = ["r1", "r2", "r3", "r4"]
    embeddings = [
        _unit_vector(8, 0),
        [0.99, 0.01] + [0.0] * 6,  # near-identical to r1
        _unit_vector(8, 5),
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.99, 0.01, 0.0],  # near-identical to r3
    ]
    clusters = cluster_reels(ids, embeddings, distance_threshold=0.1)
    assert clusters["r1"] == clusters["r2"]
    assert clusters["r3"] == clusters["r4"]
    assert clusters["r1"] != clusters["r3"]


def test_cluster_reels_empty_input():
    assert cluster_reels([], []) == {}


def test_cluster_reels_single_reel():
    result = cluster_reels(["r1"], [_unit_vector(4, 0)])
    assert result == {"r1": 0}


def test_label_cluster_picks_frequent_keywords():
    captions = [
        "3 AI tools every founder needs",
        "The best AI tools for startups",
        "AI tools that save you hours",
    ]
    label = label_cluster(captions)
    assert "ai" in label or "tools" in label


def test_label_cluster_falls_back_when_no_text():
    assert label_cluster([None, "", None]) == "uncategorized"
