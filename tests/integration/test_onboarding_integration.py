"""Real Postgres round-trip for the invite -> connect onboarding flow (Build
Doc 3). Creates and cleans up its own throwaway rows — doesn't touch any real
creator."""

from datetime import UTC, datetime, timedelta

import pytest

from creatoros.db.models import Creator
from creatoros.instagram.repository import attach_instagram_account, invite_creator
from creatoros.security.crypto import decrypt_token

pytestmark = pytest.mark.integration


def test_invite_then_attach_instagram_account_roundtrip(db_session):
    email = f"integration-test-{datetime.now(UTC).timestamp()}@example.com"
    creator = invite_creator(db_session, email=email, niche="__integration_test__")
    try:
        assert creator.instagram_user_id is None
        assert creator.token is None

        connected = attach_instagram_account(
            db_session,
            creator_id=creator.id,
            instagram_user_id=f"ig-{creator.id}",
            display_name="Integration Test Creator",
            access_token="fake-long-lived-token",
            token_expires_at=datetime.now(UTC) + timedelta(days=60),
        )

        assert connected.instagram_user_id == f"ig-{creator.id}"
        assert connected.display_name == "Integration Test Creator"
        assert decrypt_token(connected.token) == "fake-long-lived-token"
    finally:
        db_session.delete(db_session.get(Creator, creator.id))
        db_session.commit()
