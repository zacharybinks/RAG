import React, { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

/**
 * ProposalDraftGenerator
 *
 * UI to:
 *  - Trigger backend POST /rfps/{projectId}/proposal-draft
 *  - Preview saved draft_proposal.md
 *  - Download the proposal file
 *
 * Usage:
 *   <ProposalDraftGenerator projectId={project.project_id} />
 *   // Or on a route like /projects/:projectId/draft
 *   <Route path="/projects/:projectId/draft" element={<ProposalDraftGenerator />} />
 */
export default function ProposalDraftGenerator({ projectId: projectIdProp }) {
  const params = useParams();
  const projectId = projectIdProp || params.projectId;

  const API_BASE = useMemo(
    () => process.env.REACT_APP_API_URL || "http://localhost:8000",
    []
  );

  const [query, setQuery] = useState("");
  const [useKB, setUseKB] = useState(true);
  const [wordsPerSection, setWordsPerSection] = useState(1500);
  const [customSections, setCustomSections] = useState(false);
  const [sectionsText, setSectionsText] = useState("");
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resultPath, setResultPath] = useState("");
  const [resultSections, setResultSections] = useState([]);
  const [preview, setPreview] = useState("");

  function getToken() {
    return (
      localStorage.getItem("access_token") ||
      localStorage.getItem("token") ||
      ""
    );
  }

  function linesToSections(text) {
    return text
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function generateDraft(e) {
    e?.preventDefault();
    if (!projectId) {
      alert("No project id found.");
      return;
    }
    const token = getToken();
    if (!token) {
      alert("No auth token found in localStorage.");
      return;
    }

    setIsSubmitting(true);
    setStatus("Starting draft generation...");
    setResultPath("");
    setPreview("");

    const body = {
      query: query || "Draft a comprehensive proposal",
      use_knowledge_base: !!useKB,
      prompt_function_id: null,
      words_per_section: Number(wordsPerSection) || 1500,
    };
    const secs = customSections ? linesToSections(sectionsText) : null;
    if (secs && secs.length) body.sections = secs;

    try {
      const resp = await fetch(`${API_BASE}/rfps/${projectId}/proposal-draft`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(`Draft generation failed: ${resp.status} ${txt}`);
      }
      const data = await resp.json();
      setStatus("Draft generated. Fetching preview...");
      setResultPath(data.path || "");
      setResultSections(data.sections || []);

      // Fetch the draft markdown for preview
      await fetchPreview();
      setStatus("Done.");
    } catch (err) {
      console.error(err);
      setStatus(String(err.message || err));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function fetchPreview() {
    const token = getToken();
    try {
      const resp = await fetch(
        `${API_BASE}/rfps/${projectId}/documents/draft_proposal.md`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!resp.ok) {
        const msg = await resp.text();
        throw new Error(`Preview fetch failed: ${resp.status} ${msg}`);
      }
      const text = await resp.text();
      setPreview(text);
    } catch (err) {
      console.error(err);
      setPreview("");
      setStatus((s) => `${s}\n${String(err.message || err)}`);
    }
  }

  async function downloadDraft() {
    const token = getToken();
    try {
      const resp = await fetch(
        `${API_BASE}/rfps/${projectId}/documents/draft_proposal.md`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!resp.ok) throw new Error(`Download failed: ${resp.status}`);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `draft_proposal_${projectId}.md`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert(String(err.message || err));
    }
  }

  return (
    <div style={{ maxWidth: 980, margin: "0 auto", padding: 16 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>
        Proposal Draft Generator
      </h1>
      <p style={{ color: "#555", marginBottom: 16 }}>
        Project: <b>{projectId || "(none)"}</b>
      </p>

      <form onSubmit={generateDraft} style={{ display: "grid", gap: 12 }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Topic / Guidance (optional):</span>
          <textarea
            rows={4}
            placeholder="e.g., AFRL OTAFI proposal focusing on technical approach, staffing, risk, and compliance"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ padding: 8, fontFamily: "inherit" }}
          />
        </label>

        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={useKB}
              onChange={(e) => setUseKB(e.target.checked)}
            />
            <span>Use Knowledge Base</span>
          </label>

          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span>Words per section:</span>
            <input
              type="number"
              min={600}
              max={5000}
              value={wordsPerSection}
              onChange={(e) => setWordsPerSection(e.target.value)}
              style={{ width: 120, padding: 6 }}
            />
          </label>
        </div>

        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={customSections}
            onChange={(e) => setCustomSections(e.target.checked)}
          />
          <span>Provide custom section list</span>
        </label>

        {customSections && (
          <label style={{ display: "grid", gap: 6 }}>
            <span>Sections (one per line, top-level headings):</span>
            <textarea
              rows={8}
              placeholder={
                "Executive Summary\nTechnical Approach\nManagement Approach\nStaffing & Key Personnel\nSchedule & Milestones\nRisk Management\nQuality Assurance\nCompliance & Certifications\nCost & Pricing Approach\nAssumptions & Dependencies"
              }
              value={sectionsText}
              onChange={(e) => setSectionsText(e.target.value)}
              style={{ padding: 8, fontFamily: "inherit" }}
            />
          </label>
        )}

        <div style={{ display: "flex", gap: 12 }}>
          <button
            type="submit"
            disabled={isSubmitting || !projectId}
            style={{
              padding: "10px 14px",
              border: "1px solid #ddd",
              background: isSubmitting ? "#eee" : "#111",
              color: "white",
              cursor: isSubmitting ? "not-allowed" : "pointer",
              borderRadius: 6,
            }}
          >
            {isSubmitting ? "Generating…" : "Generate Draft"}
          </button>

          <button
            type="button"
            onClick={downloadDraft}
            disabled={!projectId}
            style={{
              padding: "10px 14px",
              border: "1px solid #ddd",
              background: "white",
              color: "#111",
              cursor: "pointer",
              borderRadius: 6,
            }}
          >
            Download Draft (MD)
          </button>
        </div>
      </form>

      <div style={{ marginTop: 18 }}>
        <div
          style={{
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace",
            whiteSpace: "pre-wrap",
            background: "#fafafa",
            border: "1px solid #eee",
            borderRadius: 6,
            padding: 12,
            minHeight: 60,
          }}
        >
          {status || "Idle"}
        </div>
      </div>

      <h2 style={{ marginTop: 24 }}>Preview</h2>
      {!preview && (
        <p style={{ color: "#777" }}>
          Generate a draft to see a preview. The full file is saved as{" "}
          <code>draft_proposal.md</code> in the project folder.
        </p>
      )}
      {preview && (
        <textarea
          readOnly
          value={preview}
          style={{
            width: "100%",
            height: 420,
            padding: 10,
            fontFamily: "monospace",
          }}
        />
      )}
    </div>
  );
}
