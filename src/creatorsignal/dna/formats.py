"""Rule-based format tagging, metadata-only. Genuine format classification (talking
head vs. greenscreen vs. b-roll) needs visual/audio content analysis, which Phase 1
has no pipeline for — transcript is explicitly nullable/'for future use', and there's
no CV/ASR step anywhere in Build Doc 1. This output is deliberately coarse and should
be treated as a known gap, not presented as reliable (see Build Doc 1 plan §6)."""

import re

_TUTORIAL_MARKERS = re.compile(r"\btutorial\b|\bstep\s+\d+\b|\bhow to\b", re.IGNORECASE)

UNKNOWN_DURATION = "unknown_duration"
NON_REEL = "non_reel"
TUTORIAL_STYLE = "tutorial_style"
SHORT_FORM = "short_form_quick_hit"  # <=15s
STANDARD = "standard"  # 15-30s
EXTENDED = "extended"  # 30-60s
LONG_FORM = "long_form"  # >60s


def tag_format(
    *, media_product_type: str | None, duration_seconds: float | None, caption: str | None
) -> str:
    if media_product_type != "REELS":
        return NON_REEL
    if caption and _TUTORIAL_MARKERS.search(caption):
        return TUTORIAL_STYLE
    if duration_seconds is None:
        return UNKNOWN_DURATION
    if duration_seconds <= 15:
        return SHORT_FORM
    if duration_seconds <= 30:
        return STANDARD
    if duration_seconds <= 60:
        return EXTENDED
    return LONG_FORM
