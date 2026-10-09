"""Content Generator (B7 section 7) — Sonnet. Produces hook, 30-35 second script,
storyboard, caption, CTA from the selected opportunity + evidence."""

import json

from creatorsignal.config import get_settings
from creatorsignal.content.schemas import ContentPackage
from creatorsignal.llm.client import current_date_context, parse_structured
from creatorsignal.opportunity.schemas import OpportunityCandidate
from creatorsignal.research.schemas import ResearchEvidence

_SYSTEM_PROMPT = """You are the Content Generator for CreatorSignal.ai. Given a selected \
Instagram Reels opportunity and the evidence behind it, write a complete, ready-\
to-shoot content package:

"hook": the first line/moment — must earn the next 3 seconds of attention.
"script": a 30-35 second spoken script matching the creator's typical successful \
length where Creator DNA data supports it.
"storyboard": a short shot-by-shot outline (what's on screen when).
"caption": the Instagram caption, written in a voice consistent with the \
creator's winning hooks/topics from their Creator DNA.
"cta": one specific call to action tied to the content, not a generic \
"like and follow"."""


def generate_content_package(
    *,
    selected_candidate: OpportunityCandidate,
    evidence: ResearchEvidence,
    creator_dna: dict,
) -> ContentPackage:
    settings = get_settings()
    user_message = (
        f"{current_date_context()}\n\n"
        f"Selected recommendation:\n{selected_candidate.model_dump_json(indent=2)}\n\n"
        f"Research evidence:\n{evidence.model_dump_json(indent=2)}\n\n"
        f"Creator DNA:\n{json.dumps(creator_dna, indent=2, default=str)}"
    )
    return parse_structured(
        model=settings.model_sonnet,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_format=ContentPackage,
        max_tokens=4096,
    )
