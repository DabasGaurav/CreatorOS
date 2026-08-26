import httpx
import pytest
import respx

from creatoros.instagram import oauth

BASE = "https://graph.facebook.com/v21.0"


@pytest.fixture(autouse=True)
def _meta_settings(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "test-app-id")
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    monkeypatch.setenv("META_OAUTH_REDIRECT_URI", "http://localhost:8765/callback")
    oauth.get_settings.cache_clear()
    yield
    oauth.get_settings.cache_clear()


def test_build_authorize_url_includes_required_params():
    state = oauth.generate_state()
    url = oauth.build_authorize_url(state)
    assert "client_id=test-app-id" in url
    assert f"state={state}" in url
    assert "response_type=code" in url
    assert "instagram_basic" in url


def test_generate_state_is_unique_and_url_safe():
    a, b = oauth.generate_state(), oauth.generate_state()
    assert a != b
    assert all(c.isalnum() or c in "-_" for c in a)


@respx.mock
def test_exchange_code_for_token_returns_data():
    respx.get(f"{BASE}/oauth/access_token").mock(
        return_value=httpx.Response(
            200, json={"access_token": "short-lived", "token_type": "bearer"}
        )
    )
    result = oauth.exchange_code_for_token("some-code")
    assert result["access_token"] == "short-lived"


@respx.mock
def test_exchange_code_for_token_raises_on_missing_access_token():
    respx.get(f"{BASE}/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"error": {"message": "bad code"}})
    )
    with pytest.raises(oauth.OAuthError):
        oauth.exchange_code_for_token("bad-code")


@respx.mock
def test_exchange_short_for_long_lived_token():
    respx.get(f"{BASE}/oauth/access_token").mock(
        return_value=httpx.Response(
            200, json={"access_token": "long-lived", "expires_in": 5184000}
        )
    )
    result = oauth.exchange_short_for_long_lived_token("short-lived")
    assert result["access_token"] == "long-lived"
    assert result["expires_in"] == 5184000


def test_compute_expiry_is_in_the_future():
    from datetime import UTC, datetime

    expiry = oauth.compute_expiry(60)
    assert expiry > datetime.now(UTC)
