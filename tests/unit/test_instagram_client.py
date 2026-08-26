import httpx
import pytest
import respx

from creatoros.instagram.client import GraphAPIClient, GraphAPIError, RateLimitedError

BASE = "https://graph.instagram.com/v23.0"


@pytest.fixture
def client():
    c = GraphAPIClient("fake-token")
    yield c
    c.close()


@respx.mock
def test_iter_media_follows_pagination(client):
    respx.get(f"{BASE}/123/media").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": [{"id": "m1"}, {"id": "m2"}],
                    "paging": {"cursors": {"after": "CURSOR1"}, "next": "https://x/next"},
                },
            ),
            httpx.Response(
                200,
                json={"data": [{"id": "m3"}], "paging": {"cursors": {"after": "CURSOR2"}}},
            ),
        ]
    )

    media = list(client.iter_media("123"))
    assert [m["id"] for m in media] == ["m1", "m2", "m3"]


@respx.mock
def test_get_media_insights_returns_parsed_json(client):
    respx.get(f"{BASE}/m1/insights").mock(
        return_value=httpx.Response(
            200, json={"data": [{"name": "reach", "values": [{"value": 100}]}]}
        )
    )
    result = client.get_media_insights("m1")
    assert result["data"][0]["name"] == "reach"


@respx.mock
def test_rate_limited_response_raises_and_logs(client, caplog):
    respx.get(f"{BASE}/123/media").mock(return_value=httpx.Response(429, text="rate limited"))
    with pytest.raises(RateLimitedError):
        client.get_media_page("123")


@respx.mock
def test_client_error_raises_graph_api_error(client):
    respx.get(f"{BASE}/bad/media").mock(return_value=httpx.Response(400, text="bad request"))
    with pytest.raises(GraphAPIError) as exc_info:
        client.get_media_page("bad")
    assert exc_info.value.status_code == 400


@respx.mock
def test_server_error_is_retried_then_succeeds(client):
    route = respx.get(f"{BASE}/123/media")
    route.mock(
        side_effect=[
            httpx.Response(500, text="server error"),
            httpx.Response(200, json={"data": [{"id": "m1"}], "paging": {}}),
        ]
    )
    result = client.get_media_page("123")
    assert result["data"][0]["id"] == "m1"
    assert route.call_count == 2


@respx.mock
def test_get_media_insights_requests_views_not_plays(client):
    """Regression test: "plays" was rejected live by the current API — Meta
    renamed it to "views". Assert the client requests the current metric name."""
    route = respx.get(f"{BASE}/m1/insights").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    client.get_media_insights("m1")
    requested_metrics = route.calls[0].request.url.params["metric"]
    assert "views" in requested_metrics
    assert "plays" not in requested_metrics


@respx.mock
def test_get_account_profile_returns_username(client):
    respx.get(f"{BASE}/ig123").mock(
        return_value=httpx.Response(200, json={"id": "ig123", "username": "example_creator"})
    )
    profile = client.get_account_profile("ig123")
    assert profile["username"] == "example_creator"


@respx.mock
def test_high_usage_header_triggers_warning_log(client, caplog, monkeypatch):
    monkeypatch.setattr("creatoros.instagram.client.time.sleep", lambda _s: None)
    usage_header = '{"123": [{"call_count": 85}]}'
    respx.get(f"{BASE}/123/media").mock(
        return_value=httpx.Response(
            200,
            json={"data": [], "paging": {}},
            headers={"x-business-use-case-usage": usage_header},
        )
    )
    with caplog.at_level("WARNING"):
        client.get_media_page("123")
    assert any("Business Use Case" in record.message for record in caplog.records)
