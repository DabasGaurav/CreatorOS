"""Structured-output schemas for the Market Researcher agent (B7 step 2) — the LLM
must fill these on every iteration; evidence sufficiency is a detectable state,
never inferred from freeform text."""

from typing import Literal

from pydantic import BaseModel, Field

SourceName = Literal["youtube", "reddit", "trends"]


class ResearchStep(BaseModel):
    """One agent turn: assess whether evidence gathered so far is sufficient, and
    if not, decide the next source + query to try. `next_source`/`next_query` are
    required (not Optional) even when sufficient=True, since Pydantic structured
    outputs need a fixed schema — the caller ignores them when sufficient."""

    sufficient: bool
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    next_source: SourceName
    next_query: str


class SourceObservation(BaseModel):
    """One completed source call, kept in the running history the LLM sees on
    each subsequent iteration."""

    source: SourceName
    query: str
    raw_result_summary: str
    succeeded: bool


class ResearchEvidence(BaseModel):
    """The Market Researcher's final structured output — source, timestamp,
    signal, interpretation, per B7 step 8."""

    niche: str
    objective: str
    observations: list[SourceObservation]
    final_reasoning: str
    confidence: float = Field(ge=0, le=1)
    exhausted_without_sufficient_evidence: bool
