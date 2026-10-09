"""Shared LangGraph state schema (B3 step 1) — creator_id, request_id, evidence[],
candidates[], ranked[], selection, selection_type, content_package, status, wired
across every node from research through content generation."""

from typing import TypedDict


class GraphState(TypedDict, total=False):
    creator_id: str
    request_id: str
    niche: str
    objective: str
    creator_dna: dict

    evidence: dict | None
    candidates: list[dict]
    ranked: list[dict]
    selection: dict | None
    selection_type: str | None
    content_package: dict | None
    baseline_picks: dict | None

    status: str
    error: str | None
