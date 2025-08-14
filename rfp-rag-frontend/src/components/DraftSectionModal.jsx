import React, { useState } from "react";
import api from "../services/api";
import "./ProposalBuilderV2.css";   // ✅ relative import

export default function DraftSectionModal({
  open, onClose, projectId, sectionKey, instruction, useKnowledgeBase = true, selectedExampleIds = [],
  onDraftReady, // optional callback
}) {
  const [busy, setBusy] = useState(false);
  const [resp, setResp] = useState(null);
  const [error, setError] = useState(null);

  if (!open) return null;

  async function runDraft() {
    setBusy(true); setError(null);
    try {
      const payload = {
        instruction,
        use_knowledge_base: useKnowledgeBase,
        example_ids: selectedExampleIds,
      };
      const { data } = await api.post(
        `/rfps/${encodeURIComponent(projectId)}/sections/${encodeURIComponent(sectionKey)}/draft`,
        payload
      );
      setResp(data);
      if (onDraftReady) onDraftReady(sectionKey, data?.html || "");
    } catch (e) {
      setError(e?.response?.data || e?.message || "Draft failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{
      position:"fixed", inset:0, background:"rgba(0,0,0,0.35)", display:"flex",
      alignItems:"center", justifyContent:"center", zIndex:9999
    }}>
      <div style={{background:"#fff", width:"min(1100px, 95vw)", maxHeight:"90vh", overflow:"auto", borderRadius:10, padding:18}}>
        <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
          <h2 style={{margin:0}}>Draft: {instruction?.title}</h2>
          <button onClick={onClose}>Close</button>
        </div>

        {!resp && (
          <div style={{display:"flex", gap:12, alignItems:"center", margin:"12px 0"}}>
            <button disabled={busy} onClick={runDraft}>
              {busy ? "Drafting…" : "Generate Draft"}
            </button>
            {error && <span style={{color:"crimson"}}>{String(error)}</span>}
          </div>
        )}

        {resp && (
          <div style={{display:"grid", gridTemplateColumns:"1fr 320px", gap:16}}>
            <div style={{border:"1px solid #eee", padding:20, borderRadius:8, background: "#fafafa"}}>
              <div
                className="draft-content"
                style={{
                  fontFamily: "Arial, sans-serif",
                  lineHeight: "1.6",
                  fontSize: "14px",
                  textAlign: "left"
                }}
                dangerouslySetInnerHTML={{ __html: resp.html || "" }}
              />
            </div>
            <aside style={{border:"1px solid #eee", padding:12, borderRadius:8}}>
              <h4 style={{marginTop:0}}>Quality checks</h4>
              <div>
                <strong>Similarity:</strong>{" "}
                {resp?.checks?.similarity ? (resp.checks.similarity.flag ? `⚠ ${resp.checks.similarity.max.toFixed(3)} (rephrase)` : `${resp.checks.similarity.max.toFixed(3)} OK`) : "—"}
              </div>
              <div style={{marginTop:10}}>
                <strong>Compliance:</strong>
                <ul style={{paddingLeft:18}}>
                  {(resp?.checks?.compliance || []).map((c, i) => (
                    <li key={i}>{c.met ? "✅" : "⬜"} {c.item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <strong>Sources:</strong>
                <ul style={{paddingLeft:18}}>
                  {(resp?.sources || []).slice(0, 8).map((s, i) => (
                    <li key={i}>{s.kind} · {s.source || s.id || "…"}</li>
                  ))}
                </ul>
              </div>
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}
