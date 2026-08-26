#!/usr/bin/env python
"""Run one outcome-tracking pass for a connected creator (Build Doc 3 §3, B16).
Intended to run on a schedule (poll or webhook-triggered) — syncs fresh
Instagram data, detects whether a new Reel fulfills an unlinked recommendation,
and records the outcome automatically if so.

Usage:
    uv run python scripts/run_outcome_tracking.py --instagram-user-id 1789...
"""

import argparse
import sys

from creatoros.db.base import get_session
from creatoros.db.models import Creator
from creatoros.embeddings.qdrant_client import get_client
from creatoros.outcome.outcome_tracking import run_outcome_tracking_for_creator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instagram-user-id", required=True)
    args = parser.parse_args()

    session = get_session()
    creator = (
        session.query(Creator)
        .filter(Creator.instagram_user_id == args.instagram_user_id)
        .one_or_none()
    )
    if creator is None:
        print(f"No creator found with instagram_user_id={args.instagram_user_id}", file=sys.stderr)
        return 1

    qdrant = get_client()
    outcome = run_outcome_tracking_for_creator(session, qdrant, creator)
    if outcome is None:
        print("No new outcome to record yet.")
    else:
        print(f"Recorded outcome {outcome.id} for recommendation {outcome.recommendation_id}")
        print(f"  topic_match_score: {outcome.topic_match_score}")
        print(f"  actual_engagement_rate: {outcome.actual_engagement_rate}")
        print(f"  predicted_engagement: {outcome.predicted_engagement}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
