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
      <button className="new-session-btn" onClick={onNewSession}>
        + New chat
      </button>
      <ul className="session-list">
        {sessions.map((s) => (
          <li key={s.id} className={s.id === activeSessionId ? "session-item active" : "session-item"}>
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
        {sessions.length === 0 && <li className="session-empty">No conversations yet</li>}
      </ul>
    </aside>
  );
}
