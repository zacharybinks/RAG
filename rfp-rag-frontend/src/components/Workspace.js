// rfp-rag-frontend/src/components/Workspace.js

import React, { useState, useCallback, useEffect } from 'react';
import FunctionSidebar from './FunctionSidebar';
import ProjectView from './ProjectView';
import InfoSidebar from './InfoSidebar';
import Breadcrumbs from './Breadcrumbs';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const Workspace = ({ project, onNavigateToDashboard, onOpenPromptModal, functions, fetchFunctions }) => {
    const { setView } = useAuth();
    const [chatHistory, setChatHistory] = useState([]);
    const [isQuerying, setIsQuerying] = useState(false);
    const [useKnowledgeBase, setUseKnowledgeBase] = useState(false);

    const fetchProjectData = useCallback(async () => {
        if (!project) return;
        try {
            const response = await api.get(`/rfps/${project.project_id}/chat-history`);
            const data = response.data || [];
            setChatHistory(data.map((msg) => ({
                type: msg.message_type,
                text: msg.text,
                sources: msg.sources || []
            })));
        } catch (e) {
            // ignore; chat history is optional
        }
    }, [project]);

    useEffect(() => {
        fetchProjectData();
    }, [fetchProjectData]);

    const handleClearChat = () => {
        setChatHistory([]);
    };

    const handleQuerySubmit = async ({ query, prompt_function_id, label }) => {
        const userMessageText = query || `Executing: ${label}`;
        
        setIsQuerying(true);
        
        setChatHistory(prev => [...prev, { type: 'query', text: userMessageText }]);

        try {
            const payload = prompt_function_id ? { prompt_function_id, use_knowledge_base: useKnowledgeBase } : { query, use_knowledge_base: useKnowledgeBase };
            const response = await api.post(`/rfps/${project.project_id}/query/`, payload);
            const data = response.data;
            
            setChatHistory(prev => [...prev, { type: 'answer', text: data.answer, sources: data.sources }]);

        } catch (e) {
            const errorMessage = e.response?.data?.detail || 'An error occurred.';
            setChatHistory(prev => [...prev, { type: 'error', text: errorMessage }]);
        } finally {
            setIsQuerying(false);
        }
    };

    if (!project) {
        return <div>Loading project...</div>;
    }

    return (
        <>
            <Breadcrumbs project={project} onNavigateToDashboard={onNavigateToDashboard} />
            <div style={{ display: 'flex', justifyContent: 'flex-end', margin: '8px 0' }}>
                <button onClick={() => setView('proposal')}>Open Proposal Builder</button>
            </div>
            <div className="workspace-layout">
                <FunctionSidebar 
                    onExecuteFunction={handleQuerySubmit} 
                    onOpenPromptModal={onOpenPromptModal}
                    functions={functions}
                    fetchFunctions={fetchFunctions}
                />
                <ProjectView 
                    chatHistory={chatHistory}
                    isQuerying={isQuerying}
                    onQuerySubmit={(queryText) => handleQuerySubmit({ query: queryText })}
                    useKnowledgeBase={useKnowledgeBase}
                    setUseKnowledgeBase={setUseKnowledgeBase}
                />
                <InfoSidebar 
                    project={project} 
                    key={project.project_id} 
                    onClearChat={handleClearChat} 
                />
            </div>
        </>
    );
};

export default Workspace;
