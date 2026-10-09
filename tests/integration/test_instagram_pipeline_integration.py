"""End-to-end regression against whatever real, already-connected creator exists in
this environment's Postgres (connected via scripts/connect_creator.py or a manual
provisioning step — see Build Doc 1's Definition of Done). Skips cleanly if no
creator has been connected yet, since these tests can't fabricate a real Instagram
account or token."""

import pytest

from creatorsignal.db.models import Creator, CreatorDNA, Reel, ReelInsight
from creatorsignal.dna.job import compute_and_store_dna
from creatorsignal.embeddings.job import embed_and_upsert_all_reels_for_creator
from creatorsignal.embeddings.qdrant_client import get_client
from creatorsignal.instagram.sync import sync_creator_history

pytestmark = pytest.mark.integration


@pytest.fixture
def connected_creator(db_session):
    creator = db_session.query(Creator).first()
    if creator is None:
        pytest.skip("No creator connected in this environment — run connect_creator.py first")
    return creator


def test_sync_populates_real_reels_and_insights(db_session, connected_creator):
    reels = sync_creator_history(db_session, connected_creator)
    assert len(reels) > 0

    stored_reels = db_session.query(Reel).filter(Reel.creator_id == connected_creator.id).all()
    assert len(stored_reels) == len(reels)
    for reel in stored_reels:
        assert reel.raw_media_json  # raw response stored verbatim, per spec

    reel_ids = [r.id for r in stored_reels]
    insights = db_session.query(ReelInsight).filter(ReelInsight.reel_id.in_(reel_ids)).all()
    # Not every reel has insights (Meta rejects insights for media predating the
    # account's Business conversion) — just assert at least one real row landed.
    assert len(insights) > 0


def test_embedding_job_populates_qdrant(db_session, connected_creator, qdrant_real_client):
    count = embed_and_upsert_all_reels_for_creator(
        db_session, qdrant_real_client, connected_creator.id
    )
    assert count > 0


def test_dna_job_produces_and_stores_a_new_version(db_session, connected_creator):
    qdrant = get_client()
    before = (
        db_session.query(CreatorDNA).filter(CreatorDNA.creator_id == connected_creator.id).count()
    )
    dna = compute_and_store_dna(db_session, qdrant, connected_creator)
    after = (
        db_session.query(CreatorDNA).filter(CreatorDNA.creator_id == connected_creator.id).count()
    )

    assert after == before + 1  # new version inserted, never overwritten
    assert dna.primary_kpi
    assert isinstance(dna.early_profile, bool)
