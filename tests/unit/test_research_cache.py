from datetime import UTC, datetime, timedelta

from creatorsignal.research import cache as cache_module


class FakeSession:
    def __init__(self):
        self.rows = {}

    def get(self, model, key):
        return self.rows.get(key)

    def add(self, row):
        self.rows[row.cache_key] = row

    def commit(self):
        pass


def test_set_then_get_cached_roundtrips():
    session = FakeSession()
    cache_module.set_cached(session, source="youtube", query="AI agents", result={"a": 1})
    result = cache_module.get_cached(session, source="youtube", query="AI agents", ttl_hours=12)
    assert result == {"a": 1}


def test_get_cached_returns_none_when_missing():
    session = FakeSession()
    assert cache_module.get_cached(session, source="reddit", query="nope", ttl_hours=12) is None


def test_get_cached_returns_none_when_expired(monkeypatch):
    session = FakeSession()
    cache_module.set_cached(session, source="youtube", query="AI agents", result={"a": 1})

    # Manually age the cached row past the TTL.
    row = next(iter(session.rows.values()))
    row.cached_at = datetime.now(UTC) - timedelta(hours=13)

    result = cache_module.get_cached(session, source="youtube", query="AI agents", ttl_hours=12)
    assert result is None


def test_set_cached_overwrites_existing_entry_within_same_bucket():
    session = FakeSession()
    cache_module.set_cached(session, source="youtube", query="AI agents", result={"a": 1})
    cache_module.set_cached(session, source="youtube", query="AI agents", result={"a": 2})
    assert len(session.rows) == 1
    result = cache_module.get_cached(session, source="youtube", query="AI agents", ttl_hours=12)
    assert result == {"a": 2}


def test_different_queries_get_different_cache_keys():
    session = FakeSession()
    cache_module.set_cached(session, source="youtube", query="topic A", result={"a": 1})
    cache_module.set_cached(session, source="youtube", query="topic B", result={"a": 2})
    assert len(session.rows) == 2
