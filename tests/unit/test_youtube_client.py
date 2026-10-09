import httpx
import pytest
import respx

from creatorsignal.research import youtube_client


def test_search_videos_raises_when_not_configured(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "")
    youtube_client.get_settings.cache_clear()
    with pytest.raises(youtube_client.YouTubeNotConfigured):
        youtube_client.search_videos("AI coding agents")
    youtube_client.get_settings.cache_clear()


@respx.mock
def test_search_videos_returns_raw_response(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
    youtube_client.get_settings.cache_clear()

    respx.get(youtube_client.SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [{"snippet": {"title": "AI Agents Explained"}}],
                "pageInfo": {"totalResults": 1234},
            },
        )
    )
    result = youtube_client.search_videos("AI coding agents")
    assert result["pageInfo"]["totalResults"] == 1234
    youtube_client.get_settings.cache_clear()
