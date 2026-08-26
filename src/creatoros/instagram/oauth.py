"""OAuth handler for the 'Login for Business' flow used to connect a creator's
Instagram Business/Creator account. Framework-free by design — Build Doc 1 has no
FastAPI surface yet; the connect script (scripts/connect_creator.py) prints the
authorize URL and runs a small stdlib callback listener to capture the redirect code.
"""

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from creatoros.config import get_settings
from creatoros.utils.logging import get_logger
from creatoros.utils.retry import with_backoff

logger = get_logger(__name__)

AUTHORIZE_BASE_URL = "https://www.facebook.com/{version}/dialog/oauth"
TOKEN_URL = "https://graph.facebook.com/{version}/oauth/access_token"

# Minimum scopes needed to read the creator's own media, insights, and page linkage.
DEFAULT_SCOPES = (
    "instagram_basic",
    "instagram_manage_insights",
    "pages_show_list",
    "business_management",
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
    base = AUTHORIZE_BASE_URL.format(version=settings.graph_api_version)
    return f"{base}?{urlencode(params)}"


@with_backoff(exceptions=RETRYABLE_EXCEPTIONS, max_attempts=3, initial=1.0, max_wait=10.0)
def exchange_code_for_token(code: str, *, http_client: httpx.Client | None = None) -> dict:
    """Exchange the OAuth redirect `code` for a short-lived access token."""
    settings = get_settings()
    client = http_client or httpx.Client(timeout=15.0)
    url = TOKEN_URL.format(version=settings.graph_api_version)
    response = client.get(
        url,
        params={
            "client_id": settings.meta_app_id,
            "redirect_uri": settings.meta_oauth_redirect_uri,
            "client_secret": settings.meta_app_secret,
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
    """Long-lived tokens last ~60 days — this is what gets stored (encrypted)."""
    settings = get_settings()
    client = http_client or httpx.Client(timeout=15.0)
    url = TOKEN_URL.format(version=settings.graph_api_version)
    response = client.get(
        url,
        params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.meta_app_id,
            "client_secret": settings.meta_app_secret,
            "fb_exchange_token": short_lived_token,
        },
    )
    response.raise_for_status()
    data = response.json()
    if "access_token" not in data:
        raise OAuthError(f"Long-lived exchange response missing access_token: {data}")
    return data


def compute_expiry(expires_in_seconds: int) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
