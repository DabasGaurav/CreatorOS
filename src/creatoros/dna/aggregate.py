"""Creator DNA aggregation — the core deliverable of Build Doc 1.

compute_dna() is a pure function: given a creator's reels (with engagement rates and
embeddings already resolved by the caller), it returns a JSON-serializable dict with
no DB or network I/O. This is deliberate — it's the single highest-leverage design
decision for testability in this phase, letting the whole aggregation be checked
against synthetic fixtures with zero credentials.

Leakage discipline: only ever consider reels with posted_at <= computed_at. No
recommendation engine consumes this yet, but this keeps the function forward-
compatible with Build Doc 2/3's point-in-time snapshot needs without a rewrite.
"""

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from creatoros.dna import formats, hooks, topics

# Weight above this in recent_fatigue_notes is flagged overrepresented. Arbitrary,
# documented threshold — not derived from the spec, which doesn't define one.
FATIGUE_OVERREPRESENTED_THRESHOLD = 0.4
FATIGUE_DECAY = 0.9

# Both "winning" and "weak" as roughly the top/bottom quarter of ranked topic
# clusters — spec says "top-quartile"/"bottom-quartile" without an exact definition.
QUARTILE_FRACTION = 0.25


@dataclass
class ReelForDNA:
    reel_id: str
    posted_at: datetime
    caption: str | None
    transcript: str | None
    duration_seconds: float | None
    media_product_type: str | None
    embedding: list[float] | None
    engagement_rate: float | None


def _empty_dna(*, primary_kpi: str) -> dict:
    return {
        "winning_topics": [],
        "weak_topics": [],
        "winning_hooks": [],
        "typical_length_min_seconds": None,
        "typical_length_max_seconds": None,
        "strong_formats": [],
        "primary_kpi": primary_kpi,
        "recent_fatigue_notes": {"window_size": 0, "topics": []},
        "early_profile": True,
    }


def _cluster_topics(reels: list[ReelForDNA]) -> tuple[dict[str, int], dict[int, str]]:
    """Returns (reel_id -> cluster_id, cluster_id -> label). Reels without an
    embedding are excluded from clustering — the caller decides what that means
    for hooks/formats/length, which don't depend on embeddings."""
    embedded = [r for r in reels if r.embedding is not None]
    if not embedded:
        return {}, {}

    cluster_map = topics.cluster_reels(
        [r.reel_id for r in embedded], [r.embedding for r in embedded]
    )
    captions_by_cluster: dict[int, list[str]] = defaultdict(list)
    for reel in embedded:
        cluster_id = cluster_map[reel.reel_id]
        if reel.caption:
            captions_by_cluster[cluster_id].append(reel.caption)

    labels = {cid: topics.label_cluster(caps) for cid, caps in captions_by_cluster.items()}
    return cluster_map, labels


def _rank_topic_clusters(
    reels: list[ReelForDNA], cluster_map: dict[str, int], labels: dict[int, str]
) -> list[dict]:
    by_cluster: dict[int, list[ReelForDNA]] = defaultdict(list)
    for reel in reels:
        cluster_id = cluster_map.get(reel.reel_id)
        if cluster_id is not None:
            by_cluster[cluster_id].append(reel)

    ranked = []
    for cluster_id, group in by_cluster.items():
        rates = [r.engagement_rate for r in group if r.engagement_rate is not None]
        if not rates:
            continue
        ranked.append(
            {
                "cluster_id": cluster_id,
                "label": labels.get(cluster_id, "uncategorized"),
                "avg_engagement_rate": statistics.mean(rates),
                "reel_count": len(group),
            }
        )
    ranked.sort(key=lambda c: c["avg_engagement_rate"], reverse=True)
    return ranked


def _split_winning_and_weak(ranked_clusters: list[dict]) -> tuple[list[dict], list[dict]]:
    if len(ranked_clusters) <= 1:
        return ranked_clusters, []

    quartile_size = max(1, round(len(ranked_clusters) * QUARTILE_FRACTION))
    winning = ranked_clusters[:quartile_size]
    weak = list(reversed(ranked_clusters[-quartile_size:]))
    # Guard against the same cluster appearing in both lists when quartiles overlap.
    winning_ids = {c["cluster_id"] for c in winning}
    weak = [c for c in weak if c["cluster_id"] not in winning_ids]
    return winning, weak


def _rank_hooks(reels: list[ReelForDNA]) -> list[dict]:
    by_hook: dict[str, list[ReelForDNA]] = defaultdict(list)
    for reel in reels:
        hook_type = hooks.tag_hook_type(reel.caption or reel.transcript)
        if hook_type:
            by_hook[hook_type].append(reel)

    ranked = []
    for hook_type, group in by_hook.items():
        rates = [r.engagement_rate for r in group if r.engagement_rate is not None]
        if not rates:
            continue
        ranked.append(
            {
                "hook_type": hook_type,
                "avg_engagement_rate": statistics.mean(rates),
                "reel_count": len(group),
            }
        )
    ranked.sort(key=lambda h: h["avg_engagement_rate"], reverse=True)
    return ranked


def _rank_formats(reels: list[ReelForDNA]) -> list[dict]:
    by_format: dict[str, list[ReelForDNA]] = defaultdict(list)
    for reel in reels:
        format_tag = formats.tag_format(
            media_product_type=reel.media_product_type,
            duration_seconds=reel.duration_seconds,
            caption=reel.caption,
        )
        by_format[format_tag].append(reel)

    ranked = []
    for format_tag, group in by_format.items():
        rates = [r.engagement_rate for r in group if r.engagement_rate is not None]
        if not rates:
            continue
        ranked.append(
            {
                "format": format_tag,
                "avg_engagement_rate": statistics.mean(rates),
                "reel_count": len(group),
            }
        )
    ranked.sort(key=lambda f: f["avg_engagement_rate"], reverse=True)
    return ranked


def _typical_length_range(reels: list[ReelForDNA]) -> tuple[float | None, float | None]:
    scored = [r for r in reels if r.duration_seconds is not None and r.engagement_rate is not None]
    if not scored:
        return None, None

    threshold = statistics.quantiles(
        [r.engagement_rate for r in scored], n=4, method="inclusive"
    )[-1] if len(scored) >= 2 else scored[0].engagement_rate
    top_performers = [r for r in scored if r.engagement_rate >= threshold]
    if not top_performers:
        return None, None

    durations = sorted(r.duration_seconds for r in top_performers)
    if len(durations) == 1:
        return durations[0], durations[0]

    q = statistics.quantiles(durations, n=4, method="inclusive")
    return q[0], q[-1]


def _recent_fatigue_notes(
    reels: list[ReelForDNA],
    cluster_map: dict[str, int],
    labels: dict[int, str],
    *,
    window: int,
) -> dict:
    recent = sorted(reels, key=lambda r: r.posted_at, reverse=True)[:window]
    if not recent:
        return {"window_size": 0, "topics": []}

    weight_by_label: dict[str, float] = defaultdict(float)
    count_by_label: dict[str, int] = defaultdict(int)
    total_weight = 0.0
    for rank, reel in enumerate(recent):
        cluster_id = cluster_map.get(reel.reel_id)
        label = (
            labels.get(cluster_id, "uncategorized") if cluster_id is not None else "uncategorized"
        )
        weight = FATIGUE_DECAY**rank
        weight_by_label[label] += weight
        count_by_label[label] += 1
        total_weight += weight

    entries = [
        {
            "label": label,
            "weight": weight / total_weight if total_weight else 0.0,
            "reel_count": count_by_label[label],
            "overrepresented": (weight / total_weight if total_weight else 0.0)
            > FATIGUE_OVERREPRESENTED_THRESHOLD,
        }
        for label, weight in weight_by_label.items()
    ]
    entries.sort(key=lambda e: e["weight"], reverse=True)
    return {"window_size": len(recent), "topics": entries}


def compute_dna(
    reels: list[ReelForDNA],
    *,
    primary_kpi: str,
    early_profile_threshold: int,
    recent_fatigue_window: int,
    computed_at: datetime | None = None,
) -> dict:
    now = computed_at or datetime.now(UTC)
    in_scope = [r for r in reels if r.posted_at <= now]

    if not in_scope:
        return _empty_dna(primary_kpi=primary_kpi)

    cluster_map, labels = _cluster_topics(in_scope)
    ranked_clusters = _rank_topic_clusters(in_scope, cluster_map, labels)
    winning_topics, weak_topics = _split_winning_and_weak(ranked_clusters)
    length_min, length_max = _typical_length_range(in_scope)

    return {
        "winning_topics": winning_topics,
        "weak_topics": weak_topics,
        "winning_hooks": _rank_hooks(in_scope),
        "typical_length_min_seconds": length_min,
        "typical_length_max_seconds": length_max,
        "strong_formats": _rank_formats(in_scope),
        "primary_kpi": primary_kpi,
        "recent_fatigue_notes": _recent_fatigue_notes(
            in_scope, cluster_map, labels, window=recent_fatigue_window
        ),
        "early_profile": len(in_scope) < early_profile_threshold,
    }
