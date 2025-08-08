// src/components/SectionsSidebar.js
import React, { useState } from 'react';
import './SectionsSidebar.css';

const SectionsSidebar = ({
  sections,
  activeId,
  onSelect,
  onAdd,
  onRename,
  onRemove,
  onMove,
}) => {
  const [editingId, setEditingId] = useState(null);
  const [tempTitle, setTempTitle] = useState('');

  function startEdit(s) {
    setEditingId(s.id);
    setTempTitle(s.title);
  }
  function saveEdit(id) {
    onRename(id, tempTitle || 'Untitled');
    setEditingId(null);
    setTempTitle('');
  }

  return (
    <div className="ss-wrap">
      <h3 className="ss-title">Sections</h3>
      <button onClick={() => onAdd()} className="ss-add">+ Add Section</button>
      <div className="ss-list">
        {sections.map((s) => (
          <div
            key={s.id}
            className={`ss-item ${s.id === activeId ? 'active' : ''}`}
          >
            {editingId === s.id ? (
              <>
                <input
                  value={tempTitle}
                  onChange={(e) => setTempTitle(e.target.value)}
                  className="ss-input"
                />
                <div className="ss-row">
                  <button onClick={() => saveEdit(s.id)} className="ss-btn">Save</button>
                  <button onClick={() => setEditingId(null)} className="ss-btn">Cancel</button>
                </div>
              </>
            ) : (
              <>
                <div
                  onClick={() => onSelect(s.id)}
                  className="ss-name"
                  title="Click to edit this section"
                >
                  {s.title}
                </div>
                <div className="ss-row">
                  <button onClick={() => startEdit(s)} title="Rename" className="ss-btn">Rename</button>
                  <button onClick={() => onMove(s.id, 'up')} title="Move up" className="ss-btn">↑</button>
                  <button onClick={() => onMove(s.id, 'down')} title="Move down" className="ss-btn">↓</button>
                  <button onClick={() => onRemove(s.id)} title="Delete" className="ss-btn danger">Delete</button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default SectionsSidebar;
