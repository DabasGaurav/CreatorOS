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
