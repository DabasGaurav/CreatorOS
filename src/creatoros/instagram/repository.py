import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from creatoros.db.models import Creator, Reel, ReelInsight
from creatoros.security.crypto import encrypt_token


def upsert_creator(
    session: Session,
    *,
    instagram_user_id: str,
    display_name: str,
    niche: str,
    access_token: str,
    token_expires_at: datetime,
) -> Creator:
    creator = (
        session.query(Creator).filter(Creator.instagram_user_id == instagram_user_id).one_or_none()
    )
    encrypted = encrypt_token(access_token)
    if creator is None:
        creator = Creator(
            instagram_user_id=instagram_user_id,
            display_name=display_name,
            niche=niche,
            token=encrypted,
            token_expires_at=token_expires_at,
        )
        session.add(creator)
    else:
        creator.token = encrypted
        creator.token_expires_at = token_expires_at
        creator.display_name = display_name
        creator.niche = niche
    session.commit()
    session.refresh(creator)
    return creator


def parse_media_fields(raw_media: dict) -> dict:
    """Extract the metadata Build Doc 1 needs pulled out of raw_media_json so later
    jobs don't re-parse JSONB — spec doesn't guarantee duration on every media object
    (Reels vs. images), so this degrades to None rather than raising."""
    is_reel = raw_media.get("media_product_type") == "REELS"
    return {
        "duration_seconds": raw_media.get("video_duration") if is_reel else None,
        "media_product_type": raw_media.get("media_product_type"),
    }


def upsert_reel(session: Session, *, creator_id: uuid.UUID, raw_media: dict) -> Reel:
    instagram_media_id = raw_media["id"]
    reel = (
        session.query(Reel)
        .filter(Reel.creator_id == creator_id, Reel.instagram_media_id == instagram_media_id)
        .one_or_none()
    )
    extracted = parse_media_fields(raw_media)
    duration = extracted["duration_seconds"]
    posted_at = _parse_timestamp(raw_media.get("timestamp"))

    if reel is None:
        reel = Reel(
            creator_id=creator_id,
            instagram_media_id=instagram_media_id,
            caption=raw_media.get("caption"),
            posted_at=posted_at,
            raw_media_json=raw_media,
            duration_seconds=duration,
            media_product_type=extracted["media_product_type"],
        )
        session.add(reel)
    else:
        reel.caption = raw_media.get("caption")
        reel.posted_at = posted_at
        reel.raw_media_json = raw_media
        reel.duration_seconds = duration
        reel.media_product_type = extracted["media_product_type"]
    session.commit()
    session.refresh(reel)
    return reel


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        raise ValueError("Media object missing required 'timestamp' field")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_insights_metrics(raw_insights: dict) -> dict[str, int | None]:
    """Graph API returns {"data": [{"name": "reach", "values": [{"value": N}]}, ...]} —
    flatten into a simple metric -> value dict. Missing metrics are left None rather
    than defaulted to 0, so 'not returned by the API' stays distinguishable from 'zero'."""
    metrics: dict[str, int | None] = {
        "reach": None,
        "likes": None,
        "comments": None,
        "shares": None,
        "saves": None,
        "plays": None,
    }
    name_map = {"saved": "saves"}
    for entry in raw_insights.get("data", []):
        name = name_map.get(entry.get("name"), entry.get("name"))
        if name not in metrics:
            continue
        values = entry.get("values", [])
        if values:
            metrics[name] = values[0].get("value")
    return metrics


def add_reel_insight(session: Session, *, reel_id: uuid.UUID, raw_insights: dict) -> ReelInsight:
    metrics = parse_insights_metrics(raw_insights)
    row = ReelInsight(reel_id=reel_id, raw_insights_json=raw_insights, **metrics)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
