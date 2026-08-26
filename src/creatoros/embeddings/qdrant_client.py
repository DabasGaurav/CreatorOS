"""Qdrant is retrieval infrastructure, not the recommendation model itself — similarity
scores become ranking features consumed later (Build Doc 2). This module owns the
`reels` collection and the two query functions CreatorFit/PersonalNovelty.

Point ID = reels.id (the Postgres UUID) directly, so "one point per Reel" is a
trivial count comparison. embedding_model_version is stamped on every point and
filtered on every query — never compared across versions (see Settings.embedding_model_version).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from creatoros.config import get_settings
from creatoros.embeddings.voyage_client import embed_text

# Voyage's cosine similarity is already in [-1, 1]; remap to [0, 1] so it composes
# cleanly with the other [0, 1]-scaled ranking factors in Build Doc 2's CompositeScore.
_TOP_QUARTILE = 0.75


def get_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def get_in_memory_client() -> QdrantClient:
    """Qdrant's own bundled in-memory test mode — used to unit-test collection
    setup and both query functions' math before a real Cloud cluster exists."""
    return QdrantClient(location=":memory:")


def ensure_collection(
    client: QdrantClient, *, vector_size: int, collection_name: str | None = None
) -> None:
    name = collection_name or get_settings().qdrant_collection
    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        return

    client.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
    )
    client.create_payload_index(name, "creator_id", field_schema=qm.PayloadSchemaType.KEYWORD)
    client.create_payload_index(
        name, "embedding_model_version", field_schema=qm.PayloadSchemaType.KEYWORD
    )
    client.create_payload_index(name, "posted_at_ts", field_schema=qm.PayloadSchemaType.FLOAT)
    client.create_payload_index(name, "engagement_rate", field_schema=qm.PayloadSchemaType.FLOAT)


def upsert_reel_point(
    client: QdrantClient,
    *,
    reel_id: uuid.UUID,
    creator_id: uuid.UUID,
    posted_at: datetime,
    vector: list[float],
    engagement_rate: float | None,
    topic_cluster: str | None = None,
    collection_name: str | None = None,
) -> None:
    name = collection_name or get_settings().qdrant_collection
    payload = {
        "creator_id": str(creator_id),
        "reel_id": str(reel_id),
        "posted_at": posted_at.isoformat(),
        "posted_at_ts": posted_at.timestamp(),
        "topic_cluster": topic_cluster,
        "performance_summary": {"engagement_rate": engagement_rate},
        "engagement_rate": engagement_rate,
        "embedding_model_version": get_settings().embedding_model_version,
    }
    client.upsert(
        collection_name=name,
        points=[qm.PointStruct(id=str(reel_id), vector=vector, payload=payload)],
    )


@dataclass
class CreatorPoint:
    reel_id: str
    vector: list[float]
    posted_at_ts: float
    engagement_rate: float | None


def fetch_creator_points(
    client: QdrantClient, *, creator_id: uuid.UUID, collection_name: str | None = None
) -> list[CreatorPoint]:
    """All of one creator's points at the current embedding_model_version, with
    vectors — small N at this project's scale, so filtering/scoring happens in
    Python rather than pushing every variant into a Qdrant filter expression."""
    name = collection_name or get_settings().qdrant_collection
    settings = get_settings()
    scroll_filter = qm.Filter(
        must=[
            qm.FieldCondition(key="creator_id", match=qm.MatchValue(value=str(creator_id))),
            qm.FieldCondition(
                key="embedding_model_version",
                match=qm.MatchValue(value=settings.embedding_model_version),
            ),
        ]
    )
    points: list[CreatorPoint] = []
    offset = None
    while True:
        records, offset = client.scroll(
            collection_name=name,
            scroll_filter=scroll_filter,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        for record in records:
            payload = record.payload or {}
            points.append(
                CreatorPoint(
                    reel_id=payload.get("reel_id", str(record.id)),
                    vector=record.vector,
                    posted_at_ts=payload.get("posted_at_ts", 0.0),
                    engagement_rate=payload.get("engagement_rate"),
                )
            )
        if offset is None:
            break
    return points


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _remap_to_unit_interval(cosine_score: float) -> float:
    return max(0.0, min(1.0, (cosine_score + 1.0) / 2.0))


def creator_fit(
    client: QdrantClient,
    *,
    candidate_text: str,
    creator_id: uuid.UUID,
    collection_name: str | None = None,
) -> float:
    """Match to what historically works for this creator: cosine similarity against
    the creator's own top-quartile-by-engagement Reels. Returns [0, 1]; 0.0 if the
    creator has no scored history yet (cold start — Build Doc 2 blends this with a
    category prior, not this function's job)."""
    points = fetch_creator_points(client, creator_id=creator_id, collection_name=collection_name)
    scored = [p for p in points if p.engagement_rate is not None]
    if not scored:
        return 0.0

    threshold = float(np.quantile([p.engagement_rate for p in scored], _TOP_QUARTILE))
    top_performers = [p for p in scored if p.engagement_rate >= threshold]
    if not top_performers:
        return 0.0

    candidate_vector = embed_text(candidate_text, input_type="query")
    best = max(cosine_similarity(candidate_vector, p.vector) for p in top_performers)
    return _remap_to_unit_interval(best)


def personal_novelty(
    client: QdrantClient,
    *,
    candidate_text: str,
    creator_id: uuid.UUID,
    window: int | None = None,
    collection_name: str | None = None,
) -> float:
    """Avoids over-repetition: 1 - max similarity against the creator's most recent
    N Reels (raw cosine, not remapped — unlike CreatorFit's [0,1] score, this is
    `1 - max_similarity` per spec, then clamped). High similarity to something just
    posted = low novelty. Returns [0, 1]; 1.0 (maximally novel) with no recent history."""
    settings = get_settings()
    n = window or settings.personal_novelty_window
    points = fetch_creator_points(client, creator_id=creator_id, collection_name=collection_name)
    if not points:
        return 1.0

    recent = sorted(points, key=lambda p: p.posted_at_ts, reverse=True)[:n]
    candidate_vector = embed_text(candidate_text, input_type="query")
    max_similarity = max(cosine_similarity(candidate_vector, p.vector) for p in recent)
    novelty = 1.0 - max_similarity
    return max(0.0, min(1.0, novelty))
