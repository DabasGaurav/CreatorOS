# CreatorOS

An agentic recommendation system for a single Instagram Reels creator: what to create next, backed by evidence, generated on demand.

This repo is being built in three phases, each handed off and verified independently:

- **Build Doc 1 — Data Foundation & Creator DNA** *(this phase)*: Instagram Graph API sync, Postgres schema, Qdrant embedding pipeline, deterministic Creator DNA aggregation. No LLM pipeline, no agent, no frontend.
- Build Doc 2 — On-Demand Recommendation Engine (LangGraph, ranking, LLM reranker/content generation) — not started.
- Build Doc 3 — Web App & Outcome Loop (Next.js frontend, automated outcome tracking) — not started.

## Setup

```bash
uv sync --group dev
cp .env.example .env   # fill in as credentials become available — see checkpoints below
```

## Running tests

```bash
uv run pytest                 # fast suite — no external credentials required
uv run pytest -m integration  # requires real Postgres/Meta/Voyage/Qdrant credentials in .env
```

`TOKEN_ENCRYPTION_KEY` is self-generated locally, no external account needed:

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Status: Build Doc 1 Definition of Done — VERIFIED ✅

All five DoD criteria have been checked against real infrastructure (real Neon
Postgres, real Qdrant Cloud cluster, real Voyage AI embeddings, a real Instagram
account's Graph API data). 109 tests total: 102 unit (no credentials needed) + 7
integration (require the `.env` credentials below), all passing.

1. ✅ A real Instagram Business/Creator account is connected, token stored encrypted.
2. ✅ Sync populated `reels`/`reel_insights` with real data, cross-checked against
   the raw API responses seen during integration testing.
3. ✅ The Creator DNA job produced a real profile (correctly flagged `early_profile`
   given the small real dataset — 9 reels, below the 15-reel threshold).
4. ✅ Qdrant holds one point per captioned reel; `CreatorFit` ranked a
   topically-similar query above a dissimilar one on real embeddings.
5. ✅ `niche_signal` CLI insert/list round-trips against real Postgres (smoke-tested
   and cleaned up — real curated rows are still up to the founder to add weekly).

### Real-world corrections made during integration testing (2026-08-26)

The original spec assumed the classic **Facebook Login** Graph API flow
(`graph.facebook.com`, requires a linked Facebook Page). The actual live token
tested against this project came from Meta's newer **Instagram API with Instagram
Login** product instead — direct Instagram Business/Creator login, **no Facebook
Page required at all**. This is a meaningful, positive correction to A11's stated
onboarding requirement, not a deviation:

- Host is `graph.instagram.com` (not `graph.facebook.com`) — confirmed live;
  `graph.facebook.com` rejected the token outright.
- OAuth endpoints differ: authorize at `www.instagram.com/oauth/authorize`, code
  exchange is a **POST** to `api.instagram.com/oauth/access_token` (not GET), and
  ongoing token renewal uses `ig_refresh_token` (not another `fb_exchange_token`
  call) — see `oauth.py`.
- The `/insights` metric is `views`, not `plays` (Meta renamed it since the spec
  was written) — confirmed via a live 400 error listing valid metric names.
- **The IG Media object has no duration field at all**, on any API version
  (confirmed against Meta's own field reference) — `reels.duration_seconds` will
  stay `None` for real data until/unless a future phase downloads and inspects the
  video file directly. `typical_length_range` and duration-bucketed formats
  already degrade gracefully to unknown rather than crash.
- Bumped the default `GRAPH_API_VERSION` from `v21.0` to `v23.0` (both work; v23
  is more current — Meta's own pagination links resolved to v26 during testing).

## External accounts needed for Build Doc 1 (see `.env.example` for the exact variables)

- **Meta Developer app** (Instagram API with Instagram Login product) — `META_APP_ID` /
  `META_APP_SECRET` / `META_OAUTH_REDIRECT_URI`. No Facebook Page needed (see above).
- **Neon Postgres** (free tier) — `DATABASE_URL`.
- **Voyage AI** — `VOYAGE_API_KEY`.
- **Qdrant Cloud** (free tier) — `QDRANT_URL` / `QDRANT_API_KEY`.

`TOKEN_ENCRYPTION_KEY` is self-generated locally, no external account needed — see
the Setup section above.

Build Doc 2 (the on-demand recommendation engine) can now start.
