import { ArtifactViewer } from "./ArtifactViewer";
import { SourcePreview } from "./SourcePreview";
import { ArtifactHistory } from "./ArtifactHistory";
import type {
  Artifact,
  ArtifactHistoryEntry,
  RightPanelView,
  SourceDetail,
} from "../types";

interface Props {
  view: RightPanelView;
  onChangeView: (view: RightPanelView) => void;
  onClose: () => void;

  artifact: Artifact | null;

  sourceTitle: string | null;
  source: SourceDetail | null;
  sourceLoading: boolean;
  sourceError: string | null;

  history: ArtifactHistoryEntry[];
  activeHistoryId: string | null;
  onOpenHistoryEntry: (entry: ArtifactHistoryEntry) => void;
}

/**
 * The right-hand panel. One shell, three views — the artifact currently open,
 * the transcript excerpts behind a clicked citation, and the artifacts already
 * generated in this conversation. They share a panel because they're all
 * "supporting detail for the chat", and only one is ever worth looking at at
 * a time on the widths this app targets.
 */
export function RightSidebar({
  view,
  onChangeView,
  onClose,
  artifact,
  sourceTitle,
  source,
  sourceLoading,
  sourceError,
  history,
  activeHistoryId,
  onOpenHistoryEntry,
}: Props) {
  const tabs: { id: RightPanelView; label: string; badge?: number; enabled: boolean }[] = [
    { id: "artifact", label: "Artifact", enabled: artifact !== null },
    { id: "source", label: "Source", enabled: sourceTitle !== null },
    { id: "history", label: "History", badge: history.length, enabled: true },
  ];

  return (
    <aside className="right-sidebar" aria-label="Artifact and source details">
      <div className="right-sidebar-tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            className={`right-tab${view === t.id ? " active" : ""}`}
            onClick={() => onChangeView(t.id)}
            disabled={!t.enabled}
            title={t.enabled ? undefined : `Nothing to show in ${t.label} yet`}
            aria-current={view === t.id}
          >
            {t.label}
            {t.badge ? <span className="right-tab-badge">{t.badge}</span> : null}
          </button>
        ))}
        <button
          className="right-sidebar-close"
          onClick={onClose}
          aria-label="Close panel"
          title="Close panel"
        >
          ✕
        </button>
      </div>

      <div className="right-sidebar-body">
        {view === "artifact" &&
          (artifact ? (
            <ArtifactViewer artifact={artifact} />
          ) : (
            <div className="right-empty">
              No artifact open. Generate one with <strong>Create Artifact</strong>, or pick one
              from <strong>History</strong>.
            </div>
          ))}

        {view === "source" && (
          <SourcePreview
            title={sourceTitle}
            source={source}
            loading={sourceLoading}
            error={sourceError}
          />
        )}

        {view === "history" && (
          <ArtifactHistory
            entries={history}
            activeId={activeHistoryId}
            onOpen={onOpenHistoryEntry}
          />
        )}
      </div>
    </aside>
  );
}
