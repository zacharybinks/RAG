// src/components/QuillEditor.js
import React, { useEffect, useMemo, useRef } from 'react';
import Quill from 'quill';
import 'quill/dist/quill.snow.css';
import './QuillEditor.css';

/**
 * Quill core integration (no react-quill; compatible with React 19).
 * Props:
 *  - value: HTML string
 *  - onChange: (html) => void
 */
const QuillEditor = ({ value, onChange }) => {
  const containerRef = useRef(null);
  const quillRef = useRef(null);
  const lastExternalValue = useRef(value || '');

  const modules = useMemo(
    () => ({
      toolbar: [
        [{ header: [1, 2, 3, false] }],
        ['bold', 'italic', 'underline', 'strike'],
        [{ list: 'ordered' }, { list: 'bullet' }],
        [{ indent: '-1' }, { indent: '+1' }],
        [{ align: [] }],
        ['link', 'blockquote', 'code-block'],
        ['clean'],
      ],
      clipboard: { matchVisual: false },
    }),
    []
  );

  useEffect(() => {
    if (!containerRef.current) return;

    const editorEl = document.createElement('div');
    containerRef.current.innerHTML = '';
    containerRef.current.appendChild(editorEl);

    const q = new Quill(editorEl, { theme: 'snow', modules });
    quillRef.current = q;

    if (lastExternalValue.current) {
      q.clipboard.dangerouslyPasteHTML(lastExternalValue.current);
    }

    const handler = () => {
      const html = editorEl.querySelector('.ql-editor')?.innerHTML || '';
      if (typeof onChange === 'function') onChange(html);
    };
    q.on('text-change', handler);

    return () => {
      q.off('text-change', handler);
      quillRef.current = null;
    };
  }, [modules, onChange]);

  useEffect(() => {
    const q = quillRef.current;
    if (!q) return;
    const editorEl = q.root;
    const current = editorEl?.innerHTML || '';
    const next = value || '';
    if (next !== current) {
      lastExternalValue.current = next;
      q.setContents([]); // reset
      q.clipboard.dangerouslyPasteHTML(next);
    }
  }, [value]);

  return <div className="qe-wrap" ref={containerRef} />;
};

export default QuillEditor;
