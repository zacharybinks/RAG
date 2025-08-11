import React, { useState, useCallback, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import InfoSidebar from './InfoSidebar';
import SectionsSidebar from './SectionsSidebar';
import QuillEditor from './QuillEditor';
import ExportDocButton from './ExportDocButton';
import api from '../services/api';
import './ProposalBuilder.css';

const DOC_INLINE_STYLES = `
  body { font-family: Arial, sans-serif; line-height: 1.4; }
  h1, h2, h3 { margin: 0.6em 0 0.3em; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #ddd; padding: 6px; }
  ul, ol { padding-left: 1.2em; }
  .toc ul { list-style: disc; }
`;

const ProposalBuilder = ({ project }) => {
  const { setView } = useAuth();

  const [query, setQuery] = useState('');
  const [useKB, setUseKB] = useState(true);
  const [wordsPerSection, setWordsPerSection] = useState(1500);

  const [sections, setSections] = useState([]); // [{id,title, html}]
  const [activeId, setActiveId] = useState(null);
  const [status, setStatus] = useState('Initializing...');

  const activeSection = sections.find((s) => s.id === activeId) || null;

  const addSection = useCallback((title = 'New Section') => {
    const id = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const next = { id, title, html: '' };
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
      const j = dir === 'up' ? i - 1 : i + 1;
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

  const loadLatest = useCallback(async () => {
    if (!project) return;
    try {
      setStatus('Loading latest draft...');
      const resp = await api.get(`/rfps/${project.project_id}/proposal-load`);
      const data = resp.data;
      const items = (data.sections || []).map((s, idx) => ({
        id: s.id || `${Date.now()}_${idx}`,
        title: s.title || 'Section',
        html: s.html || '',
      }));
      setSections(items);
      setActiveId(items[0]?.id || null);
      setStatus(items.length > 0 ? 'Loaded latest draft.' : 'No draft found. Ready to generate outline.');
    } catch (e) {
      // It's common for a 404 to occur if no draft exists, so we handle it gracefully.
      if (e.response && e.response.status === 404) {
        setStatus('No draft found. Ready to generate outline.');
      } else {
        console.error(e);
        setStatus(e.response?.data?.detail || e.message || String(e));
      }
    }
  }, [project]);

  // --- ADDED THIS HOOK ---
  // This automatically runs `loadLatest` when the component mounts
  // or when the project ID changes.
  useEffect(() => {
    loadLatest();
  }, [loadLatest]);

  async function askOutline() {
    if (!project) return;
    setStatus('Generating outline...');
    try {
      const resp = await api.post(`/rfps/${project.project_id}/proposal-outline`, {
        query: query || 'Draft a comprehensive proposal',
        use_knowledge_base: !!useKB,
      });
      const data = resp.data;
      const next = (data.sections || []).map((t, idx) => ({
        id: `${Date.now()}_${idx}`,
        title: t,
        html: '',
      }));
      setSections(next);
      setActiveId(next[0]?.id || null);
      setStatus('Outline created.');
    } catch (e) {
      console.error(e);
      setStatus(e.response?.data?.detail || e.message || String(e));
    }
  }

  async function generateActiveSection() {
    if (!project || !activeSection) return;
    setStatus(`Generating section: ${activeSection.title}...`);
    try {
      const resp = await api.post(`/rfps/${project.project_id}/proposal-section`, {
        section_title: activeSection.title,
        query: query || 'Draft a comprehensive proposal',
        use_knowledge_base: !!useKB,
        words_per_section: Number(wordsPerSection) || 1500,
      });
      const data = resp.data;
      setActiveHtml(data.content || '');
      setStatus(`Section generated: ${activeSection.title}`);
    } catch (e) {
      console.error(e);
      setStatus(e.response?.data?.detail || e.message || String(e));
    }
  }

  async function saveDraft(versioned = true) {
    if (!project) return;
    try {
      setStatus('Saving draft...');
      const resp = await api.post(`/rfps/${project.project_id}/proposal-save`, {
        title: 'Proposal Draft',
        sections,
        versioned,
      });
      const data = resp.data;
      setStatus(`Saved. ${versioned ? 'Versioned' : 'Latest'} JSON: ${data.json}`);
    } catch (e) {
      console.error(e);
      setStatus(e.response?.data?.detail || e.message || String(e));
    }
  }

  const fullHtml = React.useMemo(() => {
    const toc = sections.map((s) => `<li>${s.title}</li>`).join('');
    const body = sections.map((s) => `<h2>${s.title}</h2>\n${s.html || ''}`).join('\n');
    return `
      <html xmlns:o="urn:schemas-microsoft-com:office:office"
            xmlns:w="urn:schemas-microsoft-com:office:word"
            xmlns="http://www.w3.org/TR/REC-html40">
        <head>
          <meta charset="utf-8" />
          <title>Proposal Draft</title>
          <style>${DOC_INLINE_STYLES}</style>
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

  if (!project) return <div className="card">No project selected.</div>;

  return (
    <div className="pb-grid">
      <div className="pb-left">
        <InfoSidebar project={project} />
      </div>

      <div className="pb-center">
        <div className="pb-toolbar">
          <button onClick={() => setView('project')} className="pb-btn">&larr; Back to Query</button>

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
          <ExportDocButton html={fullHtml} filename={`proposal_${project.project_id}.doc`} />
        </div>

        <div className="pb-status">{status || 'Ready'}</div>

        <div className="pb-editor-wrap">
          {activeSection ? (
            <QuillEditor value={activeSection.html} onChange={setActiveHtml} />
          ) : (
            <div className="pb-placeholder">
              {status.startsWith('Loading') ? 'Loading...' : 'Select a section or generate an outline to start.'}
            </div>
          )}
        </div>
      </div>

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
};

export default ProposalBuilder;