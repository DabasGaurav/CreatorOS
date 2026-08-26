from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Meta / Instagram Graph API
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_oauth_redirect_uri: str = "http://localhost:8765/callback"
    graph_api_version: str = "v23.0"

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

    # Anthropic API (Build Doc 2) — pay-as-you-go console.anthropic.com key,
    # not a Claude subscription. Haiku for research/generation-volume steps,
    # Sonnet for reranking/final content, per the spec's cost-tiering (A6).
    anthropic_api_key: str = ""
    model_haiku: str = "claude-haiku-4-5"
    model_sonnet: str = "claude-sonnet-5"

    # Market Researcher external sources — all optional; the agent falls back
    # to cached category-level data when a source has no credentials.
    youtube_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "CreatorOS/0.1 (research agent)"

    market_researcher_max_iterations: int = Field(default=5)
    external_cache_ttl_hours: int = Field(default=12)

    opportunity_candidate_min: int = Field(default=20)
    opportunity_candidate_max: int = Field(default=50)

    # Epsilon-greedy explore/exploit (B11) — spec: ~85/15 split, exploration
    # candidates must still clear a minimum quality floor (top-40th-percentile).
    epsilon_explore_rate: float = Field(default=0.15)
    explore_quality_floor_percentile: float = Field(default=0.40)

    # CompositeScore weights (B8) — hand-set Phase-1 priors, explicitly not
    # empirically learned yet (no outcome data exists to learn them from).
    # Spec states this should be domain-reasoning guesses; starting equal-
    # weighted is the most honest "we don't know yet" prior, documented here
    # rather than picking arbitrary unequal numbers with no basis.
    weight_creator_fit: float = Field(default=0.2)
    weight_audience_demand: float = Field(default=0.2)
    weight_trend_momentum: float = Field(default=0.2)
    weight_novelty: float = Field(default=0.2)
    weight_expected_engagement: float = Field(default=0.2)

    # Resend (Build Doc 3 — magic-link auth). Beta scale (15-30 creators): the
    # default "onboarding@resend.dev" sender only delivers to the Resend
    # account's own verified email without a custom domain — fine for testing,
    # swap in a verified domain before real beta creators sign in.
    resend_api_key: str = ""
    resend_from_email: str = "CreatorOS <onboarding@resend.dev>"
    frontend_base_url: str = "http://localhost:3000"
    magic_link_token_ttl_minutes: int = Field(default=15)
    session_ttl_days: int = Field(default=30)

    @property
    def embedding_model_version(self) -> str:
        """Bump the `:v1` suffix whenever caption+transcript text construction changes,
        not only when the Voyage model changes — both break vector comparability."""
        return f"{self.voyage_embedding_model}:v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
