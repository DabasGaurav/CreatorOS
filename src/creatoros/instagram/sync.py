"""Historical sync job: pull every Reel + its insights for a connected creator via the
Graph API and upsert into Postgres. Safe to rerun — upserts by instagram_media_id, and
every raw API response is stored verbatim before any transform (§1.2 step 5)."""

from sqlalchemy.orm import Session

from creatoros.db.models import Creator, Reel
from creatoros.instagram.client import GraphAPIClient
from creatoros.instagram.repository import add_reel_insight, upsert_reel
from creatoros.security.crypto import decrypt_token
from creatoros.utils.logging import get_logger

logger = get_logger(__name__)


def sync_creator_history(session: Session, creator: Creator) -> list[Reel]:
    token = decrypt_token(creator.token)
    synced: list[Reel] = []

    with GraphAPIClient(token) as client:
        for raw_media in client.iter_media(creator.instagram_user_id):
            reel = upsert_reel(session, creator_id=creator.id, raw_media=raw_media)
            try:
                raw_insights = client.get_media_insights(raw_media["id"])
            except Exception:
                logger.exception(
                    "Failed to fetch insights for media %s — skipping this reel's insights",
                    raw_media["id"],
                )
                synced.append(reel)
                continue
            add_reel_insight(session, reel_id=reel.id, raw_insights=raw_insights)
            synced.append(reel)

    logger.info("Synced %d reels for creator %s", len(synced), creator.instagram_user_id)
    return synced
