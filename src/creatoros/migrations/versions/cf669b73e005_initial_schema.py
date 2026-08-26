"""initial schema

Revision ID: cf669b73e005
Revises:
Create Date: 2026-08-26 21:54:43.308122

Hand-authored (no live DB to autogenerate against at write time) — mirrors
creatoros.db.models exactly. Sanity-check offline with:
    uv run alembic upgrade head --sql
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cf669b73e005"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "creators",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("instagram_user_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("niche", sa.String(), nullable=False),
        sa.Column(
            "connected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("primary_kpi_goal", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instagram_user_id"),
    )

    op.create_table(
        "reels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("creator_id", sa.Uuid(), nullable=False),
        sa.Column("instagram_media_id", sa.String(), nullable=False),
        sa.Column("caption", sa.String(), nullable=True),
        sa.Column("transcript", sa.String(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_media_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("duration_seconds", sa.Numeric(), nullable=True),
        sa.Column("media_product_type", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["creator_id"], ["creators.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instagram_media_id"),
        sa.UniqueConstraint(
            "creator_id", "instagram_media_id", name="uq_reel_creator_media"
        ),
    )

    op.create_table(
        "reel_insights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reel_id", sa.Uuid(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Integer(), nullable=True),
        sa.Column("shares", sa.Integer(), nullable=True),
        sa.Column("saves", sa.Integer(), nullable=True),
        sa.Column("plays", sa.Integer(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("raw_insights_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["reel_id"], ["reels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reel_insights_reel_fetched",
        "reel_insights",
        ["reel_id", "fetched_at"],
        unique=False,
    )

    op.create_table(
        "niche_signal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("niche", sa.String(), nullable=False),
        sa.Column("account_handle", sa.String(), nullable=False),
        sa.Column("observed_topic", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("added_by", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "creator_dna",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("creator_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("winning_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("weak_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("winning_hooks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("typical_length_min_seconds", sa.Numeric(), nullable=True),
        sa.Column("typical_length_max_seconds", sa.Numeric(), nullable=True),
        sa.Column("strong_formats", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("primary_kpi", sa.String(), nullable=False),
        sa.Column("recent_fatigue_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("early_profile", sa.Boolean(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["creators.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("creator_id", "version", name="uq_creator_dna_version"),
    )


def downgrade() -> None:
    op.drop_table("creator_dna")
    op.drop_table("niche_signal")
    op.drop_index("ix_reel_insights_reel_fetched", table_name="reel_insights")
    op.drop_table("reel_insights")
    op.drop_table("reels")
    op.drop_table("creators")
