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
