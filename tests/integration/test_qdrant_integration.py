import uuid
from datetime import UTC, datetime

import pytest

from creatoros.config import get_settings
from creatoros.embeddings.qdrant_client import (
    creator_fit,
    ensure_collection,
    fetch_creator_points,
    upsert_reel_point,
)
from creatoros.embeddings.voyage_client import embed_text

pytestmark = pytest.mark.integration


def test_real_collection_exists(qdrant_real_client):
    ensure_collection(qdrant_real_client, vector_size=512)
    names = {c.name for c in qdrant_real_client.get_collections().collections}
    assert get_settings().qdrant_collection in names


def test_real_voyage_embedding_and_qdrant_roundtrip(qdrant_real_client):
    if not get_settings().voyage_api_key:
        pytest.skip("VOYAGE_API_KEY not set")

    creator_id = uuid.uuid4()  # throwaway — isolated from real creators
    reel_id = uuid.uuid4()
    vector = embed_text("a test caption about startups and AI tools")

    upsert_reel_point(
        qdrant_real_client,
        reel_id=reel_id,
        creator_id=creator_id,
        posted_at=datetime.now(UTC),
        vector=vector,
        engagement_rate=0.5,
    )
    try:
        points = fetch_creator_points(qdrant_real_client, creator_id=creator_id)
        assert len(points) == 1
        assert points[0].reel_id == str(reel_id)

        query_vector = embed_text("AI tools for startups", input_type="query")
        score = creator_fit(
            qdrant_real_client, candidate_vector=query_vector, creator_id=creator_id
        )
        assert 0.0 <= score <= 1.0
        assert score > 0.7  # should be highly similar to the seeded caption
    finally:
        qdrant_real_client.delete(
            collection_name=get_settings().qdrant_collection, points_selector=[str(reel_id)]
        )
