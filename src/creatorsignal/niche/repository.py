from datetime import UTC, datetime

from sqlalchemy.orm import Session

from creatorsignal.db.models import NicheSignal


def add_niche_signal(
    session: Session,
    *,
    niche: str,
    account_handle: str,
    observed_topic: str,
    added_by: str,
    note: str | None = None,
    observed_at: datetime | None = None,
) -> NicheSignal:
    row = NicheSignal(
        niche=niche,
        account_handle=account_handle,
        observed_topic=observed_topic,
        note=note,
        observed_at=observed_at or datetime.now(UTC),
        added_by=added_by,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_niche_signal(session: Session, *, niche: str | None = None) -> list[NicheSignal]:
    query = session.query(NicheSignal)
    if niche:
        query = query.filter(NicheSignal.niche == niche)
    return query.order_by(NicheSignal.observed_at.desc()).all()
