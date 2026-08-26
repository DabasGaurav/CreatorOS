"""OAuth handler for Meta's 'Instagram API with Instagram Login' flow — direct
Instagram Business/Creator account login, no linked Facebook Page required.

Confirmed against a real live token during Build Doc 1 integration testing
(2026-08-26): this project's tokens use www.instagram.com / api.instagram.com /
graph.instagram.com hosts, NOT graph.facebook.com. This is a different, newer
Meta product than the classic 'Login for Business' (Facebook Login) flow the
original spec assumed — graph.facebook.com rejected the token outright
("Cannot parse access token"). This also means A11's Facebook-Page-linkage
requirement doesn't apply to accounts onboarded this way: no Facebook Page,
no `get_pages`/`get_instagram_business_account` resolution step needed.

Framework-free by design — Build Doc 1 has no FastAPI surface yet; the connect
script (scripts/connect_creator.py) prints the authorize URL and runs a small
stdlib callback listener to capture the redirect code.
"""

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from creatoros.config import get_settings
from creatoros.utils.logging import get_logger
from creatoros.utils.retry import with_backoff

logger = get_logger(__name__)

AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
CODE_EXCHANGE_URL = "https://api.instagram.com/oauth/access_token"
LONG_LIVED_EXCHANGE_URL = "https://graph.instagram.com/access_token"
REFRESH_URL = "https://graph.instagram.com/refresh_access_token"

DEFAULT_SCOPES = (
    "instagram_business_basic",
    "instagram_business_manage_insights",
    "instagram_business_content_publish",
)

RETRYABLE_EXCEPTIONS = (httpx.TransportError, httpx.HTTPStatusError)


class OAuthError(Exception):
    pass


def generate_state() -> str:
    return secrets.token_urlsafe(24)


def build_authorize_url(state: str, *, scopes: tuple[str, ...] = DEFAULT_SCOPES) -> str:
    settings = get_settings()
    params = {
        "client_id": settings.meta_app_id,
        "redirect_uri": settings.meta_oauth_redirect_uri,
        "scope": ",".join(scopes),
        "response_type": "code",
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


@with_backoff(exceptions=RETRYABLE_EXCEPTIONS, max_attempts=3, initial=1.0, max_wait=10.0)
def exchange_code_for_token(code: str, *, http_client: httpx.Client | None = None) -> dict:
    """POST to api.instagram.com — returns a short-lived (~1hr) token plus the
    Instagram-scoped user id, per this flow's contract (Facebook Login's
    equivalent exchange is a GET, not a POST — a real difference, not a typo)."""
    settings = get_settings()
    client = http_client or httpx.Client(timeout=15.0)
    response = client.post(
        CODE_EXCHANGE_URL,
        data={
            "client_id": settings.meta_app_id,
            "client_secret": settings.meta_app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": settings.meta_oauth_redirect_uri,
            "code": code,
        },
    )
    response.raise_for_status()
    data = response.json()
    if "access_token" not in data:
        raise OAuthError(f"Token exchange response missing access_token: {data}")
    return data


@with_backoff(exceptions=RETRYABLE_EXCEPTIONS, max_attempts=3, initial=1.0, max_wait=10.0)
def exchange_short_for_long_lived_token(
    short_lived_token: str, *, http_client: httpx.Client | None = None
) -> dict:
    """Long-lived tokens last ~60 days. Only valid on a short-lived token — calling
    this again on an already-long-lived token errors; use refresh_long_lived_token
    instead for ongoing renewal (see token_refresh.py)."""
    settings = get_settings()
    client = http_client or httpx.Client(timeout=15.0)
    response = client.get(
        LONG_LIVED_EXCHANGE_URL,
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": settings.meta_app_secret,
            "access_token": short_lived_token,
        },
    )
    response.raise_for_status()
    data = response.json()
    if "access_token" not in data:
        raise OAuthError(f"Long-lived exchange response missing access_token: {data}")
    return data


@with_backoff(exceptions=RETRYABLE_EXCEPTIONS, max_attempts=3, initial=1.0, max_wait=10.0)
def refresh_long_lived_token(
    current_token: str, *, http_client: httpx.Client | None = None
) -> dict:
    """The ongoing renewal path for an already-long-lived Instagram Login token —
    confirmed live: returns a new ~60-day token. Distinct from
    exchange_short_for_long_lived_token, which only works once, on the initial
    short-lived token."""
    client = http_client or httpx.Client(timeout=15.0)
    response = client.get(
        REFRESH_URL,
        params={"grant_type": "ig_refresh_token", "access_token": current_token},
    )
    response.raise_for_status()
    data = response.json()
    if "access_token" not in data:
        raise OAuthError(f"Refresh response missing access_token: {data}")
    return data


def compute_expiry(expires_in_seconds: int) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
