#!/usr/bin/env python
"""Connect a creator's Instagram Business/Creator account (Build Doc 1, §1.2 step 2).

Deliberately framework-free — no FastAPI yet. Prints the authorize URL, runs a
one-shot local HTTP server to catch the OAuth redirect, exchanges the code for a
long-lived token, resolves the linked Instagram Business Account via the user's
Facebook Pages, and upserts the creator row (token stored encrypted).

Usage:
    uv run python scripts/connect_creator.py --niche "AI/startups"
"""

import argparse
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from creatoros.db.base import get_session
from creatoros.instagram.client import GraphAPIClient
from creatoros.instagram.oauth import (
    build_authorize_url,
    compute_expiry,
    exchange_code_for_token,
    exchange_short_for_long_lived_token,
    generate_state,
)
from creatoros.instagram.repository import upsert_creator


class _CallbackResult:
    code: str | None = None
    state: str | None = None
    error: str | None = None


def _run_callback_server(expected_state: str, port: int, result: _CallbackResult) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 — required method name for BaseHTTPRequestHandler
            query = parse_qs(urlparse(self.path).query)
            if query.get("state", [None])[0] != expected_state:
                result.error = "state mismatch — possible CSRF, aborting"
            elif "code" in query:
                result.code = query["code"][0]
                result.state = query["state"][0]
            else:
                result.error = query.get("error_description", ["unknown error"])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            message = "You can close this tab." if result.code else f"Error: {result.error}"
            self.wfile.write(message.encode())

        def log_message(self, format, *args):  # noqa: A002 — silence default request logging
            pass

    server = HTTPServer(("localhost", port), Handler)
    server.handle_request()  # single request, then stop
    server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--niche", required=True, help="Creator's niche, e.g. 'AI/startups'")
    parser.add_argument("--port", type=int, default=8765, help="Local callback listener port")
    args = parser.parse_args()

    state = generate_state()
    result = _CallbackResult()
    server_thread = threading.Thread(
        target=_run_callback_server, args=(state, args.port, result), daemon=True
    )
    server_thread.start()

    url = build_authorize_url(state)
    print(f"Open this URL to connect an Instagram account:\n\n{url}\n")
    print(f"Waiting for the OAuth redirect on http://localhost:{args.port}/callback ...")
    server_thread.join(timeout=300)

    if result.error:
        print(f"OAuth failed: {result.error}", file=sys.stderr)
        return 1
    if not result.code:
        print("Timed out waiting for the OAuth redirect.", file=sys.stderr)
        return 1

    print("Exchanging code for a short-lived token...")
    short_lived = exchange_code_for_token(result.code)

    print("Exchanging for a long-lived (60-day) token...")
    long_lived = exchange_short_for_long_lived_token(short_lived["access_token"])
    access_token = long_lived["access_token"]
    expires_at = compute_expiry(long_lived.get("expires_in", 60 * 24 * 60 * 60))

    print("Resolving the linked Instagram Business Account...")
    with GraphAPIClient(access_token) as client:
        pages = client.get_pages()
        if not pages:
            print("No Facebook Pages found for this account.", file=sys.stderr)
            return 1

        ig_user_id = None
        for page in pages:
            ig_user_id = client.get_instagram_business_account(page["id"])
            if ig_user_id:
                break

        if not ig_user_id:
            print(
                "No linked Instagram Business/Creator account found on any Page. "
                "The account must be Business/Creator type and linked to a Facebook Page.",
                file=sys.stderr,
            )
            return 1

        profile = client.get_account_profile(ig_user_id)

    session = get_session()
    creator = upsert_creator(
        session,
        instagram_user_id=ig_user_id,
        display_name=profile.get("username", ig_user_id),
        niche=args.niche,
        access_token=access_token,
        token_expires_at=expires_at,
    )
    print(f"Connected creator {creator.display_name} (id={creator.id}, ig_user_id={ig_user_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
