// rfp-rag-frontend/src/components/Workspace.js

import React, { useState, useCallback, useEffect } from 'react';
import FunctionSidebar from './FunctionSidebar';
import ProjectView from './ProjectView';
import InfoSidebar from './InfoSidebar';
import Breadcrumbs from './Breadcrumbs';
import api from '../services/api';

const Workspace = ({ project, onNavigateToDashboard, onOpenPromptModal, functions, fetchFunctions }) => {
    const [chatHistory, setChatHistory] = useState([]);
    const [isQuerying, setIsQuerying] = useState(false);
    const [useKnowledgeBase, setUseKnowledgeBase] = useState(false);

    const fetchProjectData = useCallback(async () => {
        if (!project) return;
        setChatHistory(project.chat_messages.map(msg => ({
            type: msg.message_type,
            text: msg.text,
            sources: msg.sources || []
        })));
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