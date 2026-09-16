import type { ConfigPayload, Provider } from "../types";

interface Props {
  config: ConfigPayload | null;
  onChangeProvider: (provider: Provider) => void;
  sessionTitle?: string | null;
}

const LABELS: Record<Provider, string> = {
  ollama: "Ollama (local)",
  anthropic: "Anthropic",
  openai: "OpenAI",
};

const SHORT_LABELS: Record<Provider, string> = {
  ollama: "Ollama",
  anthropic: "Anthropic",
  openai: "OpenAI",
};

export function ModelBadge({ config, onChangeProvider, sessionTitle }: Props) {
  if (!config) {
    return (
      <div className="app-header-right">
        <div className="status-pill status-pill-provider">
          <span className="status-dot" />
          Loading…
        </div>
      </div>
    );
  }

  const modelName =
    config.active_provider === "ollama"
      ? config.ollama_model
      : config.active_provider === "anthropic"
        ? config.anthropic_model
        : config.openai_model;

  const isActive = config.provider_status[config.active_provider];

  return (
    <>
      {/* Session Title in header */}
      {sessionTitle && (
        <span className="app-header-title" style={{ flex: 1, textAlign: "center", fontSize: "13px" }}>
          {sessionTitle}
        </span>
      )}

      <div className="app-header-right">
        {/* Provider Select Pill */}
        <div className="status-pill status-pill-provider">
          <span className="status-dot" data-active={isActive} style={{
            background: isActive ? 'var(--success)' : 'var(--danger)',
            boxShadow: isActive ? '0 0 5px rgba(52,211,153,0.5)' : 'none'
          }} />
          <select
            className="model-badge-select"
            value={config.active_provider}
            onChange={(e) => onChangeProvider(e.target.value as Provider)}
            title="Switch the active LLM provider"
            style={{ border: 'none', background: 'transparent', padding: '0', color: 'inherit' }}
          >
            {(Object.keys(LABELS) as Provider[]).map((p) => (
              <option key={p} value={p} disabled={!config.provider_status[p] && p !== "ollama"}>
                {SHORT_LABELS[p]}
                {!config.provider_status[p] && p !== "ollama" ? " (no key)" : ""}
              </option>
            ))}
          </select>
        </div>

        {/* Model name pill */}
        <div className="status-pill status-pill-provider">
          <span className="model-badge-name">{modelName}</span>
        </div>

        {/* RAG active pill */}
        <div className="status-pill status-pill-rag">
          📚 Lenny Transcripts Active
        </div>

        {/* Real status of the provider that will actually serve the next turn.
            This previously always read "Ready" regardless of provider health,
            which is exactly backwards on the screen where an evaluator checks
            whether the model is reachable. */}
        <div
          className="status-pill status-pill-latency"
          title={
            isActive
              ? `${SHORT_LABELS[config.active_provider]} is reachable`
              : `${SHORT_LABELS[config.active_provider]} is not reachable — requests fall back to local Ollama`
          }
        >
          {isActive ? "⚡ Ready" : "⚠ Unavailable — falls back to Ollama"}
        </div>

        {/* User avatar */}
        <div className="user-avatar" title="Account">PL</div>
      </div>
    </>
  );
}
