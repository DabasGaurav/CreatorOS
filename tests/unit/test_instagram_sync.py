from types import SimpleNamespace

from creatorsignal.instagram import sync as sync_module


class FakeGraphClient:
    def __init__(self, token, media, insights_by_id, fail_ids=()):
        self.token = token
        self._media = media
        self._insights_by_id = insights_by_id
        self._fail_ids = set(fail_ids)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def iter_media(self, ig_user_id):
        yield from self._media

    def get_media_insights(self, media_id):
        if media_id in self._fail_ids:
            raise RuntimeError("insights fetch failed")
        return self._insights_by_id[media_id]


def test_sync_creator_history_upserts_reel_and_insight_per_media(monkeypatch):
    media = [{"id": "m1"}, {"id": "m2"}]
    insights = {"m1": {"data": []}, "m2": {"data": []}}
    upserted_reels = []
    inserted_insights = []

    def fake_upsert_reel(session, *, creator_id, raw_media):
        reel = SimpleNamespace(id=f"reel-{raw_media['id']}")
        upserted_reels.append(raw_media["id"])
        return reel

    def fake_add_reel_insight(session, *, reel_id, raw_insights):
        inserted_insights.append(reel_id)
        return SimpleNamespace(id=f"insight-{reel_id}")

    monkeypatch.setattr(sync_module, "decrypt_token", lambda token: "plaintext-token")
    monkeypatch.setattr(
        sync_module,
        "GraphAPIClient",
        lambda token: FakeGraphClient(token, media, insights),
    )
    monkeypatch.setattr(sync_module, "upsert_reel", fake_upsert_reel)
    monkeypatch.setattr(sync_module, "add_reel_insight", fake_add_reel_insight)

    creator = SimpleNamespace(id="creator-1", instagram_user_id="ig-1", token="ciphertext")
    result = sync_module.sync_creator_history(session=None, creator=creator)

    assert upserted_reels == ["m1", "m2"]
    assert inserted_insights == ["reel-m1", "reel-m2"]
    assert len(result) == 2


def test_sync_creator_history_continues_when_insights_fetch_fails(monkeypatch):
    media = [{"id": "m1"}, {"id": "m2"}]
    insights = {"m2": {"data": []}}
    inserted_insights = []

    def fake_upsert_reel(session, *, creator_id, raw_media):
        return SimpleNamespace(id=f"reel-{raw_media['id']}")

    def fake_add_reel_insight(session, *, reel_id, raw_insights):
        inserted_insights.append(reel_id)
        return SimpleNamespace(id=f"insight-{reel_id}")

    monkeypatch.setattr(sync_module, "decrypt_token", lambda token: "plaintext-token")
    monkeypatch.setattr(
        sync_module,
        "GraphAPIClient",
        lambda token: FakeGraphClient(token, media, insights, fail_ids={"m1"}),
    )
    monkeypatch.setattr(sync_module, "upsert_reel", fake_upsert_reel)
    monkeypatch.setattr(sync_module, "add_reel_insight", fake_add_reel_insight)

    creator = SimpleNamespace(id="creator-1", instagram_user_id="ig-1", token="ciphertext")
    result = sync_module.sync_creator_history(session=None, creator=creator)

    # m1's insights fetch failed, but its reel is still recorded and sync continues to m2.
    assert inserted_insights == ["reel-m2"]
    assert len(result) == 2
