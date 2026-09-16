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

export interface SourceExcerpt {
  chunk_index: number;
  content: string;
}

export interface SourceDetail {
  title: string;
  url: string | null;
  total_chunks: number;
  excerpts: SourceExcerpt[];
}

/** An artifact plus the message it came from, for the history list. */
export interface ArtifactHistoryEntry {
  messageId: string;
  artifact: Artifact;
  title: string;
  createdAt: string;
}

/** What the right sidebar is currently showing. */
export type RightPanelView = "artifact" | "source" | "history";

export interface SessionSearchHit {
  id: string;
  title: string | null;
  updated_at: string;
  matched_in: "title" | "message";
  snippet: string | null;
}

export interface KnowledgeBaseStats {
  chunk_count: number;
  source_count: number;
  sources: string[];
}

export interface HealthPayload {
  status: string;
  components: {
    database: string;
    providers: Record<string, boolean>;
    active_provider: string;
  };
}

export interface ConfigPayload {
  active_provider: Provider;
  configured_default: Provider;
  provider_status: Record<Provider, boolean>;
  ollama_model: string;
  anthropic_model: string;
  openai_model: string;
}
