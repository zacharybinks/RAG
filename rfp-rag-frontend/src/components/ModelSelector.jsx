// src/components/ModelSelector.jsx
import React, { useEffect, useMemo, useState } from "react";

/**
 * ModelSelector (router-free)
 *
 * Props:
 *   - projectId (required): string
 *
 * Behavior:
 *   - GET /models
 *   - GET /rfps/:projectId/settings
 *   - POST /rfps/:projectId/settings { model_name }
 */
export default function ModelSelector({ projectId }) {
  const API_BASE = useMemo(
    () => process.env.REACT_APP_API_URL || "http://localhost:8000",
    []
  );
  const token = useMemo(
    () =>
      localStorage.getItem("access_token") ||
      localStorage.getItem("token") ||
      "",
    []
  );

  const [models, setModels] = useState([]);
  const [current, setCurrent] = useState("");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    async function load() {
      if (!projectId) {
        setStatus("No projectId provided to ModelSelector.");
        return;
      }
      try {
        const [m, s] = await Promise.all([
          fetch(`${API_BASE}/models`),
          fetch(`${API_BASE}/rfps/${projectId}/settings`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);
        if (!m.ok) throw new Error(`GET /models failed: ${m.status}`);
        if (!s.ok) throw new Error(`GET /rfps/${projectId}/settings failed: ${s.status}`);

        const mjs = await m.json();
        const sjs = await s.json();
        setModels(mjs);
        setCurrent(sjs?.model_name || mjs?.[0]?.model_name || "");
        setStatus("");
      } catch (e) {
        setStatus(String(e.message || e));
      }
    }
    load();
  }, [API_BASE, projectId, token]);

  async function save(e) {
    e?.preventDefault();
    if (!projectId) {
      setStatus("No projectId provided.");
      return;
    }
    setSaving(true);
    setStatus("Saving...");
    try {
      const resp = await fetch(`${API_BASE}/rfps/${projectId}/settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ model_name: current }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      setStatus("Saved");
    } catch (e) {
      setStatus(String(e.message || e));
    } finally {
      setSaving(false);
    }
  }

  if (!projectId) {
    return (
      <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
        <h3 style={{ marginTop: 0 }}>Model</h3>
        <p style={{ color: "#b00" }}>
          ModelSelector needs a <code>projectId</code> prop.
        </p>
      </div>
    );
  }

  return (
    <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
      <h3 style={{ marginTop: 0 }}>Model</h3>
      <p style={{ color: "#555", marginTop: 0 }}>
        Pick a curated option. The backend enforces token limits per model.
      </p>
      <form
        onSubmit={save}
        style={{ display: "flex", gap: 12, alignItems: "center" }}
      >
        <select
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          style={{ padding: 8 }}
        >
          {models.map((m) => (
            <option key={m.id} value={m.model_name}>
              {m.label} — ctx {m.context_tokens} / max out{" "}
              {m.max_completion_tokens}
            </option>
          ))}
        </select>
        <button
          disabled={saving || !current}
          type="submit"
          style={{ padding: "8px 12px" }}
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </form>
      {status && <div style={{ marginTop: 8, color: "#666" }}>{status}</div>}
    </div>
  );
}
