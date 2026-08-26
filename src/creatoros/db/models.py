import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from creatoros.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Creator(Base):
    """A connected Instagram creator. `token` is Fernet ciphertext, never plaintext."""

    __tablename__ = "creators"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    instagram_user_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    niche: Mapped[str] = mapped_column(String, nullable=False)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    token: Mapped[str] = mapped_column(String, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Not in the spec's minimum schema. `primary_kpi` is described as "creator-selected at
    # onboarding" but Build Doc 1 has no onboarding UI to collect it — nullable now, populated
    # by Build Doc 3's onboarding flow; the Creator DNA job falls back to a configured default
    # (see Settings.creator_dna_default_primary_kpi) when this is null.
    primary_kpi_goal: Mapped[str | None] = mapped_column(String, nullable=True)

    reels: Mapped[list["Reel"]] = relationship(back_populates="creator")
    dna_versions: Mapped[list["CreatorDNA"]] = relationship(back_populates="creator")


class Reel(Base):
    __tablename__ = "reels"
    __table_args__ = (
        UniqueConstraint("creator_id", "instagram_media_id", name="uq_reel_creator_media"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    creator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("creators.id"), nullable=False)
    instagram_media_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    caption: Mapped[str | None] = mapped_column(String, nullable=True)
    transcript: Mapped[str | None] = mapped_column(String, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_media_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Extracted from raw_media_json at ingest so length/format heuristics in the Creator DNA
    # job don't need to re-parse JSONB on every run.
    duration_seconds: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    media_product_type: Mapped[str | None] = mapped_column(String, nullable=True)

    creator: Mapped["Creator"] = relationship(back_populates="reels")
    insights: Mapped[list["ReelInsight"]] = relationship(back_populates="reel")


class ReelInsight(Base):
    """Append-only time series — a reel may be re-fetched multiple times, so `fetched_at`
    is not unique per reel. `id` is a surrogate key since the spec's column list has none."""

    __tablename__ = "reel_insights"
    __table_args__ = (Index("ix_reel_insights_reel_fetched", "reel_id", "fetched_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    reel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reels.id"), nullable=False)
    reach: Mapped[int | None] = mapped_column(nullable=True)
    likes: Mapped[int | None] = mapped_column(nullable=True)
    comments: Mapped[int | None] = mapped_column(nullable=True)
    shares: Mapped[int | None] = mapped_column(nullable=True)
    saves: Mapped[int | None] = mapped_column(nullable=True)
    plays: Mapped[int | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Not in the spec's minimum schema, but §1.2 requires raw responses stored before
    # transforming for both media *and* insights — only raw_media_json is defined on Reel.
    raw_insights_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    reel: Mapped["Reel"] = relationship(back_populates="insights")


class NicheSignal(Base):
    """Manually curated — never populated by scraping or automated collection."""

    __tablename__ = "niche_signal"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    niche: Mapped[str] = mapped_column(String, nullable=False)
    account_handle: Mapped[str] = mapped_column(String, nullable=False)
    observed_topic: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    added_by: Mapped[str] = mapped_column(String, nullable=False)


class CreatorDNA(Base):
    """Versioned, never overwritten — insert a new row each recomputation."""

    __tablename__ = "creator_dna"
    __table_args__ = (UniqueConstraint("creator_id", "version", name="uq_creator_dna_version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    creator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("creators.id"), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    winning_topics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    weak_topics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    winning_hooks: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Spec names this a single `typical_length_range` field; split into two explicit numeric
    # columns since it's a small fixed structure — simpler to query and index than a JSONB range.
    typical_length_min_seconds: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    typical_length_max_seconds: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    strong_formats: Mapped[dict] = mapped_column(JSONB, nullable=False)
    primary_kpi: Mapped[str] = mapped_column(String, nullable=False)
    recent_fatigue_notes: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Required by §4.1 step 3 ("flag the profile as early_profile = true") but missing from
    # the spec's §2 column list — a genuine spec gap, added here.
    early_profile: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    creator: Mapped["Creator"] = relationship(back_populates="dna_versions")


class Recommendation(Base):
    """One on-demand recommendation cycle (Build Doc 2, B3/B13). Row id doubles as
    the LangGraph run's request_id, polled via GET /recommendations/{id}."""

    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    creator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("creators.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(String, nullable=True)

    topic: Mapped[str | None] = mapped_column(String, nullable=True)
    angle: Mapped[str | None] = mapped_column(String, nullable=True)
    format: Mapped[str | None] = mapped_column(String, nullable=True)

    composite_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    evidence_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    selection_type: Mapped[str | None] = mapped_column(String, nullable=True)
    content_package: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # B13 step 2: log baseline picks alongside the real pick for offline comparison.
    baseline_picks: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # B16 step 4 (Build Doc 3 outcome loop reads this): the Expected Engagement
    # model's prediction at recommendation time, never recomputed retroactively.
    expected_engagement_prediction: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator: Mapped["Creator"] = relationship()


class FeatureSnapshot(Base):
    """Timestamped snapshot of every Expected Engagement model input, captured at
    recommendation time — built before any model code, per B9 step 2, specifically
    so the model can never leak post-hoc data: every feature here is exactly what
    was known at the moment of the recommendation, never recomputed later."""

    __tablename__ = "feature_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id"), nullable=False
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("creators.id"), nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)
    predicted_engagement: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExternalResultCache(Base):
    """TTL cache for Market Researcher external calls (YouTube/Reddit/pytrends),
    keyed by (source, query, date-bucket) — B4 step 5 / B7 step 4. Backed by
    Postgres so it survives process restarts during iterative agent development."""

    __tablename__ = "external_result_cache"

    cache_key: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    query: Mapped[str] = mapped_column(String, nullable=False)
    date_bucket: Mapped[str] = mapped_column(String, nullable=False)
    result_json: Mapped[str] = mapped_column(String, nullable=False)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
