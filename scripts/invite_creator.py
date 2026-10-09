#!/usr/bin/env python
"""Invite a beta creator by email (Build Doc 3 onboarding). Creates a bare
creator row (email + niche only) — they sign in via magic link and connect
their own Instagram account from the web app afterward.

Usage:
    uv run python scripts/invite_creator.py --email creator@example.com --niche "AI/startups"
"""

import argparse

from creatorsignal.db.base import get_session
from creatorsignal.instagram.repository import invite_creator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--niche", required=True)
    args = parser.parse_args()

    session = get_session()
    creator = invite_creator(session, email=args.email, niche=args.niche)
    print(f"Invited creator {creator.id} ({args.email}, niche={args.niche})")
    print("They can now request a magic-link sign-in at /auth/signin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
