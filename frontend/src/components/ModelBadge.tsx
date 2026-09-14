import type { ConfigPayload, Provider } from "../types";

interface Props {
  config: ConfigPayload | null;
  onChangeProvider: (provider: Provider) => void;
}

const LABELS: Record<Provider, string> = {
  ollama: "Ollama (local)",
  anthropic: "Anthropic",
  openai: "OpenAI",
};

export function ModelBadge({ config, onChangeProvider }: Props) {
  if (!config) return <div className="model-badge">Loading config…</div>;

  const modelName =
    config.active_provider === "ollama"
      ? config.ollama_model
      : config.active_provider === "anthropic"
        ? config.anthropic_model
        : config.openai_model;

  return (
    <div className="model-badge">
      <span className="model-badge-dot" data-active={config.provider_status[config.active_provider]} />
      <select
        className="model-badge-select"
        value={config.active_provider}
        onChange={(e) => onChangeProvider(e.target.value as Provider)}
        title="Switch the active LLM provider"
      >
        {(Object.keys(LABELS) as Provider[]).map((p) => (
          <option key={p} value={p} disabled={!config.provider_status[p] && p !== "ollama"}>
            {LABELS[p]}
            {!config.provider_status[p] && p !== "ollama" ? " (no key)" : ""}
          </option>
        ))}
      </select>
      <span className="model-badge-name">{modelName}</span>
    </div>
  );
}
