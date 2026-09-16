import { useCallback, useEffect, useState } from "react";
import "./App.css";
import "./panels.css";
import "./shell.css";
import { api, ApiError } from "./api/client";
import { ChatPane } from "./components/ChatPane";
import { RightSidebar } from "./components/RightSidebar";
import { ModelBadge } from "./components/ModelBadge";
import { SessionSidebar } from "./components/SessionSidebar";
import { StatusDashboard } from "./components/StatusDashboard";
import type {
  ArtifactFormat,
  ChatMessage,
  ConfigPayload,
  Provider,
  SessionDetail,
  SessionSummary,
  Skill,
  ArtifactHistoryEntry,
  RightPanelView,
  SourceDetail,
} from "./types";
import { suggestFollowUps } from "./followups";

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
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Right panel: artifact viewer / citation source preview / artifact history
  const [rightOpen, setRightOpen] = useState(false);
  const [rightView, setRightView] = useState<RightPanelView>("artifact");
  const [sourceTitle, setSourceTitle] = useState<string | null>(null);
  const [source, setSource] = useState<SourceDetail | null>(null);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [statusOpen, setStatusOpen] = useState(false);

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

  const handleRenameSession = useCallback(
    async (id: string, title: string) => {
      try {
        await api.renameSession(id, title);
        setActiveSession((prev) => (prev && prev.id === id ? { ...prev, title } : prev));
        await refreshSessions();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Failed to rename conversation.");
      }
    },
    [refreshSessions]
  );

  // Takes the session id explicitly so a just-created session can be sent to
  // immediately -- handleSend closes over activeSession, which is still null
  // on the render where a quick-start action creates one.
  const handleSendTo = useCallback(
    async (
      sessionId: string,
      message: string,
      skill: Skill | undefined,
      artifactFormat: ArtifactFormat | undefined
    ) => {
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
        const result = await api.sendMessage(sessionId, message, skill, artifactFormat);
        setFellBack(result.fell_back_to_ollama);
        const fresh = await api.getSession(sessionId);
        setActiveSession(fresh);
        await refreshSessions();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Failed to send message.");
      } finally {
        setSending(false);
      }
    },
    [refreshSessions]
  );

  const handleSend = useCallback(
    (message: string, skill: Skill | undefined, artifactFormat: ArtifactFormat | undefined) => {
      if (!activeSession) return;
      void handleSendTo(activeSession.id, message, skill, artifactFormat);
    },
    [activeSession, handleSendTo]
  );

  const handleQuickStart = useCallback(
    async (prompt: string, mode: "auto" | "ship30" | "artifact") => {
      setError(null);
      try {
        let session = activeSession;
        if (!session) {
          const created = await api.createSession({ client_id: getOrCreateClientId() });
          session = { ...created, messages: [] };
          setActiveSession(session);
          await refreshSessions();
        }
        const skill: Skill | undefined =
          mode === "ship30" ? "ship30" : mode === "artifact" ? "artifact" : undefined;
        const fmt: ArtifactFormat | undefined = mode === "artifact" ? "html" : undefined;
        await handleSendTo(session.id, prompt, skill, fmt);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Failed to start that conversation.");
      }
    },
    [activeSession, refreshSessions, handleSendTo]
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

  // Artifact history for the open conversation, newest first. Derived from
  // messages already loaded -- no extra requests.
  const artifactHistory: ArtifactHistoryEntry[] = (activeSession?.messages ?? [])
    .filter((m) => m.artifact)
    .map((m, idx, arr) => ({
      messageId: m.id,
      artifact: m.artifact!,
      title: `${m.artifact!.format === "html" ? "HTML page" : "Markdown doc"} #${arr.length - idx}`,
      createdAt: m.created_at,
    }))
    .reverse();

  const followUps = suggestFollowUps(activeSession?.messages ?? []);

  const openArtifact = useCallback((message: ChatMessage) => {
    setOpenArtifactMessage(message);
    setRightView("artifact");
    setRightOpen(true);
  }, []);

  const openCitation = useCallback(async (title: string) => {
    setSourceTitle(title);
    setRightView("source");
    setRightOpen(true);
    setSourceLoading(true);
    setSourceError(null);
    setSource(null);
    try {
      setSource(await api.getSource(title));
    } catch (e) {
      setSourceError(e instanceof ApiError ? e.message : "Failed to load source excerpts.");
    } finally {
      setSourceLoading(false);
    }
  }, []);

  const sessionTitle = activeSession?.title || (activeSession ? "New conversation" : null);

  return (
    <div className="app-shell">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSession?.id ?? null}
        onSelect={handleSelectSession}
        onNewSession={handleNewSession}
        onDelete={handleDeleteSession}
        onRename={handleRenameSession}
        onOpenStatus={() => setStatusOpen(true)}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <div className="main-column">
        {/* Top Bar */}
        <header className="app-header">
          <div className="app-header-left">
            <button
              className="sidebar-toggle"
              onClick={() => setSidebarOpen((open) => !open)}
              aria-label={sidebarOpen ? "Close conversation list" : "Open conversation list"}
              aria-expanded={sidebarOpen}
            >
              ☰
            </button>
            {sessionTitle && (
              <span className="app-header-title">{sessionTitle}</span>
            )}
          </div>

          <ModelBadge
            config={config}
            onChangeProvider={handleChangeProvider}
            sessionTitle={sessionTitle && !sessionTitle.startsWith("app-header") ? undefined : undefined}
          />
        </header>

        <div className="content-row">
          <ChatPane
            session={activeSession}
            sending={sending}
            error={error}
            fellBack={fellBack}
            onSend={handleSend}
            onOpenArtifact={openArtifact}
            onOpenCitation={openCitation}
            followUps={followUps}
            onNewSession={handleNewSession}
            onQuickStart={handleQuickStart}
          />

          {!rightOpen && (artifactHistory.length > 0 || activeSession) && (
            <button
              className="right-sidebar-reopen"
              onClick={() => setRightOpen(true)}
              title="Open the artifact and source panel"
            >
              ◧ Panel
            </button>
          )}

          {rightOpen && (
            <RightSidebar
              view={rightView}
              onChangeView={setRightView}
              onClose={() => setRightOpen(false)}
              artifact={openArtifactMessage?.artifact ?? null}
              sourceTitle={sourceTitle}
              source={source}
              sourceLoading={sourceLoading}
              sourceError={sourceError}
              history={artifactHistory}
              activeHistoryId={openArtifactMessage?.id ?? null}
              onOpenHistoryEntry={(entry) => {
                const msg = (activeSession?.messages ?? []).find((m) => m.id === entry.messageId);
                if (msg) openArtifact(msg);
              }}
            />
          )}
        </div>
      </div>

      {statusOpen && <StatusDashboard config={config} onClose={() => setStatusOpen(false)} />}
    </div>
  );
}
