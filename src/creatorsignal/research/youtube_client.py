"""YouTube Data API v3 — official, free tier. Thin httpx wrapper (not the heavy
google-api-python-client) since only the search endpoint is needed here."""

import httpx

from creatorsignal.config import get_settings
from creatorsignal.utils.logging import get_logger
from creatorsignal.utils.retry import with_backoff

logger = get_logger(__name__)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

RETRYABLE_EXCEPTIONS = (httpx.TransportError,)


class YouTubeNotConfigured(Exception):
    pass


@with_backoff(exceptions=RETRYABLE_EXCEPTIONS, max_attempts=3, initial=1.0, max_wait=10.0)
def search_videos(
    query: str, *, max_results: int = 10, http_client: httpx.Client | None = None
) -> dict:
    """Returns the raw YouTube search response: totalResults (a demand proxy) and
    per-video snippets (title, publishedAt, channelTitle — a recency/velocity
    proxy). Evidence-sufficiency scoring happens in the Market Researcher, not
    here — this stays a thin, testable data fetcher."""
    settings = get_settings()
    if not settings.youtube_api_key:
        raise YouTubeNotConfigured("YOUTUBE_API_KEY not set — skip this source")

    client = http_client or httpx.Client(timeout=15.0)
    response = client.get(
        SEARCH_URL,
        params={
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "relevance",
            "maxResults": max_results,
            "key": settings.youtube_api_key,
        },
    )
    response.raise_for_status()
    return response.json()
