#!/usr/bin/env python
"""Run the historical Reel + insights sync for a connected creator (Build Doc 1, §1.2 step 5).

Usage:
    uv run python scripts/run_sync.py --instagram-user-id 1789...
"""

import argparse
import sys

from creatoros.db.base import get_session
from creatoros.db.models import Creator
from creatoros.instagram.sync import sync_creator_history


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
        print("Run scripts/connect_creator.py first.", file=sys.stderr)
        return 1

    reels = sync_creator_history(session, creator)
    print(f"Synced {len(reels)} reels for {creator.display_name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
