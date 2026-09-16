import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../types";

interface Props {
  message: ChatMessage;
  onOpenArtifact: (message: ChatMessage) => void;
  onOpenCitation: (title: string) => void;
  /** Re-asks the question that produced this answer. Null for the user's
   *  own messages and when the preceding question can't be determined. */
  onRegenerate: (() => void) | null;
}

function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export function MessageBubble({ message, onOpenArtifact, onOpenCitation, onRegenerate }: Props) {
  const isUser = message.role === "user";
  const citations = message.citations ?? [];
  const [showGrounding, setShowGrounding] = useState(false);
  const [copied, setCopied] = useState(false);

  // Long-form output is the case where copying actually matters; a one-line
  // answer doesn't need its own button cluttering every bubble.
  const isLongForm = message.skill === "ship30" || message.content.length > 600;

  function handleCopy() {
    navigator.clipboard
      .writeText(message.content)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
      })
      .catch(() => {});
  }

  return (
    <div className={isUser ? "message message-user" : "message message-assistant"}>
      <div className="message-meta">
        <div
          className={
            isUser ? "message-avatar message-avatar-user" : "message-avatar message-avatar-assistant"
          }
        >
          {isUser ? "PL" : "L"}
        </div>
        <span className="message-role">{isUser ? "Product Lead" : "Lenny AI"}</span>
        <span className="message-time">{formatTime(message.created_at)}</span>
        {!isUser && message.skill === "ship30" && (
          <span className="message-skill-chip">🚢 Ship 30</span>
        )}
        {!isUser && message.provider && (
          <span className="message-provider">
            {message.provider}
            {message.model ? ` · ${message.model}` : ""}
          </span>
        )}
        {!isUser && message.grounded === false && message.skill !== "smalltalk" && (
          <span className="message-not-grounded">not grounded</span>
        )}
      </div>

      {/* Grounding summary — expandable into the list of sources actually used */}
      {!isUser && message.grounded === true && citations.length > 0 && (
        <div className="message-grounding message-grounding-verified">
          <span className="grounding-icon">🎙</span>
          <button
            className="grounding-toggle"
            onClick={() => setShowGrounding((v) => !v)}
            aria-expanded={showGrounding}
          >
            Grounded in {citations.length} source{citations.length === 1 ? "" : "s"}
            <span className="grounding-caret">{showGrounding ? "▾" : "▸"}</span>
          </button>
          <span className="verified-badge">Verified RAG</span>
        </div>
      )}

      {!isUser && showGrounding && citations.length > 0 && (
        <div className="grounding-panel">
          <div className="grounding-panel-title">Sources used for this answer</div>
          <ul className="grounding-panel-list">
            {citations.map((c, i) => (
              <li key={c.title}>
                <button className="grounding-panel-item" onClick={() => onOpenCitation(c.title)}>
                  <span className="citation-badge">{i + 1}</span>
                  <span className="grounding-panel-item-title">{c.title}</span>
                  <span className="grounding-panel-item-action">View excerpts →</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div
        className={isUser ? "message-bubble message-bubble-user" : "message-bubble message-bubble-assistant"}
      >
        <div className="message-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
      </div>

      <div className="message-actions">
        {message.artifact && (
          <button className="artifact-open-btn" onClick={() => onOpenArtifact(message)}>
            <span>🗂</span>
            Open {message.artifact.format === "html" ? "HTML" : "Markdown"} artifact
          </button>
        )}
        {!isUser && isLongForm && (
          <button className="message-copy-btn" onClick={handleCopy} title="Copy this answer">
            {copied ? "✓ Copied" : "📋 Copy"}
          </button>
        )}
        {!isUser && onRegenerate && message.skill !== "smalltalk" && (
          <button
            className="message-copy-btn"
            onClick={onRegenerate}
            title="Ask the same question again — the answer is appended as a new turn, the original is kept"
          >
            ↻ Regenerate
          </button>
        )}
      </div>

      {/* Citations — each one opens its transcript excerpts in the right panel */}
      {citations.length > 0 && (
        <div className="message-citations">
          {citations.map((c, i) => (
            <button
              key={c.title}
              className="citation-card citation-card-clickable"
              onClick={() => onOpenCitation(c.title)}
              title="View the transcript excerpts from this source"
            >
              <div className="citation-badge">{i + 1}</div>
              <div>
                <div className="citation-title">{c.title}</div>
                <div className="citation-hint">View excerpts →</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
