import { useEffect, useRef, useState } from "react";
import type { ArtifactFormat, ChatMessage, SessionDetail, Skill } from "../types";
import { MessageBubble } from "./MessageBubble";

interface Props {
  session: SessionDetail | null;
  sending: boolean;
  error: string | null;
  fellBack: boolean;
  onSend: (message: string, skill: Skill | undefined, artifactFormat: ArtifactFormat | undefined) => void;
  onOpenArtifact: (message: ChatMessage) => void;
  onOpenCitation: (title: string) => void;
  followUps: string[];
  onNewSession: () => void;
}

type SkillChoice = "auto" | "qa" | "ship30" | "artifact-markdown" | "artifact-html";

// Mirrors MAX_HISTORY_TURNS in backend/app/api/chat.py -- the number of prior
// messages actually replayed to the model.
const HISTORY_TURNS_SENT = 12;
const CONTEXT_HINT =
  "Approximate tokens (~4 chars each) in the conversation history replayed to the model. " +
  "The backend sends at most the last 12 messages.";

const QUICK_PROMPTS = [
  { label: "🔁 Ask Lenny", value: "auto" as SkillChoice, placeholder: "Ask about retention curves, growth loops, PMF benchmarks, pricing experiments…" },
  { label: "🚢 Ship 30 Essay (~1,250 words)", value: "ship30" as SkillChoice, placeholder: "Write a Ship 30 essay on…" },
  { label: "✏️ Create Artifact", value: "artifact-html" as SkillChoice, placeholder: "Generate an interactive HTML artifact for…" },
];

export function ChatPane({
  session,
  sending,
  error,
  fellBack,
  onSend,
  onOpenArtifact,
  onOpenCitation,
  followUps,
  onNewSession,
}: Props) {
  const [input, setInput] = useState("");
  const [skillChoice, setSkillChoice] = useState<SkillChoice>("auto");
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages.length, sending]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [input]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    let skill: Skill | undefined;
    let artifactFormat: ArtifactFormat | undefined;

    if (skillChoice === "qa") {
      skill = "qa";
    } else if (skillChoice === "ship30") {
      skill = "ship30";
    } else if (skillChoice === "artifact-markdown") {
      skill = "artifact";
      artifactFormat = "markdown";
    } else if (skillChoice === "artifact-html") {
      skill = "artifact";
      artifactFormat = "html";
    }

    onSend(trimmed, skill, artifactFormat);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  }

  const currentPlaceholder =
    QUICK_PROMPTS.find((p) => p.value === skillChoice)?.placeholder ??
    "Ask about product-market fit, growth loops, pricing…";

  // Real figures, not decoration. The backend replays at most the last
  // MAX_HISTORY_TURNS messages as history (app/api/chat.py), so that slice is
  // what actually reaches the model; the token count is a ~4-chars-per-token
  // estimate over it. We deliberately don't print a context *ceiling*: it
  // varies per model (llama3.1 is 128k, not the 8k this once hardcoded) and
  // inventing one would be exactly the kind of fabricated number this product
  // is supposed to avoid.
  const historySlice = (session?.messages ?? []).slice(-HISTORY_TURNS_SENT);
  const approxTokens = Math.round(
    historySlice.reduce((sum, m) => sum + (m.content?.length ?? 0), 0) / 4
  );
  const contextLabel = session
    ? `~${approxTokens >= 1000 ? `${(approxTokens / 1000).toFixed(1)}k` : approxTokens} tokens · ${historySlice.length} msg${historySlice.length === 1 ? "" : "s"}`
    : "no session";

  return (
    <section className="chat-pane">
      <div className="chat-messages">
        {/* Empty State */}
        {!session && (
          <div className="chat-empty">
            <div className="chat-empty-icon">🎙</div>
            <div className="chat-empty-title">Ask Lenny anything</div>
            <div className="chat-empty-subtitle">
              Grounded answers from Lenny's podcast transcripts. Ask about
              retention curves, growth loops, PMF benchmarks, pricing
              experiments, and more.
            </div>
            <button className="chat-empty-btn" onClick={onNewSession}>
              Start a new chat
            </button>
          </div>
        )}

        {/* Messages */}
        {session?.messages.map((m) => (
          <MessageBubble
            key={m.id}
            message={m}
            onOpenArtifact={onOpenArtifact}
            onOpenCitation={onOpenCitation}
          />
        ))}

        {/* Thinking Indicator */}
        {sending && (
          <div className="message message-assistant">
            <div className="message-meta">
              <div className="message-avatar message-avatar-assistant">L</div>
              <span className="message-role">Lenny AI</span>
            </div>
            <div className="message-pending">
              <div className="thinking-dots">
                <div className="thinking-dot" />
                <div className="thinking-dot" />
                <div className="thinking-dot" />
              </div>
              {skillChoice === "ship30" ? (
                <span>
                  Writing a ~1,250-word Ship 30 essay…
                  <span className="pending-hint">
                    Drafts, then expands until it meets the rubric. On a local 8B model this
                    takes several minutes — the tab can be left open.
                  </span>
                </span>
              ) : (
                "Thinking…"
              )}
            </div>
          </div>
        )}
        {/* Suggested follow-ups — only after a grounded answer, and only when
            we're not mid-generation. Derived from the cited episodes, so every
            suggestion points at something the corpus can actually answer. */}
        {!sending && followUps.length > 0 && (
          <div className="followups">
            <div className="followups-label">Suggested follow-ups</div>
            <div className="followups-list">
              {followUps.map((q) => (
                <button
                  key={q}
                  type="button"
                  className="followup-chip"
                  onClick={() => {
                    if (!session || sending) return;
                    const isEssay = /ship 30|essay/i.test(q);
                    onSend(q, isEssay ? "ship30" : undefined, undefined);
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={scrollRef} />
      </div>

      {/* Banners */}
      {fellBack && (
        <div className="chat-banner chat-banner-warning">
          ⚠️ Cloud provider unavailable — falling back to local Ollama for this response.
        </div>
      )}
      {error && <div className="chat-banner chat-banner-error">⚠ {error}</div>}

      {skillChoice === "ship30" && (
        <div className="mode-banner mode-banner-ship30">
          🚢 <strong>Ship 30 mode</strong> — the next message writes a ~1,250-word essay with
          headings, bullets and citations. Expect several minutes on a local model.
        </div>
      )}
      {(skillChoice === "artifact-html" || skillChoice === "artifact-markdown") && (
        <div className="mode-banner mode-banner-artifact">
          ✏️ <strong>Artifact mode</strong> — the next message generates a{" "}
          {skillChoice === "artifact-html" ? "sandboxed HTML page" : "Markdown document"} in the
          right panel.
        </div>
      )}

      {/* Input Area */}
      <div className="chat-input-area">
        <form onSubmit={handleSubmit}>
          <div className="chat-input-wrapper">
            <textarea
              ref={textareaRef}
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={currentPlaceholder}
              disabled={!session || sending}
              rows={1}
              aria-label="Chat message input"
            />
            <div className="chat-input-bottom">
              {/* Quick Action Chips */}
              {QUICK_PROMPTS.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  className={`action-chip${skillChoice === p.value ? " active" : ""}`}
                  onClick={() => setSkillChoice(p.value)}
                  style={skillChoice === p.value ? {
                    borderColor: "var(--accent)",
                    background: "var(--accent-dim)",
                    color: "var(--text)"
                  } : {}}
                >
                  {p.label}
                </button>
              ))}

              {/* Context info */}
              <div className="chat-context-info">
                <span className="chat-context-badge" title={CONTEXT_HINT}>
                  {contextLabel}
                </span>
                <span className="chat-enter-hint">Enter ↵ to send</span>
              </div>

              {/* Send Button */}
              <button
                type="submit"
                className="chat-send-btn"
                disabled={!session || sending || !input.trim()}
                aria-label="Send message"
              >
                ↑
              </button>
            </div>
          </div>
        </form>

        {/* Skill select (hidden — controlled by chips above) */}
        <select
          className="skill-select"
          value={skillChoice}
          onChange={(e) => setSkillChoice(e.target.value as SkillChoice)}
          style={{ display: "none" }}
          aria-hidden="true"
        >
          <option value="auto">Auto-detect</option>
          <option value="qa">Grounded Q&amp;A</option>
          <option value="ship30">Ship 30 essay</option>
          <option value="artifact-markdown">Markdown artifact</option>
          <option value="artifact-html">HTML artifact</option>
        </select>
      </div>
    </section>
  );
}
