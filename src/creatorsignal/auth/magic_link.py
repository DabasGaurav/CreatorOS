"""Magic-link sign-in (Build Doc 3 onboarding). Beta-scale simplification,
documented rather than hidden: a Session token proves the holder clicked a link
sent to a real creator's registered email at sign-in time. It is NOT re-verified
per API call — every endpoint still trusts whatever creator_id/request_id the
client supplies, same as before this feature existed. That's a real gap for a
public product; it's an acceptable one for a founder-onboarded beta of 15-30
known creators, matching how the spec itself defers "Advanced Access / public
self-serve onboarding" and other hardening to post-beta (A5, B17).
"""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session as DbSession

from creatorsignal.auth.resend_client import send_email
from creatorsignal.config import get_settings
from creatorsignal.db.models import Creator, MagicLinkToken
from creatorsignal.db.models import Session as SessionModel
from creatorsignal.utils.logging import get_logger

logger = get_logger(__name__)


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def _magic_link_email_html(link_url: str) -> str:
    return f"""
    <p>Click below to sign in to CreatorSignal.ai. This link expires in
    {get_settings().magic_link_token_ttl_minutes} minutes and works once.</p>
    <p><a href="{link_url}">Sign in to CreatorSignal.ai</a></p>
    <p>If you didn't request this, you can ignore this email.</p>
    """


def request_magic_link(db_session: DbSession, email: str) -> bool:
    """Returns True if an email was sent. Always returns quickly either way —
    callers should give the same response to the user regardless (don't leak
    which emails are registered)."""
    creator = db_session.query(Creator).filter(Creator.email == email).one_or_none()
    if creator is None:
        logger.info("Magic-link requested for unknown email %s", email)
        return False

    settings = get_settings()
    token = _generate_token()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.magic_link_token_ttl_minutes)
    db_session.add(MagicLinkToken(creator_id=creator.id, token=token, expires_at=expires_at))
    db_session.commit()

    link_url = f"{settings.frontend_base_url}/auth/verify?token={token}"
    send_email(
        to=email,
        subject="Sign in to CreatorSignal.ai",
        html=_magic_link_email_html(link_url),
    )
    return True


def verify_magic_link_token(db_session: DbSession, token: str) -> SessionModel | None:
    """Consumes the token (single-use) and issues a new Session. Returns None
    for an unknown, expired, or already-used token — the caller decides how to
    surface that (a 400, a "link expired" page, etc.), this function just
    reports validity."""
    record = db_session.query(MagicLinkToken).filter(MagicLinkToken.token == token).one_or_none()
    if record is None:
        return None
    if record.used_at is not None:
        return None
    if record.expires_at < datetime.now(UTC):
        return None

    record.used_at = datetime.now(UTC)

    settings = get_settings()
    session_row = SessionModel(
        creator_id=record.creator_id,
        token=_generate_token(),
        expires_at=datetime.now(UTC) + timedelta(days=settings.session_ttl_days),
    )
    db_session.add(session_row)
    db_session.commit()
    db_session.refresh(session_row)
    return session_row


def resolve_session(db_session: DbSession, session_token: str) -> SessionModel | None:
    """Looks up a session token, returning None if unknown or expired."""
    record = (
        db_session.query(SessionModel).filter(SessionModel.token == session_token).one_or_none()
    )
    if record is None:
        return None
    if record.expires_at < datetime.now(UTC):
        return None
    return record
