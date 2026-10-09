"""Tester-invite tracking.

Confirmed against Meta's current docs: adding an Instagram Tester is a manual
App Dashboard action (Roles -> Instagram Testers, username entered by hand) — there
is no public Graph API endpoint for it. This module does not attempt to call one;
it just prints the manual steps and records invite status in a small local JSON
file (not a Postgres table — this is a low-volume, founder-run admin step at beta
scale, and each CLI invocation is a separate process, so an in-memory dict alone
wouldn't persist between runs).
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

_STORE_PATH = Path(__file__).resolve().parents[3] / ".tester_invites.json"


class InviteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"


@dataclass
class TesterInviteRecord:
    instagram_handle: str
    status: InviteStatus
    recorded_at: str


def _load() -> dict[str, dict]:
    if not _STORE_PATH.exists():
        return {}
    return json.loads(_STORE_PATH.read_text())


def _save(data: dict[str, dict]) -> None:
    _STORE_PATH.write_text(json.dumps(data, indent=2, sort_keys=True))


def print_manual_invite_instructions(instagram_handle: str) -> None:
    print(  # noqa: T201 — this is a CLI-facing admin instruction, not app logging
        f"""
Manual step required — Meta has no API for this:
  1. Go to your Meta App Dashboard -> Roles -> Instagram Testers.
  2. Enter the Instagram username: {instagram_handle}
  3. Submit the invite.
  4. Ask the creator to open Instagram -> Settings -> Apps and Websites ->
     Tester Invites, and accept.
"""
    )


def record_invite_sent(instagram_handle: str) -> TesterInviteRecord:
    record = TesterInviteRecord(
        instagram_handle=instagram_handle,
        status=InviteStatus.PENDING,
        recorded_at=datetime.now(UTC).isoformat(),
    )
    data = _load()
    data[instagram_handle] = asdict(record)
    _save(data)
    return record


def record_invite_accepted(instagram_handle: str) -> TesterInviteRecord:
    data = _load()
    existing = data.get(instagram_handle)
    record = TesterInviteRecord(
        instagram_handle=instagram_handle,
        status=InviteStatus.ACCEPTED,
        recorded_at=existing["recorded_at"] if existing else datetime.now(UTC).isoformat(),
    )
    data[instagram_handle] = asdict(record)
    _save(data)
    return record


def get_invite_status(instagram_handle: str) -> InviteStatus | None:
    data = _load()
    record = data.get(instagram_handle)
    return InviteStatus(record["status"]) if record else None
