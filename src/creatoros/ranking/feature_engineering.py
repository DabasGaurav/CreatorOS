"""Builds the Expected Engagement model's feature vector from real signals already
computed elsewhere — the four ranking factors (B8) plus posting-time and
categorical hook/format codes reused from Build Doc 1's taxonomies (dna/hooks.py,
dna/formats.py), so the encoding stays consistent with what Creator DNA already
tags on historical reels.
"""

from datetime import datetime

from creatoros.dna.formats import (
    EXTENDED,
    LONG_FORM,
    NON_REEL,
    SHORT_FORM,
    STANDARD,
    TUTORIAL_STYLE,
    UNKNOWN_DURATION,
)
from creatoros.dna.hooks import UNKNOWN as UNKNOWN_HOOK

# Fixed, stable ordinal encodings — order doesn't matter for LightGBM's tree
# splits, but must stay stable across training/prediction calls.
_HOOK_TYPES = [
    "pov",
    "listicle",
    "direct_callout",
    "story_relatable",
    "contrarian",
    "stat_shock",
    "question",
    UNKNOWN_HOOK,
]
_FORMAT_TAGS = [
    SHORT_FORM,
    STANDARD,
    EXTENDED,
    LONG_FORM,
    TUTORIAL_STYLE,
    UNKNOWN_DURATION,
    NON_REEL,
]


def encode_hook_type(hook_type: str | None) -> int:
    if hook_type in _HOOK_TYPES:
        return _HOOK_TYPES.index(hook_type)
    return len(_HOOK_TYPES)  # unseen value gets its own code, not silently dropped


def encode_format(format_tag: str | None) -> int:
    if format_tag in _FORMAT_TAGS:
        return _FORMAT_TAGS.index(format_tag)
    return len(_FORMAT_TAGS)


def build_feature_dict(
    *,
    creator_fit: float,
    audience_demand: float,
    trend_momentum: float,
    novelty: float,
    hook_type: str | None,
    format_tag: str | None,
    posting_time: datetime,
) -> dict:
    return {
        "creator_fit": creator_fit,
        "audience_demand": audience_demand,
        "trend_momentum": trend_momentum,
        "novelty": novelty,
        "posting_hour": posting_time.hour,
        "posting_weekday": posting_time.weekday(),
        "hook_type_code": encode_hook_type(hook_type),
        "format_code": encode_format(format_tag),
    }
