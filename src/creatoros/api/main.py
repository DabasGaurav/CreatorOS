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
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from creatoros.auth.magic_link import request_magic_link, verify_magic_link_token
from creatoros.db.base import get_session
from creatoros.db.models import Creator, CreatorDNA, Outcome, Recommendation
from creatoros.embeddings.qdrant_client import get_client
from creatoros.graph.pipeline import build_pipeline
from creatoros.utils.logging import get_logger

logger = get_logger(__name__)
app = FastAPI(title="CreatorOS Recommendation Engine")

# Beta scale — the frontend runs on a different origin/port than this API.
# Locked to localhost dev origins now; tighten to the real deployed frontend
# origin once Build Doc 3's web app is deployed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Maps LangGraph node names to the spec's UI-facing loading-state vocabulary
# (C4: "research -> candidates -> ranked -> selected -> written"). baselines
# and rerank don't get their own UI stage — they complete within "ranked" and
# "selected" respectively from the creator's point of view.
_NODE_TO_STAGE = {
    "research": "research",
    "opportunity": "candidates",
    "ranking": "ranked",
    "baselines": "ranked",
    "explore_exploit": "selected",
    "rerank": "selected",
    "content": "written",
}


class RequestMagicLinkRequest(BaseModel):
    email: str


class VerifyMagicLinkRequest(BaseModel):
    token: str


class VerifyMagicLinkResponse(BaseModel):
    session_token: str
    creator_id: uuid.UUID


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

        # Stream rather than invoke so current_stage can be updated as each real
        # node completes (C4: a progressively filling frame outline, not a
        # spinner) — genuine progress, not a simulated animation.
        result: dict = {}
        for step in pipeline.stream(
            {
                "creator_id": str(creator_id),
                "request_id": str(recommendation_id),
                "niche": creator.niche,
                "objective": objective,
                "creator_dna": creator_dna,
            },
            stream_mode="updates",
        ):
            for node_name, partial_state in step.items():
                result.update(partial_state)
                stage = _NODE_TO_STAGE.get(node_name)
                if stage:
                    row.current_stage = stage
                    session.commit()

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
    # Every endpoint here must close its session on every exit path, including
    # raised HTTPExceptions — a live run showed the two GET endpoints leaking a
    # connection per request with no close() at all. At a 2s frontend poll
    # interval this exhausted the pool (5 + 10 overflow) within minutes and
    # starved the background pipeline task of a connection, which looked like
    # the pipeline being "stuck" but was actually connection-pool exhaustion.
    session = get_session()
    try:
        creator = session.get(Creator, request.creator_id)
        if creator is None:
            raise HTTPException(status_code=404, detail="Creator not found")

        row = Recommendation(creator_id=request.creator_id, status="pending")
        session.add(row)
        session.commit()
        session.refresh(row)
        recommendation_id = row.id
    finally:
        session.close()

    background_tasks.add_task(
        _run_pipeline_and_store, recommendation_id, request.creator_id, request.objective
    )
    return CreateRecommendationResponse(request_id=recommendation_id, status="pending")


@app.post("/auth/request-link")
def request_link(request: RequestMagicLinkRequest) -> dict:
    session = get_session()
    try:
        # Always the same response regardless of whether the email matched a
        # creator — don't let this endpoint reveal which emails are registered.
        request_magic_link(session, request.email)
        return {"detail": "If that email is registered, a sign-in link has been sent."}
    finally:
        session.close()


@app.post("/auth/verify", response_model=VerifyMagicLinkResponse)
def verify_link(request: VerifyMagicLinkRequest) -> VerifyMagicLinkResponse:
    session = get_session()
    try:
        result = verify_magic_link_token(session, request.token)
        if result is None:
            raise HTTPException(status_code=400, detail="Link is invalid, expired, or already used")
        return VerifyMagicLinkResponse(session_token=result.token, creator_id=result.creator_id)
    finally:
        session.close()


@app.get("/creators/{creator_id}")
def get_creator(creator_id: uuid.UUID) -> dict:
    session = get_session()
    try:
        creator = session.get(Creator, creator_id)
        if creator is None:
            raise HTTPException(status_code=404, detail="Creator not found")

        latest_dna = (
            session.query(CreatorDNA)
            .filter(CreatorDNA.creator_id == creator_id)
            .order_by(CreatorDNA.version.desc())
            .first()
        )
        return {
            "id": creator.id,
            "display_name": creator.display_name,
            "niche": creator.niche,
            "dna": _dna_to_dict(latest_dna) if latest_dna else None,
        }
    finally:
        session.close()


@app.get("/recommendations/{request_id}")
def get_recommendation(request_id: uuid.UUID) -> dict:
    session = get_session()
    try:
        row = session.get(Recommendation, request_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        outcome = (
            session.query(Outcome).filter(Outcome.recommendation_id == row.id).one_or_none()
        )

        return {
            "request_id": row.id,
            "status": row.status,
            "current_stage": row.current_stage,
            "error": row.error,
            "topic": row.topic,
            "angle": row.angle,
            "format": row.format,
            # SQLAlchemy Numeric columns serialize to JSON *strings* under
            # FastAPI's default encoder (Decimal-safe by default), unlike the
            # plain floats already inside evidence_breakdown's JSONB — an
            # inconsistent API contract that crashed the frontend's
            # score.toFixed(2) with "not a function" on a real live run.
            # Cast explicitly so every numeric field in this response is
            # actually a JSON number.
            "composite_score": (
                float(row.composite_score) if row.composite_score is not None else None
            ),
            "evidence_breakdown": row.evidence_breakdown,
            "selection_type": row.selection_type,
            "content_package": row.content_package,
            "baseline_picks": row.baseline_picks,
            "created_at": row.created_at,
            "completed_at": row.completed_at,
            "outcome": (
                {
                    "topic_match_score": (
                        float(outcome.topic_match_score)
                        if outcome.topic_match_score is not None
                        else None
                    ),
                    "actual_engagement_rate": (
                        float(outcome.actual_engagement_rate)
                        if outcome.actual_engagement_rate is not None
                        else None
                    ),
                    "predicted_engagement": (
                        float(outcome.predicted_engagement)
                        if outcome.predicted_engagement is not None
                        else None
                    ),
                    "detected_at": outcome.detected_at,
                }
                if outcome
                else None
            ),
        }
    finally:
        session.close()
