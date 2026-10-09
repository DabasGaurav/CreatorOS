
import pytest

from creatorsignal.research import reddit_client


def test_get_reddit_client_raises_when_not_configured(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "")
    reddit_client.get_settings.cache_clear()
    with pytest.raises(reddit_client.RedditNotConfigured):
        reddit_client.get_reddit_client()
    reddit_client.get_settings.cache_clear()


class FakeSubmission:
    def __init__(self, title, score, num_comments, created_utc, subreddit):
        self.title = title
        self.score = score
        self.num_comments = num_comments
        self.created_utc = created_utc
        self.subreddit = subreddit


class FakeSubreddit:
    def __init__(self, submissions):
        self._submissions = submissions

    def search(self, query, limit=10, sort="relevance"):
        return iter(self._submissions[:limit])


class FakeReddit:
    def __init__(self, submissions):
        self._submissions = submissions

    def subreddit(self, name):
        assert name == "all"
        return FakeSubreddit(self._submissions)


def test_search_posts_returns_normalized_fields():
    fake = FakeReddit(
        [
            FakeSubmission("AI agents are changing dev work", 150, 42, 1700000000.0, "programming"),
            FakeSubmission("Just started using AI agents", 30, 5, 1700001000.0, "webdev"),
        ]
    )
    results = reddit_client.search_posts("AI agents", reddit=fake)
    assert len(results) == 2
    assert results[0]["title"] == "AI agents are changing dev work"
    assert results[0]["score"] == 150
    assert results[0]["subreddit"] == "programming"


def test_search_posts_respects_limit():
    fake = FakeReddit([FakeSubmission(f"post {i}", i, i, 0.0, "test") for i in range(20)])
    results = reddit_client.search_posts("query", limit=3, reddit=fake)
    assert len(results) == 3
