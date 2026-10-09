"""Reddit API via PRAW — official, free tier. The `reddit` client is injectable
so search_posts is unit-testable against a fake without a live PRAW connection."""

import praw

from creatorsignal.config import get_settings


class RedditNotConfigured(Exception):
    pass


def get_reddit_client() -> praw.Reddit:
    settings = get_settings()
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        raise RedditNotConfigured("REDDIT_CLIENT_ID/SECRET not set — skip this source")
    return praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
    )


def search_posts(query: str, *, limit: int = 10, reddit: praw.Reddit | None = None) -> list[dict]:
    """Returns [{title, score, num_comments, created_utc, subreddit}, ...] — score
    and num_comments are the community-engagement signal; created_utc lets the
    Market Researcher compute discussion velocity."""
    client = reddit or get_reddit_client()
    results = []
    for submission in client.subreddit("all").search(query, limit=limit, sort="relevance"):
        results.append(
            {
                "title": submission.title,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "created_utc": submission.created_utc,
                "subreddit": str(submission.subreddit),
            }
        )
    return results
