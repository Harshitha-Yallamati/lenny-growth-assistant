# Demo Video Script (2–3 minutes)

The assignment requires a 2–3 minute video **with your camera enabled**, uploaded to YouTube, covering four things: the problem, the product, a **local Ollama demo**, and **one technical trade-off**. The last two are explicitly required — don't let them get squeezed out by the demo.

---

## Before you hit record

1. `docker compose up -d` — wait until all three containers report healthy (`docker compose ps`).
2. **Warm the model.** Send one real question and let it finish. The first generation after startup takes ~50–60s while Ollama cold-loads; you don't want that on camera. Note: a greeting like "hey" will *not* warm it — the smalltalk skill answers those without calling the model at all.
3. **Pre-generate the Ship 30 essay.** It takes ~18 minutes on a CPU-only laptop with `llama3.1` (it runs a second expansion pass when the first draft comes up short). Generate it beforehand and just open that session on camera.
4. **Pre-generate the HTML artifact** too, so the Artifact Viewer opens instantly.
5. Two tabs ready: the app (http://localhost:5173) and http://localhost:8000/api/health.
6. Camera on, screen share on, sidebar visible.

---

## Beat-by-beat (target 2:30)

### 0:00–0:20 — The problem *(camera on you)*

> "Product and growth teams sit on hours of podcast transcripts they can't search. The answer they need is two minutes buried inside a 90-minute episode — and once they find it, they still have to write it up themselves. The Lenny Growth Assistant collapses search, synthesis, and drafting into one conversation."

### 0:20–0:50 — Grounded answer with citations *(screen)*

Open the pre-warmed session and ask: **"How do I know if I've found product-market fit?"**

Point at three things, in this order:
- the inline `(Source: …)` attribution inside the answer
- the **🎙 Grounded in 2 podcast sources · Verified RAG** badge above the message
- the numbered **citation cards** underneath

> "Every answer is retrieved from the transcript corpus first, and it cites the episode it came from. The grounding badge isn't decoration — it's a field persisted on every message, so you can audit how often the thing is actually grounded."

### 0:50–1:10 — Honest refusal *(screen)*

Ask: **"What's the weather in Tokyo tomorrow?"**

Point at the amber **not grounded** tag.

> "When the knowledge base doesn't cover something, it says so instead of inventing an answer. That's the behaviour I care most about in a RAG product — being wrong confidently is worse than being unhelpful."

### 1:10–1:35 — Local Ollama proof *(screen)* ← **required**

Point at the header: the provider dropdown on **Ollama**, the **llama3.1** model pill, **📚 Lenny Transcripts Active**, and **⚡ Ready**.

Switch to the health tab and show:
```json
"providers": { "ollama": true, "anthropic": false, "openai": false }
```

> "This runs entirely locally on Ollama — no API key, nothing leaving the machine. The provider is a config toggle, switchable live from this dropdown, and if a cloud provider fails the request falls back to local automatically."

*Optional if you have 10 spare seconds:* switch the dropdown to Anthropic and send a message — the amber **falling back to local Ollama** banner appears and the answer still arrives.

### 1:35–2:00 — Artifact viewer + security *(screen)*

Open the pre-generated HTML artifact. Point at the **✓ Sandboxed Preview** badge and the **Preview / Code / Markdown** tabs.

> "Generated HTML renders beside the chat instead of as a wall of code. It's treated as untrusted in two independent layers: the server strips script tags and event handlers before it's ever stored, and the viewer renders it in an iframe with a completely empty sandbox attribute — zero permissions, no script execution, no access to the parent page. I tested it by explicitly asking the model to inject an alert; nothing survived."

### 2:00–2:30 — One technical trade-off *(camera on you)* ← **required**

Pick **one** and say it crisply. Option A is the strongest — it's a real bug, with measured numbers and an honest residual limitation.

**Option A — Retrieval (recommended):**

> "The trade-off I'd call out is retrieval. I used Postgres full-text search instead of a vector database — no embedding model to download, no pgvector, one less moving part, and it reuses the database I already needed. The catch is lexical matching, and it bit me. My first implementation used `plainto_tsquery`, which ANDs every word in the question together — so 'how do I *know* if I have product-market fit' required the literal word 'know' to appear in the transcript. On my corpus that matched one chunk instead of thirty, and the assistant claimed it didn't cover topics it covers in depth. I switched to OR semantics with a measured relevance floor — on-topic questions score around 0.08, off-topic ones around 0.02, so the floor is what keeps 'not grounded' honest. The limitation I'd still flag: lexical search misses paraphrases a vector search would catch. pgvector is the documented upgrade path, and it's a one-file change."

**Option B — Agent SDK security:**

> "The Anthropic path is built on the Claude Agent SDK, which is Claude Code packaged as a library. Two things about that shaped the design. It drives the Claude Code CLI as a subprocess, so the backend image needs Node — and it ships built-in Bash, Read and Write tools, which is correct for a coding agent and actively dangerous inside a web backend. So the allow-list names exactly one tool, my transcript search: no shell, no filesystem. And because that's a heavier runtime contract than a pip install, the provider degrades — Agent SDK, then the native Messages API, then Ollama — so a missing Node runtime can never take down the local path the demo depends on."

**Option C — Illustrative corpus:**

> "The brief said to use Lenny's Podcast transcripts but didn't point at a licensed dataset, and bulk-scraping a subscription newsletter wasn't a call I wanted to make. So the shipped corpus is ten originally-written, episode-style documents modelling well-known themes from the show, tagged `illustrative: true` in the manifest and disclosed in the PRD. The ingestion pipeline is corpus-agnostic — swapping in real licensed transcripts is a data change, not a code change."

---

## Things worth mentioning only if asked

- **Smalltalk routing:** "hey" is answered deterministically with no retrieval and no model call — it used to return the "knowledge base doesn't cover this" refusal, which read as broken.
- **Cloud fallback depth:** it covers both a missing key *and* a live request failure. Verified with a deliberately invalid key: the Agent SDK reached the real Anthropic API, got a 401, and the turn still returned a grounded answer via Ollama.
- **Tests:** 64 passing, zero skips — including regression tests for the retrieval bug above and for the artifact sanitizer.

## Don't say

- ~~"It uses the native Messages API instead of the Agent SDK"~~ — that was an earlier decision and was **reversed**. It now uses `claude-agent-sdk`.
- Don't claim the cloud path is fully verified end-to-end. No valid API key was available: it's verified up to the authentication boundary (a real 401 from the live API), and the fallback is verified. Say that if it comes up.

## After recording

- Upload to YouTube (Unlisted is fine unless the form says otherwise).
- Put the link in the submission form: https://forms.gle/LgotDHNVxW1mbzNE7
