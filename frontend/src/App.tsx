import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { api, ApiError } from "./api/client";
import { ArtifactViewer } from "./components/ArtifactViewer";
import { ChatPane } from "./components/ChatPane";
import { ModelBadge } from "./components/ModelBadge";
import { SessionSidebar } from "./components/SessionSidebar";
import type {
  ArtifactFormat,
  ChatMessage,
  ConfigPayload,
  Provider,
  SessionDetail,
  SessionSummary,
  Skill,
} from "./types";

const CLIENT_ID_KEY = "lenny-growth-assistant-client-id";

function getOrCreateClientId(): string {
  let id = localStorage.getItem(CLIENT_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(CLIENT_ID_KEY, id);
  }
  return id;
}

export default function App() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<SessionDetail | null>(null);
  const [config, setConfig] = useState<ConfigPayload | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fellBack, setFellBack] = useState(false);
  const [openArtifactMessage, setOpenArtifactMessage] = useState<ChatMessage | null>(null);

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await api.listSessions());
    } catch {
      // Session list is non-critical; the chat pane will surface real errors.
    }
  }, []);

  const refreshConfig = useCallback(async () => {
    try {
      setConfig(await api.getConfig());
    } catch {
      setConfig(null);
    }
  }, []);

  useEffect(() => {
    refreshSessions();
    refreshConfig();
  }, [refreshSessions, refreshConfig]);

  const handleNewSession = useCallback(async () => {
    setError(null);
    try {
      const session = await api.createSession({ client_id: getOrCreateClientId() });
      setActiveSession({ ...session, messages: [] });
      await refreshSessions();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to create a new session.");
    }
  }, [refreshSessions]);

  const handleSelectSession = useCallback(async (id: string) => {
    setError(null);
    try {
      setActiveSession(await api.getSession(id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load session.");
    }
  }, []);

  const handleDeleteSession = useCallback(
    async (id: string) => {
      try {
        await api.deleteSession(id);
        if (activeSession?.id === id) setActiveSession(null);
        await refreshSessions();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Failed to delete session.");
      }
    },
    [activeSession, refreshSessions]
  );

  const handleSend = useCallback(
    async (message: string, skill: Skill | undefined, artifactFormat: ArtifactFormat | undefined) => {
      if (!activeSession) return;
      setSending(true);
      setError(null);
      setFellBack(false);

      const optimisticUser: ChatMessage = {
        id: `pending-${Date.now()}`,
        role: "user",
        content: message,
        provider: null,
        model: null,
        skill: null,
        citations: null,
        artifact: null,
        grounded: null,
        created_at: new Date().toISOString(),
      };
      setActiveSession((prev) =>
        prev ? { ...prev, messages: [...prev.messages, optimisticUser] } : prev
      );

      try {
        const result = await api.sendMessage(activeSession.id, message, skill, artifactFormat);
        setFellBack(result.fell_back_to_ollama);
        const fresh = await api.getSession(activeSession.id);
        setActiveSession(fresh);
        await refreshSessions();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Failed to send message.");
      } finally {
        setSending(false);
      }
    },
    [activeSession, refreshSessions]
  );

  const handleChangeProvider = useCallback(
    async (provider: Provider) => {
      try {
        setConfig(await api.setProvider(provider));
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Failed to switch provider.");
      }
    },
    []
  );

  return (
    <div className="app-shell">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSession?.id ?? null}
        onSelect={handleSelectSession}
        onNewSession={handleNewSession}
        onDelete={handleDeleteSession}
      />

      <div className="main-column">
        <header className="app-header">
          <h1>The Lenny Growth Assistant</h1>
          <ModelBadge config={config} onChangeProvider={handleChangeProvider} />
        </header>

        <div className="content-row">
          <ChatPane
            session={activeSession}
            sending={sending}
            error={error}
            fellBack={fellBack}
            onSend={handleSend}
            onOpenArtifact={setOpenArtifactMessage}
          />
          {openArtifactMessage?.artifact && (
            <ArtifactViewer
              artifact={openArtifactMessage.artifact}
              onClose={() => setOpenArtifactMessage(null)}
            />
          )}
        </div>
      </div>
    </div>
  );
}
