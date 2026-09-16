import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { SessionSearchHit, SessionSummary } from "../types";

interface Props {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onNewSession: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onOpenStatus: () => void;
  isOpen: boolean;
  onClose: () => void;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onSelect,
  onNewSession,
  onDelete,
  onRename,
  onOpenStatus,
  isOpen,
  onClose,
}: Props) {
  const [query, setQuery] = useState("");
  // Results are stored with the query they belong to, so render can tell
  // "results for what I typed" from "stale results for the previous query".
  // Without this, typing a new search flashed the previous search's hits
  // during the debounce window.
  const [result, setResult] = useState<{ q: string; hits: SessionSearchHit[] } | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const renameRef = useRef<HTMLInputElement>(null);

  // Debounced server-side search. Title matches come back from the session
  // list alone, but matching *message bodies* needs the backend, since the
  // list endpoint only returns summaries.
  useEffect(() => {
    const q = query.trim();
    if (!q) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const hits = await api.searchSessions(q);
        if (!cancelled) setResult({ q, hits });
      } catch {
        if (!cancelled) setResult({ q, hits: [] });
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  useEffect(() => {
    if (renamingId) renameRef.current?.focus();
  }, [renamingId]);

  function startRename(session: { id: string; title: string | null }) {
    setRenamingId(session.id);
    setDraftTitle(session.title ?? "");
  }

  function commitRename(id: string) {
    const title = draftTitle.trim();
    if (title) onRename(id, title);
    setRenamingId(null);
  }

  const trimmed = query.trim();
  const isSearch = trimmed.length > 0;
  // Only treat results as current when they match what's typed right now.
  const current = result && result.q === trimmed ? result.hits : null;
  const searching = isSearch && current === null;

  const listed: { id: string; title: string | null; snippet?: string | null }[] = isSearch
    ? (current ?? []).map((h) => ({ id: h.id, title: h.title, snippet: h.snippet }))
    : sessions.map((s) => ({ id: s.id, title: s.title }));

  return (
    <aside className={isOpen ? "sidebar sidebar-open" : "sidebar"}>
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">L</div>
        <span className="sidebar-brand-name">Lenny Growth</span>
      </div>

      <div className="sidebar-actions">
        <button className="new-session-btn" onClick={onNewSession} id="new-chat-btn">
          <span>+ New Chat</span>
          <span className="new-session-btn-shortcut">⌘K</span>
        </button>
      </div>

      <div className="sidebar-search">
        <input
          className="sidebar-search-input"
          type="text"
          placeholder="Search conversations…"
          aria-label="Search conversations by title or message content"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {isSearch && (
          <button
            className="sidebar-search-clear"
            onClick={() => setQuery("")}
            aria-label="Clear search"
          >
            ✕
          </button>
        )}
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-label">
          {isSearch
            ? searching
              ? "Searching…"
              : `${listed.length} result${listed.length === 1 ? "" : "s"}`
            : "Recent Sessions"}
        </div>

        <ul className="session-list">
          {listed.map((s) => (
            <li
              key={s.id}
              className={s.id === activeSessionId ? "session-item active" : "session-item"}
            >
              {renamingId === s.id ? (
                <input
                  ref={renameRef}
                  className="session-rename-input"
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                  onBlur={() => commitRename(s.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitRename(s.id);
                    if (e.key === "Escape") setRenamingId(null);
                  }}
                  aria-label="New conversation title"
                />
              ) : (
                <>
                  <button
                    className="session-item-btn"
                    onClick={() => {
                      onSelect(s.id);
                      onClose();
                    }}
                    onDoubleClick={() => startRename(s)}
                    title={s.snippet ?? undefined}
                  >
                    <span className="session-item-title">{s.title || "New conversation"}</span>
                    {s.snippet && (
                      <span className="session-item-snippet">
                        <span className="session-match-tag">in message</span>
                        {s.snippet}
                      </span>
                    )}
                  </button>
                  <button
                    className="session-rename-btn"
                    aria-label="Rename conversation"
                    title="Rename"
                    onClick={(e) => {
                      e.stopPropagation();
                      startRename(s);
                    }}
                  >
                    ✎
                  </button>
                  <button
                    className="session-delete-btn"
                    aria-label="Delete conversation"
                    title="Delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(s.id);
                    }}
                  >
                    ×
                  </button>
                </>
              )}
            </li>
          ))}

          {listed.length === 0 && (
            <li className="session-empty">
              {searching
                ? "Searching…"
                : isSearch
                  ? "No conversations match that search"
                  : "No conversations yet"}
            </li>
          )}
        </ul>
      </div>

      <div className="sidebar-footer">
        <button className="sidebar-status-btn" onClick={onOpenStatus} title="System status">
          <span className="sidebar-status-dot" /> System status
        </button>
      </div>
    </aside>
  );
}
