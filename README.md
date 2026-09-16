# The Lenny Growth Assistant

A full-stack, RAG-powered conversational assistant over Lenny's Podcast transcripts. Ask grounded product/growth questions, generate Ship 30 for 30-style essays, and produce Markdown/HTML artifacts rendered in an in-app Artifact Viewer — all running locally on Ollama by default, with Anthropic/OpenAI as optional, config-only cloud providers.

See also: [PRD](docs/PRD.md) · [design.md](docs/design.md) · [architecture.md](docs/architecture.md) · [manual test plan](tests/manual_test_plan.md) · [agent transcripts](agent-transcripts/) · [demo script](docs/demo-script.md)

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
- Optional, for cloud providers: an Anthropic and/or OpenAI API key. (The Anthropic path uses the Claude Agent SDK, which needs Node.js + the Claude Code CLI — both are installed inside the backend image, nothing to do on your host.)

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
| `OLLAMA_TIMEOUT_SECONDS` | no | `600` | Raise if long generations time out on slow hardware |
| `SHIP30_MAX_RETRIES` | no | `2` | Expansion passes allowed before shipping the best draft. Lower to `1` for a faster, less compliant demo |
| `ANTHROPIC_API_KEY` | no | empty | Leave blank to skip. Falls back to Ollama if absent **or** if a live request fails (bad/expired key, rate limit) |
| `ANTHROPIC_MODEL` | no | `claude-opus-5` | |
| `OPENAI_API_KEY` | no | empty | Same fallback behavior as Anthropic |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | |
| `DATA_DIR` | no | `/app/data` | Transcript corpus location; only change for non-Docker local runs |
| `CORS_ORIGINS` | no | `http://localhost:5173` | Comma-separated |

## Local model setup (mandatory demo path)

1. Install Ollama: https://ollama.com/download
2. Pull a model that runs comfortably on your machine: `ollama pull llama3.1` (or `phi`, `qwen2.5:1.5b` for lighter hardware).
3. Make sure Ollama is running (`ollama serve`, or it's already running as a background service after install).
4. Leave `LLM_PROVIDER=ollama` in `.env` (the default) — no keys needed.

### What to expect on local hardware

Measured on a CPU-only Windows laptop with `llama3.1` (8B), so you know what's normal vs. broken:

| Action | Measured time |
|---|---|
| First message after startup (model cold-load) | ~50–60s |
| Subsequent grounded Q&A | ~20–40s |
| Ship 30 essay (~1,250 words, up to 3 passes) | **~18–30 minutes** |

The Ship 30 skill is genuinely slow on CPU: it generates long-form output, then re-runs expansion passes until the draft satisfies the rubric's hard requirements (length, `## ` headings, a bulleted list, a `## The Takeaway` section) or `SHIP30_MAX_RETRIES` is exhausted. An 8B local model needs them — measured drafts came in at 633–697 words against a 1,000-word floor, and often with zero `## ` headings until the prompt was given an explicit structural skeleton. That's expected, not a hang.

Compliance is best-effort by design: the skill detects every unmet requirement and logs it (`ship30_requirements_unmet`), but it will ship the best draft it got rather than loop forever. A larger local model or a cloud provider clears the bar far more reliably than `llama3.1`.

**If you're demoing or evaluating, don't wait on this path with `llama3.1`.** Either set `OLLAMA_MODEL=qwen2.5:1.5b` for a dramatically faster (lower-quality) run, use a cloud provider, or generate the essay ahead of time. `OLLAMA_TIMEOUT_SECONDS` defaults to 600s **per call** — that covers each pass individually, but raise it if you see the timeout message.

## Cloud model setup (optional)

1. Get an Anthropic key at https://console.anthropic.com/settings/keys (or an OpenAI key at https://platform.openai.com/api-keys).
2. Put it in `.env` as `ANTHROPIC_API_KEY=...` (or `OPENAI_API_KEY=...`).
3. Either set `LLM_PROVIDER=anthropic` (or `openai`) in `.env`, or leave the default and switch providers live from the model badge dropdown in the UI (`POST /api/config`).
4. If the key is missing **or a live request fails** (expired/revoked key, rate limit, network error, wrong model name), the backend logs a warning and **automatically falls back to Ollama** rather than failing the chat — visible in the UI as a banner on the affected response. Both halves are covered by tests (`test_llm_registry.py` for the config pre-check, `test_runtime_fallback.py` for in-flight failures).

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

64 tests, 0 skips. They cover API contracts and error shapes, session/message persistence round-trips, retrieval ranking (including the AND-vs-OR regression and the relevance floor), skill routing, smalltalk handling, provider config switching and fallback, Ollama timeout behavior, the Claude Agent SDK availability/degradation logic, the Ship 30 length/structure gate, and artifact sanitization.

> A note on the skips: this suite previously reported "10 passed, 7 skipped" and looked healthy. The 7 skips were every Postgres-backed test, hidden behind a `except Exception` that reported any setup failure as "database unreachable". Two real bugs were sitting behind it. The fixture now skips only on a genuine `OperationalError`, so **if you see skips, treat them as a problem, not as normal.**

Frontend has no automated test suite in this MVP (documented scope exclusion — see PRD); a manual test plan covering the UI is in [tests/manual_test_plan.md](tests/manual_test_plan.md).

### What was verified end-to-end

Against a clean `git clone` + `docker compose up --build`, with Ollama/`llama3.1` on the host:

| Check | Result |
|---|---|
| Auto-ingestion on first boot | 47 chunks from 10 sources, no manual step |
| Grounded Q&A | Correct answer + inline `(Source: …)` + citation list |
| Follow-up in session context | Resolved "which of *those* signals" from history |
| Out-of-corpus question | `grounded: false`, honest refusal, no fabrication |
| Ship 30 essay | 1,025 words, 6 headings, 7 bullets, takeaway, cited |
| HTML artifact + XSS attempt | `<script>`, `onclick`, `alert(` all stripped; rendered in `sandbox=""` iframe with CSP `default-src 'none'` |
| Cloud fallback with no API key | `fell_back_to_ollama: true`, answer still served |
| Cloud path with an **invalid** key | Claude Agent SDK reached the live API and returned `401 API key is invalid`; turn still answered via Ollama with `fell_back_to_ollama: true` |
| Frontend production build | Builds clean from a fresh clone |

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `GET /api/health` shows `providers.ollama: false` | Ollama isn't running, or the backend container can't reach it | Run `ollama serve` on the host; on Linux hosts, replace `host.docker.internal` with your host IP in `.env` |
| Chat replies "I couldn't reach the language model" | The active provider is down and there was nothing to fall back to (e.g. Ollama itself is down) | Check `ollama list`, ensure the model in `OLLAMA_MODEL` is actually pulled |
| Chat replies "that took longer than Ollama was given" | A generation exceeded `OLLAMA_TIMEOUT_SECONDS` — the model is healthy, just slow | Raise the timeout, or set `OLLAMA_MODEL` to something smaller (`qwen2.5:1.5b`, `phi`) |
| First message of a session takes ~1 minute | Ollama cold-loads the model into memory before generating | Expected. `keep_alive` keeps it resident for 30m, so later turns are much faster |
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

See the PRD's "Scope choices" and "Risks and trade-offs" sections for the full list and rationale. In brief: no auth/multi-user accounts, no streaming responses, no Alembic migrations (schema created at startup), retrieval uses Postgres full-text search rather than a vector database, and no automated frontend tests. The Anthropic path is built on the **Claude Agent SDK**, which requires Node.js + the Claude Code CLI in the backend image; if either is absent the app degrades to the native Messages API and then to Ollama rather than failing.
