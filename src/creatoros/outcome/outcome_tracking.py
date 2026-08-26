"""Automated outcome tracking (Build Doc 3 §3, B16) — both halves are automatic:
performance numbers via the same Graph API connection (Build Doc 1's sync job),
and topic-match scoring via embedding similarity against the original
recommendation. No manual link-pasting, no screenshots, anywhere.

Matching model: the oldest completed recommendation without a linked outcome is
presumed fulfilled by the creator's next-published Reel after it. The spec
describes this as "the original recommendation" (singular) with no multi-
candidate disambiguation scheme, so a real creator publishing one Reel per cycle
maps naturally to first-unlinked-recommendation -> first-new-reel-after-it.
topic_match_score is a similarity signal for later evaluation, not the matching
key itself.
"""

import uuid

from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from creatoros.db.models import Creator, Outcome, Recommendation, Reel
from creatoros.dna.job import compute_and_store_dna
from creatoros.dna.metrics import compute_engagement_rate
from creatoros.embeddings.qdrant_client import cosine_similarity
from creatoros.embeddings.voyage_client import embed_text
from creatoros.instagram.repository import get_latest_insight
from creatoros.instagram.sync import sync_creator_history
from creatoros.utils.logging import get_logger

logger = get_logger(__name__)


def _remap_cosine_to_unit(score: float) -> float:
    return max(0.0, min(1.0, (score + 1.0) / 2.0))


def _oldest_unlinked_recommendation(
    session: Session, creator_id: uuid.UUID
) -> Recommendation | None:
    linked_ids = select(Outcome.recommendation_id)
    return (
        session.query(Recommendation)
        .filter(
            Recommendation.creator_id == creator_id,
            Recommendation.status == "completed",
            Recommendation.id.notin_(linked_ids),
        )
        .order_by(Recommendation.created_at.asc())
        .first()
    )


def _earliest_reel_after(session: Session, creator_id: uuid.UUID, after) -> Reel | None:
    linked_reel_ids = select(Outcome.reel_id)
    return (
        session.query(Reel)
        .filter(
            Reel.creator_id == creator_id,
            Reel.posted_at > after,
            Reel.id.notin_(linked_reel_ids),
        )
        .order_by(Reel.posted_at.asc())
        .first()
    )


def _topic_match_score(recommendation: Recommendation, reel: Reel) -> float | None:
    reel_text = " ".join(t for t in (reel.caption, reel.transcript) if t)
    if not reel_text or not recommendation.topic:
        return None
    recommendation_text = f"{recommendation.topic} {recommendation.angle or ''}".strip()
    reel_vector = embed_text(reel_text, input_type="query")
    recommendation_vector = embed_text(recommendation_text, input_type="query")
    return _remap_cosine_to_unit(cosine_similarity(reel_vector, recommendation_vector))


def detect_and_record_outcome(session: Session, creator: Creator) -> Outcome | None:
    """Runs one outcome-detection pass for a single creator. Returns the new
    Outcome row if one was found and recorded, else None (nothing new to link
    yet — not an error)."""
    recommendation = _oldest_unlinked_recommendation(session, creator.id)
    if recommendation is None:
        return None

    reel = _earliest_reel_after(session, creator.id, recommendation.created_at)
    if reel is None:
        return None

    insight = get_latest_insight(session, reel.id)
    actual_engagement_rate = (
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

    outcome = Outcome(
        recommendation_id=recommendation.id,
        reel_id=reel.id,
        topic_match_score=_topic_match_score(recommendation, reel),
        actual_engagement_rate=actual_engagement_rate,
        predicted_engagement=recommendation.expected_engagement_prediction,
        selection_type=recommendation.selection_type,
    )
    session.add(outcome)
    session.commit()
    session.refresh(outcome)
    logger.info(
        "Recorded outcome for recommendation %s: reel=%s topic_match=%s actual_engagement=%s",
        recommendation.id,
        reel.id,
        outcome.topic_match_score,
        outcome.actual_engagement_rate,
    )
    return outcome


def run_outcome_tracking_for_creator(
    session: Session, qdrant: QdrantClient, creator: Creator
) -> Outcome | None:
    """Full pass: sync fresh Instagram data (so any newly published Reel is in
    Postgres before we look for it), detect + record an outcome if one's ready,
    and recompute Creator DNA if a new outcome landed (B16 step 3)."""
    sync_creator_history(session, creator)
    outcome = detect_and_record_outcome(session, creator)
    if outcome is not None:
        compute_and_store_dna(session, qdrant, creator)
    return outcome
