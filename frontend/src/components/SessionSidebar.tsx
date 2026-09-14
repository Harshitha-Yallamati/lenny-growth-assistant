import type { SessionSummary } from "../types";

interface Props {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onNewSession: () => void;
  onDelete: (id: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onSelect,
  onNewSession,
  onDelete,
  isOpen,
  onClose,
}: Props) {
  return (
    <aside className={isOpen ? "sidebar sidebar-open" : "sidebar"}>
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">L</div>
        <span className="sidebar-brand-name">Lenny Growth</span>
      </div>

      {/* New Chat Button */}
      <div className="sidebar-actions">
        <button className="new-session-btn" onClick={onNewSession} id="new-chat-btn">
          <span>+ New Chat</span>
          <span className="new-session-btn-shortcut">⌘K</span>
        </button>
      </div>

      {/* Search */}
      <div className="sidebar-search">
        <input
          className="sidebar-search-input"
          type="text"
          placeholder="Search archives…"
          aria-label="Search sessions"
        />
      </div>

      {/* Session List */}
      <div className="sidebar-section">
        <div className="sidebar-section-label">Recent Sessions</div>
        <ul className="session-list">
          {sessions.map((s) => (
            <li
              key={s.id}
              className={s.id === activeSessionId ? "session-item active" : "session-item"}
            >
              <button
                className="session-item-btn"
                onClick={() => {
                  onSelect(s.id);
                  onClose();
                }}
              >
                {s.title || "New conversation"}
              </button>
              <button
                className="session-delete-btn"
                aria-label="Delete session"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(s.id);
                }}
              >
                ×
              </button>
            </li>
          ))}
          {sessions.length === 0 && (
            <li className="session-empty">No conversations yet</li>
          )}
        </ul>

        {/* Transcripts & Playbooks section header */}
        {sessions.length > 0 && (
          <div className="sidebar-section-label" style={{ marginTop: "12px" }}>
            Transcripts &amp; Playbooks
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-footer-icons">
          <div className="sidebar-footer-icon" title="Settings">⚙</div>
          <div className="sidebar-footer-icon" title="Keyboard shortcuts">⌨</div>
          <div className="sidebar-footer-icon" title="Help">?</div>
        </div>
        <span className="sidebar-footer-version">v2.4.0</span>
      </div>
    </aside>
  );
}
