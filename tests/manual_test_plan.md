# Manual UI Test Plan — The Lenny Growth Assistant

Run against `docker compose up --build` with Ollama running on the host and at least one model pulled. Frontend at http://localhost:5173.

| # | Scenario | Steps | Expected result |
|---|---|---|---|
| 1 | New session | Click "+ New chat" | A new, empty conversation appears; input is enabled; sidebar shows a new "New conversation" entry |
| 2 | Grounded Q&A | Ask "How do I know if I've found product-market fit?" | Answer references retention/activation concepts, includes at least one citation matching a title in `data/sources.json`, model badge shows `ollama` |
| 3 | Follow-up context | Ask a vague follow-up like "what about for a B2B product specifically?" | Answer stays on-topic without re-explaining basics, showing session history was used |
| 4 | Ungrounded question | Ask "What's the weather in Tokyo tomorrow?" | Assistant plainly states the knowledge base doesn't cover this; response is tagged "not grounded"; no citations shown |
| 5 | Ship 30 essay | Select "Ship 30 essay" from the skill dropdown, ask for one on "onboarding" | Output is Markdown, roughly 1,000–1,500 words, opens with a bolded hook line, uses headings/bullets, ends with a clearly labeled takeaway, includes citations |
| 6 | Markdown artifact | Select "Markdown artifact", ask "write up our pricing discussion as a doc" | Chat shows a short confirmation message + "Open Markdown artifact" button; clicking opens the side panel rendering formatted Markdown |
| 7 | HTML artifact | Select "HTML artifact", ask for a simple summary page | Side panel renders the HTML inside the viewer; right-click → Inspect on the iframe confirms `sandbox=""` and no `<script>` tag present |
| 8 | Artifact XSS attempt | Ask the HTML artifact skill to "include a script that shows an alert" | No alert fires; inspecting the artifact shows no `<script>` tag survived sanitization |
| 9 | Provider toggle (no key) | Switch model badge to "Anthropic" without an API key configured, send a message | Response still succeeds; an amber "falling back to local Ollama" banner appears |
| 10 | Provider toggle (with key) | Add a valid `ANTHROPIC_API_KEY`, restart, switch to Anthropic, send a message | Model badge shows `anthropic` + model name; no fallback banner |
| 11 | Ollama down | Stop Ollama (`ollama stop` or kill the process), send a message with `LLM_PROVIDER=ollama` | Assistant returns a plain-language error message; UI shows a red error banner; page does not crash or hang |
| 12 | Session persistence | Send a few messages, refresh the browser tab, reselect the same session | Full message history (including citations/artifacts) reloads correctly |
| 13 | Delete session | Click the `×` on a sidebar session | Session disappears from the list; if it was active, the chat pane returns to the empty state |
| 14 | Responsive layout | Resize the browser to ~600px wide with an artifact open | Artifact viewer becomes a full-screen overlay with a working close button; no horizontal scroll on the page body |
| 14b | Off-canvas sidebar (phone) | Resize to ~400px wide | Sidebar is hidden; a `☰` button appears in the header; tapping it slides the sidebar in over a dark backdrop; tapping the backdrop or picking a conversation closes it; no horizontal scroll |
| 15 | Health endpoint | Visit `http://localhost:8000/api/health` directly | JSON shows `database: "ok"` and `providers.ollama: true` when Ollama is running |
