// src/components/ExportDocButton.js
import React from 'react';

/**
 * Exports a full HTML string as a .doc file (Word opens it natively).
 * No dependencies, no polyfills.
 *
 * Props:
 *  - html:   full HTML string (include <html><head>... and inline styles)
 *  - filename: "proposal.doc"
 */
export default function ExportDocButton({ html, filename = 'proposal.doc' }) {
  function handleExport() {
    // Prepend BOM to help Word pick up UTF-8
    const blob = new Blob(['\ufeff', html], { type: 'application/msword' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;

    // ensure .doc extension
    a.download = filename.toLowerCase().endsWith('.doc') ? filename : `${filename}.doc`;

    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <button onClick={handleExport} className="pb-btn">
      Export DOC
    </button>
  );
}
