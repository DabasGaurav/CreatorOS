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

## External accounts needed for Build Doc 1 (see `.env.example` for the exact variables)

- **Meta Developer app** — Instagram Graph API product, target account added as a Tester. See `META_APP_ID` / `META_APP_SECRET` / `META_OAUTH_REDIRECT_URI`.
- **Neon Postgres** (free tier) — `DATABASE_URL`.
- **Voyage AI** — `VOYAGE_API_KEY`.
- **Qdrant Cloud** (free tier) — `QDRANT_URL` / `QDRANT_API_KEY`.

`TOKEN_ENCRYPTION_KEY` is self-generated locally, no external account needed:

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Status

All of Build Doc 1's logic is written and unit-tested (102 tests, no live credentials
required) — data model, migrations, token encryption, `niche_signal` CLI, Instagram
Graph API client/OAuth/sync/token-refresh, Voyage+Qdrant embeddings with
CreatorFit/PersonalNovelty, and the Creator DNA aggregation job. What's blocked on
external accounts (`.env` values above) before the Definition of Done can be verified
end-to-end:

1. `uv run alembic upgrade head` — apply the schema to a real Neon Postgres.
2. `uv run python scripts/seed_niche_signal.py add ...` — closes the `niche_signal` DoD
   item immediately once Postgres exists (no Instagram/Voyage/Qdrant dependency).
3. `uv run python scripts/connect_creator.py --niche "..."` — OAuth-connect a real
   Instagram Business/Creator account (needs the Meta app + Tester invite accepted).
4. `uv run python scripts/run_sync.py --instagram-user-id ...` — pull real history.
5. `uv run python scripts/run_dna.py --instagram-user-id ...` — compute the first
   real Creator DNA version (needs Voyage/Qdrant for the embeddings it reads).

Once all five Definition-of-Done checks in the build doc pass, Build Doc 2 (the
on-demand recommendation engine) can start.
