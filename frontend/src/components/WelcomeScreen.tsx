interface Props {
  onQuickStart: (prompt: string, mode: "auto" | "ship30" | "artifact") => void;
  onNewSession: () => void;
  hasSession: boolean;
}

/**
 * Onboarding for the empty state.
 *
 * The example questions are real topics from the shipped corpus, so a first
 * click lands on a grounded answer with citations rather than a "not covered"
 * refusal — which is the worst possible first impression for a RAG product.
 */
const EXAMPLES = [
  "How do I know if I've found product-market fit?",
  "What's the difference between a growth loop and a funnel?",
  "How do I find our activation aha moment?",
  "How should I think about pricing and packaging?",
];

const ACTIONS: {
  mode: "auto" | "ship30" | "artifact";
  icon: string;
  title: string;
  body: string;
  prompt: string;
}[] = [
  {
    mode: "auto",
    icon: "🔁",
    title: "Ask Lenny",
    body: "Grounded answers with citations back to the transcript they came from.",
    prompt: "How do I know if I've found product-market fit?",
  },
  {
    mode: "ship30",
    icon: "🚢",
    title: "Ship 30 Essay",
    body: "A ~1,250-word essay with a hook, headings and a takeaway. Takes a few minutes locally.",
    prompt: "Write a Ship 30 essay about user onboarding and activation.",
  },
  {
    mode: "artifact",
    icon: "✏️",
    title: "Create Artifact",
    body: "A Markdown doc or sandboxed HTML page, rendered in the right panel.",
    prompt: "Create an HTML summary page about retention.",
  },
];

export function WelcomeScreen({ onQuickStart, onNewSession, hasSession }: Props) {
  return (
    <div className="welcome">
      <div className="welcome-icon">🎙</div>
      <h1 className="welcome-title">Ask Lenny anything</h1>
      <p className="welcome-subtitle">
        Grounded answers from Lenny's podcast transcripts — product-market fit, growth loops,
        activation, pricing, retention and more. Every answer cites the episode it came from.
      </p>

      <div className="welcome-actions">
        {ACTIONS.map((a) => (
          <button
            key={a.mode}
            className="welcome-action"
            onClick={() => onQuickStart(a.prompt, a.mode)}
          >
            <span className="welcome-action-icon">{a.icon}</span>
            <span className="welcome-action-title">{a.title}</span>
            <span className="welcome-action-body">{a.body}</span>
          </button>
        ))}
      </div>

      <div className="welcome-examples">
        <div className="welcome-examples-label">Try one of these</div>
        <div className="welcome-examples-list">
          {EXAMPLES.map((q) => (
            <button key={q} className="welcome-example" onClick={() => onQuickStart(q, "auto")}>
              {q}
            </button>
          ))}
        </div>
      </div>

      {!hasSession && (
        <button className="chat-empty-btn" onClick={onNewSession}>
          Or start a blank chat
        </button>
      )}
    </div>
  );
}
