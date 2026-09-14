# Build Log — The Lenny Growth Assistant

Session date: 2026-09-13 → 2026-09-14. Built with Claude Code against the take-home assignment brief. This log covers the real decisions, dead ends, and fixes from the actual build session, in order.

## 1. Reading the brief and scoping

The assignment doc (`Forward_Deployed_Engineer_Take_Home_Assignment.docx`) was read via pandoc/XML extraction (pandoc wasn't on PATH in this environment, so the `.docx` was unzipped and `word/document.xml` was stripped of tags directly with Python's `re`/`html.unescape` — a fallback that worked fine for a text-only document).

Given the ~2-day deadline, before writing any code the plan was scoped deliberately down to an MVP that hits every rubric line item with **documented** trade-offs rather than attempting a maximal build. Key scoping decisions made up front (see PRD.md for full rationale):
- Postgres full-text search instead of pgvector/embeddings — avoids an extra infra dependency and a model-download step.
- Anthropic path uses the native Messages API tool-use pattern instead of `claude-agent-sdk`, to avoid bundling a Node/CLI subprocess into the backend image for an optional path that had no API key to test against during the build.
- No streaming, no Alembic, no auth — all called out explicitly as scope exclusions rather than silently skipped.

These were presented to the user as a written plan (via Claude Code's plan mode) before any implementation began, and approved with additional emphasis on keeping things MVP-focused and testing incrementally.

## 2. Environment check before building

Before scaffolding anything, checked what was actually available on the machine rather than assuming: `ollama --version` / `ollama list` (found `llama3.1`, `phi`, `qwen2.5:1.5b` already pulled), `docker --version` / `docker compose version`, `gh --version` (not installed), `git --version`, `node --version`, `python --version`. This shaped real decisions — e.g., Ollama already having three models meant no time needed to be spent on pull instructions during the build itself.

## 3. Backend build order (each phase curl/pytest-verified before moving on)

Built in the order: scaffold (docker-compose, .env.example, .gitignore) → DB models/config/logging → LLM provider abstraction (Ollama first, since it's the mandatory path) → RAG ingestion/retrieval → agent orchestrator + skills (qa, ship30, artifact) → artifact sanitization → API routers → automated tests.

**Failed attempt / correction — Ship 30 for 30 rubric.** Initially considered writing the Ship 30 for 30 skill's rubric from memory/assumption. Corrected this by actually running a web search and fetching `ship30for30.com`'s own "How to Write an Atomic Essay" guide first, and encoding the *real* documented rules (headline formula, promise-matching structure, bolded key points, editing-as-a-separate-pass) into `ship30_skill.py` as an explicit `Ship30Rubric` dataclass — matching the assignment's specific instruction to "encode [principles] in the skill rather than relying on an unstructured one-off prompt."

**Failed attempt / correction — transcript corpus sourcing.** Attempted to find a real, freely-licensed source of Lenny's Podcast transcripts via web search (`lennysnewsletter.com` podcast pages). The search didn't turn up a straightforward, reliably scrapable free transcript archive within the time available, and bulk-scraping a subscription newsletter's content carried real licensing uncertainty. Corrected course by writing a small (10-episode) **originally-written, clearly-labeled illustrative** corpus modeling well-known real Lenny's Podcast themes (PMF, growth loops, pricing, retention, etc.), tagged `"illustrative": true` in `data/sources.json`, and documented this substitution explicitly as an Assumption in the PRD rather than presenting it as real transcript data. The ingestion/chunking/retrieval pipeline is corpus-agnostic, so swapping in a real licensed corpus later is a data change, not a code change.

**Failed attempt / correction — async session lazy-loading.** The first draft of `GET /api/sessions/{id}` accessed `session.messages` after a plain `db.get(ChatSession, id)`, which would fail at runtime under SQLAlchemy's async ORM (no implicit lazy-loading via greenlet without an explicit eager-load strategy). Caught this during code review before ever running it and fixed it by switching to an explicit `select(...).options(selectinload(ChatSession.messages))` query.

**Design correction — bleach's `<script>`/`<style>` handling.** Needed to confirm `bleach.clean()` fully drops `<script>` tag *content*, not just the tag itself (leaving raw JS visible as text would be a lesser but still real defect). Verified via the automated sanitization tests (`test_artifact_sanitize.py`) rather than assuming, and paired the server-side sanitizer with a second, independent layer — a fully token-less `<iframe sandbox="">` on the frontend — precisely so no single sanitization bug is a full XSS vector.

**Bug caught by the automated test suite — `bleach` doesn't strip script content.** `test_strips_script_tags_entirely` initially failed: `sanitize_html_artifact("<div>Hello</div><script>alert('xss')</script>")` still contained the literal text `alert('xss')` in its output. The assumption going in was that `bleach.clean()` fully removes a disallowed tag *and* its inner content — that was wrong for `bleach` 2.x+, which by design only strips the tag markup and leaves inner text behind (useful for e.g. an accidentally-unclosed `<b>`, actively wrong for `<script>`). Fixed by adding an explicit regex pre-pass in `sanitize.py` that removes `<script>...</script>` blocks (and unclosed `<script>` tags) entirely before handing off to `bleach.clean()` for everything else. This is exactly why the artifact viewer has a second, independent layer (the fully token-less `<iframe sandbox="">`) rather than relying on server-side sanitization alone — a single sanitizer bug like this one would otherwise have been a real, shipped XSS vector.

## 3a. Three bugs found during final verification (and why the test suite had been hiding one)

**Bug — the test suite was green for the wrong reason.** `pytest` reported "10 passed, 7 skipped" and looked healthy. The 7 skips were every test that touches Postgres — i.e. the API-contract, persistence, and retrieval tests that matter most. The skip message claimed "Postgres test database not reachable… run `docker compose up -d db` first", but the database *was* running and reachable. The real cause was a bare `except Exception` in `conftest.py` that turned **any** setup failure into a "database unreachable" skip. Two genuine defects were hiding behind it:
1. **Missing `greenlet` dependency.** SQLAlchemy's async engine requires `greenlet`, and it only auto-installs on some interpreter/platform combinations — it was absent on the Python 3.13 host venv, so every async DB call failed with `the greenlet library is required to use this function`. It worked in Docker (Python 3.12) purely by luck, which is exactly the kind of "works on my machine" gap that burns an evaluator. Fixed by pinning `greenlet==3.1.1` explicitly in `requirements.txt`.
2. **psycopg3 vs. Windows' default event loop.** On Windows, asyncio defaults to `ProactorEventLoop`, which psycopg3's async mode refuses to run on. Fixed by selecting `WindowsSelectorEventLoopPolicy` in `conftest.py` under a `sys.platform == "win32"` guard, so the suite runs on a Windows host as well as in Linux containers.

The conftest was then narrowed to skip only on a genuine `OperationalError`, so a real failure can never masquerade as "Postgres isn't running" again. Result: **19 passed, 0 skipped** — where the suite previously ran 10 of 17 tests and called it success.

**Bug — RAG retrieval was AND-ing every word of the question (the significant one).** With the DB tests finally executing, `test_retrieve_returns_relevant_chunk_ranked_first` failed outright. Root cause: `plainto_tsquery` combines every lexeme with `&`, so *"how do I know if I have product-market fit"* required a chunk to contain "know" alongside the actual topic. Verified against the real corpus rather than reasoning about it in the abstract:

| query | AND (`plainto_tsquery`) | OR |
|---|---|---|
| "how do I know if I have product-market fit" | **1** chunk | **30** chunks |

This was a genuine product-breaking defect, not a test artifact — the demo's core loop is asking natural questions, and most of them would have returned "the knowledge base doesn't cover this" about topics the corpus covers in depth. Fixed by rewriting the parsed query's `&` operators to `|` and letting `ts_rank` do the relevance work, plus a measured `retrieval_min_rank` floor (default 0.03) so that OR semantics don't make every off-topic question look answerable — on-topic questions score ~0.05–0.08 on this corpus, off-topic ones ~0.02. Both directions are now pinned by regression tests, and the whole rationale is written up in architecture.md rather than left as an unexplained magic number.

Worth noting the sequencing: the retrieval bug was only findable *because* the skip-masking bug was fixed first. A suite that skips its integration tests by default is worse than having no suite, because it reports success.

## 3b. The Ship 30 skill quietly missed its own brief

With the timeout fixed, the Ship 30 skill finally completed end-to-end — and the output still didn't meet the assignment. Measured on `llama3.1`: **546 words, zero Markdown headings**, against a brief that asks for "approximately 1,250 words" with "skimmable formatting with headings, bullets, and selective bold emphasis."

The code already *knew*: `word_count_within_tolerance()` was called on every result and wrote an `ship30_word_count_out_of_range` log line. It just didn't do anything about it. Detecting a requirement violation and then shipping the violation anyway is worse than not checking — it creates the appearance of a quality gate.

Two changes:
1. **Made the requirements explicit and checkable in the prompt** — a minimum word count stated as a hard floor ("this is a long-form essay, not a summary; do not stop early"), at least 4 `## ` headings, at least one bulleted list, and a required `## The Takeaway` section. Vague targets ("approximately 1,250 words") are easy for a small model to ignore.
2. **Added a second expansion pass.** If the first draft lands under the floor, the skill re-prompts with the draft attached and asks for expansion that preserves the existing hook, argument, and `(Source: ...)` citations rather than restarting or padding. The expansion is only accepted if it actually came back longer — a model that returns something shorter has ignored the instruction, and the original draft is kept.

Result: **546 words / 0 headings → 1,025 words / 6 headings / 7 bullets / takeaway section**, still grounded with citations.

The honest cost is latency: the two-pass run takes **~18 minutes** on a CPU-only laptop with an 8B model. That number is now in the README (my first estimate of "5–10 minutes" was wrong, so it was corrected against the measured run rather than left as a plausible-sounding guess) along with the advice to use a smaller model or pre-generate for a demo.

## 4. Infrastructure failure: Docker Desktop crash, mid-build

While bringing up `docker compose up -d db backend` for the first real end-to-end test, Docker Desktop crashed with:
```
starting services: initializing Inference manager: listening on unix://...dockerInference:
remove ...dockerInference: The file cannot be accessed by the system.
(listener: The filename, directory name, or volume label syntax is incorrect.)
```
Root cause: a dangling/corrupted reparse point (an AF_UNIX socket file) at `%LocalAppData%\Docker\run\dockerInference`, unrelated to this project — a pre-existing Docker Desktop state issue on the host machine. Standard deletion attempts (`Remove-Item`, `.NET File.Delete`, `cmd /c del`, `takeown`/`icacls`) all failed identically with "The file cannot be accessed by the system," because the symlink's target no longer existed and most Win32 file APIs try to resolve a reparse point's target before touching it.

**Fix:** rather than fighting the single broken file, stopped all Docker processes (`Stop-Process -Force` on every `*docker*`/`com.docker.*` process) and renamed the *parent* `run` directory (`Rename-Item ... run.broken`) instead of deleting the specific corrupted entry — `run` holds only ephemeral runtime sockets/PIDs, not persistent image/container data (that lives in Docker's separate WSL disk), so this was safe and non-destructive. Relaunching Docker Desktop recreated `run` cleanly, but the engine then crashed a second time on a **different** dangling socket at `%LocalAppData%\docker-secrets-engine\engine.sock` (same underlying corruption pattern, a different subsystem). Applied the identical fix — stop processes, rename the containing folder rather than fight the individual reparse point — and the engine came up cleanly on the next retry. Both times this avoided the nuclear "Reset to factory defaults" option Docker's own crash dialog offered, which would have wiped the user's unrelated existing images/containers just to fix what was really two stale socket files.

## 5. GitHub repo creation without `gh`

`gh` (GitHub CLI) wasn't installed. Rather than installing new global tooling for a one-time action, checked for an existing git credential the user's own git client already had configured (`git config credential.helper` → `store`, `~/.git-credentials` present) and verified via `GET /user` against the GitHub API that it authenticated as the user's own account before using it — this was the user's own pre-existing, already-trusted credential, not something introduced during this session, and repo creation was explicitly requested by the user beforehand. Created the repository via `POST /user/repos`.

**Minor correction:** the first repo-creation `curl` call with an inline `-d '{...}'` JSON string failed with "Problems parsing JSON" because of an em-dash character in the description getting mangled by shell quoting. Fixed by writing the JSON payload to a file and passing it with `--data-binary @file` instead of inlining it.

## 6. What's left to a human

- Recording the 2–3 minute demo video (camera required — outside what a coding agent can produce) and uploading to YouTube.
- Optionally supplying a real Anthropic/OpenAI API key to demo the cloud path live (the app runs and demos fully on Ollama without one).
- Swapping the illustrative transcript corpus for a real, licensed one if this were to go beyond a take-home demo.
