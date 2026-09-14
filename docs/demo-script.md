# Demo Video Script (2–3 minutes)

The assignment requires a 2–3 minute video **with your camera enabled**, uploaded to YouTube, covering: the problem, the product, a local Ollama demo, and one technical trade-off.

## Before you hit record

1. `docker compose up -d` and wait for all three containers to be healthy (`docker compose ps`).
2. **Warm the model first** — send one throwaway message so Ollama cold-loads. Otherwise your first on-camera question sits for ~60s.
3. Pre-create a session that already contains a grounded Q&A exchange, so you can show results instantly instead of waiting on camera.
4. Do **not** generate a Ship 30 essay live — measured at ~18 minutes on a CPU-only laptop with `llama3.1` (it runs a second expansion pass). Generate one beforehand and open that session to show the finished output.
5. Have two browser tabs ready: the app (http://localhost:5173) and `http://localhost:8000/api/health`.
6. Camera on, screen share on.

## Beat-by-beat (target 2:30)

**0:00–0:20 — Problem (camera on you)**
> "Product and growth teams sit on hours of podcast transcripts they can't search. The answer they need is two minutes buried inside a 90-minute episode — and once they find it, they still have to write it up themselves. The Lenny Growth Assistant collapses search, synthesis, and drafting into one conversation."

**0:20–0:50 — Grounded answer with citations (screen)**
Ask: *"How do I know if I've found product-market fit?"*
Point at: the answer, the inline `(Source: …)` attribution, and the **Sources** list under the message.
> "Every answer is grounded in the transcript corpus and cites which episode it came from."

**0:50–1:10 — Honest refusal (screen)**
Ask: *"What's the weather in Tokyo tomorrow?"*
Point at the **"not grounded"** badge.
> "When the knowledge base doesn't cover something, it says so instead of making something up. That badge is persisted per-message, so you can audit how often it's actually grounded."

**1:10–1:35 — Local Ollama proof (screen)** ← *explicitly required*
Point at the model badge: **Ollama (local) · llama3.1**, green status dot.
Show `http://localhost:8000/api/health`: `"providers":{"ollama":true,...}`.
> "This is running entirely locally on Ollama — no API key, no data leaving the machine. Cloud providers are a config toggle, and if a cloud key is missing it falls back to local automatically."
*(Optional, fast:* switch the dropdown to Anthropic and send a message — the amber fallback banner appears.*)*

**1:35–2:00 — Artifact viewer + security (screen)**
Open the pre-generated HTML artifact.
> "Generated HTML renders beside the chat, not as a wall of code. And it's treated as untrusted: the server strips script tags and event handlers, and the viewer renders it in an iframe with a completely empty sandbox attribute — zero permissions, no script execution, no access to the parent page."

**2:00–2:30 — One technical trade-off (camera on you)** ← *explicitly required*
Pick **one** and say it crisply. The retrieval one is the strongest because it's a real bug you found and fixed:

> "The trade-off I'd call out is retrieval. I used Postgres full-text search instead of a vector database — no embedding model to download, no pgvector, one less moving part, and it reuses the database I already needed. The catch is lexical matching. My first implementation used `plainto_tsquery`, which ANDs every word in the question together — so 'how do I *know* if I have product-market fit' required the word 'know' to appear in the transcript. On my corpus that matched one chunk instead of thirty, and the assistant claimed it didn't cover topics it covers in depth. I fixed it by switching to OR semantics with a measured relevance floor. The honest limitation is that lexical search still misses paraphrases a vector search would catch — pgvector is the documented upgrade path."

## If you'd rather lead with a different trade-off

- **Agent SDK substitution:** why the Anthropic path uses the native Messages API instead of `claude-agent-sdk` (avoids bundling a Node/CLI subprocess into a Python image for an optional path with no key to test against).
- **Illustrative corpus:** why the transcripts are originally-written and labelled `illustrative: true` rather than bulk-scraped from a subscription newsletter, and that swapping in a licensed corpus is a data change, not a code change.

## After recording

- Upload to YouTube (Unlisted is fine unless the form says otherwise).
- Put the link in the submission form: https://forms.gle/LgotDHNVxW1mbzNE7
