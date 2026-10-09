import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from creatorsignal.embeddings import job as job_module


class FakeInsightQuery:
    def __init__(self, insights):
        self._insights = insights

    def filter(self, condition):
        reel_id = condition.right.value
        return FakeInsightQuery([i for i in self._insights if i.reel_id == reel_id])

    def order_by(self, *_args):
        return self

    def first(self):
        return self._insights[0] if self._insights else None


class FakeReelQuery:
    def __init__(self, reels):
        self._reels = reels

    def filter(self, condition):
        creator_id = condition.right.value
        return FakeReelQuery([r for r in self._reels if r.creator_id == creator_id])

    def all(self):
        return list(self._reels)


class FakeSession:
    def __init__(self, reels=(), insights=()):
        self._reels = list(reels)
        self._insights = list(insights)

    def query(self, model):
        if model.__name__ == "ReelInsight":
            return FakeInsightQuery(self._insights)
        return FakeReelQuery(self._reels)


def _reel(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        creator_id=uuid.uuid4(),
        caption="a caption",
        transcript=None,
        posted_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _insight(reel_id, **overrides):
    defaults = dict(reel_id=reel_id, likes=10, comments=1, shares=1, saves=1, reach=100)
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_embed_and_upsert_reel_computes_engagement_rate_and_upserts(monkeypatch):
    reel = _reel()
    insight = _insight(reel.id)
    session = FakeSession(insights=[insight])
    captured = {}

    monkeypatch.setattr(job_module, "embed_text", lambda text: [0.1, 0.2])
    monkeypatch.setattr(
        job_module,
        "upsert_reel_point",
        lambda client, **kwargs: captured.update(kwargs),
    )

    job_module.embed_and_upsert_reel(session, qdrant=object(), reel=reel)

    assert captured["reel_id"] == reel.id
    assert captured["engagement_rate"] == (10 + 1 + 1 + 1) / 100
    assert captured["vector"] == [0.1, 0.2]


def test_embed_and_upsert_reel_with_no_insight_yet_has_none_engagement_rate(monkeypatch):
    reel = _reel()
    session = FakeSession(insights=[])
    captured = {}

    monkeypatch.setattr(job_module, "embed_text", lambda text: [0.1, 0.2])
    monkeypatch.setattr(
        job_module,
        "upsert_reel_point",
        lambda client, **kwargs: captured.update(kwargs),
    )

    job_module.embed_and_upsert_reel(session, qdrant=object(), reel=reel)

    assert captured["engagement_rate"] is None


def test_embed_and_upsert_reel_skips_when_no_text(monkeypatch):
    reel = _reel(caption=None, transcript=None)
    session = FakeSession(insights=[])
    called = {"n": 0}

    monkeypatch.setattr(
        job_module, "upsert_reel_point", lambda client, **kwargs: called.__setitem__("n", 1)
    )

    job_module.embed_and_upsert_reel(session, qdrant=object(), reel=reel)

    assert called["n"] == 0


def test_embed_and_upsert_all_reels_for_creator_processes_each_reel(monkeypatch):
    creator_id = uuid.uuid4()
    reels = [_reel(creator_id=creator_id) for _ in range(3)]
    session = FakeSession(reels=reels, insights=[])
    processed = []

    monkeypatch.setattr(
        job_module,
        "embed_and_upsert_reel",
        lambda session, qdrant, reel: processed.append(reel.id),
    )

    count = job_module.embed_and_upsert_all_reels_for_creator(
        session, qdrant=object(), creator_id=creator_id
    )

    assert count == 3
    assert len(processed) == 3
