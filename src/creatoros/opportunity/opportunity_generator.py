"""Opportunity Generator (B8) — one Haiku call over Creator DNA + research
evidence, constrained via structured output to 20-50 (topic, angle, format)
candidates. No ranking happens here — that's the deterministic layer next."""

import json

from creatoros.config import get_settings
from creatoros.llm.client import current_date_context, parse_structured
from creatoros.opportunity.schemas import OpportunityCandidate, OpportunitySet
from creatoros.research.schemas import ResearchEvidence

_SYSTEM_PROMPT = """You are the Opportunity Generator for CreatorOS. Given a \
creator's Creator DNA (their historical winning/weak topics, hooks, formats) and \
research evidence about their niche, generate a broad, diverse set of concrete \
content opportunities.

An opportunity is topic + angle + audience need + format + timing — never a bare \
topic. "AI agents" is too broad; "AI agents replacing junior developers — a \
talking-head Reel for an audience wondering if their entry-level job is at risk, \
timely now while the debate is trending" is an opportunity.

Generate a genuinely diverse set — different angles, formats, and levels of \
novelty — so the ranking layer downstream has real signal to differentiate \
between. Don't just produce 30 minor variations of the same idea."""


def generate_opportunities(
    *, creator_dna: dict, evidence: ResearchEvidence, niche: str
) -> list[OpportunityCandidate]:
    settings = get_settings()
    user_message = (
        f"{current_date_context()}\n\n"
        f"Niche: {niche}\n\n"
        f"Creator DNA:\n{json.dumps(creator_dna, indent=2, default=str)}\n\n"
        f"Research evidence:\n{evidence.model_dump_json(indent=2)}\n\n"
        f"Generate between {settings.opportunity_candidate_min} and "
        f"{settings.opportunity_candidate_max} distinct content opportunities."
    )
    result: OpportunitySet = parse_structured(
        model=settings.model_haiku,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_format=OpportunitySet,
        max_tokens=8000,
    )
    return result.candidates
