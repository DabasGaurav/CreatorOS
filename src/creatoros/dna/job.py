"""Thin DB/Qdrant wrapper around the pure compute_dna() function — assembles each
reel's engagement rate (Postgres) and embedding (Qdrant) into ReelForDNA, runs the
aggregation, and inserts a new versioned creator_dna row (never overwrites)."""

import uuid

from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from creatoros.config import get_settings
from creatoros.db.models import Creator, CreatorDNA, Reel
from creatoros.dna.aggregate import ReelForDNA, compute_dna
from creatoros.dna.metrics import compute_engagement_rate
from creatoros.embeddings.qdrant_client import fetch_creator_points
from creatoros.instagram.repository import get_latest_insight
from creatoros.utils.logging import get_logger

logger = get_logger(__name__)


def _build_reels_for_dna(
    session: Session, qdrant: QdrantClient, creator_id: uuid.UUID
) -> list[ReelForDNA]:
    reels = session.query(Reel).filter(Reel.creator_id == creator_id).all()
    points_by_reel_id = {
        p.reel_id: p for p in fetch_creator_points(qdrant, creator_id=creator_id)
    }

    result = []
    for reel in reels:
        insight = get_latest_insight(session, reel.id)
        engagement_rate = (
            compute_engagement_rate(
                likes=insight.likes,
                comments=insight.comments,
                shares=insight.shares,
                saves=insight.saves,
                reach=insight.reach,
            )
            if insight
            else None
        )
        point = points_by_reel_id.get(str(reel.id))
        result.append(
            ReelForDNA(
                reel_id=str(reel.id),
                posted_at=reel.posted_at,
                caption=reel.caption,
                transcript=reel.transcript,
                duration_seconds=(
                    float(reel.duration_seconds) if reel.duration_seconds is not None else None
                ),
                media_product_type=reel.media_product_type,
                embedding=point.vector if point else None,
                engagement_rate=engagement_rate,
            )
        )
    return result


def _next_version(session: Session, creator_id: uuid.UUID) -> int:
    existing = session.query(CreatorDNA.version).filter(CreatorDNA.creator_id == creator_id).all()
    versions = [v[0] for v in existing]
    return max(versions) + 1 if versions else 1


def compute_and_store_dna(session: Session, qdrant: QdrantClient, creator: Creator) -> CreatorDNA:
    settings = get_settings()
    reels_for_dna = _build_reels_for_dna(session, qdrant, creator.id)
    primary_kpi = creator.primary_kpi_goal or settings.creator_dna_default_primary_kpi

    dna = compute_dna(
        reels_for_dna,
        primary_kpi=primary_kpi,
        early_profile_threshold=settings.creator_dna_early_profile_threshold,
        recent_fatigue_window=settings.creator_dna_recent_fatigue_window,
    )

    row = CreatorDNA(
        creator_id=creator.id,
        version=_next_version(session, creator.id),
        winning_topics=dna["winning_topics"],
        weak_topics=dna["weak_topics"],
        winning_hooks=dna["winning_hooks"],
        typical_length_min_seconds=dna["typical_length_min_seconds"],
        typical_length_max_seconds=dna["typical_length_max_seconds"],
        strong_formats=dna["strong_formats"],
        primary_kpi=dna["primary_kpi"],
        recent_fatigue_notes=dna["recent_fatigue_notes"],
        early_profile=dna["early_profile"],
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    logger.info(
        "Computed Creator DNA v%d for creator %s (early_profile=%s, %d reels)",
        row.version,
        creator.instagram_user_id,
        row.early_profile,
        len(reels_for_dna),
    )
    return row
