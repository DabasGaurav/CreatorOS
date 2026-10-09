"""Thin httpx wrapper over Resend's transactional email API — used only for
magic-link sign-in emails (Build Doc 3 onboarding)."""

import httpx

from creatorsignal.config import get_settings
from creatorsignal.utils.retry import with_backoff

RESEND_URL = "https://api.resend.com/emails"

RETRYABLE_EXCEPTIONS = (httpx.TransportError,)


class ResendNotConfigured(Exception):
    pass


class ResendSendError(Exception):
    pass


@with_backoff(exceptions=RETRYABLE_EXCEPTIONS, max_attempts=3, initial=1.0, max_wait=10.0)
def send_email(
    *, to: str, subject: str, html: str, http_client: httpx.Client | None = None
) -> dict:
    settings = get_settings()
    if not settings.resend_api_key:
        raise ResendNotConfigured("RESEND_API_KEY not set")

    client = http_client or httpx.Client(timeout=15.0)
    response = client.post(
        RESEND_URL,
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={
            "from": settings.resend_from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        },
    )
    if response.status_code >= 400:
        raise ResendSendError(f"Resend send failed ({response.status_code}): {response.text}")
    return response.json()
