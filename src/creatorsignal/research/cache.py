"""TTL cache keyed by (source, query, date-bucket) — wraps every external research
call so the Market Researcher's refine/retry loop doesn't burn quota or cost during
development, and so repeated queries within the TTL window are free (B4 step 5,
B7 step 4). Backed by Postgres (db.models.ExternalResultCache) so it survives
process restarts — a plain in-memory cache would defeat the point during iterative
local development.
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from creatorsignal.db.models import ExternalResultCache
from creatorsignal.utils.logging import get_logger

logger = get_logger(__name__)


def _date_bucket(now: datetime) -> str:
    """Coarse date bucket, not a full timestamp — deliberately imprecise so
    near-identical queries within the same window hit the same cache key."""
    return now.strftime("%Y-%m-%d-%H")


def _cache_key(source: str, query: str, date_bucket: str) -> str:
    raw = f"{source}:{query}:{date_bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached(session: Session, *, source: str, query: str, ttl_hours: int) -> Any | None:
    now = datetime.now(UTC)
    key = _cache_key(source, query, _date_bucket(now))
    row = session.get(ExternalResultCache, key)
    if row is None:
        return None
    if row.cached_at < now - timedelta(hours=ttl_hours):
        return None
    return json.loads(row.result_json)


def set_cached(session: Session, *, source: str, query: str, result: Any) -> None:
    now = datetime.now(UTC)
    bucket = _date_bucket(now)
    key = _cache_key(source, query, bucket)
    existing = session.get(ExternalResultCache, key)
    if existing:
        existing.result_json = json.dumps(result)
        existing.cached_at = now
    else:
        session.add(
            ExternalResultCache(
                cache_key=key,
                source=source,
                query=query,
                date_bucket=bucket,
                result_json=json.dumps(result),
                cached_at=now,
            )
        )
    session.commit()
