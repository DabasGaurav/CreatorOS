"""On each new Reel import, compute its embedding and upsert into Qdrant.
Run after Instagram sync (Build Doc 1, §1.2 step 5) populates reels/reel_insights."""

import uuid

from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from creatorsignal.db.models import Reel
from creatorsignal.dna.metrics import compute_engagement_rate
from creatorsignal.embeddings.qdrant_client import upsert_reel_point
from creatorsignal.embeddings.voyage_client import build_reel_embedding_text, embed_text
from creatorsignal.instagram.repository import get_latest_insight
from creatorsignal.utils.logging import get_logger

logger = get_logger(__name__)


def embed_and_upsert_reel(session: Session, qdrant: QdrantClient, reel: Reel) -> None:
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

    text = build_reel_embedding_text(caption=reel.caption, transcript=reel.transcript)
    if not text:
        logger.warning("Reel %s has no caption or transcript — skipping embedding", reel.id)
        return

    vector = embed_text(text)
    upsert_reel_point(
        qdrant,
        reel_id=reel.id,
        creator_id=reel.creator_id,
        posted_at=reel.posted_at,
        vector=vector,
        engagement_rate=engagement_rate,
    )


def embed_and_upsert_all_reels_for_creator(
    session: Session, qdrant: QdrantClient, creator_id: uuid.UUID
) -> int:
    reels = session.query(Reel).filter(Reel.creator_id == creator_id).all()
    count = 0
    for reel in reels:
        embed_and_upsert_reel(session, qdrant, reel)
        count += 1
    logger.info("Embedded %d reels for creator %s", count, creator_id)
    return count
