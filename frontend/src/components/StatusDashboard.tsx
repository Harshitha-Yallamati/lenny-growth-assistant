import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ConfigPayload, HealthPayload, KnowledgeBaseStats } from "../types";

interface Props {
  config: ConfigPayload | null;
  onClose: () => void;
}

type Row = { label: string; ok: boolean | null; detail: string };

/**
 * Operational status for the four things that can break a turn: the
 * database, the local model, the corpus, and the backend itself.
 *
 * Every row is read from a live endpoint — nothing here is hardcoded. If a
 * check can't be performed the row says "unknown" rather than assuming
 * healthy, because a status panel that defaults to green is worse than none.
 */
export function StatusDashboard({ config, onClose }: Props) {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [kb, setKb] = useState<KnowledgeBaseStats | null>(null);
  const [backendReachable, setBackendReachable] = useState<boolean | null>(null);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const h = await api.getHealth();
      setHealth(h);
      setBackendReachable(true);
    } catch {
      setHealth(null);
      setBackendReachable(false);
    }
    try {
      setKb(await api.getKnowledgeBaseStats());
    } catch {
      setKb(null);
    }
    setCheckedAt(new Date());
    setRefreshing(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const dbOk = health ? health.components.database === "ok" : null;
  const ollamaOk = health ? health.components.providers.ollama === true : null;
  const activeProvider = health?.components.active_provider ?? config?.active_provider ?? "unknown";

  const rows: Row[] = [
    {
      label: "Backend (FastAPI)",
      ok: backendReachable,
      detail:
        backendReachable === null
          ? "checking…"
          : backendReachable
            ? `reachable · status "${health?.status ?? "?"}"`
            : "unreachable — is the backend container running?",
    },
    {
      label: "PostgreSQL",
      ok: dbOk,
      detail:
        dbOk === null
          ? "unknown — backend unreachable"
          : dbOk
            ? "connected"
            : health?.components.database ?? "error",
    },
    {
      label: "Ollama (local model)",
      ok: ollamaOk,
      detail:
        ollamaOk === null
          ? "unknown — backend unreachable"
          : ollamaOk
            ? `reachable · ${config?.ollama_model ?? "model unknown"}`
            : "not reachable — run `ollama serve` on the host",
    },
    {
      label: "Knowledge base",
      ok: kb === null ? null : kb.chunk_count > 0,
      detail:
        kb === null
          ? "unknown"
          : kb.chunk_count > 0
            ? `${kb.chunk_count} chunks from ${kb.source_count} sources`
            : "empty — ingestion has not run",
    },
  ];

  return (
    <div className="status-overlay" role="dialog" aria-label="System status">
      <div className="status-dialog">
        <div className="status-header">
          <span className="status-title">System status</span>
          <button className="status-refresh" onClick={refresh} disabled={refreshing}>
            {refreshing ? "Checking…" : "↻ Refresh"}
          </button>
          <button className="status-close" onClick={onClose} aria-label="Close status">
            ✕
          </button>
        </div>

        <ul className="status-rows">
          {rows.map((r) => (
            <li key={r.label} className="status-row">
              <span
                className={`status-dot ${
                  r.ok === null ? "status-dot-unknown" : r.ok ? "status-dot-ok" : "status-dot-bad"
                }`}
                aria-hidden="true"
              />
              <span className="status-row-label">{r.label}</span>
              <span className="status-row-detail">{r.detail}</span>
            </li>
          ))}
        </ul>

        <div className="status-meta">
          <div>
            Active provider: <strong>{activeProvider}</strong>
            {health && !health.components.providers[activeProvider] && (
              <span className="status-warn"> — unreachable, requests fall back to Ollama</span>
            )}
          </div>
          {kb && kb.sources.length > 0 && (
            <details className="status-sources">
              <summary>{kb.source_count} sources indexed</summary>
              <ul>
                {kb.sources.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </details>
          )}
          {checkedAt && (
            <div className="status-checked">
              Last checked {checkedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
