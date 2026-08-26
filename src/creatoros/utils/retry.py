from collections.abc import Callable
from typing import TypeVar

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

T = TypeVar("T")


def with_backoff(
    *,
    exceptions: tuple[type[Exception], ...],
    max_attempts: int = 5,
    initial: float = 1.0,
    max_wait: float = 30.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Exponential backoff with jitter, retrying only on the given exception types."""
    return retry(
        retry=retry_if_exception_type(exceptions),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=initial, max=max_wait),
        reraise=True,
    )
