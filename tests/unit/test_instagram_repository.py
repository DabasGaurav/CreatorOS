
import pytest
from cryptography.fernet import Fernet

from creatoros.instagram import repository
from creatoros.security import crypto


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    crypto.get_settings.cache_clear()
    yield
    crypto.get_settings.cache_clear()


def test_parse_media_fields_extracts_duration_for_reels():
    raw = {"media_product_type": "REELS", "video_duration": 27.5}
    fields = repository.parse_media_fields(raw)
    assert fields["duration_seconds"] == 27.5
    assert fields["media_product_type"] == "REELS"


def test_parse_media_fields_no_duration_for_non_reel():
    raw = {"media_product_type": "IMAGE"}
    fields = repository.parse_media_fields(raw)
    assert fields["duration_seconds"] is None


def test_parse_insights_metrics_flattens_and_maps_saved_to_saves():
    raw = {
        "data": [
            {"name": "reach", "values": [{"value": 1000}]},
            {"name": "saved", "values": [{"value": 12}]},
            {"name": "likes", "values": [{"value": 50}]},
        ]
    }
    metrics = repository.parse_insights_metrics(raw)
    assert metrics["reach"] == 1000
    assert metrics["saves"] == 12
    assert metrics["likes"] == 50
    assert metrics["comments"] is None


def test_parse_insights_metrics_missing_data_defaults_to_none():
    metrics = repository.parse_insights_metrics({"data": []})
    assert all(v is None for v in metrics.values())


def test_parse_timestamp_handles_zulu_suffix():
    dt = repository._parse_timestamp("2026-01-15T10:00:00Z")
    assert dt.tzinfo is not None
    assert dt.year == 2026


def test_parse_timestamp_raises_on_missing_value():
    with pytest.raises(ValueError):
        repository._parse_timestamp(None)
