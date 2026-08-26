"""Graph API client: retry-with-backoff, rate-limit awareness, and cursor pagination.
Every call is wrapped so throttling is logged, never silently swallowed (per spec).

Host confirmed against a real live token during Build Doc 1 integration testing
(2026-08-26): this project's tokens come from Meta's 'Instagram API with Instagram
Login' product (direct Instagram Business/Creator login, no Facebook Page required)
— which lives at graph.instagram.com, NOT graph.facebook.com. The classic 'Login
for Business' flow the original spec assumed (Facebook Login + a linked Page) is a
different, older product; graph.facebook.com returned "Cannot parse access token"
for this token. This also means the A11 Facebook-Page-linkage requirement doesn't
apply to accounts onboarded this way — see oauth.py.
"""

import time
from collections.abc import Generator
from typing import Any

import httpx

from creatoros.config import get_settings
from creatoros.utils.logging import get_logger
from creatoros.utils.retry import with_backoff

logger = get_logger(__name__)

GRAPH_BASE_URL = "https://graph.instagram.com/{version}"

# Business Use Case usage is impression-based; proactively slow down past this % to
# avoid actually hitting the hard limit and getting throttled with a hard error.
RATE_LIMIT_WARN_THRESHOLD_PCT = 80


class GraphAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class RateLimitedError(GraphAPIError):
    pass


RETRYABLE_EXCEPTIONS = (httpx.TransportError,)


class GraphAPIClient:
    def __init__(self, access_token: str, *, http_client: httpx.Client | None = None):
        self._token = access_token
        settings = get_settings()
        self._base_url = GRAPH_BASE_URL.format(version=settings.graph_api_version)
        self._http = http_client or httpx.Client(timeout=20.0)

    def close(self):
        self._http.close()

    def __enter__(self) -> "GraphAPIClient":
        return self

    def __exit__(self, *exc):
        self.close()

    @with_backoff(exceptions=RETRYABLE_EXCEPTIONS, max_attempts=5, initial=1.0, max_wait=30.0)
    def _request(self, path: str, *, params: dict[str, Any] | None = None) -> dict:
        url = path if path.startswith("http") else f"{self._base_url}/{path.lstrip('/')}"
        request_params = dict(params or {})
        request_params["access_token"] = self._token

        response = self._http.get(url, params=request_params)
        self._check_rate_limit(response)

        if response.status_code == 429:
            logger.warning("Graph API rate limited (HTTP 429) on %s", path)
            raise RateLimitedError("Rate limited", status_code=429, payload=response.text)

        if response.status_code >= 500:
            # Let tenacity retry these via RETRYABLE_EXCEPTIONS by raising as a transport-ish error.
            raise httpx.TransportError(f"Graph API {response.status_code} on {path}")

        if response.status_code >= 400:
            raise GraphAPIError(
                f"Graph API error {response.status_code} on {path}: {response.text}",
                status_code=response.status_code,
                payload=response.text,
            )

        return response.json()

    def _check_rate_limit(self, response: httpx.Response) -> None:
        """Parse Meta's Business Use Case usage header; proactively sleep + log a
        WARNING rather than failing silently when usage crosses the warn threshold."""
        header = response.headers.get("x-business-use-case-usage")
        if not header:
            return
        try:
            import json

            usage = json.loads(header)
        except ValueError:
            return

        max_pct = 0
        for entries in usage.values():
            for entry in entries:
                for key in ("call_count", "total_cputime", "total_time"):
                    max_pct = max(max_pct, entry.get(key, 0))

        if max_pct >= RATE_LIMIT_WARN_THRESHOLD_PCT:
            logger.warning(
                "Graph API usage at %s%% of the Business Use Case limit — backing off", max_pct
            )
            time.sleep(2.0)

    def get_media_page(
        self, ig_user_id: str, *, after: str | None = None, limit: int = 25
    ) -> dict:
        fields = "id,caption,media_type,media_product_type,timestamp,permalink"
        params: dict[str, Any] = {"fields": fields, "limit": limit}
        if after:
            params["after"] = after
        return self._request(f"{ig_user_id}/media", params=params)

    def iter_media(self, ig_user_id: str, *, page_limit: int = 25) -> Generator[dict, None, None]:
        after: str | None = None
        while True:
            page = self.get_media_page(ig_user_id, after=after, limit=page_limit)
            yield from page.get("data", [])
            cursors = page.get("paging", {}).get("cursors", {})
            after = page.get("paging", {}).get("next") and cursors.get("after")
            if not after:
                break

    def get_media_insights(self, media_id: str) -> dict:
        # "plays" was rejected live by the current API ("must be one of ... views
        # ..."); Meta renamed/replaced it with "views" since the spec was written.
        metrics = "reach,likes,comments,shares,saved,views"
        return self._request(f"{media_id}/insights", params={"metric": metrics})

    def get_account_profile(self, ig_user_id: str) -> dict:
        return self._request(ig_user_id, params={"fields": "id,username,account_type,media_count"})
