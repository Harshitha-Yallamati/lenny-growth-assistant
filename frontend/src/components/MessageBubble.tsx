import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../types";

interface Props {
  message: ChatMessage;
  onOpenArtifact: (message: ChatMessage) => void;
}

export function MessageBubble({ message, onOpenArtifact }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={isUser ? "message message-user" : "message message-assistant"}>
      <div className="message-meta">
        <span className="message-role">{isUser ? "You" : "Assistant"}</span>
        {!isUser && message.provider && (
          <span className="message-provider">
            {message.provider}
            {message.model ? ` · ${message.model}` : ""}
          </span>
        )}
        {!isUser && message.grounded === false && (
          <span className="message-not-grounded">not grounded</span>
        )}
      </div>

      <div className="message-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
      </div>

      {message.artifact && (
        <button className="artifact-open-btn" onClick={() => onOpenArtifact(message)}>
          Open {message.artifact.format === "html" ? "HTML" : "Markdown"} artifact
        </button>
      )}

      {message.citations && message.citations.length > 0 && (
        <div className="message-citations">
          <span className="message-citations-label">Sources:</span>
          <ul>
            {message.citations.map((c) => (
              <li key={c.title}>{c.title}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
