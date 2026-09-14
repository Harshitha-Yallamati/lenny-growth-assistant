import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Artifact } from "../types";

interface Props {
  artifact: Artifact | null;
  onClose: () => void;
}

type ArtifactTab = "preview" | "code" | "markdown";

/**
 * Security note (see architecture.md): the backend already strips <script>
 * tags and event-handler attributes from HTML artifacts server-side. This
 * viewer adds a second, independent layer: the HTML renders inside an
 * <iframe sandbox=""> with NO tokens enabled at all -- no allow-scripts, no
 * allow-same-origin, no allow-forms, no allow-popups. That means even a
 * script that slipped past sanitization cannot execute, and the frame has no
 * access to the parent page, cookies, or localStorage regardless. A strict
 * CSP meta tag is injected as a third layer in case sandboxing is ever
 * loosened later. Markdown artifacts render through react-markdown without
 * rehype-raw, so embedded raw HTML is displayed as inert text, never parsed.
 */
export function ArtifactViewer({ artifact, onClose }: Props) {
  const [tab, setTab] = useState<ArtifactTab>("preview");

  const srcDoc = useMemo(() => {
    if (!artifact || artifact.format !== "html") return "";
    return `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data: https:; font-src data:;" />
<style>body{font-family:system-ui,sans-serif;margin:16px;color:#1a1a1a;}</style>
</head>
<body>${artifact.content}</body>
</html>`;
  }, [artifact]);

  if (!artifact) return null;

  const isHtml = artifact.format === "html";
  const formatLabel = isHtml ? "HTML Component" : "Markdown";

  function handleCopy() {
    navigator.clipboard.writeText(artifact!.content).catch(() => {});
  }

  return (
    <div className="artifact-viewer">
      {/* Header */}
      <div className="artifact-viewer-header">
        {/* Format Badge */}
        <div className="artifact-format-badge">
          {isHtml ? "HTML" : "MD"}
          &nbsp;{isHtml ? "Component" : "Document"}
        </div>

        {/* Sandboxed badge for HTML */}
        {isHtml && (
          <div className="artifact-sandboxed-badge">
            ✓ Sandboxed Preview
          </div>
        )}

        {/* Tabs */}
        <div className="artifact-tabs">
          <button
            className={`artifact-tab${tab === "preview" ? " active" : ""}`}
            onClick={() => setTab("preview")}
          >
            Preview
          </button>
          <button
            className={`artifact-tab${tab === "code" ? " active" : ""}`}
            onClick={() => setTab("code")}
          >
            Code
          </button>
          <button
            className={`artifact-tab${tab === "markdown" ? " active" : ""}`}
            onClick={() => setTab("markdown")}
          >
            Markdown
          </button>
        </div>

        {/* Actions */}
        <div className="artifact-actions">
          <button className="artifact-action-btn" onClick={handleCopy} title="Copy to clipboard">
            📋
          </button>
          <button className="artifact-action-btn" title="Download">
            ⬇
          </button>
          <button
            className="artifact-action-btn"
            onClick={onClose}
            title="Close artifact viewer"
            aria-label="Close artifact viewer"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="artifact-viewer-body">
        {tab === "preview" && isHtml && (
          <iframe
            title={`${formatLabel} preview`}
            className="artifact-iframe"
            srcDoc={srcDoc}
            sandbox=""
            referrerPolicy="no-referrer"
          />
        )}

        {tab === "preview" && !isHtml && (
          <div className="artifact-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content}</ReactMarkdown>
          </div>
        )}

        {tab === "code" && (
          <div className="artifact-markdown">
            <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--text)", lineHeight: 1.6 }}>
              {artifact.content}
            </pre>
          </div>
        )}

        {tab === "markdown" && (
          <div className="artifact-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
