/*
-------------------------------------------------------------------
File: src/components/InfoSidebar.js (Corrected)
Description: Removed the unused DownloadIcon component to fix the build error.
-------------------------------------------------------------------
*/
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

// The unused DownloadIcon component has been removed from this file.

const InfoSidebar = ({ project }) => {
    const { addNotification } = useNotification();
    const [activeTab, setActiveTab] = useState('documents');
    const [selectedFile, setSelectedFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [systemPrompt, setSystemPrompt] = useState('');
    const [isSavingSettings, setIsSavingSettings] = useState(false);
    const [documents, setDocuments] = useState([]);
    const [error, setError] = useState(null);

    const fetchSidebarData = useCallback(async () => {
        if (!project?.project_id) return;
        try {
            const settingsRes = await api.get(`/rfps/${project.project_id}/settings`);
            setSystemPrompt(settingsRes.data.system_prompt);
            const docsRes = await api.get(`/rfps/${project.project_id}/documents/`);
            setDocuments(docsRes.data);
        } catch (e) {
            setError("Failed to load project data.");
        }
    }, [project]);

    useEffect(() => {
        fetchSidebarData();
    }, [fetchSidebarData]);

    const handleSaveSettings = async () => {
        setIsSavingSettings(true);
        try {
            await api.post(`/rfps/${project.project_id}/settings`, { system_prompt: systemPrompt });
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
        const formData = new FormData();
        formData.append('file', selectedFile);
        try {
            await api.post(`/rfps/${project.project_id}/upload/`, formData);
            addNotification(`File '${selectedFile.name}' uploaded successfully!`);
            setSelectedFile(null);
            await fetchSidebarData();
        } catch (e) {
            addNotification('File upload failed.', 'error');
        } finally {
            setIsUploading(false);
        }
    };

    const handleDownload = (docName) => {
        window.open(`${api.defaults.baseURL}/rfps/${project.project_id}/documents/${docName}`, '_blank');
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
                                {documents.map(doc => (
                                    <li key={doc.name} onClick={() => handleDownload(doc.name)}>
                                        <span className="doc-name">{doc.name}</span>
                                        <div className="doc-actions">
                                            <button onClick={(e) => { e.stopPropagation(); handleDelete(doc.name); }} title="Delete">
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
                            <p>Set the AI's persona for this project.</p>
                            <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} rows="10"/>
                            <button onClick={handleSaveSettings} disabled={isSavingSettings}>{isSavingSettings ? 'Saving...' : 'Save Settings'}</button>
                        </div>
                    )}
                </div>
                 {error && <p className="error-message">{error}</p>}
            </div>
        </aside>
    );
};

export default InfoSidebar;