import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { useNotification } from '../context/NotificationContext';

const TrashIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"></polyline>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
    <line x1="10" y1="11" x2="10" y2="17"></line>
    <line x1="14" y1="11" x2="14" y2="17"></line>
  </svg>
);

export default function EnhancedSidebar({ project, selectedExampleIds = [], onExampleChange, onClearChat }) {
  const { addNotification } = useNotification();
  const [activeTab, setActiveTab] = useState('examples');
  
  // Examples state
  const [examples, setExamples] = useState([]);
  const [loadingExamples, setLoadingExamples] = useState(false);
  
  // Documents state
  const [documents, setDocuments] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  
  // Settings state
  const [systemPrompt, setSystemPrompt] = useState('');
  const [modelName, setModelName] = useState('gpt-3.5-turbo');
  const [temperature, setTemperature] = useState(0.7);
  const [contextSize, setContextSize] = useState('medium');
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  
  const [error, setError] = useState(null);

  // Load examples
  const loadExamples = useCallback(async () => {
    setLoadingExamples(true);
    try {
      const { data } = await api.get("/examples");
      // Handle both possible response formats for compatibility
      const examplesList = data.examples || data || [];
      setExamples(examplesList);
      console.log("Loaded examples:", examplesList); // Debug log
    } catch (err) {
      console.error("Failed to load examples:", err);
      setExamples([]);
    } finally {
      setLoadingExamples(false);
    }
  }, []);

  // Load project data (documents and settings)
  const fetchProjectData = useCallback(async () => {
    if (!project?.project_id) return;
    try {
      const settingsRes = await api.get(`/rfps/${project.project_id}/settings`);
      setSystemPrompt(settingsRes.data.system_prompt);
      setModelName(settingsRes.data.model_name);
      setTemperature(settingsRes.data.temperature);
      setContextSize(settingsRes.data.context_size);
      
      const docsRes = await api.get(`/rfps/${project.project_id}/documents/`);
      setDocuments(docsRes.data);
    } catch (e) {
      setError("Failed to load project data.");
    }
  }, [project]);

  useEffect(() => {
    loadExamples();
    fetchProjectData();
  }, [loadExamples, fetchProjectData]);

  // Example selection toggle
  const toggleExample = (id) => {
    if (!onExampleChange) return;
    const set = new Set(selectedExampleIds);
    set.has(id) ? set.delete(id) : set.add(id);
    onExampleChange(Array.from(set));
  };

  // Document handlers
  const handleFileChange = (event) => setSelectedFile(event.target.files[0]);

  const handleFileUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      await api.post(`/rfps/${project.project_id}/upload/`, formData);
      addNotification(`'${selectedFile.name}' uploaded successfully. Processing...`);
      setSelectedFile(null);
      await fetchProjectData();
    } catch (e) {
      addNotification(e.response?.data?.detail || 'File upload failed.', 'error');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownload = async (docName) => {
    try {
      const response = await api.get(`/rfps/${project.project_id}/documents/${docName}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', docName);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (error) {
      addNotification('Failed to download document.', 'error');
    }
  };

  const handleDelete = async (docName) => {
    if (window.confirm(`Are you sure you want to delete ${docName}? This cannot be undone.`)) {
      try {
        await api.delete(`/rfps/${project.project_id}/documents/${docName}`);
        addNotification('Document deleted successfully!');
        await fetchProjectData();
      } catch (e) {
        addNotification('Failed to delete document.', 'error');
      }
    }
  };

  // Settings handlers
  const handleSaveSettings = async () => {
    setIsSavingSettings(true);
    try {
      await api.post(`/rfps/${project.project_id}/settings`, { 
        system_prompt: systemPrompt,
        model_name: modelName,
        temperature: temperature,
        context_size: contextSize
      });
      addNotification('Settings saved successfully!');
    } catch (e) {
      addNotification('Failed to save settings.', 'error');
    } finally {
      setIsSavingSettings(false);
    }
  };

  const handleClearChatHistory = async () => {
    if (window.confirm('Are you sure you want to delete the entire chat history for this project? This cannot be undone.')) {
      try {
        await api.delete(`/rfps/${project.project_id}/chat-history`);
        addNotification('Chat history cleared successfully!');
        if (onClearChat) onClearChat();
      } catch (error) {
        addNotification('Failed to clear chat history.', 'error');
      }
    }
  };

  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16, height: "fit-content" }}>
      <h3 style={{ marginTop: 0 }}>{project?.name || "Project"}</h3>
      
      {/* Tab Navigation */}
      <div style={{ display: "flex", marginBottom: 16, borderBottom: "1px solid #eee" }}>
        {['examples', 'documents', 'settings'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: "8px 16px",
              border: "none",
              background: activeTab === tab ? "#007bff" : "transparent",
              color: activeTab === tab ? "white" : "#666",
              borderRadius: "4px 4px 0 0",
              cursor: "pointer",
              textTransform: "capitalize"
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={{ minHeight: 200 }}>
        {activeTab === 'examples' && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <h4 style={{ margin: 0 }}>Select Examples</h4>
              <button
                onClick={loadExamples}
                disabled={loadingExamples}
                style={{
                  padding: "4px 8px",
                  fontSize: "12px",
                  background: loadingExamples ? "#6c757d" : "#007bff",
                  color: "white",
                  border: "none",
                  borderRadius: 4,
                  cursor: loadingExamples ? "not-allowed" : "pointer"
                }}
              >
                {loadingExamples ? "Loading..." : "Refresh"}
              </button>
            </div>
            <p style={{ fontSize: "14px", color: "#666", marginBottom: 16 }}>
              Choose examples to guide tone/structure. The model will emulate patterns—not copy.
            </p>
            
            {loadingExamples ? (
              <div>Loading examples...</div>
            ) : examples.length === 0 ? (
              <div style={{ color: "#666", textAlign: "center", padding: 20 }}>
                No examples uploaded yet.
              </div>
            ) : (
              <div style={{ display: "grid", gap: 8 }}>
                {examples.map((ex) => {
                  const id = ex.id || ex.ID || ex.uuid;
                  const checked = selectedExampleIds.includes(id);
                  return (
                    <label 
                      key={id} 
                      style={{
                        border: "1px solid #e1e1e1", 
                        borderRadius: 8, 
                        padding: 10, 
                        display: "flex", 
                        alignItems: "center", 
                        gap: 8,
                        cursor: "pointer"
                      }}
                    >
                      <input 
                        type="checkbox" 
                        checked={checked} 
                        onChange={() => toggleExample(id)} 
                      />
                      <div>
                        <div style={{ fontWeight: 600 }}>{ex.title || "Untitled example"}</div>
                        <div style={{ color: "#666", fontSize: 12 }}>
                          {ex.client_type || "—"} · {ex.domain || "—"} · {ex.contract_vehicle || "—"}
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === 'documents' && (
          <div>
            <h4 style={{ marginTop: 0 }}>Project Documents</h4>
            
            {/* File Upload */}
            <div style={{ marginBottom: 16, padding: 12, border: "1px dashed #ddd", borderRadius: 4 }}>
              <input 
                type="file" 
                onChange={handleFileChange} 
                accept=".pdf" 
                style={{ marginBottom: 8 }}
              />
              <button 
                onClick={handleFileUpload} 
                disabled={!selectedFile || isUploading}
                style={{
                  padding: "6px 12px",
                  background: !selectedFile || isUploading ? "#6c757d" : "#007bff",
                  color: "white",
                  border: "none",
                  borderRadius: 4,
                  cursor: !selectedFile || isUploading ? "not-allowed" : "pointer"
                }}
              >
                {isUploading ? 'Uploading...' : 'Upload File'}
              </button>
            </div>

            {/* Document List */}
            <div style={{ maxHeight: 300, overflowY: "auto" }}>
              {documents
                .filter(doc => !doc.name.endsWith('.md'))
                .map(doc => (
                  <div 
                    key={doc.name}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "8px 0",
                      borderBottom: "1px solid #eee"
                    }}
                  >
                    <span
                      onClick={() => handleDownload(doc.name)}
                      style={{ cursor: 'pointer', flex: 1, color: "#007bff" }}
                      title="Click to download"
                    >
                      {doc.name}
                    </span>
                    <button
                      onClick={() => handleDelete(doc.name)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#dc3545",
                        cursor: "pointer",
                        padding: 4
                      }}
                      title="Delete"
                    >
                      <TrashIcon />
                    </button>
                  </div>
                ))}
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div>
            <h4 style={{ marginTop: 0 }}>Project Settings</h4>
            
            <div style={{ display: "grid", gap: 12 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>System Prompt</label>
                <textarea 
                  value={systemPrompt} 
                  onChange={(e) => setSystemPrompt(e.target.value)} 
                  rows="6"
                  style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 4 }}
                />
              </div>
              
              <div>
                <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>OpenAI Model</label>
                <select 
                  value={modelName} 
                  onChange={(e) => setModelName(e.target.value)}
                  style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 4 }}
                >
                  <option value="gpt-4o-mini">Fast (cheap) — gpt-4o-mini</option>
                  <option value="gpt-4o">Balanced — gpt-4o</option>
                  <option value="gpt-4.1">Verbose — gpt-4.1</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>
                  Creativity: {temperature}
                </label>
                <input 
                  type="range" 
                  min="0" 
                  max="2" 
                  step="0.1" 
                  value={temperature} 
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  style={{ width: "100%" }}
                />
              </div>

              <div>
                <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>Context Size</label>
                <select 
                  value={contextSize} 
                  onChange={(e) => setContextSize(e.target.value)}
                  style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 4 }}
                >
                  <option value="low">Low (10 docs)</option>
                  <option value="medium">Medium (15 docs)</option>
                  <option value="high">High (20 docs)</option>
                </select>
              </div>

              <button 
                onClick={handleSaveSettings} 
                disabled={isSavingSettings}
                style={{
                  padding: "10px 16px",
                  background: isSavingSettings ? "#6c757d" : "#28a745",
                  color: "white",
                  border: "none",
                  borderRadius: 4,
                  cursor: isSavingSettings ? "not-allowed" : "pointer"
                }}
              >
                {isSavingSettings ? 'Saving...' : 'Save Settings'}
              </button>

              <div style={{ borderTop: "1px solid #eee", paddingTop: 12, marginTop: 12 }}>
                <button 
                  onClick={handleClearChatHistory}
                  style={{
                    padding: "8px 16px",
                    background: "#dc3545",
                    color: "white",
                    border: "none",
                    borderRadius: 4,
                    cursor: "pointer"
                  }}
                >
                  Clear Chat History
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div style={{ 
          color: "#dc3545", 
          background: "#f8d7da", 
          padding: 8, 
          borderRadius: 4, 
          marginTop: 12,
          fontSize: "14px"
        }}>
          {error}
        </div>
      )}
    </div>
  );
}
