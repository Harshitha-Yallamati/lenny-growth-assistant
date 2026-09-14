# The Lenny Growth Assistant

A full-stack, RAG-powered conversational assistant over Lenny's Podcast transcripts. Ask grounded product/growth questions, generate Ship 30 for 30-style essays, and produce Markdown/HTML artifacts rendered in an in-app Artifact Viewer — all running locally on Ollama by default, with Anthropic/OpenAI as optional, config-only cloud providers.

See also: [PRD](docs/PRD.md) · [design.md](docs/design.md) · [architecture.md](docs/architecture.md) · [manual test plan](tests/manual_test_plan.md) · [agent transcripts](agent-transcripts/)

## Architecture overview

```
                    ┌─────────────┐
                    │   Frontend   │  React + TS (Vite), served by nginx
                    │ Chat + Artifact Viewer
                    └──────┬──────┘
                           │ REST (JSON)
                    ┌──────▼──────┐
                    │   Backend    │  FastAPI
                    │  api/ agent/ │
                    │  rag/ llm/   │
                    └──┬───────┬──┘
              ┌────────┘       └────────┐
      ┌───────▼──────┐          ┌───────▼───────┐
      │  PostgreSQL   │          │  LLM provider  │
      │ sessions,     │          │  Ollama (local,│
      │ messages,     │          │  mandatory) /  │
      │ chunks (FTS)  │          │  Anthropic /   │
      └──────────────┘          │  OpenAI        │
                                 └───────────────┘
```

Full detail (DB schema, API contracts, retrieval/agent flow, security) is in [architecture.md](docs/architecture.md).

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Compose v2+)
- [Ollama](https://ollama.com/) installed **on your host machine** (not in Docker) with at least one model pulled:
  ```bash
  ollama pull llama3.1
  ```
  The backend container reaches host Ollama via `host.docker.internal`.
- Optional, for cloud providers: an Anthropic and/or OpenAI API key.

## Installation & one-command startup

```bash
git clone <this-repo-url>
cd lenny-growth-assistant
cp .env.example .env
docker compose up --build
```

Then open:
- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

On first startup the backend automatically ingests the sample transcript corpus in `data/` into Postgres — no manual step required.

## Environment variables

All variables live in `.env` (copy from `.env.example`; **never commit `.env`**).

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | points at the `db` compose service | Only change if using an external Postgres |
| `LLM_PROVIDER` | yes | `ollama` | `ollama` \| `anthropic` \| `openai` — the default provider; can also be switched at runtime from the UI |
| `OLLAMA_BASE_URL` | yes | `http://host.docker.internal:11434` | Where the backend finds your host's Ollama |
| `OLLAMA_MODEL` | yes | `llama3.1` | Any model you've pulled |
| `ANTHROPIC_API_KEY` | no | empty | Leave blank to skip; falls back to Ollama automatically if selected without a key |
| `ANTHROPIC_MODEL` | no | `claude-sonnet-4-5-20250929` | |
| `OPENAI_API_KEY` | no | empty | Same fallback behavior as Anthropic |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | |
| `DATA_DIR` | no | `/app/data` | Transcript corpus location; only change for non-Docker local runs |
| `CORS_ORIGINS` | no | `http://localhost:5173` | Comma-separated |

## Local model setup (mandatory demo path)

1. Install Ollama: https://ollama.com/download
2. Pull a model that runs comfortably on your machine: `ollama pull llama3.1` (or `phi`, `qwen2.5:1.5b` for lighter hardware).
3. Make sure Ollama is running (`ollama serve`, or it's already running as a background service after install).
4. Leave `LLM_PROVIDER=ollama` in `.env` (the default) — no keys needed.

## Cloud model setup (optional)

1. Get an Anthropic key at https://console.anthropic.com/settings/keys (or an OpenAI key at https://platform.openai.com/api-keys).
2. Put it in `.env` as `ANTHROPIC_API_KEY=...` (or `OPENAI_API_KEY=...`).
3. Either set `LLM_PROVIDER=anthropic` (or `openai`) in `.env`, or leave the default and switch providers live from the model badge dropdown in the UI (`POST /api/config`).
4. If the key is missing or a request fails, the backend logs a warning and **automatically falls back to Ollama** rather than failing the chat — this is visible in the UI as a banner on the affected response.

## Run commands

```bash
docker compose up --build        # start everything
docker compose up -d --build     # start in the background
docker compose logs -f backend   # tail backend logs (structured JSON)
docker compose down              # stop everything
docker compose down -v           # stop and wipe the Postgres volume
```

Re-run ingestion manually after editing `data/sources.json` or a transcript, without restarting:
```bash
docker compose exec backend python -m scripts.ingest_transcripts
```

## Tests

Backend tests need a reachable Postgres — `docker compose up -d db` provisions a dedicated `lenny_growth_assistant_test` database automatically (see `db/init/`).

```bash
docker compose up -d db
cd backend
pip install -r requirements.txt
pytest
```

Frontend has no automated test suite in this MVP (documented scope exclusion — see PRD); a manual test plan covering the UI is in [tests/manual_test_plan.md](tests/manual_test_plan.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `GET /api/health` shows `providers.ollama: false` | Ollama isn't running, or the backend container can't reach it | Run `ollama serve` on the host; on Linux hosts, replace `host.docker.internal` with your host IP in `.env` |
| Chat replies "I couldn't reach the language model" | The active provider is down and there was nothing to fall back to (e.g. Ollama itself is down) | Check `ollama list`, ensure the model in `OLLAMA_MODEL` is actually pulled |
| Answers ignore transcript content / "not grounded" on everything | Ingestion didn't run | Check `docker compose logs backend \| grep ingest`; run `docker compose exec backend python -m scripts.ingest_transcripts` |
| `docker compose up` fails on `db` healthcheck | Port 5432 already in use by another Postgres | Stop the other instance, or change the host-side port mapping in `docker-compose.yml` |
| Frontend shows "Could not reach the backend" | Backend container not up yet, or CORS mismatch | Confirm `docker compose ps` shows backend healthy; confirm `CORS_ORIGINS` includes the frontend's origin |
| Anthropic/OpenAI selected but nothing happens | Missing/invalid API key | Check `GET /api/config` — `provider_status` shows which providers are actually reachable; the app should have silently fallen back to Ollama |

## Repository structure

```
backend/        FastAPI app (app/), tests/, ingestion script
frontend/       React + TS (Vite) app
data/           Curated transcript corpus + sources.json manifest
docs/           PRD, design.md, architecture.md
agent-transcripts/   Coding-agent session logs for this build
tests/          Manual UI test plan (backend tests live in backend/tests)
docker-compose.yml, .env.example
```

## Known scope exclusions (documented trade-offs)

See the PRD's "Scope choices" and "Risks and trade-offs" sections for the full list and rationale. In brief: no auth/multi-user accounts, no streaming responses, no Alembic migrations (schema created at startup), retrieval uses Postgres full-text search rather than a vector database, and the Anthropic path uses the native Anthropic Messages API tool-use pattern rather than the `claude-agent-sdk` package (avoids bundling a Node/CLI runtime for an optional, untested-at-build-time path).
