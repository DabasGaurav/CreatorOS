#!/usr/bin/env python
"""Compute and store a new Creator DNA version for a connected creator
(Build Doc 1, §4.1). Run after scripts/run_sync.py has populated reels/reel_insights
and the embedding job has populated Qdrant.

Usage:
    uv run python scripts/run_dna.py --instagram-user-id 1789...
"""

import argparse
import sys

from creatoros.db.base import get_session
from creatoros.db.models import Creator
from creatoros.dna.job import compute_and_store_dna
from creatoros.embeddings.qdrant_client import get_client


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
    dna = compute_and_store_dna(session, qdrant, creator)
    print(f"Computed Creator DNA v{dna.version} for {creator.display_name}")
    print(f"  early_profile: {dna.early_profile}")
    print(f"  winning_topics: {dna.winning_topics}")
    print(f"  winning_hooks: {dna.winning_hooks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
