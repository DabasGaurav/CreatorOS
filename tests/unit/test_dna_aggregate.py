from datetime import UTC, datetime, timedelta

from creatorsignal.dna.aggregate import ReelForDNA, compute_dna

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _unit_vector(dim: int, index: int) -> list[float]:
    v = [0.0] * dim
    v[index] = 1.0
    return v


AI_TOOLS_EMBEDDING = _unit_vector(8, 0)
COOKING_EMBEDDING = _unit_vector(8, 5)


def _reel(
    reel_id: str,
    *,
    days_ago: int = 0,
    caption: str = "a generic caption",
    transcript: str | None = None,
    duration_seconds: float | None = 25.0,
    media_product_type: str = "REELS",
    embedding: list[float] | None = None,
    engagement_rate: float | None = 0.05,
) -> ReelForDNA:
    return ReelForDNA(
        reel_id=reel_id,
        posted_at=BASE_TIME - timedelta(days=days_ago),
        caption=caption,
        transcript=transcript,
        duration_seconds=duration_seconds,
        media_product_type=media_product_type,
        embedding=embedding,
        engagement_rate=engagement_rate,
    )


def _default_kwargs(**overrides):
    kwargs = dict(
        primary_kpi="reach",
        early_profile_threshold=15,
        recent_fatigue_window=10,
        computed_at=BASE_TIME,
    )
    kwargs.update(overrides)
    return kwargs


def test_compute_dna_identifies_winning_and_weak_topics():
    reels = [
        _reel(
            f"ai-{i}",
            days_ago=i,
            embedding=AI_TOOLS_EMBEDDING,
            engagement_rate=0.10 + (i % 3) * 0.01,
            caption="AI tools content",
        )
        for i in range(18)
    ] + [
        _reel(
            f"cooking-{i}",
            days_ago=i,
            embedding=COOKING_EMBEDDING,
            engagement_rate=0.01 + (i % 3) * 0.001,
            caption="cooking content",
        )
        for i in range(6)
    ]

    dna = compute_dna(reels, **_default_kwargs())

    assert len(dna["winning_topics"]) >= 1
    assert dna["winning_topics"][0]["avg_engagement_rate"] > 0.08
    assert len(dna["weak_topics"]) >= 1
    assert dna["weak_topics"][0]["avg_engagement_rate"] < 0.02
    # Winning must outrank weak.
    assert (
        dna["winning_topics"][0]["avg_engagement_rate"]
        > dna["weak_topics"][0]["avg_engagement_rate"]
    )


def test_compute_dna_identifies_winning_hooks():
    reels = (
        [
            _reel(
                f"pov-{i}",
                days_ago=i,
                embedding=AI_TOOLS_EMBEDDING,
                caption="POV: you just found the best AI tool for your startup",
                engagement_rate=0.15,
            )
            for i in range(5)
        ]
        + [
            _reel(
                f"listicle-{i}",
                days_ago=i,
                embedding=AI_TOOLS_EMBEDDING,
                caption="3 ways to use AI in your daily workflow",
                engagement_rate=0.09,
            )
            for i in range(5)
        ]
        + [
            _reel(
                f"plain-{i}",
                days_ago=i,
                embedding=AI_TOOLS_EMBEDDING,
                caption="Some thoughts on AI tools today",
                engagement_rate=0.04,
            )
            for i in range(5)
        ]
    )

    dna = compute_dna(reels, **_default_kwargs())

    winning_hooks = dna["winning_hooks"]
    assert winning_hooks[0]["hook_type"] == "pov"
    hook_order = [h["hook_type"] for h in winning_hooks]
    assert hook_order.index("pov") < hook_order.index("listicle")


def test_compute_dna_identifies_strong_formats():
    reels = [
        _reel(
            f"short-{i}",
            days_ago=i,
            embedding=AI_TOOLS_EMBEDDING,
            duration_seconds=10.0,
            engagement_rate=0.14,
            caption="a short punchy reel",
        )
        for i in range(5)
    ] + [
        _reel(
            f"long-{i}",
            days_ago=i,
            embedding=AI_TOOLS_EMBEDDING,
            duration_seconds=90.0,
            engagement_rate=0.03,
            caption="a long rambling reel",
        )
        for i in range(5)
    ]

    dna = compute_dna(reels, **_default_kwargs())

    strong_formats = dna["strong_formats"]
    assert strong_formats[0]["format"] == "short_form_quick_hit"


def test_compute_dna_typical_length_range_reflects_top_performers():
    # Top performers all 20-24s; everyone else is either much shorter or much longer.
    reels = [
        _reel(
            f"top-{i}",
            days_ago=i,
            embedding=AI_TOOLS_EMBEDDING,
            duration_seconds=20.0 + i,
            engagement_rate=0.20,
        )
        for i in range(4)
    ] + [
        _reel(
            f"low-{i}",
            days_ago=i,
            embedding=AI_TOOLS_EMBEDDING,
            duration_seconds=90.0,
            engagement_rate=0.01,
        )
        for i in range(12)
    ]

    dna = compute_dna(reels, **_default_kwargs())

    assert dna["typical_length_min_seconds"] is not None
    assert 18 <= dna["typical_length_min_seconds"] <= 25
    assert 18 <= dna["typical_length_max_seconds"] <= 25


def test_compute_dna_early_profile_flag_below_threshold():
    reels = [_reel(f"r{i}", embedding=AI_TOOLS_EMBEDDING) for i in range(14)]
    dna = compute_dna(reels, **_default_kwargs(early_profile_threshold=15))
    assert dna["early_profile"] is True


def test_compute_dna_early_profile_flag_at_threshold():
    reels = [_reel(f"r{i}", embedding=AI_TOOLS_EMBEDDING) for i in range(15)]
    dna = compute_dna(reels, **_default_kwargs(early_profile_threshold=15))
    assert dna["early_profile"] is False


def test_compute_dna_respects_leakage_discipline():
    past_reel = _reel("past", days_ago=1, embedding=AI_TOOLS_EMBEDDING, engagement_rate=0.05)
    future_reel = ReelForDNA(
        reel_id="future",
        posted_at=BASE_TIME + timedelta(days=5),
        caption="posted after computed_at",
        transcript=None,
        duration_seconds=20.0,
        media_product_type="REELS",
        embedding=AI_TOOLS_EMBEDDING,
        engagement_rate=0.99,
    )
    dna = compute_dna([past_reel, future_reel], **_default_kwargs())
    # If leakage discipline were broken, the future reel's 0.99 engagement rate
    # would dominate every ranked output — assert it's excluded entirely.
    assert dna["winning_topics"][0]["avg_engagement_rate"] < 0.5


def test_compute_dna_empty_input_returns_default_shape():
    dna = compute_dna([], **_default_kwargs())
    assert dna["early_profile"] is True
    assert dna["winning_topics"] == []
    assert dna["weak_topics"] == []
    assert dna["winning_hooks"] == []
    assert dna["strong_formats"] == []
    assert dna["typical_length_min_seconds"] is None
    assert dna["primary_kpi"] == "reach"


def test_compute_dna_recent_fatigue_notes_flags_overrepresented_topic():
    # 8 of the last 10 posts (window=10) are AI tools — should be flagged overrepresented.
    reels = [
        _reel(f"ai-{i}", days_ago=i, embedding=AI_TOOLS_EMBEDDING, engagement_rate=0.05)
        for i in range(8)
    ] + [
        _reel(f"cooking-{i}", days_ago=8 + i, embedding=COOKING_EMBEDDING, engagement_rate=0.05)
        for i in range(2)
    ]
    dna = compute_dna(reels, **_default_kwargs(recent_fatigue_window=10))

    fatigue = dna["recent_fatigue_notes"]
    assert fatigue["window_size"] == 10
    top_entry = fatigue["topics"][0]
    assert top_entry["overrepresented"] is True


def test_compute_dna_primary_kpi_passthrough():
    reels = [_reel("r1", embedding=AI_TOOLS_EMBEDDING)]
    dna = compute_dna(reels, **_default_kwargs(primary_kpi="shares"))
    assert dna["primary_kpi"] == "shares"


def test_compute_dna_handles_reels_without_embeddings_gracefully():
    # Reels missing an embedding can't be clustered, but should still contribute
    # to hooks/formats/length rather than crashing the whole aggregation.
    reels = [
        _reel("no-embedding", embedding=None, engagement_rate=0.05, duration_seconds=20.0),
        _reel("with-embedding", embedding=AI_TOOLS_EMBEDDING, engagement_rate=0.05),
    ]
    dna = compute_dna(reels, **_default_kwargs())
    assert dna["winning_hooks"] is not None  # doesn't raise
