import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Artifact } from "../types";

interface Props {
  artifact: Artifact | null;
  onClose: () => void;
}

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

  return (
    <div className="artifact-viewer">
      <div className="artifact-viewer-header">
        <span className="artifact-viewer-title">
          Artifact ({artifact.format === "html" ? "HTML/CSS" : "Markdown"})
        </span>
        <button className="artifact-viewer-close" onClick={onClose} aria-label="Close artifact viewer">
          ×
        </button>
      </div>
      <div className="artifact-viewer-body">
        {artifact.format === "html" ? (
          <iframe
            title="Generated artifact"
            className="artifact-iframe"
            srcDoc={srcDoc}
            sandbox=""
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="artifact-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
