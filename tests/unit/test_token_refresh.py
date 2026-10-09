from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from creatorsignal.instagram import token_refresh


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, condition):
        cutoff = condition.right.value
        return FakeQuery([r for r in self._rows if r.token_expires_at <= cutoff])

    def all(self):
        return list(self._rows)


class FakeSession:
    def __init__(self, creators):
        self.creators = creators
        self.committed = 0

    def query(self, model):
        return FakeQuery(self.creators)

    def commit(self):
        self.committed += 1

    def refresh(self, row):
        pass


def _creator(expires_in_days):
    return SimpleNamespace(
        instagram_user_id=f"ig-{expires_in_days}",
        token="ciphertext",
        token_expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
    )


def test_creators_due_for_refresh_includes_only_those_within_window():
    soon = _creator(3)
    later = _creator(30)
    session = FakeSession([soon, later])

    due = token_refresh.creators_due_for_refresh(session)

    assert soon in due
    assert later not in due


def test_refresh_creator_token_updates_token_and_expiry(monkeypatch):
    creator = _creator(2)
    session = FakeSession([creator])

    monkeypatch.setattr(token_refresh, "decrypt_token", lambda t: "old-plaintext")
    monkeypatch.setattr(token_refresh, "encrypt_token", lambda t: f"encrypted:{t}")
    monkeypatch.setattr(
        token_refresh,
        "refresh_long_lived_token",
        lambda token: {"access_token": "new-token", "expires_in": 5184000},
    )

    updated = token_refresh.refresh_creator_token(session, creator)

    assert updated.token == "encrypted:new-token"
    assert updated.token_expires_at > datetime.now(UTC) + timedelta(days=50)
    assert session.committed == 1


def test_refresh_all_due_skips_failures_and_continues(monkeypatch):
    creator1 = _creator(1)
    creator2 = _creator(2)
    session = FakeSession([creator1, creator2])

    monkeypatch.setattr(token_refresh, "decrypt_token", lambda t: "old-plaintext")
    monkeypatch.setattr(token_refresh, "encrypt_token", lambda t: f"encrypted:{t}")

    calls = {"n": 0}

    def flaky_exchange(token):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("network error")
        return {"access_token": "new-token", "expires_in": 5184000}

    monkeypatch.setattr(token_refresh, "refresh_long_lived_token", flaky_exchange)

    refreshed = token_refresh.refresh_all_due(session)

    assert len(refreshed) == 1
