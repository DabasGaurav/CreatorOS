"""The Market Researcher agent (B7) — the one genuinely agentic node in the
pipeline. A fixed "always call Trends, then Reddit, then YouTube" sequence is not
agentic; this makes a runtime decision every iteration: assess whether evidence
gathered so far is sufficient, and if not, choose which source to try next and
construct a query for it. The iteration cap is enforced in code (not just
prompted) — a hard `for` loop bound, not a suggestion the LLM can ignore.

`call_step` is injectable so the loop-control logic (cap enforcement, fallback
triggering, source dispatch, cache use) is unit-testable without a live Anthropic
call; the default implementation is the real Haiku call.
"""

from collections.abc import Callable

from sqlalchemy.orm import Session

from creatoros.config import get_settings
from creatoros.llm.client import parse_structured
from creatoros.research.cache import get_cached, set_cached
from creatoros.research.reddit_client import RedditNotConfigured, search_posts
from creatoros.research.schemas import ResearchEvidence, ResearchStep, SourceObservation
from creatoros.research.trends_client import TrendsUnavailable, get_trend_data
from creatoros.research.youtube_client import YouTubeNotConfigured, search_videos
from creatoros.utils.logging import get_logger

logger = get_logger(__name__)

StepFn = Callable[[str, str, list[SourceObservation]], ResearchStep]

_SYSTEM_PROMPT = """You are the Market Researcher agent for CreatorOS, a decision \
tool for a single Instagram Reels creator. Your job: gather just enough evidence \
about current audience demand and trend momentum in the creator's niche to \
support one content recommendation — not exhaustive research.

On each turn: look at the evidence gathered so far. If it's sufficient to judge \
audience demand and trend momentum for a topic in this niche, say so (sufficient=true) \
and explain why in `reasoning`. If not, pick exactly ONE source — "youtube", \
"reddit", or "trends" — most likely to add real signal next, and write a specific \
search query for it. Prefer stopping early over exhaustive research; each \
additional call costs time and money for a real creator waiting on this."""


def _call_source(session: Session, source: str, query: str) -> SourceObservation:
    settings = get_settings()
    cached = get_cached(
        session, source=source, query=query, ttl_hours=settings.external_cache_ttl_hours
    )
    if cached is not None:
        return SourceObservation(
            source=source, query=query, raw_result_summary=cached["summary"], succeeded=True
        )

    try:
        if source == "youtube":
            raw = search_videos(query)
            total = raw.get("pageInfo", {}).get("totalResults", "unknown")
            summary = f"YouTube search for {query!r}: {total} total results"
        elif source == "reddit":
            posts = search_posts(query)
            total_score = sum(p["score"] for p in posts)
            summary = f"Reddit search for {query!r}: {len(posts)} posts, total score {total_score}"
        elif source == "trends":
            trend = get_trend_data(query)
            summary = (
                f"Google Trends for {query!r}: slope={trend['slope']:.2f}, "
                f"avg interest={trend['average_interest']:.1f} over {trend['data_points']} points"
            )
        else:
            raise ValueError(f"Unknown source: {source}")
    except (YouTubeNotConfigured, RedditNotConfigured, TrendsUnavailable) as exc:
        logger.warning("Source %s unavailable for query %r: %s", source, query, exc)
        return SourceObservation(
            source=source, query=query, raw_result_summary=f"unavailable: {exc}", succeeded=False
        )

    set_cached(session, source=source, query=query, result={"summary": summary})
    return SourceObservation(source=source, query=query, raw_result_summary=summary, succeeded=True)


def _default_call_step(
    niche: str, objective: str, observations: list[SourceObservation]
) -> ResearchStep:
    settings = get_settings()
    history_text = (
        "\n".join(f"- {o.source} (query={o.query!r}): {o.raw_result_summary}" for o in observations)
        or "(no evidence gathered yet)"
    )
    user_message = (
        f"Niche: {niche}\nObjective: {objective}\n\nEvidence gathered so far:\n{history_text}"
    )
    return parse_structured(
        model=settings.model_haiku,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_format=ResearchStep,
    )


def _fallback_evidence_summary(session: Session, niche: str) -> str:
    """On exhaustion, fall back to the most recent cached category-level snapshot
    rather than returning silently weak evidence (B7 step 8)."""
    for source in ("trends", "youtube", "reddit"):
        cached = get_cached(session, source=source, query=niche, ttl_hours=24 * 30)
        if cached is not None:
            return f"Fallback cached {source} snapshot for niche {niche!r}: {cached['summary']}"
    return f"No cached category-level data available for niche {niche!r} either."


def run_market_researcher(
    session: Session,
    *,
    niche: str,
    objective: str,
    max_iterations: int | None = None,
    call_step: StepFn | None = None,
) -> ResearchEvidence:
    settings = get_settings()
    max_iterations = max_iterations or settings.market_researcher_max_iterations
    call_step = call_step or _default_call_step

    observations: list[SourceObservation] = []
    for _iteration in range(max_iterations):
        step = call_step(niche, objective, observations)
        if step.sufficient:
            return ResearchEvidence(
                niche=niche,
                objective=objective,
                observations=observations,
                final_reasoning=step.reasoning,
                confidence=step.confidence,
                exhausted_without_sufficient_evidence=False,
            )
        observations.append(_call_source(session, step.next_source, step.next_query))

    fallback_summary = _fallback_evidence_summary(session, niche)
    logger.warning("Market Researcher exhausted %d iterations for niche %r", max_iterations, niche)
    return ResearchEvidence(
        niche=niche,
        objective=objective,
        observations=observations,
        final_reasoning=(
            f"Exhausted {max_iterations} iterations without sufficient evidence. {fallback_summary}"
        ),
        confidence=0.0,
        exhausted_without_sufficient_evidence=True,
    )
