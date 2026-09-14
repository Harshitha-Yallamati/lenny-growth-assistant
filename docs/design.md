# design.md — The Lenny Growth Assistant

## UI/UX principles

1. **The model is visible, never hidden.** Every assistant message shows which provider and model produced it; the header always shows the active provider with a live/down status dot. An evaluator switching providers should never have to guess what actually ran.
2. **Grounding is legible, not just trusted.** Citations render inline under a message; a "not grounded" badge appears the moment the knowledge base didn't support an answer, so the user can calibrate trust per-message rather than for the whole product.
3. **Artifacts live beside the conversation, not instead of it.** Generating a doc/HTML page never replaces the chat — it opens an adjacent panel, preserving the conversational thread that produced it.
4. **Skill selection is optional, not mandatory.** Auto-detection covers the common case (asking a question, asking for an essay, asking for a doc); the skill dropdown exists for the evaluator who wants to force a specific skill deterministically while testing.
5. **Failure states are conversational, not technical.** A dead Ollama or a bad cloud key shows up as a plain-language assistant message or a banner, never a raw stack trace in the chat pane.

## Information architecture

```
App
├── Sidebar            — session list, "+ New chat"
├── Header             — title, ModelBadge (active provider + switcher)
└── Content row
    ├── ChatPane        — message list, skill selector, input
    └── ArtifactViewer  — opens only when a message has an artifact; closable
```

Everything is one screen — no routing/pages. Session state lives in React state, hydrated from `GET /api/sessions` and `GET /api/sessions/{id}` on load and after every mutation; there's no client-side cache invalidation logic beyond "refetch after write," which is the right trade-off for a chat app with low request volume.

## Key interaction states

| State | Behavior |
|---|---|
| No session selected | Chat pane shows an empty-state prompt; input is disabled until "New chat" is clicked. |
| Sending a message | An optimistic user bubble appears immediately; a "Thinking…" placeholder bubble shows while awaiting the response; input is disabled to prevent double-submits. |
| Grounded answer | Citations list renders under the message content. |
| Not-grounded answer | An amber "not grounded" tag renders next to the provider name. |
| Cloud fallback occurred | An amber banner appears above the input for that turn: "Cloud provider unavailable — falling back to local Ollama." |
| Hard failure (both DB and provider down, or an exception) | A red banner with a plain-language message; the message that failed to send is not silently dropped from view. |
| Artifact present | An "Open Markdown/HTML artifact" button appears under the message; clicking opens/updates the side panel. |
| Provider switched | Model badge updates immediately; the dropdown greys out cloud options that have no configured key (still selectable — selecting one with no key simply triggers the documented fallback behavior on the next message, which is itself a useful thing for an evaluator to see). |

## Responsive behavior

- **Desktop (>900px):** three-column layout — sidebar, chat, optional artifact panel (45% width) side by side.
- **Narrow (≤900px):** sidebar collapses to a slimmer rail; the artifact viewer becomes a full-screen overlay with its own close button rather than squeezing into a fraction of the width, since HTML artifacts need real estate to render meaningfully.
- All text areas and message bubbles use relative widths (`max-width` in px capped, but flexible below that) so they reflow rather than overflow.

## Accessibility considerations

- All interactive controls (`New chat`, provider `<select>`, skill `<select>`, send button, artifact close button) are real semantic `<button>`/`<select>` elements — not `<div onClick>` — so they're keyboard-reachable and screen-reader-labeled by default.
- The artifact close button and per-session delete button both carry explicit `aria-label`s since their visible content is a symbol (`×`), not text.
- Color is never the only signal: the "not grounded" state is a labeled tag with text, not just a colored dot; the provider status dot is paired with the provider name in text.
- Dark theme uses a high-contrast palette (`#e8eaed` text on `#0f1115`/`#171a21` panels) chosen for readability rather than pure aesthetics; no text is rendered below WCAG AA contrast against its background at the sizes used.
- The HTML Artifact Viewer's sandboxed iframe intentionally cannot inherit the app's focus-trap/keyboard patterns from arbitrary generated HTML — this is a deliberate security/accessibility trade-off documented in architecture.md, since allowing generated HTML to script its own focus behavior would reopen the exact isolation the sandbox exists to provide.

## Design decisions worth calling out

- **Dark theme by default, no light-mode toggle.** Scoped out for time; the CSS uses design tokens (CSS variables) so adding a light theme later is a values-only change, not a rewrite.
- **No streaming text.** A short "Thinking…" state substitutes for token-by-token streaming, which was cut to keep the backend's request/response contract simple for this MVP (documented in the PRD as a scope exclusion). The trade-off is a less "live" feel on longer Ship 30 essay generations.
- **Skill selector defaults to "Auto-detect."** Keyword-based auto-routing (see architecture.md) covers the demo's needs; the explicit selector exists mainly so an evaluator can deterministically test each skill without needing to phrase a prompt just right.
