import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../types";

interface Props {
  message: ChatMessage;
  onOpenArtifact: (message: ChatMessage) => void;
}

function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export function MessageBubble({ message, onOpenArtifact }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={isUser ? "message message-user" : "message message-assistant"}>
      {/* Message Header */}
      <div className="message-meta">
        <div className={isUser ? "message-avatar message-avatar-user" : "message-avatar message-avatar-assistant"}>
          {isUser ? "PL" : "L"}
        </div>
        <span className="message-role">{isUser ? "Product Lead" : "Lenny AI"}</span>
        <span className="message-time">{formatTime(message.created_at)}</span>
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

      {/* Grounding indicator (for grounded assistant messages) */}
      {!isUser && message.grounded === true && message.citations && message.citations.length > 0 && (
        <div className="message-grounding message-grounding-verified">
          <span className="grounding-icon">🎙</span>
          <span>
            Grounded in {message.citations.length} podcast
            {message.citations.length !== 1 ? " & playbook" : ""} source
            {message.citations.length !== 1 ? "s" : ""}
          </span>
          <span className="verified-badge">Verified RAG</span>
        </div>
      )}

      {/* Bubble */}
      <div className={isUser ? "message-bubble message-bubble-user" : "message-bubble message-bubble-assistant"}>
        <div className="message-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
      </div>

      {/* Artifact Open Button */}
      {message.artifact && (
        <button
          className="artifact-open-btn"
          onClick={() => onOpenArtifact(message)}
        >
          <span>🗂</span>
          Open {message.artifact.format === "html" ? "HTML" : "Markdown"} artifact
        </button>
      )}

      {/* Citations */}
      {message.citations && message.citations.length > 0 && (
        <div className="message-citations">
          {message.citations.map((c, i) => (
            <div key={c.title} className="citation-card">
              <div className="citation-badge">{i + 1}</div>
              <div>
                <div className="citation-title">{c.title}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
