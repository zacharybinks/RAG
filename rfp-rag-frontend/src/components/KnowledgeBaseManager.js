// rfp-rag-frontend/src/components/KnowledgeBaseManager.js

import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { useNotification } from '../context/NotificationContext';
import Modal from './Modal';

const KnowledgeBaseManager = ({ onClose }) => {
    const [documents, setDocuments] = useState([]);
    const [selectedFile, setSelectedFile] = useState(null);
    const [description, setDescription] = useState('');
    const [isUploading, setIsUploading] = useState(false);
    const { addNotification } = useNotification();

    const fetchDocuments = useCallback(async () => {
        try {
            const response = await api.get('/knowledge-base/documents/');
            setDocuments(response.data);
        } catch (error) {
            addNotification('Failed to fetch knowledge base documents.', 'error');
        }
    }, [addNotification]);

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    const handleFileChange = (event) => {
        setSelectedFile(event.target.files[0]);
    };

    const handleFileUpload = async () => {
        if (!selectedFile) return;
        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('description', description);

        try {
            await api.post('/knowledge-base/upload/', formData);
            addNotification('Document uploaded to knowledge base successfully.');
            setSelectedFile(null);
            setDescription('');
            fetchDocuments();
        } catch (error) {
            addNotification(error.response?.data?.detail || 'Upload failed.', 'error');
        } finally {
            setIsUploading(false);
        }
    };

    const handleDelete = async (docName) => {
        if (window.confirm(`Are you sure you want to delete ${docName} from the knowledge base?`)) {
            try {
                await api.delete(`/knowledge-base/documents/${docName}`);
                addNotification('Document deleted successfully.');
                fetchDocuments();
            } catch (error) {
                addNotification('Failed to delete document.', 'error');
            }
        }
    };
    
    const handleDownload = (docName) => {
        window.open(`${api.defaults.baseURL}/knowledge-base/documents/${docName}`, '_blank');
    };

    return (
        <Modal onClose={onClose} title="Knowledge Base Management">
            <div className="file-upload-area">
                <input type="file" onChange={handleFileChange} accept=".pdf" />
                <input 
                    type="text" 
                    placeholder="Optional: Description" 
                    value={description} 
                    onChange={(e) => setDescription(e.target.value)} 
                />
                <button onClick={handleFileUpload} disabled={!selectedFile || isUploading}>
                    {isUploading ? 'Uploading...' : 'Upload to Knowledge Base'}
                </button>
            </div>
            <div className="document-list-area">
                <h4>Existing Documents</h4>
                <ul className="document-list">
                    {documents.map(doc => (
                        <li key={doc.document_name} onClick={() => handleDownload(doc.document_name)}>
                            <span className="doc-name">{doc.document_name}</span>
                            <div className="doc-actions">
                                <button onClick={(e) => { e.stopPropagation(); handleDelete(doc.document_name); }} title="Delete">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                                </button>
                            </div>
                        </li>
                    ))}
                </ul>
            </div>
        </Modal>
    );
};

export default KnowledgeBaseManager;