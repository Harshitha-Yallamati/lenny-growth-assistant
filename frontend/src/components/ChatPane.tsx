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
}

type SkillChoice = "auto" | "qa" | "ship30" | "artifact-markdown" | "artifact-html";

export function ChatPane({ session, sending, error, fellBack, onSend, onOpenArtifact }: Props) {
  const [input, setInput] = useState("");
  const [skillChoice, setSkillChoice] = useState<SkillChoice>("auto");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages.length, sending]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    let skill: Skill | undefined;
    let artifactFormat: ArtifactFormat | undefined;
    if (skillChoice === "qa" || skillChoice === "ship30") {
      skill = skillChoice;
    } else if (skillChoice === "artifact-markdown") {
      skill = "artifact";
      artifactFormat = "markdown";
    } else if (skillChoice === "artifact-html") {
      skill = "artifact";
      artifactFormat = "html";
    }

    onSend(trimmed, skill, artifactFormat);
    setInput("");
  }

  return (
    <section className="chat-pane">
      <div className="chat-messages">
        {!session && <div className="chat-empty">Start a new chat to ask about product & growth.</div>}
        {session?.messages.map((m) => (
          <MessageBubble key={m.id} message={m} onOpenArtifact={onOpenArtifact} />
        ))}
        {sending && <div className="message message-assistant message-pending">Thinking…</div>}
        <div ref={scrollRef} />
      </div>

      {fellBack && (
        <div className="chat-banner chat-banner-warning">
          Cloud provider unavailable — falling back to local Ollama for this response.
        </div>
      )}
      {error && <div className="chat-banner chat-banner-error">{error}</div>}

      <form className="chat-input-row" onSubmit={handleSubmit}>
        <select
          className="skill-select"
          value={skillChoice}
          onChange={(e) => setSkillChoice(e.target.value as SkillChoice)}
          title="Choose a skill, or let the assistant detect it automatically"
        >
          <option value="auto">Auto-detect</option>
          <option value="qa">Grounded Q&A</option>
          <option value="ship30">Ship 30 essay</option>
          <option value="artifact-markdown">Markdown artifact</option>
          <option value="artifact-html">HTML artifact</option>
        </select>
        <input
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about product-market fit, growth loops, pricing…"
          disabled={!session || sending}
        />
        <button type="submit" className="chat-send-btn" disabled={!session || sending || !input.trim()}>
          Send
        </button>
      </form>
    </section>
  );
}
