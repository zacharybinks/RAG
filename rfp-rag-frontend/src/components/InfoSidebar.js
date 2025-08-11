// rfp-rag-frontend/src/components/InfoSidebar.js

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

const InfoSidebar = ({ project, onClearChat }) => {
    const { addNotification } = useNotification();
    const [activeTab, setActiveTab] = useState('documents');
    const [selectedFile, setSelectedFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [systemPrompt, setSystemPrompt] = useState('');
    const [modelName, setModelName] = useState('gpt-3.5-turbo');
    const [temperature, setTemperature] = useState(0.7);
    const [contextSize, setContextSize] = useState('medium');
    const [isSavingSettings, setIsSavingSettings] = useState(false);
    const [documents, setDocuments] = useState([]);
    const [error, setError] = useState(null);

    const fetchSidebarData = useCallback(async () => {
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
        fetchSidebarData();
    }, [fetchSidebarData]);

    const handleClearChatHistory = async () => {
        if (window.confirm('Are you sure you want to delete the entire chat history for this project? This cannot be undone.')) {
            try {
                await api.delete(`/rfps/${project.project_id}/chat-history`);
                addNotification('Chat history cleared successfully!');
                onClearChat();
            } catch (error) {
                addNotification('Failed to clear chat history.', 'error');
            }
        }
    };

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
            await fetchSidebarData();
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
                await fetchSidebarData();
            } catch (e) {
                addNotification('Failed to delete document.', 'error');
            }
        }
    };

    return (
        <aside className="info-sidebar">
            <div className="card">
                <h3>{project.name}</h3>
                <div className="sidebar-tabs">
                    <button onClick={() => setActiveTab('documents')} className={activeTab === 'documents' ? 'active' : ''}>Documents</button>
                    <button onClick={() => setActiveTab('settings')} className={activeTab === 'settings' ? 'active' : ''}>Settings</button>
                </div>
                <div className="sidebar-content">
                    {activeTab === 'documents' && (
                        <div className="document-list-area">
                            <div className="file-upload-area">
                                <input type="file" onChange={handleFileChange} accept=".pdf" />
                                <button onClick={handleFileUpload} disabled={!selectedFile || isUploading}>{isUploading ? 'Uploading...' : 'Upload File'}</button>
                            </div>
                            <ul className="document-list">
                                {documents
                                    .filter(doc => !doc.name.endsWith('.md'))
                                    .map(doc => (
                                        <li key={doc.name}>
                                        <span
                                            className="doc-name"
                                            onClick={() => handleDownload(doc.name)}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            {doc.name}
                                        </span>
                                        <div className="doc-actions">
                                            <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleDelete(doc.name);
                                            }}
                                            title="Delete"
                                            >
                                            <TrashIcon />
                                            </button>
                                        </div>
                                        </li>
                                    ))}
                            </ul>
                        </div>
                    )}
                    {activeTab === 'settings' && (
                        <div className="settings-area">
                            <label htmlFor="system-prompt">System Prompt</label>
                            <textarea id="system-prompt" value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} rows="10"/>
                            
                            <label htmlFor="model-name">OpenAI Model</label>
                            <select id="model-name"value={modelName}onChange={(e) => setModelName(e.target.value)}>
                                <option value="gpt-4o-mini">Fast (cheap) — gpt-4o-mini</option>
                                <option value="gpt-4o">Balanced — gpt-4o</option>
                                <option value="gpt-4.1">Verbose — gpt-4.1</option>
                            </select>

                            <label htmlFor="temperature">Creativity: {temperature}</label>
                            <input id="temperature" type="range" min="0" max="2" step="0.1" value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} />

                            <label htmlFor="context-size">Context Size</label>
                            <select id="context-size" value={contextSize} onChange={(e) => setContextSize(e.target.value)}>
                                <option value="low">Low (10 docs)</option>
                                <option value="medium">Medium (15 docs)</option>
                                <option value="high">High (20 docs)</option>
                            </select>

                            <button onClick={handleSaveSettings} disabled={isSavingSettings}>{isSavingSettings ? 'Saving...' : 'Save Settings'}</button>

                            <div className="danger-zone">
                                <button className="danger" onClick={handleClearChatHistory}>Clear Chat History</button>
                            </div>
                        </div>
                    )}
                </div>
                 {error && <p className="error-message">{error}</p>}
            </div>
        </aside>
    );
};

export default InfoSidebar;