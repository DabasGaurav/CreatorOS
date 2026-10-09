"""Rule-based hook-type tagging. The spec allows hook-tagging to be 'rule-based or
LLM-assisted' but Build Doc 1's own hard rule is 'no LLM pipeline' — resolved in
favor of the hard rule (see Build Doc 1 plan §7). LLM-assisted tagging is deferred
to a later phase, once an LLM reasoning layer legitimately exists in the architecture.

Ordered most-specific-first, since many captions end in a question mark regardless
of their actual hook style — a bare '?' match would otherwise swallow everything.
"""

import re

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("pov", re.compile(r"^\s*pov[:\s]", re.IGNORECASE)),
    (
        "listicle",
        re.compile(
            r"^\s*\d+\s+(ways|reasons|tips|things|mistakes|signs|steps|lessons)\b",
            re.IGNORECASE,
        ),
    ),
    ("direct_callout", re.compile(r"^\s*if you\b", re.IGNORECASE)),
    ("story_relatable", re.compile(r"^\s*i (used to|remember|thought|was)\b", re.IGNORECASE)),
    (
        "contrarian",
        re.compile(
            r"\bunpopular opinion\b|\beveryone thinks\b|\bactually,?\s+\w+\s+wrong\b",
            re.IGNORECASE,
        ),
    ),
    ("stat_shock", re.compile(r"\d+%|\bshocking\b|\bnobody tells you\b", re.IGNORECASE)),
    ("question", re.compile(r"\?")),
]

UNKNOWN = "other"


def tag_hook_type(text: str | None) -> str | None:
    """Returns a hook-type tag, `UNKNOWN` if text exists but matches no known
    pattern, or None if there's no text (caption and transcript both missing)."""
    if not text or not text.strip():
        return None
    for name, pattern in _PATTERNS:
        if pattern.search(text):
            return name
    return UNKNOWN
