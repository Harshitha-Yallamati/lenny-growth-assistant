# PRD — The Lenny Growth Assistant

## 1. Forward Deployment Brief

### User and problem
**Primary user:** an internal PM, founder, or growth operator at a company evaluating this tool — someone who wants credible, sourced product/growth advice without reading or re-listening to dozens of hours of podcast content, and without needing to know anything about prompts, RAG, or which model is running underneath.

**Job to be done:** "Give me a fast, trustworthy answer to a specific product/growth question, backed by what an actual expert said, and let me turn that answer into something I can publish or share (an essay, a doc, a one-pager) without starting from a blank page."

**Pain removed:** the current alternative is manually searching podcast episode notes/transcripts (if they exist at all), skimming for the relevant 2 minutes, and then separately opening a doc to write up what they learned. This assistant collapses "search → synthesize → write → format" into one conversation.

### Success metric
Primary: **% of chat sessions that end in a grounded answer (citations present) rather than a "not covered" or error response**, tracked via the `grounded` field already persisted on every assistant message. Target for this MVP: ≥ 80% grounded rate on questions that fall within the corpus's covered topics (PMF, growth loops, activation, onboarding, pricing, retention, PLG vs. sales, growth teams, positioning, prioritization).

Secondary (operational): **p50 response latency** on the local Ollama path, and **fallback rate** (how often a cloud-provider request silently drops to Ollama) — both already logged as structured events (`chat_turn_failed`, `provider_fallback`) for a real deployment to monitor.

### Assumptions (brief was incomplete)
1. **Transcript source.** The brief names "the transcripts from Lenny's Podcast / Newsletter transcript repository" without pointing at a specific dataset or granting a bulk-scraping mandate. Given the take-home's timeline and to avoid uncertain-licensing bulk scraping of a subscription newsletter's content, the shipped corpus (`data/transcripts/`) is a small set of **originally written, illustrative** episode-style Q&A documents modeling common, well-known Lenny's Podcast themes (PMF, growth loops, pricing, etc.) — not verbatim transcripts of real episodes. This is called out in the UI's source citations (`illustrative: true` in `data/sources.json`) and is a one-file-per-episode drop-in to replace with real, licensed transcripts — no code changes required.
2. **No authentication/multi-user accounts.** Sessions are anonymous, client-generated UUIDs stored in `localStorage`. Not mentioned in the brief as a requirement; adding real auth would meaningfully expand scope without changing the evaluation of the core assistant.
3. **Single-tenant, single-org deployment.** No workspace/team boundaries — every session sees the same knowledge base.
4. **"Long-context" vs. RAG:** the brief allows either; RAG was chosen so ingestion/chunking/retrieval/citation-traceability (explicitly required in §3.3) has something real to point at.

### Scope choices

**Included:**
- FastAPI backend with sessions, messages, and a transcript knowledge base persisted in PostgreSQL.
- A provider-agnostic LLM layer (Ollama default/mandatory, Anthropic and OpenAI as optional config-only swaps), switchable live from the UI, with automatic fallback to Ollama if a cloud provider is unavailable.
- The agent layer for the Anthropic path built on the **Claude Agent SDK** (§3.1), with transcript retrieval exposed to it as a real SDK tool and its built-in shell/filesystem tools deliberately withheld via a strict allow-list — see architecture.md.
- Grounded Q&A over the transcript corpus using PostgreSQL full-text search, with inline citations and honest "not covered" responses.
- A Ship 30 for 30 writing skill with an explicit, researched rubric (not an ad hoc prompt).
- A Markdown/HTML artifact-generation skill with a sandboxed, isolated in-app Artifact Viewer.
- Structured logging, a component-level `/api/health` endpoint, and graceful degradation on provider/DB failures.
- Docker Compose one-command startup, `.env.example`, automated backend tests, and a manual UI test plan.

**Intentionally excluded (see Risks & trade-offs for why):**
- Vector-database/embedding-based semantic retrieval (used Postgres full-text search instead).
- Streaming token-by-token responses (plain request/response JSON).
- Database migrations via Alembic (schema created via `SQLAlchemy.metadata.create_all` at startup).
- Authentication, multi-user workspaces, and rate limiting.
- Automated frontend tests (covered by a manual test plan instead).
- A real, licensed bulk transcript corpus (see Assumption 1).

### Core user flows

1. **New grounded question.** User clicks "New chat" → types a product/growth question → assistant retrieves relevant transcript chunks → answers with inline citations, or plainly says the knowledge base doesn't cover it.
2. **Follow-up in context.** User asks a follow-up in the same session → prior turns are included as history → assistant answers coherently without re-explaining context.
3. **Ship 30 essay.** User asks for an essay (or picks "Ship 30 essay" from the skill selector) on a topic → assistant produces a ~1,250-word, hook-led, citation-grounded essay following the encoded rubric.
4. **Artifact generation.** User asks for a doc/HTML page (or picks it from the skill selector) → assistant emits a typed artifact payload → frontend opens the Artifact Viewer beside the chat, rendering Markdown safely or HTML inside a fully sandboxed iframe.
5. **Provider toggle.** User switches the model badge dropdown to Anthropic/OpenAI → subsequent messages use that provider until switched back, or fall back to Ollama transparently if the key is missing/invalid.
6. **Resilience path.** Ollama is stopped mid-session → next message returns a clear, non-crashing error message rather than a stack trace or hang.

### Acceptance criteria

- A fresh clone + `docker compose up --build` (with Ollama already running and a model pulled on the host) serves a working chat UI at `localhost:5173` with no manual DB/ingestion step.
- Asking a question covered by the corpus returns an answer with at least one citation whose title matches an entry in `data/sources.json`.
- Asking an out-of-corpus question (e.g. "what's the weather today") returns an explicit "not covered" style answer, not a fabricated one.
- Requesting a Ship 30 essay returns Markdown between ~1,000–1,500 words with a clear hook line, headings/bullets, and a labeled takeaway.
- Requesting an HTML artifact renders inside the Artifact Viewer's sandboxed iframe; inspecting the iframe shows no executable `<script>` and the iframe's `sandbox` attribute is empty (no tokens).
- Stopping Ollama and sending a message returns a handled error response (HTTP 200 with an apologetic assistant message, or a clean error banner) — never a 500 with a raw traceback to the user.
- `pytest` passes against a Postgres instance provisioned by `docker compose up -d db`.

### Risks and trade-offs

| Risk | Mitigation / trade-off |
|---|---|
| **Hallucination** on out-of-corpus questions | System prompt strictly forbids outside knowledge when no chunks are retrieved; `grounded: false` is persisted and shown as a badge in the UI so the evaluator can audit it. |
| **Latency** on small local models (qwen2.5:1.5b) | Kept the QA/artifact prompts short and context-focused; no multi-step agent loop for the local path (single completion call) to minimize round trips. |
| **Local-model quality** producing weaker essays/artifacts than cloud models | Documented explicitly, not hidden — the model name is always shown in the UI so output quality can be attributed to the active provider. |
| **Data leakage** via HTML artifacts | See architecture.md's security section — server-side sanitization + iframe sandboxing with zero tokens is defense-in-depth against exfiltration via a malicious artifact. |
| **Unsafe artifact rendering** | Same as above; Markdown renders through `react-markdown` without raw-HTML passthrough. |
| **Retrieval recall** (lexical search misses paraphrased questions) | Accepted trade-off for zero extra infra; documented upgrade path to pgvector. |
| **Claude Agent SDK path is untestable without an API key** | Implemented against the documented SDK API with unit coverage of the availability/fallback logic, but the live round-trip is unverified and stated as such. The registry degrades Agent SDK → native Messages API → Ollama, so a missing key or CLI cannot break the demo. |
| **Agent SDK ships built-in Bash/file tools** | Running the Claude Code harness inside a web backend would otherwise expose shell and filesystem access on the server; `allowed_tools` is restricted to our retrieval tool only. |
| **Small/illustrative transcript corpus** limits topic coverage | Acceptable for an MVP demo; ingestion path is corpus-size-agnostic so swapping in a full real corpus is a data change, not a code change. |

## 2. Implementation plan

See the phased build order in this repo's commit history: scaffold → backend core (DB, providers, health) → RAG (corpus + full-text retrieval) → skills (QA, Ship 30, artifact) + multi-provider → artifact security → frontend (chat, sidebar, artifact viewer, model badge) → automated tests → docs → GitHub handoff. Each phase was verified end-to-end (curl/pytest/browser) before moving to the next, per the actual build log in `agent-transcripts/`.
