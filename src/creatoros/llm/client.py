"""Shared Anthropic API access for every LLM-touching node (Market Researcher,
Opportunity Generator, LLM Reranker, Content Generator). Model tiering per A6:
Haiku for research/generation-volume steps, Sonnet for reranking/final content.
"""

import anthropic
from pydantic import BaseModel

from creatoros.config import get_settings
from creatoros.utils.retry import with_backoff

RETRYABLE_EXCEPTIONS = (
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
)


def get_anthropic_client() -> anthropic.Anthropic:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


@with_backoff(exceptions=RETRYABLE_EXCEPTIONS, max_attempts=4, initial=2.0, max_wait=30.0)
def parse_structured(
    *,
    model: str,
    system: str,
    messages: list[dict],
    output_format: type[BaseModel],
    max_tokens: int = 4096,
    client: anthropic.Anthropic | None = None,
):
    """Returns a validated instance of `output_format`, via client.messages.parse
    (structured outputs) — never freeform text the caller has to hope parses."""
    anthropic_client = client or get_anthropic_client()
    response = anthropic_client.messages.parse(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        output_format=output_format,
    )
    return response.parsed_output
