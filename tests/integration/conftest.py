import pytest

from creatoros.config import get_settings


def _require(value: str, var_name: str):
    if not value:
        pytest.skip(f"{var_name} not set in .env — skipping integration test")


@pytest.fixture
def db_session():
    settings = get_settings()
    _require(settings.database_url, "DATABASE_URL")
    from creatoros.db.base import get_session

    session = get_session()
    yield session
    session.close()


@pytest.fixture
def qdrant_real_client():
    settings = get_settings()
    _require(settings.qdrant_url, "QDRANT_URL")
    _require(settings.qdrant_api_key, "QDRANT_API_KEY")
    from creatoros.embeddings.qdrant_client import get_client

    return get_client()
