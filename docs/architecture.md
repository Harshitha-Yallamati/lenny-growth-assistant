# architecture.md — The Lenny Growth Assistant

## Component boundaries

```
frontend/   React + TS, talks to the backend only via the REST contract below. No direct DB or LLM access.
backend/app/
  api/        HTTP layer: FastAPI routers, request/response schemas, error mapping. No business logic.
  agent/      Orchestration + skills. Decides which skill handles a turn and builds skill-specific prompts.
  rag/        Ingestion (files -> DB) and retrieval (query -> ranked chunks). No knowledge of skills or providers.
  llm/        Provider abstraction (Ollama/Anthropic/OpenAI) + registry/fallback logic. No knowledge of prompts or skills.
  artifacts/  Server-side HTML sanitization. No knowledge of providers or persistence.
  db/         SQLAlchemy models + async session factory. No business logic.
  core/       Settings (env-driven) and runtime state (in-memory provider override) + logging setup.
```

Each layer only depends on layers below it (`api -> agent -> {rag, llm, artifacts} -> db/core`); `rag`, `llm`, and `artifacts` don't depend on each other or on `agent`, which is what makes them independently testable (see `backend/tests/`).

## Database schema

Three tables, all in the same Postgres instance used for both persistence and retrieval (see "Why full-text search, not pgvector" below).

**`sessions`**
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| title | varchar(200), nullable | set from the first user message |
| user_metadata | jsonb | anonymous client id, etc. |
| created_at, updated_at | timestamptz | |

**`messages`**
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| session_id | uuid FK -> sessions.id, ON DELETE CASCADE | |
| role | varchar(20) | `user` \| `assistant` |
| content | text | |
| provider, model | varchar, nullable | which LLM actually produced this message |
| skill | varchar(30), nullable | `qa` \| `ship30` \| `artifact` |
| citations | jsonb, nullable | `[{title, url}]` |
| artifact | jsonb, nullable | `{format, content}` |
| grounded | boolean, nullable | did retrieval find any relevant chunks |
| created_at | timestamptz | |

**`chunks`** (the knowledge base)
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| source_title, source_url | varchar | citation display fields |
| chunk_index | int | position within the source document |
| content | text | |
| content_tsv | tsvector, **generated column** (`to_tsvector('english', content)`), GIN-indexed | powers retrieval |
| created_at | timestamptz | |

Schema is created via `SQLAlchemy Base.metadata.create_all` on backend startup — no Alembic (documented scope exclusion; fine for a from-scratch MVP schema, not fine for a production system with live migrations).

## API endpoints

| Method & path | Purpose |
|---|---|
| `GET /api/health` | DB connectivity + per-provider reachability; used for container healthcheck and evaluator diagnostics |
| `POST /api/sessions` | Create a session |
| `GET /api/sessions` | List sessions (sidebar) |
| `GET /api/sessions/{id}` | Session + full message history |
| `DELETE /api/sessions/{id}` | Delete a session and its messages |
| `POST /api/chat` | The core turn: `{session_id, message, skill?, artifact_format?}` -> persists the user message, runs the orchestrator, persists and returns the assistant message |
| `GET /api/config` | Active provider, configured default, per-provider reachability, model names |
| `POST /api/config` | `{provider}` — runtime-only override of the active provider (not persisted; resets on restart) |

All error responses follow `{error: str, detail: str}` via a global `HTTPException` handler and a catch-all 500 handler that never leaks a raw traceback to the client (it's logged server-side instead).

## Ingestion / retrieval flow

1. **Ingestion** (`app/rag/ingest.py`), run automatically on startup if `chunks` is empty (and manually via `scripts/ingest_transcripts.py`): reads `data/sources.json` (title, url, filename per source), splits each transcript file on blank-line paragraph boundaries, and greedily packs paragraphs into ~180-word chunks (never splitting a paragraph mid-sentence). Existing chunks for a source title are deleted and reinserted, so re-running after an edit is safe and idempotent.
2. **Retrieval** (`app/rag/retrieval.py`): a single SQL query using Postgres's built-in full-text search against the generated `content_tsv` column, `ORDER BY ts_rank DESC LIMIT top_k` (default 5). No results -> the orchestrator treats the turn as **not grounded**.

   **Query semantics (a bug worth documenting).** The obvious implementation, `plainto_tsquery`, ANDs every lexeme in the question together. That quietly breaks conversational RAG: *"how do I know if I have product-market fit"* requires a chunk to contain "know" **and** "product-market" **and** "fit", so realistic questions matched nothing and the assistant reported the knowledge base didn't cover its own core topics. Measured on this corpus, that question matched **1** chunk under AND semantics versus **30** under OR. The fix keeps `plainto_tsquery` for its safe parsing/stemming/stopword handling, then rewrites its `&` operators to `|` (`replace(plainto_tsquery(...)::text,'&','|')::tsquery`) so partial matches are allowed and `ts_rank` decides relevance. Because that alone would let any chunk sharing one incidental common word count as grounding, a `retrieval_min_rank` floor (default `0.03`, configurable) filters the tail. The default was measured, not guessed: on-topic questions score ~0.05–0.08 here, while an off-topic one ("weather in Tokyo tomorrow") scrapes a single ~0.02 match. Both behaviors are pinned by regression tests in `backend/tests/test_retrieval.py`.
3. **Traceability**: every chunk carries its source title and URL; `to_citations()` deduplicates by title so a multi-chunk answer shows each source once.

### Why full-text search, not pgvector/an embedding model

This trades semantic/paraphrase recall for zero extra infrastructure: no embedding model to download at build time, no pgvector extension, no vector-dimension config, and it reuses the one Postgres instance already required for persistence. For a small, curated corpus this is good enough and dramatically more reliable to demo than a pipeline with an extra model-download step. The natural upgrade path — swap `retrieval.py`'s query for a pgvector `<=>` similarity search fed by a local embedding model — doesn't touch any other layer, because `agent/` only depends on the `RetrievedChunk` shape, not on how it was produced.

## Agent routing

`app/agent/orchestrator.py` is the only place that decides "what kind of turn is this":

1. If the request explicitly names a skill (`qa`/`ship30`/`artifact` from the frontend's skill selector), use it.
2. Else, if the message matches artifact-intent keywords ("as html", "as a markdown document", etc.), route to the **artifact** skill.
3. Else, if the message matches Ship-30 keywords ("ship 30", "atomic essay", "turn this into an essay"), route to the **ship30** skill.
4. Else, default to **qa**.

Each skill module (`app/agent/skills/*.py`) owns its own system-prompt construction and is the only place that encodes skill-specific rules — the orchestrator just wires retrieval -> skill prompt -> provider call -> response shape. This is a deliberate boundary: adding a fourth skill means adding one module and one `elif` branch, not touching retrieval or provider code.

## Model toggle (flexible LLM configuration)

- `app/llm/base.py` defines one `LLMProvider` interface (`is_available()`, `complete()`); `ollama_provider.py`, `claude_agent_provider.py`, `anthropic_provider.py`, `openai_provider.py` each implement it independently — the orchestrator and skills never import a specific provider.
- `app/core/config.py` (`LLM_PROVIDER` env var) sets the **default**; `app/core/runtime_state.py` holds an in-memory override so `POST /api/config` can switch providers live from the UI without a restart (intentionally not persisted — a restart reverts to the `.env` default, which is the right behavior for a demo toggle).
- `app/llm/registry.py`'s `resolve_provider()` is the single fallback chokepoint: if the active provider is a cloud provider and `is_available()` is false (missing/invalid key, unreachable), it logs a `provider_fallback` event and transparently returns the Ollama provider instead. The API layer surfaces this as `fell_back_to_ollama: true` on the response, which the frontend renders as a banner.

### The agent layer: Claude Agent SDK (`app/llm/claude_agent_provider.py`)

The Anthropic path is built on the **Claude Agent SDK** (`claude-agent-sdk`), per §3.1. Two properties of that SDK drove the design.

**It is Claude Code packaged as a library.** It doesn't call the HTTP API directly — it drives the `claude` CLI as a subprocess, so the runtime needs Node.js plus `@anthropic-ai/claude-code`. The backend image installs both (see `backend/Dockerfile`). Because that's a heavier contract than "pip install and go", `sdk_available()` verifies *both* halves — the Python package importable **and** the `claude` binary on PATH — and the registry degrades in three steps rather than failing: **Agent SDK → native Messages API (`anthropic_provider.py`) → Ollama.** A missing CLI can therefore never take the app down, and the mandatory local demo path is unaffected.

**It ships built-in Read/Write/Edit/Bash/Glob/Grep tools.** That is the right default for a coding agent and the wrong one for a web backend — unconstrained, it would hand the model shell and filesystem access on the server. `ClaudeAgentOptions.allowed_tools` is therefore a strict allow-list naming exactly one tool, our own `mcp__lenny_kb__search_transcripts`. No `Bash`, no file read/write, nothing else is granted. This is a deliberate security boundary, not an oversight.

Retrieval is exposed as a real SDK tool (`@tool` + `create_sdk_mcp_server`), so the agent can search the corpus itself rather than only consuming context handed to it — that's what makes this an agent layer rather than a completion wrapper. The per-request DB session reaches the tool callback through a `ContextVar` (each request runs in its own asyncio task, so it can't leak across concurrent turns). Sessions stay in Postgres rather than the CLI's own store — we deliberately don't use `continue_conversation`/`resume`, which would split the source of truth for conversation state.

The orchestrator still pre-retrieves and injects context into the system prompt for *every* provider, so `grounded`/citations behave identically no matter which is active; the tool is additive. If the agent never calls it, behavior matches the other providers exactly.

**Honest limitation:** no Anthropic API key was available during this build, so this path's live network round-trip has not been exercised. `backend/tests/test_claude_agent_provider.py` covers everything that decides whether the path is entered (key present, CLI present, allow-list namespacing, prompt construction) and the registry's fallback behavior — but not a real call. Ollama is the verified demo path.

## Security: artifact rendering

Generated HTML is treated as fully untrusted, with two independent layers:

1. **Server-side sanitization** (`app/artifacts/sanitize.py`, via `bleach`): strips `<script>` tags (content and all), inline event-handler attributes (`onclick=`, etc.), `javascript:` URLs, and any tag/attribute not on an explicit allow-list (structural and text tags, `style`, `class`, `id`, safe `href`/`src`). This runs before the artifact payload ever leaves the backend.
2. **Client-side isolation** (`ArtifactViewer.tsx`): HTML artifacts render inside `<iframe sandbox="">` — an **empty** sandbox attribute, meaning *no* permissions are granted at all: no script execution, no same-origin access, no form submission, no popups, no top-level navigation. Even if a script somehow survived sanitization, the browser refuses to execute it, and the frame has zero access to the parent page, cookies, or `localStorage` regardless. A strict CSP (`default-src 'none'`) is additionally injected into the iframe's document as a third layer in case sandboxing is ever loosened later.

Markdown artifacts render through `react-markdown` **without** `rehype-raw`, so any raw HTML embedded in Markdown is displayed as inert escaped text, never parsed or executed.

**What this permits:** static structure, styling (inline `<style>`/`style=`), images from `https:`/`data:` URLs, links (rendered inert-ish by the sandbox anyway — no `allow-top-navigation`, so clicking a link inside the iframe does nothing, which is intentional).
**What this blocks:** any script execution, any network call the artifact might try to make, any access to the parent app's session/cookies/storage, form submission anywhere.
**What an evaluator can verify directly:** open devtools on the rendered artifact iframe and confirm the `sandbox=""` attribute and the absence of any `<script>` tag in the rendered DOM.

## Deployment topology

```
docker-compose.yml
├── db        postgres:16-alpine, port 5432 published, GIN index on chunks.content_tsv,
│             db/init/ auto-creates a lenny_growth_assistant_test database for the test suite
├── backend   FastAPI (uvicorn), port 8000, reads ./data read-only, reaches host Ollama via
│             host.docker.internal, depends_on db healthcheck
└── frontend  Vite build served by nginx, port 5173, VITE_API_BASE_URL baked in at build time
              (browser calls the backend directly on localhost:8000, not through the frontend container)
```

Ollama itself is **not** containerized — it's assumed to already be running on the host, per the assignment's "Ollama, mandatory for the demo" requirement, which is a host-level install, not a service we should be sandboxing away from the model files/GPU access a user already has configured.
