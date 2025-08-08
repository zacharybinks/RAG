import React, { useMemo, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import InfoSidebar from "../components/InfoSidebar";
import SectionsSidebar from "../components/SectionsSidebar";
import QuillEditor from "../components/QuillEditor";
import ExportDocxButton from "../components/ExportDocButton";
import "./ProposalBuilderPage.css";

export default function ProposalBuilderPage({ projectId: projectIdProp }) {
  const params = useParams();
  const projectId = projectIdProp || params?.projectId;

  const API_BASE = useMemo(() => process.env.REACT_APP_API_URL || "http://localhost:8000", []);
  const token = useMemo(
    () => localStorage.getItem("access_token") || localStorage.getItem("token") || "",
    []
  );

  // Builder state
  const [query, setQuery] = useState("");
  const [useKB, setUseKB] = useState(true);
  const [wordsPerSection, setWordsPerSection] = useState(1500);

  const [sections, setSections] = useState([]); // [{id,title, html}]
  const [activeId, setActiveId] = useState(null);
  const [status, setStatus] = useState("");

  const activeSection = sections.find((s) => s.id === activeId) || null;

  const addSection = useCallback((title = "New Section") => {
    const id = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const next = { id, title, html: "" };
    setSections((prev) => [...prev, next]);
    setActiveId(id);
  }, []);

  const renameSection = useCallback((id, title) => {
    setSections((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)));
  }, []);

  const removeSection = useCallback(
    (id) => {
      setSections((prev) => prev.filter((s) => s.id !== id));
      if (activeId === id) setActiveId(null);
    },
    [activeId]
  );

  const moveSection = useCallback((id, dir) => {
    setSections((prev) => {
      const i = prev.findIndex((s) => s.id === id);
      if (i < 0) return prev;
      const j = dir === "up" ? i - 1 : i + 1;
      if (j < 0 || j >= prev.length) return prev;
      const copy = prev.slice();
      const [item] = copy.splice(i, 1);
      copy.splice(j, 0, item);
      return copy;
    });
  }, []);

  const setActiveHtml = useCallback(
    (html) => {
      if (!activeId) return;
      setSections((prev) => prev.map((s) => (s.id === activeId ? { ...s, html } : s)));
    },
    [activeId]
  );

  // --- Outline & generation ---
  async function askOutline() {
    if (!projectId) return alert("No project id");
    setStatus("Generating outline...");
    try {
      const resp = await fetch(`${API_BASE}/rfps/${projectId}/proposal-outline`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ query: query || "Draft a comprehensive proposal", use_knowledge_base: !!useKB }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      const next = (data.sections || []).map((t, idx) => ({
        id: `${Date.now()}_${idx}`,
        title: t,
        html: "",
      }));
      setSections(next);
      setActiveId(next[0]?.id || null);
      setStatus("Outline created.");
    } catch (e) {
      console.error(e);
      setStatus(String(e.message || e));
    }
  }

  async function generateActiveSection() {
    if (!projectId || !activeSection) return;
    setStatus(`Generating section: ${activeSection.title}...`);
    try {
      const resp = await fetch(`${API_BASE}/rfps/${projectId}/proposal-section`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          section_title: activeSection.title,
          query: query || "Draft a comprehensive proposal",
          use_knowledge_base: !!useKB,
          words_per_section: Number(wordsPerSection) || 1500,
        }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      setActiveHtml(data.content || "");
      setStatus(`Section generated: ${activeSection.title}`);
    } catch (e) {
      console.error(e);
      setStatus(String(e.message || e));
    }
  }

  // --- Save / Load ---
  async function saveDraft(versioned = true) {
    try {
      setStatus("Saving draft...");
      const resp = await fetch(`${API_BASE}/rfps/${projectId}/proposal-save`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          title: "Proposal Draft",
          sections,
          versioned,
        }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      setStatus(`Saved. ${versioned ? "Versioned" : "Latest"} JSON: ${data.json}`);
    } catch (e) {
      console.error(e);
      setStatus(String(e.message || e));
    }
  }

  async function loadLatest() {
    try {
      setStatus("Loading latest draft...");
      const resp = await fetch(`${API_BASE}/rfps/${projectId}/proposal-load`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json(); // {title, sections, timestamp}
      const items = (data.sections || []).map((s, idx) => ({
        id: s.id || `${Date.now()}_${idx}`,
        title: s.title || "Section",
        html: s.html || "",
      }));
      setSections(items);
      setActiveId(items[0]?.id || null);
      setStatus("Loaded latest draft.");
    } catch (e) {
      console.error(e);
      setStatus(String(e.message || e));
    }
  }

  // Compile full HTML for export
  const fullHtml = useMemo(() => {
    const toc = sections.map((s) => `<li>${s.title}</li>`).join("");
    const body = sections.map((s) => `<h2>${s.title}</h2>\n${s.html || ""}`).join("\n");
    return `
      <html>
      <head>
        <meta charset="utf-8" />
        <link rel="stylesheet" href="/proposal-doc.css">
      </head>
      <body>
        <h1>Proposal Draft</h1>
        <div class="toc">
          <h2>Table of Contents</h2>
          <ul>${toc}</ul>
        </div>
        ${body}
      </body>
      </html>
    `;
  }, [sections]);

  return (
    <div className="pb-grid">
      {/* Left: Info Sidebar */}
      <div className="pb-left">
        <InfoSidebar />
      </div>

      {/* Center: Editor Canvas */}
      <div className="pb-center">
        <div className="pb-toolbar">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Topic / guidance (optional)"
            className="pb-input"
          />
          <label className="pb-inline">
            <input type="checkbox" checked={useKB} onChange={(e) => setUseKB(e.target.checked)} />
            <span>Use Knowledge Base</span>
          </label>
          <label className="pb-inline">
            <span>Words per section:</span>
            <input
              type="number"
              min={600}
              max={5000}
              value={wordsPerSection}
              onChange={(e) => setWordsPerSection(e.target.value)}
              className="pb-num"
            />
          </label>

          <button onClick={askOutline} className="pb-btn">Generate Outline</button>
          <button onClick={generateActiveSection} disabled={!activeSection} className="pb-btn">
            Generate Current Section
          </button>
          <button onClick={() => saveDraft(true)} className="pb-btn">Save (Versioned)</button>
          <button onClick={() => saveDraft(false)} className="pb-btn">Save (Latest)</button>
          <button onClick={loadLatest} className="pb-btn">Load Latest</button>
          <ExportDocxButton html={fullHtml} filename={`proposal_${projectId}.docx`} />
        </div>

        <div className="pb-status">{status || "Ready"}</div>

        <div className="pb-editor-wrap">
          {activeSection ? (
            <QuillEditor value={activeSection.html} onChange={setActiveHtml} />
          ) : (
            <div className="pb-placeholder">Select a section to start editing.</div>
          )}
        </div>
      </div>

      {/* Right: Sections Sidebar */}
      <div className="pb-right">
        <SectionsSidebar
          sections={sections}
          activeId={activeId}
          onSelect={setActiveId}
          onAdd={addSection}
          onRename={renameSection}
          onRemove={removeSection}
          onMove={moveSection}
        />
      </div>
    </div>
  );
}
