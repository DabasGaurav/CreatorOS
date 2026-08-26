import voyageai

from creatoros.config import get_settings
from creatoros.utils.retry import with_backoff

RETRYABLE_EXCEPTIONS = (Exception,)  # voyageai raises its own exception types; narrowed below
try:  # pragma: no cover — exact exception class depends on the installed SDK version
    from voyageai.error import VoyageError

    RETRYABLE_EXCEPTIONS = (VoyageError,)
except ImportError:  # pragma: no cover
    pass


def _client() -> voyageai.Client:
    settings = get_settings()
    return voyageai.Client(api_key=settings.voyage_api_key)


@with_backoff(exceptions=RETRYABLE_EXCEPTIONS, max_attempts=3, initial=1.0, max_wait=10.0)
def embed_text(text: str, *, input_type: str = "document") -> list[float]:
    return embed_texts([text], input_type=input_type)[0]


@with_backoff(exceptions=RETRYABLE_EXCEPTIONS, max_attempts=3, initial=1.0, max_wait=10.0)
def embed_texts(texts: list[str], *, input_type: str = "document") -> list[list[float]]:
    settings = get_settings()
    result = _client().embed(
        texts, model=settings.voyage_embedding_model, input_type=input_type
    )
    return result.embeddings


def build_reel_embedding_text(*, caption: str | None, transcript: str | None) -> str:
    """The exact text-construction logic that feeds the embedding. If this changes,
    bump the `:v1` suffix in Settings.embedding_model_version — old and new vectors
    become incomparable even though the underlying Voyage model didn't change."""
    parts = [p for p in (caption, transcript) if p]
    return "\n\n".join(parts)
