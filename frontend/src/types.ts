export type Provider = "ollama" | "anthropic" | "openai";
export type Skill = "qa" | "ship30" | "artifact" | "smalltalk";
export type ArtifactFormat = "markdown" | "html";

export interface Citation {
  title: string;
  url: string;
}

export interface Artifact {
  format: ArtifactFormat;
  content: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  provider: string | null;
  model: string | null;
  skill: Skill | null;
  citations: Citation[] | null;
  artifact: Artifact | null;
  grounded: boolean | null;
  created_at: string;
}

export interface SessionSummary {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionDetail extends SessionSummary {
  messages: ChatMessage[];
}

export interface ChatResponsePayload {
  message: ChatMessage;
  fell_back_to_ollama: boolean;
}

export interface ConfigPayload {
  active_provider: Provider;
  configured_default: Provider;
  provider_status: Record<Provider, boolean>;
  ollama_model: string;
  anthropic_model: string;
  openai_model: string;
}
