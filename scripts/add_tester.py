#!/usr/bin/env python
"""Record + print instructions for adding a beta creator as a Meta App Tester
(Build Doc 1, §1.2 step 3). This is a manual App Dashboard action — Meta exposes
no API for it — this script just prints the steps and tracks invite status.

Usage:
    uv run python scripts/add_tester.py --handle @example_creator --sent
    uv run python scripts/add_tester.py --handle @example_creator --accepted
"""

import argparse

from creatoros.instagram.tester_admin import (
    get_invite_status,
    print_manual_invite_instructions,
    record_invite_accepted,
    record_invite_sent,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handle", required=True, help="Instagram username, e.g. @example")
    parser.add_argument("--sent", action="store_true", help="Mark the invite as sent")
    parser.add_argument("--accepted", action="store_true", help="Mark the invite as accepted")
    args = parser.parse_args()

    if args.accepted:
        record_invite_accepted(args.handle)
    elif args.sent:
        print_manual_invite_instructions(args.handle)
        record_invite_sent(args.handle)
    else:
        print(f"Current status for {args.handle}: {get_invite_status(args.handle)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
