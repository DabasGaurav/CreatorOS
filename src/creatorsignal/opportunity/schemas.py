"""An opportunity is topic + angle + audience need + format + timing (B8) — a bare
topic like 'AI agents' is too broad. Structured output bounds the candidate set to
20-50 (spec's range), so the Opportunity Generator can't silently return one
guess or a runaway list."""

from pydantic import BaseModel, Field


class OpportunityCandidate(BaseModel):
    topic: str
    angle: str
    audience_need: str
    format: str
    timing: str


class OpportunitySet(BaseModel):
    candidates: list[OpportunityCandidate] = Field(min_length=20, max_length=50)
