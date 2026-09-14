import type { SessionSummary } from "../types";

interface Props {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onNewSession: () => void;
  onDelete: (id: string) => void;
}

export function SessionSidebar({ sessions, activeSessionId, onSelect, onNewSession, onDelete }: Props) {
  return (
    <aside className="sidebar">
      <button className="new-session-btn" onClick={onNewSession}>
        + New chat
      </button>
      <ul className="session-list">
        {sessions.map((s) => (
          <li key={s.id} className={s.id === activeSessionId ? "session-item active" : "session-item"}>
            <button className="session-item-btn" onClick={() => onSelect(s.id)}>
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
