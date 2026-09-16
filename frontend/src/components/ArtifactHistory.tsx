import type { ArtifactHistoryEntry } from "../types";

interface Props {
  entries: ArtifactHistoryEntry[];
  activeId: string | null;
  onOpen: (entry: ArtifactHistoryEntry) => void;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

/**
 * Artifacts generated in the current conversation, newest first.
 *
 * Scoped to the open session on purpose: artifacts live on messages, so a
 * cross-session list would mean fetching every session's full message history
 * up front. Switching conversations repopulates this from that session's
 * messages, which are already loaded.
 */
export function ArtifactHistory({ entries, activeId, onOpen }: Props) {
  if (entries.length === 0) {
    return (
      <div className="right-empty">
        No artifacts in this conversation yet. Use <strong>Create Artifact</strong> to generate a
        Markdown doc or an HTML page.
      </div>
    );
  }

  return (
    <ul className="artifact-history">
      {entries.map((entry) => (
        <li key={entry.messageId}>
          <button
            className={`artifact-history-item${entry.messageId === activeId ? " active" : ""}`}
            onClick={() => onOpen(entry)}
          >
            <span
              className={`artifact-type-chip artifact-type-${entry.artifact.format}`}
              aria-label={entry.artifact.format === "html" ? "HTML artifact" : "Markdown artifact"}
            >
              {entry.artifact.format === "html" ? "HTML" : "MD"}
            </span>
            <span className="artifact-history-text">
              <span className="artifact-history-title">{entry.title}</span>
              <span className="artifact-history-meta">
                {formatTime(entry.createdAt)} · {entry.artifact.content.length.toLocaleString()} chars
              </span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
