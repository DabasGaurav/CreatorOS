"""LLM Reranker (B3/B7 section 7) — resolves a real ambiguity between two parts of
the spec: B3's component table describes this node as "reason over top candidates,
select final pick," but section 7's own text says it "takes the top-ranked
candidates (post explore/exploit selection)" — i.e. runs AFTER B11's deterministic
epsilon-greedy pick, not before it.

Resolution used here: epsilon-greedy selection (ranking/explore_exploit.py) is the
sole decider of *which* candidate gets recommended and its selection_type — this
keeps the 85/15 exploit/explore split (B11) meaningful and testable, which it
would not be if an LLM could silently override the algorithmic pick afterward.
The Reranker's job is narrower and still valuable: generate the evidence-grounded
"why now" / "why you" narrative for the already-selected candidate.

This resolution also defuses the spec's temperature=0-for-determinism requirement,
which is no longer satisfiable as written — current-generation Sonnet rejects the
temperature parameter outright (verified against live API documentation during
this build). Since selection itself is pure Python, not an LLM call, "the top-1
pick stays stable across runs" (B15's golden-set framing) is now guaranteed by
construction; the Reranker's only remaining nondeterminism is prose wording, which
the spec's own test guidance says not to assert on verbatim.
"""

import json

from creatoros.config import get_settings
from creatoros.content.schemas import RerankerOutput
from creatoros.llm.client import parse_structured
from creatoros.opportunity.schemas import OpportunityCandidate
from creatoros.research.schemas import ResearchEvidence

_SYSTEM_PROMPT = """You are the reasoning layer for CreatorOS's Evidence Receipt. \
You are given one already-selected content recommendation (selection is made by \
deterministic code, not you) plus the evidence and Creator DNA behind it. Write \
two short paragraphs a creator will actually read before publishing:

"why_now": why this topic, specifically now — grounded in the research evidence \
provided. Do not invent trend data that isn't in the evidence.

"why_you": why this fits this specific creator — grounded in their Creator DNA. \
Do not invent historical performance that isn't in the DNA provided.

Be concrete and specific, not generic filler. If the evidence is thin, say so \
plainly rather than overstating confidence — creators will lose trust in an \
Evidence Receipt that oversells weak evidence."""


def rerank_and_explain(
    *,
    selected_candidate: OpportunityCandidate,
    evidence: ResearchEvidence,
    creator_dna: dict,
) -> RerankerOutput:
    settings = get_settings()
    user_message = (
        f"Selected recommendation:\n{selected_candidate.model_dump_json(indent=2)}\n\n"
        f"Research evidence:\n{evidence.model_dump_json(indent=2)}\n\n"
        f"Creator DNA:\n{json.dumps(creator_dna, indent=2, default=str)}"
    )
    return parse_structured(
        model=settings.model_sonnet,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_format=RerankerOutput,
    )
