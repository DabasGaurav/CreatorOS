"""Refresh long-lived (60-day) tokens before they expire. Intended to run on a
schedule (e.g. daily) and refresh anyone within REFRESH_WINDOW of expiry."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from creatoros.db.models import Creator
from creatoros.instagram.oauth import compute_expiry, refresh_long_lived_token
from creatoros.security.crypto import decrypt_token, encrypt_token
from creatoros.utils.logging import get_logger

logger = get_logger(__name__)

REFRESH_WINDOW = timedelta(days=7)


def creators_due_for_refresh(session: Session, *, now: datetime | None = None) -> list[Creator]:
    cutoff = (now or datetime.now(UTC)) + REFRESH_WINDOW
    return session.query(Creator).filter(Creator.token_expires_at <= cutoff).all()


def refresh_creator_token(session: Session, creator: Creator) -> Creator:
    """Ongoing renewal for an already-long-lived Instagram Login token uses
    ig_refresh_token (refresh_long_lived_token), not the initial short-lived
    exchange — a distinct endpoint, confirmed against a real token."""
    current_token = decrypt_token(creator.token)
    result = refresh_long_lived_token(current_token)
    creator.token = encrypt_token(result["access_token"])
    creator.token_expires_at = compute_expiry(result.get("expires_in", 60 * 24 * 60 * 60))
    session.commit()
    session.refresh(creator)
    logger.info(
        "Refreshed token for creator %s, new expiry %s",
        creator.instagram_user_id,
        creator.token_expires_at,
    )
    return creator


def refresh_all_due(session: Session) -> list[Creator]:
    refreshed = []
    for creator in creators_due_for_refresh(session):
        try:
            refreshed.append(refresh_creator_token(session, creator))
        except Exception:
            logger.exception("Failed to refresh token for creator %s", creator.instagram_user_id)
    return refreshed
