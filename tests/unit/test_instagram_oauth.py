import httpx
import pytest
import respx

from creatorsignal.instagram import oauth


@pytest.fixture(autouse=True)
def _meta_settings(monkeypatch):
    monkeypatch.setenv("META_APP_ID", "test-app-id")
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    monkeypatch.setenv("META_OAUTH_REDIRECT_URI", "http://localhost:8765/callback")
    oauth.get_settings.cache_clear()
    yield
    oauth.get_settings.cache_clear()


def test_build_authorize_url_uses_instagram_login_host():
    state = oauth.generate_state()
    url = oauth.build_authorize_url(state)
    assert url.startswith("https://www.instagram.com/oauth/authorize?")
    assert "client_id=test-app-id" in url
    assert f"state={state}" in url
    assert "response_type=code" in url
    assert "instagram_business_basic" in url


def test_generate_state_is_unique_and_url_safe():
    a, b = oauth.generate_state(), oauth.generate_state()
    assert a != b
    assert all(c.isalnum() or c in "-_" for c in a)


@respx.mock
def test_exchange_code_for_token_posts_to_api_instagram_com():
    route = respx.post("https://api.instagram.com/oauth/access_token").mock(
        return_value=httpx.Response(
            200, json={"access_token": "short-lived", "user_id": "17841400797801816"}
        )
    )
    result = oauth.exchange_code_for_token("some-code")
    assert result["access_token"] == "short-lived"
    assert result["user_id"] == "17841400797801816"
    assert route.calls[0].request.method == "POST"


@respx.mock
def test_exchange_code_for_token_raises_on_missing_access_token():
    respx.post("https://api.instagram.com/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"error_message": "bad code"})
    )
    with pytest.raises(oauth.OAuthError):
        oauth.exchange_code_for_token("bad-code")


@respx.mock
def test_exchange_short_for_long_lived_token_uses_ig_exchange_token():
    route = respx.get("https://graph.instagram.com/access_token").mock(
        return_value=httpx.Response(
            200, json={"access_token": "long-lived", "expires_in": 5184000}
        )
    )
    result = oauth.exchange_short_for_long_lived_token("short-lived")
    assert result["access_token"] == "long-lived"
    assert result["expires_in"] == 5184000
    assert route.calls[0].request.url.params["grant_type"] == "ig_exchange_token"


@respx.mock
def test_refresh_long_lived_token_uses_ig_refresh_token():
    route = respx.get("https://graph.instagram.com/refresh_access_token").mock(
        return_value=httpx.Response(
            200, json={"access_token": "refreshed", "expires_in": 5183312}
        )
    )
    result = oauth.refresh_long_lived_token("current-token")
    assert result["access_token"] == "refreshed"
    assert route.calls[0].request.url.params["grant_type"] == "ig_refresh_token"


@respx.mock
def test_refresh_long_lived_token_raises_on_missing_access_token():
    respx.get("https://graph.instagram.com/refresh_access_token").mock(
        return_value=httpx.Response(400, json={"error": {"message": "invalid session"}})
    )
    with pytest.raises((oauth.OAuthError, httpx.HTTPStatusError)):
        oauth.refresh_long_lived_token("bad-token")


def test_compute_expiry_is_in_the_future():
    from datetime import UTC, datetime

    expiry = oauth.compute_expiry(60)
    assert expiry > datetime.now(UTC)
