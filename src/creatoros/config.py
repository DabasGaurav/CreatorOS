from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Meta / Instagram Graph API
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_oauth_redirect_uri: str = "http://localhost:8765/callback"
    graph_api_version: str = "v21.0"

    # Postgres
    database_url: str = "postgresql+psycopg://user:password@localhost/creatoros"

    # Token encryption
    token_encryption_key: str = ""

    # Voyage AI
    voyage_api_key: str = ""
    voyage_embedding_model: str = "voyage-3-lite"

    # Qdrant
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "reels"

    # Creator DNA job defaults
    creator_dna_early_profile_threshold: int = Field(default=15)
    creator_dna_recent_fatigue_window: int = Field(default=10)
    creator_dna_default_primary_kpi: str = "reach"
    personal_novelty_window: int = Field(default=10)

    log_level: str = "INFO"

    @property
    def embedding_model_version(self) -> str:
        """Bump the `:v1` suffix whenever caption+transcript text construction changes,
        not only when the Voyage model changes — both break vector comparability."""
        return f"{self.voyage_embedding_model}:v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
