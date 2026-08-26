import pytest

from creatoros.dna.hooks import UNKNOWN, tag_hook_type


@pytest.mark.parametrize(
    "text,expected",
    [
        ("POV: you just found the best AI tool", "pov"),
        ("3 ways to grow your startup in 2026", "listicle"),
        ("If you're still doing this manually, stop", "direct_callout"),
        ("I used to think AI agents were hype", "story_relatable"),
        ("Unpopular opinion: most SaaS founders are wrong about pricing", "contrarian"),
        ("90% of founders get this wrong", "stat_shock"),
        ("Why is nobody talking about this?", "question"),
        ("Just a regular caption with no hook pattern.", UNKNOWN),
    ],
)
def test_tag_hook_type_matches_expected_pattern(text, expected):
    assert tag_hook_type(text) == expected


def test_tag_hook_type_none_for_missing_text():
    assert tag_hook_type(None) is None
    assert tag_hook_type("") is None
    assert tag_hook_type("   ") is None


def test_tag_hook_type_prioritizes_specific_patterns_over_bare_question_mark():
    # Ends in '?' but should match the more specific listicle pattern first.
    text = "3 ways to grow your audience — which one works for you?"
    assert tag_hook_type(text) == "listicle"
