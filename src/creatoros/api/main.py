"""FastAPI endpoint (B3 step 3): POST /recommendations triggers a graph run and
returns a request_id; GET /recommendations/{id} polls status/result. This
on-demand trigger is the entire interaction model — no scheduler, no cron.

The graph run happens in a FastAPI BackgroundTask rather than blocking the POST
response — several sequential LLM calls (research iterations, opportunity
generation, rerank, content) can run well past a typical client HTTP timeout.
"""

import uuid
from datetime import UTC, datetime

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from creatoros.db.base import get_session
from creatoros.db.models import Creator, CreatorDNA, Recommendation
from creatoros.embeddings.qdrant_client import get_client
from creatoros.graph.pipeline import build_pipeline
from creatoros.utils.logging import get_logger

logger = get_logger(__name__)
app = FastAPI(title="CreatorOS Recommendation Engine")


class CreateRecommendationRequest(BaseModel):
    creator_id: uuid.UUID
    objective: str = "grow reach"


class CreateRecommendationResponse(BaseModel):
    request_id: uuid.UUID
    status: str


def _run_pipeline_and_store(
    recommendation_id: uuid.UUID, creator_id: uuid.UUID, objective: str
) -> None:
    session = get_session()
    try:
        row = session.get(Recommendation, recommendation_id)
        row.status = "running"
        session.commit()

        creator = session.get(Creator, creator_id)
        latest_dna = (
            session.query(CreatorDNA)
            .filter(CreatorDNA.creator_id == creator_id)
            .order_by(CreatorDNA.version.desc())
            .first()
        )
        creator_dna = _dna_to_dict(latest_dna) if latest_dna else {}

        qdrant = get_client()
        pipeline = build_pipeline(session, qdrant)
        result = pipeline.invoke(
            {
                "creator_id": str(creator_id),
                "request_id": str(recommendation_id),
                "niche": creator.niche,
                "objective": objective,
                "creator_dna": creator_dna,
            }
        )

        selection = result["selection"]
        row.topic = selection.get("topic")
        row.angle = selection.get("angle")
        row.format = selection.get("format")
        row.composite_score = selection.get("composite_score")
        row.evidence_breakdown = {
            "creator_fit": selection.get("creator_fit"),
            "audience_demand": selection.get("audience_demand"),
            "trend_momentum": selection.get("trend_momentum"),
            "novelty": selection.get("novelty"),
            "expected_engagement": selection.get("expected_engagement"),
            "why_now": selection.get("why_now"),
            "why_you": selection.get("why_you"),
        }
        row.selection_type = result["selection_type"]
        row.content_package = result["content_package"]
        row.baseline_picks = result.get("baseline_picks")
        row.expected_engagement_prediction = selection.get("expected_engagement")
        row.status = "completed"
        row.completed_at = datetime.now(UTC)
        session.commit()
    except Exception as exc:
        logger.exception("Recommendation run %s failed", recommendation_id)
        row = session.get(Recommendation, recommendation_id)
        if row:
            row.status = "failed"
            row.error = str(exc)
            session.commit()
    finally:
        session.close()


def _dna_to_dict(dna: CreatorDNA) -> dict:
    return {
        "winning_topics": dna.winning_topics,
        "weak_topics": dna.weak_topics,
        "winning_hooks": dna.winning_hooks,
        "typical_length_min_seconds": dna.typical_length_min_seconds,
        "typical_length_max_seconds": dna.typical_length_max_seconds,
        "strong_formats": dna.strong_formats,
        "primary_kpi": dna.primary_kpi,
        "recent_fatigue_notes": dna.recent_fatigue_notes,
        "early_profile": dna.early_profile,
    }


@app.post("/recommendations", response_model=CreateRecommendationResponse)
def create_recommendation(
    request: CreateRecommendationRequest, background_tasks: BackgroundTasks
) -> CreateRecommendationResponse:
    session = get_session()
    creator = session.get(Creator, request.creator_id)
    if creator is None:
        raise HTTPException(status_code=404, detail="Creator not found")

    row = Recommendation(creator_id=request.creator_id, status="pending")
    session.add(row)
    session.commit()
    session.refresh(row)
    recommendation_id = row.id
    session.close()

    background_tasks.add_task(
        _run_pipeline_and_store, recommendation_id, request.creator_id, request.objective
    )
    return CreateRecommendationResponse(request_id=recommendation_id, status="pending")


@app.get("/recommendations/{request_id}")
def get_recommendation(request_id: uuid.UUID) -> dict:
    session = get_session()
    row = session.get(Recommendation, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    return {
        "request_id": row.id,
        "status": row.status,
        "error": row.error,
        "topic": row.topic,
        "angle": row.angle,
        "format": row.format,
        "composite_score": row.composite_score,
        "evidence_breakdown": row.evidence_breakdown,
        "selection_type": row.selection_type,
        "content_package": row.content_package,
        "baseline_picks": row.baseline_picks,
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }
