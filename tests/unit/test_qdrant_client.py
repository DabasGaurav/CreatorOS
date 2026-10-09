import uuid
from datetime import UTC, datetime, timedelta

import pytest

from creatorsignal.embeddings import qdrant_client as qc

VECTOR_SIZE = 8


@pytest.fixture
def client():
    c = qc.get_in_memory_client()
    qc.ensure_collection(c, vector_size=VECTOR_SIZE, collection_name="reels_test")
    yield c


def _unit_vector(*nonzero_indices: int) -> list[float]:
    v = [0.0] * VECTOR_SIZE
    for i in nonzero_indices:
        v[i] = 1.0
    norm = sum(x * x for x in v) ** 0.5
    return [x / norm for x in v] if norm else v


def test_upsert_then_fetch_creator_points_round_trips(client):
    creator_id = uuid.uuid4()
    reel_id = uuid.uuid4()
    qc.upsert_reel_point(
        client,
        reel_id=reel_id,
        creator_id=creator_id,
        posted_at=datetime.now(UTC),
        vector=_unit_vector(0),
        engagement_rate=0.1,
        collection_name="reels_test",
    )
    points = qc.fetch_creator_points(client, creator_id=creator_id, collection_name="reels_test")
    assert len(points) == 1
    assert points[0].reel_id == str(reel_id)
    assert points[0].engagement_rate == 0.1


def test_fetch_creator_points_only_returns_matching_creator_and_version(client):
    creator_a, creator_b = uuid.uuid4(), uuid.uuid4()
    qc.upsert_reel_point(
        client,
        reel_id=uuid.uuid4(),
        creator_id=creator_a,
        posted_at=datetime.now(UTC),
        vector=_unit_vector(0),
        engagement_rate=0.2,
        collection_name="reels_test",
    )
    qc.upsert_reel_point(
        client,
        reel_id=uuid.uuid4(),
        creator_id=creator_b,
        posted_at=datetime.now(UTC),
        vector=_unit_vector(1),
        engagement_rate=0.3,
        collection_name="reels_test",
    )
    points = qc.fetch_creator_points(client, creator_id=creator_a, collection_name="reels_test")
    assert len(points) == 1


def test_cosine_similarity_identical_vectors_is_one():
    v = _unit_vector(0)
    assert qc.cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert qc.cosine_similarity(_unit_vector(0), _unit_vector(1)) == pytest.approx(0.0)


def test_creator_fit_ranks_similar_topic_higher_than_dissimilar(client):
    creator_id = uuid.uuid4()
    now = datetime.now(UTC)

    # Two historically high-performing reels: one "AI tools" (dim 0), one "cooking" (dim 5).
    qc.upsert_reel_point(
        client,
        reel_id=uuid.uuid4(),
        creator_id=creator_id,
        posted_at=now,
        vector=_unit_vector(0),
        engagement_rate=0.9,
        collection_name="reels_test",
    )
    qc.upsert_reel_point(
        client,
        reel_id=uuid.uuid4(),
        creator_id=creator_id,
        posted_at=now,
        vector=_unit_vector(5),
        engagement_rate=0.8,
        collection_name="reels_test",
    )
    # A low-performing outlier that shouldn't count toward the top-quartile filter.
    qc.upsert_reel_point(
        client,
        reel_id=uuid.uuid4(),
        creator_id=creator_id,
        posted_at=now,
        vector=_unit_vector(3),
        engagement_rate=0.01,
        collection_name="reels_test",
    )

    similar_score = qc.creator_fit(
        client,
        candidate_vector=_unit_vector(0),
        creator_id=creator_id,
        collection_name="reels_test",
    )
    dissimilar_score = qc.creator_fit(
        client,
        candidate_vector=_unit_vector(6),
        creator_id=creator_id,
        collection_name="reels_test",
    )

    assert similar_score > dissimilar_score
    assert 0.0 <= similar_score <= 1.0
    assert 0.0 <= dissimilar_score <= 1.0


def test_creator_fit_returns_zero_with_no_history(client):
    score = qc.creator_fit(
        client,
        candidate_vector=_unit_vector(0),
        creator_id=uuid.uuid4(),
        collection_name="reels_test",
    )
    assert score == 0.0


def test_personal_novelty_low_for_near_duplicate_of_recent_post(client):
    creator_id = uuid.uuid4()
    now = datetime.now(UTC)
    qc.upsert_reel_point(
        client,
        reel_id=uuid.uuid4(),
        creator_id=creator_id,
        posted_at=now,
        vector=_unit_vector(0),
        engagement_rate=0.5,
        collection_name="reels_test",
    )

    novelty = qc.personal_novelty(
        client,
        candidate_vector=_unit_vector(0),
        creator_id=creator_id,
        collection_name="reels_test",
    )
    assert novelty == pytest.approx(0.0, abs=1e-6)


def test_personal_novelty_high_for_dissimilar_topic(client):
    creator_id = uuid.uuid4()
    now = datetime.now(UTC)
    qc.upsert_reel_point(
        client,
        reel_id=uuid.uuid4(),
        creator_id=creator_id,
        posted_at=now,
        vector=_unit_vector(0),
        engagement_rate=0.5,
        collection_name="reels_test",
    )

    novelty = qc.personal_novelty(
        client,
        candidate_vector=_unit_vector(7),
        creator_id=creator_id,
        collection_name="reels_test",
    )
    assert novelty == pytest.approx(1.0, abs=1e-6)


def test_personal_novelty_returns_one_with_no_history(client):
    novelty = qc.personal_novelty(
        client,
        candidate_vector=_unit_vector(0),
        creator_id=uuid.uuid4(),
        collection_name="reels_test",
    )
    assert novelty == 1.0


def test_personal_novelty_respects_window_ignoring_older_similar_posts(client):
    creator_id = uuid.uuid4()
    now = datetime.now(UTC)

    # An old post very similar to the candidate...
    qc.upsert_reel_point(
        client,
        reel_id=uuid.uuid4(),
        creator_id=creator_id,
        posted_at=now - timedelta(days=365),
        vector=_unit_vector(0),
        engagement_rate=0.5,
        collection_name="reels_test",
    )
    # ...and a recent post that's dissimilar.
    qc.upsert_reel_point(
        client,
        reel_id=uuid.uuid4(),
        creator_id=creator_id,
        posted_at=now,
        vector=_unit_vector(7),
        engagement_rate=0.5,
        collection_name="reels_test",
    )
    novelty = qc.personal_novelty(
        client,
        candidate_vector=_unit_vector(0),
        creator_id=creator_id,
        window=1,
        collection_name="reels_test",
    )
    # Window=1 only considers the most recent (dissimilar) post, so novelty should be high
    # even though an old, highly similar post exists in the full history.
    assert novelty == pytest.approx(1.0, abs=1e-6)
