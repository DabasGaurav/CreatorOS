"""Runs the real outcome-detection query logic against whatever real creator,
recommendations, and reels already exist in this environment's Postgres (from
connect_creator.py / run_sync.py / the FastAPI backend during manual testing).
Skips cleanly if there's nothing to work with — it can't fabricate a real
creator or recommendation."""

import pytest

from creatorsignal.db.models import Creator, Outcome, Recommendation
from creatorsignal.outcome.outcome_tracking import _oldest_unlinked_recommendation

pytestmark = pytest.mark.integration


def test_oldest_unlinked_recommendation_excludes_already_linked(db_session):
    creator = db_session.query(Creator).first()
    if creator is None:
        pytest.skip("No creator connected in this environment")

    completed = (
        db_session.query(Recommendation)
        .filter(Recommendation.creator_id == creator.id, Recommendation.status == "completed")
        .all()
    )
    if not completed:
        pytest.skip("No completed recommendations for this creator yet")

    result = _oldest_unlinked_recommendation(db_session, creator.id)

    if result is not None:
        # Whatever it returns must genuinely have no linked outcome yet.
        linked = db_session.query(Outcome).filter(Outcome.recommendation_id == result.id).first()
        assert linked is None
        # And it must be the oldest such one, not just any unlinked one.
        earlier_unlinked = [
            r
            for r in completed
            if r.created_at < result.created_at
            and db_session.query(Outcome).filter(Outcome.recommendation_id == r.id).first() is None
        ]
        assert earlier_unlinked == []
