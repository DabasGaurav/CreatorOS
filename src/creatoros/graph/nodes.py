"""LangGraph node functions (B3 step 2). Each node factory closes over the DB
session and Qdrant client (not put in graph state — they aren't serializable),
returning a plain function of (state) -> partial state update, per LangGraph's
node contract.
"""

import uuid
from datetime import UTC, datetime

from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from creatoros.content.content_generator import generate_content_package
from creatoros.content.reranker import rerank_and_explain
from creatoros.content.schemas import ContentPackage
from creatoros.dna.hooks import tag_hook_type
from creatoros.embeddings.qdrant_client import creator_fit, personal_novelty
from creatoros.embeddings.voyage_client import embed_texts
from creatoros.evaluation import baselines
from creatoros.graph.state import GraphState
from creatoros.niche.repository import list_niche_signal
from creatoros.opportunity.opportunity_generator import generate_opportunities
from creatoros.opportunity.schemas import OpportunityCandidate
from creatoros.ranking.composite_score import FactorScores, composite_score, weights_from_settings
from creatoros.ranking.engagement_model import predict_expected_engagement
from creatoros.ranking.explore_exploit import select_recommendation
from creatoros.ranking.factors import audience_demand, niche_saturation, novelty, trend_momentum
from creatoros.ranking.feature_engineering import build_feature_dict
from creatoros.research.market_researcher import run_market_researcher
from creatoros.research.schemas import ResearchEvidence
from creatoros.utils.logging import get_logger

logger = get_logger(__name__)


def research_node_factory(session: Session):
    def research_node(state: GraphState) -> dict:
        evidence = run_market_researcher(
            session, niche=state["niche"], objective=state["objective"]
        )
        return {"evidence": evidence.model_dump()}

    return research_node


def opportunity_node_factory():
    def opportunity_node(state: GraphState) -> dict:
        evidence = ResearchEvidence(**state["evidence"])
        candidates = generate_opportunities(
            creator_dna=state["creator_dna"], evidence=evidence, niche=state["niche"]
        )
        return {"candidates": [c.model_dump() for c in candidates]}

    return opportunity_node


def _candidate_text(candidate: dict) -> str:
    return f"{candidate['topic']} — {candidate['angle']}"


def ranking_node_factory(session: Session, qdrant: QdrantClient):
    def ranking_node(state: GraphState) -> dict:
        creator_id = uuid.UUID(state["creator_id"])
        evidence = state.get("evidence") or {}
        # Evidence is gathered once per cycle at the niche level, not per candidate
        # (research runs before opportunity generation) — its confidence is used
        # as a shared proxy for AudienceDemand/TrendMomentum across all candidates
        # this cycle. A genuinely per-candidate market signal would need a second
        # research pass per candidate, out of scope for this build.
        evidence_confidence = evidence.get("confidence", 0.0)

        niche_rows = list_niche_signal(session, niche=state["niche"])
        niche_texts = [r.observed_topic for r in niche_rows]

        # Batch-embed once per cycle rather than per candidate per factor — a live
        # ranking run showed creator_fit/personal_novelty/niche_saturation each
        # separately re-embedding the same candidate text, multiplying Voyage
        # calls by 3x per candidate and blowing through the free-tier 3 RPM limit
        # on a real 20+ candidate batch.
        candidate_texts = [_candidate_text(c) for c in state["candidates"]]
        candidate_vectors = embed_texts(candidate_texts, input_type="query")
        niche_vectors = embed_texts(niche_texts, input_type="document") if niche_texts else []

        weights = weights_from_settings()
        ranked = []
        for candidate, vector in zip(state["candidates"], candidate_vectors, strict=True):
            fit = creator_fit(qdrant, candidate_vector=vector, creator_id=creator_id)
            p_novelty = personal_novelty(qdrant, candidate_vector=vector, creator_id=creator_id)
            saturation = niche_saturation(candidate_vector=vector, niche_vectors=niche_vectors)
            nov = novelty(personal_novelty=p_novelty, niche_saturation_score=saturation)
            demand = audience_demand(
                normalized_search_volume=evidence_confidence,
                community_engagement_score=evidence_confidence,
            )
            momentum = trend_momentum(
                trend_slope=evidence_confidence, discussion_velocity=evidence_confidence
            )

            # Cold-start (no per-creator LightGBM model trained yet in this build) —
            # predict_expected_engagement(None, ...) returns the configured neutral
            # prior regardless of the feature values, so a best-effort feature dict
            # is fine here even though duration is unknown (Build Doc 1 finding).
            features = build_feature_dict(
                creator_fit=fit,
                audience_demand=demand,
                trend_momentum=momentum,
                novelty=nov,
                hook_type=tag_hook_type(candidate.get("angle")),
                format_tag=None,
                posting_time=datetime.now(UTC),
            )
            expected_engagement = predict_expected_engagement(None, features)

            factors = FactorScores(
                creator_fit=fit,
                audience_demand=demand,
                trend_momentum=momentum,
                novelty=nov,
                expected_engagement=expected_engagement,
            )
            ranked.append(
                {
                    **candidate,
                    "creator_fit": fit,
                    "audience_demand": demand,
                    "trend_momentum": momentum,
                    "novelty": nov,
                    "expected_engagement": expected_engagement,
                    "composite_score": composite_score(factors, weights),
                }
            )
        ranked.sort(key=lambda c: c["composite_score"], reverse=True)
        return {"ranked": ranked}

    return ranking_node


def explore_exploit_node(state: GraphState) -> dict:
    selection, selection_type = select_recommendation(state["ranked"])
    return {"selection": selection, "selection_type": selection_type}


def rerank_node_factory():
    def rerank_node(state: GraphState) -> dict:
        evidence = ResearchEvidence(**state["evidence"])
        selected = OpportunityCandidate(**{
            k: v
            for k, v in state["selection"].items()
            if k in OpportunityCandidate.model_fields
        })
        narrative = rerank_and_explain(
            selected_candidate=selected, evidence=evidence, creator_dna=state["creator_dna"]
        )
        return {"selection": {**state["selection"], **narrative.model_dump()}}

    return rerank_node


def content_node_factory():
    def content_node(state: GraphState) -> dict:
        evidence = ResearchEvidence(**state["evidence"])
        selected = OpportunityCandidate(**{
            k: v
            for k, v in state["selection"].items()
            if k in OpportunityCandidate.model_fields
        })
        package: ContentPackage = generate_content_package(
            selected_candidate=selected, evidence=evidence, creator_dna=state["creator_dna"]
        )
        return {"content_package": package.model_dump(), "status": "completed"}

    return content_node


def baseline_node_factory():
    def baseline_node(state: GraphState) -> dict:
        candidates = state["ranked"]
        picks = {
            "trending_only": baselines.trending_only_baseline(candidates).get("topic"),
            "popularity_only": baselines.popularity_only_baseline(candidates).get("topic"),
            "random": baselines.random_baseline(candidates).get("topic"),
            "historical_top_topic": baselines.historical_top_topic_baseline(
                candidates,
                creator_dna_winning_topics=state["creator_dna"].get("winning_topics", []),
            ).get("topic"),
            "most_recent_successful_topic": baselines.most_recent_successful_topic_baseline(
                candidates,
                creator_dna_recent_fatigue_topics=state["creator_dna"]
                .get("recent_fatigue_notes", {})
                .get("topics", []),
            ).get("topic"),
        }
        return {"baseline_picks": picks}

    return baseline_node
