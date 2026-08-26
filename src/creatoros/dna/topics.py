"""Topic clustering — method unspecified by the spec. Using agglomerative clustering
(cosine distance, average linkage, distance threshold) rather than k-means, since the
number of topics per creator isn't known ahead of time and per-creator N is small
(tens of reels). Deterministic, no heavyweight extra dependency.

This clustering is computed fresh here, for Creator DNA's JSON output only — it is
NOT written back into Qdrant's `topic_cluster` payload field, which the spec says
stays null until Build Doc 2 assigns clusters. See Build Doc 1 plan §6 for the
reconciliation of this apparent spec conflict.
"""

import re
from collections import Counter

import numpy as np
from sklearn.cluster import AgglomerativeClustering

DEFAULT_DISTANCE_THRESHOLD = 0.35

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "is",
    "are", "you", "your", "i", "my", "this", "that", "with", "it", "at", "as",
    "be", "how", "why", "what", "so", "if", "not", "just", "do", "did", "will",
    "can", "we", "us", "our", "me", "was", "have", "has", "when", "who",
}


def cluster_reels(
    reel_ids: list[str],
    embeddings: list[list[float]],
    *,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
) -> dict[str, int]:
    """Returns {reel_id: cluster_id}. Reels with no embedding should be excluded by
    the caller before calling this — clustering needs a vector per item."""
    if not reel_ids:
        return {}
    if len(reel_ids) == 1:
        return {reel_ids[0]: 0}

    X = np.array(embeddings)
    model = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=distance_threshold,
    )
    labels = model.fit_predict(X)
    return dict(zip(reel_ids, (int(label) for label in labels), strict=True))


def label_cluster(captions: list[str], *, top_n: int = 2) -> str:
    """No LLM allowed in Phase 1 — a lightweight keyword-frequency label instead of
    an LLM-generated one. Falls back to a generic label when there's no usable text."""
    words: Counter[str] = Counter()
    for caption in captions:
        if not caption:
            continue
        tokens = re.findall(r"[a-zA-Z']+", caption.lower())
        words.update(t for t in tokens if len(t) > 2 and t not in _STOPWORDS)

    top_words = [w for w, _ in words.most_common(top_n)]
    return " ".join(top_words) if top_words else "uncategorized"
