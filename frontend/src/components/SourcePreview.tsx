import type { SourceDetail } from "../types";

interface Props {
  title: string | null;
  source: SourceDetail | null;
  loading: boolean;
  error: string | null;
}

/**
 * The transcript excerpts behind a clicked citation.
 *
 * Excerpts are fetched from /api/sources rather than carried on the citation
 * payload, so this also works for messages persisted before the endpoint
 * existed.
 */
export function SourcePreview({ title, source, loading, error }: Props) {
  if (!title) {
    return (
      <div className="right-empty">
        Click any citation under an answer to read the transcript excerpts it came from.
      </div>
    );
  }

  return (
    <div className="source-preview">
      <div className="source-preview-header">
        <div className="source-preview-title">{title}</div>
        {source?.url && (
          <a
            className="source-preview-link"
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open original ↗
          </a>
        )}
      </div>

      {loading && <div className="right-empty">Loading excerpts…</div>}

      {error && <div className="chat-banner chat-banner-error">⚠ {error}</div>}

      {!loading && !error && source && source.excerpts.length === 0 && (
        <div className="right-empty">
          No excerpts found for this source. It may have been renamed or removed from the corpus
          since this answer was generated.
        </div>
      )}

      {!loading && !error && source && source.excerpts.length > 0 && (
        <>
          <div className="source-preview-meta">
            Showing {source.excerpts.length} excerpt
            {source.excerpts.length === 1 ? "" : "s"} from this source
          </div>
          <ol className="source-excerpt-list">
            {source.excerpts.map((e) => (
              <li key={e.chunk_index} className="source-excerpt">
                <div className="source-excerpt-index">#{e.chunk_index + 1}</div>
                <p className="source-excerpt-text">{e.content}</p>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
