import React, { useEffect, useMemo, useState } from "react";
import api from "../services/api";              // ✅ default API client (relative)
import "./ProposalBuilderV2.css";
import { useAuth } from "../context/AuthContext";
import SectionInstructionCard from "./SectionInstructionCard";
import DraftSectionModal from "./DraftSectionModal";
import ExampleManager from "./ExampleManager";
import InstructionEditor from "./InstructionEditor";
import QuillEditor from "./QuillEditor";
import EnhancedSidebar from "./EnhancedSidebar";

function toKey(title) {
  return String(title || "section").toLowerCase().replace(/\s+/g, "_").replaceAll("/", "_");
}

export default function ProposalBuilderV2({ project }) {
  const { setView } = useAuth();
  const [topic, setTopic] = useState("");
  const [useKB, setUseKB] = useState(true);
  const [outline, setOutline] = useState([]);           // [{ title, key }]
  const [instructions, setInstructions] = useState({}); // key -> SectionInstruction
  const [selectedExampleIds, setSelectedExampleIds] = useState([]);
  const [drafts, setDrafts] = useState({});             // key -> html
  const [activeKey, setActiveKey] = useState(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("Ready.");
  const [showDraft, setShowDraft] = useState(false);
  const [editingSection, setEditingSection] = useState(null);
  const [newSectionTitle, setNewSectionTitle] = useState("");
  const [editingDraft, setEditingDraft] = useState(null);
  const [tempDraftContent, setTempDraftContent] = useState("");
  const [expandedSections, setExpandedSections] = useState(new Set());
  const [showExampleManager, setShowExampleManager] = useState(false);
  const [editingInstruction, setEditingInstruction] = useState(null);
  const [autoSaving, setAutoSaving] = useState(false);
  const [collapsedDrafts, setCollapsedDrafts] = useState(new Set());

  useEffect(() => {
    if (!project) {
      setStatus("No project selected.");
    } else {
      loadLatest();
    }
  }, [project]);

  // Load previously saved content
  async function loadLatest() {
    if (!project) return;
    try {
      setStatus("Loading latest draft...");
      const resp = await api.get(`/rfps/${project.project_id}/proposal-load`);
      const data = resp.data;
      const sections = data.sections || [];

      if (sections.length > 0) {
        // Reconstruct outline from saved sections
        const loadedOutline = sections.map(s => ({
          title: s.title || "Section",
          key: s.id || toKey(s.title || "section")
        }));
        setOutline(loadedOutline);

        // Reconstruct drafts from saved sections
        const loadedDrafts = {};
        const loadedInstructions = {};

        sections.forEach(s => {
          const key = s.id || toKey(s.title || "section");
          if (s.html) {
            loadedDrafts[key] = s.html;
          }
          // Load instructions if they exist in the saved data
          if (s.instruction) {
            loadedInstructions[key] = s.instruction;
          }
        });

        setDrafts(loadedDrafts);
        setInstructions(loadedInstructions);

        // Load metadata if available
        if (data.metadata) {
          if (data.metadata.selectedExampleIds) {
            setSelectedExampleIds(data.metadata.selectedExampleIds);
          }
        }

        const instructionCount = Object.keys(loadedInstructions).length;
        const draftCount = Object.keys(loadedDrafts).length;
        setStatus(`Loaded ${sections.length} sections (${instructionCount} instructions, ${draftCount} drafts) from latest draft.`);
      } else {
        setStatus("No previous draft found. Ready to generate outline.");
      }
    } catch (e) {
      // It's common for a 404 to occur if no draft exists, so handle gracefully
      if (e.response && e.response.status === 404) {
        setStatus("No previous draft found. Ready to generate outline.");
      } else {
        console.error("Load error:", e);
        setStatus("Failed to load previous draft. Ready to generate outline.");
      }
    }
  }

  async function generateOutline() {
    if (!project) return;
    setBusy(true);
    setStatus("Generating outline...");
    try {
      const { data } = await api.post(`/rfps/${project.project_id}/proposal-outline`, {
        query: topic || "Draft a comprehensive proposal",
        use_knowledge_base: !!useKB,
      });
      const sections = data?.sections || [
        "Executive Summary","Technical Approach","Management Approach","Staffing & Key Personnel",
        "Schedule & Milestones","Risk Management","Quality Assurance",
        "Compliance & Certifications","Cost & Pricing Approach","Assumptions & Dependencies",
      ];
      const normalized = sections.map((t) => ({ title: t, key: toKey(t) }));
      setOutline(normalized);
      setInstructions({});
      setDrafts({});
      setActiveKey(normalized[0]?.key ?? null);
      setStatus("Outline created.");
    } catch (e) {
      console.error(e);
      setStatus(e?.response?.data?.detail || e?.message || "Outline failed.");
    } finally {
      setBusy(false);
    }
  }

  async function generateInstructionSheets() {
    if (!project) return;
    if (!outline.length) { setStatus("Add or generate an outline first."); return; }
    setBusy(true);
    setStatus("Generating instruction sheets...");
    try {
      const payload = { outline: outline.map(o => ({ title: o.title, key: o.key })), use_knowledge_base: !!useKB };
      const { data } = await api.post(`/rfps/${project.project_id}/sections/instructions`, payload);
      const map = Object.create(null);
      for (const instr of data?.instructions || data || []) map[instr.section_key] = instr;
      setInstructions(map);
      setStatus("Instruction sheets generated.");
    } catch (e) {
      console.error(e);
      setStatus(e?.response?.data?.detail || e?.message || "Instruction generation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveAssembled() {
    if (!project || !outline.length) { setStatus("Nothing to save."); return; }
    setBusy(true);
    setStatus("Saving draft...");
    try {
      // Include instructions in the sections data
      const sections = outline.map(o => ({
        id: o.key,
        title: o.title,
        html: drafts[o.key] || "",
        instruction: instructions[o.key] || null  // Add instructions to each section
      }));

      const payload = {
        title: "Proposal Draft (V2)",
        sections,
        // Add metadata to track that this is from V2 with instructions
        metadata: {
          version: "v2",
          hasInstructions: Object.keys(instructions).length > 0,
          outline: outline,
          selectedExampleIds: selectedExampleIds
        }
      };

      await api.post(`/rfps/${project.project_id}/proposal-save`, payload);
      setStatus(`Saved with ${Object.keys(instructions).length} instructions and ${Object.keys(drafts).length} drafts.`);
    } catch (e) {
      console.error("Save error:", e);
      setStatus(e?.response?.data?.detail || e?.message || "Save failed.");
    } finally {
      setBusy(false);
    }
  }

  // Compiled HTML for export functionality
  const compiledHtml = useMemo(() => {
    if (!outline.length) return "";
    const toc = outline.map(o => `<li><a href="#${o.key}">${o.title}</a></li>`).join("");
    const body = outline.map(o => `<h2 id="${o.key}">${o.title}</h2>\n${drafts[o.key] || "<p><em>Section not yet drafted</em></p>"}`).join("\n\n");
    return `<!doctype html><html><head><meta charset="utf-8"/><title>Proposal Draft (V2)</title><style>body{font-family:Arial,sans-serif;line-height:1.6;max-width:800px;margin:0 auto;padding:20px}h1,h2{color:#333}a{color:#0066cc}</style></head><body><h1>Proposal Draft (V2)</h1><div class="toc"><h2>Table of Contents</h2><ul>${toc}</ul></div><hr/>${body}</body></html>`;
  }, [outline, drafts]);

  // Export function for downloading compiled HTML
  const exportHtml = () => {
    if (!compiledHtml) return;
    const blob = new Blob([compiledHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `proposal-draft-${project?.project_id || 'unknown'}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Section management functions
  const addSection = () => {
    if (!newSectionTitle.trim()) return;
    const key = toKey(newSectionTitle);
    const newSection = { title: newSectionTitle.trim(), key };
    setOutline(prev => [...prev, newSection]);
    setNewSectionTitle("");
  };

  const removeSection = (keyToRemove) => {
    setOutline(prev => prev.filter(o => o.key !== keyToRemove));
    // Clean up related data
    setInstructions(prev => {
      const updated = { ...prev };
      delete updated[keyToRemove];
      return updated;
    });
    setDrafts(prev => {
      const updated = { ...prev };
      delete updated[keyToRemove];
      return updated;
    });
  };

  const renameSection = (key, newTitle) => {
    setOutline(prev => prev.map(o => o.key === key ? { ...o, title: newTitle } : o));
    setEditingSection(null);
  };

  const moveSection = (fromIndex, toIndex) => {
    setOutline(prev => {
      const updated = [...prev];
      const [moved] = updated.splice(fromIndex, 1);
      updated.splice(toIndex, 0, moved);
      return updated;
    });
  };

  // Draft editing functions
  const startEditingDraft = (key) => {
    setEditingDraft(key);
    setTempDraftContent(drafts[key] || "");
  };

  const saveDraftEdit = (key) => {
    setDrafts(prev => ({ ...prev, [key]: tempDraftContent }));
    setEditingDraft(null);
    setTempDraftContent("");
  };

  const cancelDraftEdit = () => {
    setEditingDraft(null);
    setTempDraftContent("");
  };

  // Accordion functions
  const toggleSection = (key) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(key)) {
        newSet.delete(key);
      } else {
        newSet.add(key);
      }
      return newSet;
    });
  };

  // Instruction editing functions
  const startEditingInstruction = (sectionKey) => {
    setEditingInstruction(sectionKey);
  };

  const saveInstructionEdit = (sectionKey, updatedInstruction) => {
    setInstructions(prev => ({
      ...prev,
      [sectionKey]: { ...prev[sectionKey], ...updatedInstruction }
    }));
    setEditingInstruction(null);
  };

  const cancelInstructionEdit = () => {
    setEditingInstruction(null);
  };

  // Draft collapse toggle
  const toggleDraftCollapse = (key) => {
    setCollapsedDrafts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(key)) {
        newSet.delete(key);
      } else {
        newSet.add(key);
      }
      return newSet;
    });
  };

  // Auto-save functionality
  const autoSave = async () => {
    if (!project || !outline.length || autoSaving) return;

    setAutoSaving(true);
    try {
      await saveAssembled(); // Save to single file
    } catch (error) {
      console.error("Auto-save failed:", error);
    } finally {
      setAutoSaving(false);
    }
  };

  // Auto-save when drafts change
  useEffect(() => {
    const timer = setTimeout(() => {
      if (Object.keys(drafts).length > 0) {
        autoSave();
      }
    }, 5000); // Auto-save 5 seconds after changes

    return () => clearTimeout(timer);
  }, [drafts]);

  // Navigation function
  const goBackToMain = () => {
    setView('project'); // Use the proper view navigation system
  };

  if (!project) return <div className="card">No project selected.</div>;
  const activeInstr = activeKey ? instructions[activeKey] : null;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
      <div>
        {/* Topic/Guidance Textarea */}
        <div style={{ marginBottom: 12 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>Topic / Guidance (Optional)</label>
          <textarea
            value={topic}
            onChange={(e)=>setTopic(e.target.value)}
            placeholder="Enter topic, guidance, or specific changes you'd like made to sections when re-drafting..."
            style={{
              width: "100%",
              minHeight: 80,
              padding: 8,
              border: "1px solid #ddd",
              borderRadius: 4,
              resize: "vertical",
              fontFamily: "inherit"
            }}
          />
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 12, alignItems: "center" }}>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={useKB} onChange={(e)=>setUseKB(e.target.checked)} />
            Use Knowledge Base
          </label>

          <button
            disabled={busy}
            onClick={generateOutline}
            style={{
              padding: "8px 16px",
              background: "#007bff",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: busy ? "not-allowed" : "pointer"
            }}
          >
            Generate Outline
          </button>

          <button
            disabled={busy || !outline.length}
            onClick={generateInstructionSheets}
            style={{
              padding: "8px 16px",
              background: busy || !outline.length ? "#6c757d" : "#28a745",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: busy || !outline.length ? "not-allowed" : "pointer"
            }}
          >
            Generate Instructions
          </button>

          <button
            disabled={busy || !outline.length}
            onClick={saveAssembled}
            style={{
              padding: "8px 16px",
              background: busy || !outline.length ? "#6c757d" : "#28a745",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: busy || !outline.length ? "not-allowed" : "pointer"
            }}
            title="Save draft"
          >
            Save Draft
          </button>

          <button
            disabled={!outline.length || !Object.keys(drafts).length}
            onClick={exportHtml}
            style={{
              padding: "8px 16px",
              background: !outline.length || !Object.keys(drafts).length ? "#6c757d" : "#17a2b8",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: !outline.length || !Object.keys(drafts).length ? "not-allowed" : "pointer"
            }}
            title="Export as HTML file"
          >
            Export HTML
          </button>

          <button
            onClick={() => setShowExampleManager(true)}
            style={{
              padding: "8px 16px",
              background: "#6f42c1",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: "pointer"
            }}
            title="Manage examples"
          >
            Manage Examples
          </button>

          <button
            onClick={loadLatest}
            disabled={busy}
            style={{
              padding: "8px 16px",
              background: busy ? "#6c757d" : "#20c997",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: busy ? "not-allowed" : "pointer"
            }}
            title="Load latest saved draft"
          >
            Load Latest
          </button>

          <button
            onClick={() => {
              console.log("=== DEBUG STATE ===");
              console.log("Instructions:", instructions);
              console.log("Drafts:", drafts);
              console.log("Outline:", outline);
              console.log("Selected Examples:", selectedExampleIds);
            }}
            style={{
              padding: "8px 16px",
              background: "#6f42c1",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: "pointer"
            }}
            title="Debug current state"
          >
            Debug State
          </button>



          <button
            onClick={goBackToMain}
            style={{
              padding: "8px 16px",
              background: "#dc3545",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: "pointer"
            }}
            title="Go back to main query window"
          >
            ← Back to Main
          </button>

          {autoSaving && (
            <span style={{ color: "#28a745", fontSize: "14px", fontStyle: "italic" }}>
              Auto-saving...
            </span>
          )}
        </div>

        <div style={{ marginBottom: 8, color: "#666" }}>{status}</div>

        {/* Add new section */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16, padding: 12, border: "1px dashed #ccc", borderRadius: 8 }}>
          <input
            value={newSectionTitle}
            onChange={(e) => setNewSectionTitle(e.target.value)}
            placeholder="Add new section title..."
            style={{ flex: 1, padding: 8, border: "1px solid #ddd", borderRadius: 4 }}
            onKeyDown={(e) => e.key === 'Enter' && addSection()}
          />
          <button onClick={addSection} disabled={!newSectionTitle.trim()}>Add Section</button>
        </div>

        {!outline.length && (<div style={{ color: "#666" }}>Start by generating an outline (or add your own sections).</div>)}

        {!!outline.length && (
          <div style={{ display: "grid", gap: 8 }}>
            {outline.map((o, index) => {
              const isExpanded = expandedSections.has(o.key);
              const hasInstructions = !!instructions[o.key];
              const hasDraft = !!drafts[o.key];

              return (
                <div key={o.key} style={{ border: "1px solid #ddd", borderRadius: 8, overflow: "hidden" }}>
                  {/* Section Header */}
                  <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "12px 16px",
                    background: isExpanded ? "#f8f9fa" : "#fff",
                    borderBottom: isExpanded ? "1px solid #e9ecef" : "none"
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1 }}>
                      <button
                        onClick={() => toggleSection(o.key)}
                        style={{
                          background: "none",
                          border: "none",
                          fontSize: "16px",
                          cursor: "pointer",
                          padding: "4px",
                          transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
                          transition: "transform 0.2s"
                        }}
                      >
                        ▶
                      </button>

                      {editingSection === o.key ? (
                        <input
                          defaultValue={o.title}
                          onBlur={(e) => renameSection(o.key, e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') renameSection(o.key, e.target.value);
                            if (e.key === 'Escape') setEditingSection(null);
                          }}
                          autoFocus
                          style={{ fontSize: "16px", fontWeight: "600", border: "1px solid #007acc", padding: "4px 8px", borderRadius: 4 }}
                        />
                      ) : (
                        <h3
                          style={{ margin: 0, cursor: "pointer", fontSize: "16px", fontWeight: "600" }}
                          onClick={() => setEditingSection(o.key)}
                        >
                          {o.title}
                        </h3>
                      )}

                      {/* Status indicators */}
                      <div style={{ display: "flex", gap: 4 }}>
                        <span style={{
                          fontSize: "12px",
                          padding: "2px 6px",
                          borderRadius: 12,
                          background: hasInstructions ? "#d4edda" : "#f8d7da",
                          color: hasInstructions ? "#155724" : "#721c24"
                        }}>
                          {hasInstructions ? "✓ Instructions" : "○ No Instructions"}
                        </span>
                        <span style={{
                          fontSize: "12px",
                          padding: "2px 6px",
                          borderRadius: 12,
                          background: hasDraft ? "#d1ecf1" : "#f8d7da",
                          color: hasDraft ? "#0c5460" : "#721c24"
                        }}>
                          {hasDraft ? "✓ Draft" : "○ No Draft"}
                        </span>
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div style={{ display: "flex", gap: 4 }}>
                      <button
                        onClick={() => moveSection(index, index - 1)}
                        disabled={index === 0}
                        title="Move up"
                        style={{ padding: "4px 6px", fontSize: "12px" }}
                      >
                        ↑
                      </button>
                      <button
                        onClick={() => moveSection(index, index + 1)}
                        disabled={index === outline.length - 1}
                        title="Move down"
                        style={{ padding: "4px 6px", fontSize: "12px" }}
                      >
                        ↓
                      </button>
                      <button
                        onClick={() => removeSection(o.key)}
                        title="Remove section"
                        style={{ padding: "4px 6px", fontSize: "12px", background: "#dc3545", color: "white", border: "1px solid #dc3545" }}
                      >
                        ×
                      </button>
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div style={{ padding: "16px" }}>
                      {/* Action Buttons */}
                      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                        <button
                          onClick={() => {
                            setActiveKey(o.key);
                            if (instructions[o.key]) setShowDraft(true);
                          }}
                          disabled={!instructions[o.key]}
                          title={instructions[o.key] ? "Draft this section" : "Generate instructions first"}
                          style={{
                            padding: "8px 12px",
                            background: instructions[o.key] ? "#007bff" : "#6c757d",
                            color: "white",
                            border: "none",
                            borderRadius: 4
                          }}
                        >
                          {hasDraft ? "Re-draft Section" : "Draft Section"}
                        </button>
                        {hasDraft && (
                          <button
                            onClick={() => startEditingDraft(o.key)}
                            style={{ padding: "8px 12px", background: "#28a745", color: "white", border: "none", borderRadius: 4 }}
                          >
                            Edit Draft
                          </button>
                        )}
                      </div>

                      {/* Instructions Display */}
                      {instructions[o.key] ? (
                        <div style={{ marginBottom: 16 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                            <h4 style={{ margin: 0 }}>Instructions</h4>
                            <button
                              onClick={() => startEditingInstruction(o.key)}
                              style={{ padding: "4px 8px", fontSize: "12px", background: "#ffc107", border: "1px solid #ffc107" }}
                              title="Edit instructions"
                            >
                              Edit
                            </button>
                          </div>
                          <SectionInstructionCard instruction={instructions[o.key]} />
                        </div>
                      ) : (
                        <div style={{ color: "#777", marginBottom: 16, padding: 12, background: "#f8f9fa", borderRadius: 4, textAlign: "left" }}>
                          No instruction yet for this section. Generate instruction sheets first.
                        </div>
                      )}

                      {/* Draft Display/Edit */}
                      {drafts[o.key] && (
                        <div style={{ borderTop: "1px dashed #e5e5e5", paddingTop: 8 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                            <div style={{ fontWeight: 600 }}>Current Draft</div>
                            <div style={{ display: "flex", gap: 8 }}>
                              <button
                                onClick={() => toggleDraftCollapse(o.key)}
                                style={{ padding: "4px 8px", fontSize: "12px", background: "#f8f9fa", border: "1px solid #ddd" }}
                                title={collapsedDrafts.has(o.key) ? "Show draft" : "Hide draft"}
                              >
                                {collapsedDrafts.has(o.key) ? "Show" : "Hide"}
                              </button>
                              <button
                                onClick={() => startEditingDraft(o.key)}
                                style={{ padding: "4px 8px", fontSize: "12px" }}
                                title="Edit this draft"
                              >
                                Edit
                              </button>
                            </div>
                          </div>

                          {!collapsedDrafts.has(o.key) && (
                            <>
                              {editingDraft === o.key ? (
                                <div>
                                  <div style={{ border: "1px solid #ddd", borderRadius: 4, minHeight: 200 }}>
                                    <QuillEditor
                                      value={tempDraftContent}
                                      onChange={setTempDraftContent}
                                    />
                                  </div>
                                  <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                                    <button
                                      onClick={() => saveDraftEdit(o.key)}
                                      style={{ background: "#28a745", color: "white", border: "1px solid #1e7e34", padding: "6px 12px" }}
                                    >
                                      Save
                                    </button>
                                    <button
                                      onClick={cancelDraftEdit}
                                      style={{ background: "#6c757d", color: "white", border: "1px solid #545b62", padding: "6px 12px" }}
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <div
                                  style={{
                                    border: "1px solid #eee",
                                    borderRadius: 6,
                                    padding: 20,
                                    background: "#fafafa",
                                    textAlign: "left",
                                    fontFamily: "Arial, sans-serif",
                                    lineHeight: "1.6",
                                    fontSize: "14px"
                                  }}
                                  className="draft-content"
                                  dangerouslySetInnerHTML={{ __html: drafts[o.key] }}
                                />
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <EnhancedSidebar
        project={project}
        selectedExampleIds={selectedExampleIds}
        onExampleChange={setSelectedExampleIds}
      />

      {showDraft && activeKey && (
        <DraftSectionModal
          open={showDraft}
          onClose={() => setShowDraft(false)}
          projectId={project.project_id}
          sectionKey={activeKey}
          instruction={activeInstr}
          selectedExampleIds={selectedExampleIds}
          useKnowledgeBase={useKB}
          onDraftReady={(key, html) => setDrafts(prev => ({ ...prev, [key]: html }))}
        />
      )}

      {/* Example Manager Modal */}
      {showExampleManager && (
        <ExampleManager onClose={() => setShowExampleManager(false)} />
      )}

      {/* Instruction Editor Modal */}
      {editingInstruction && instructions[editingInstruction] && (
        <InstructionEditor
          instruction={instructions[editingInstruction]}
          onSave={(updatedInstruction) => saveInstructionEdit(editingInstruction, updatedInstruction)}
          onCancel={cancelInstructionEdit}
        />
      )}
    </div>
  );
}
