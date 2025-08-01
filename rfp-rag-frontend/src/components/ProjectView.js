/*
-------------------------------------------------------------------
File: src/components/ProjectView.js (Corrected)
Description: This is the refactored version that only handles chat.
-------------------------------------------------------------------
*/
import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

const ProjectView = ({ chatHistory, isQuerying, onQuerySubmit }) => {
    const [query, setQuery] = useState('');
    const [expandedSources, setExpandedSources] = useState({});
    const chatEndRef = useRef(null);

    const toggleSources = (index) => {
        setExpandedSources(prev => ({
            ...prev,
            [index]: !prev[index]
        }));
    };

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [chatHistory]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!query.trim() || isQuerying) return;
        onQuerySubmit(query);
        setQuery('');
    };

    return (
        <div className="chat-container">
            <div className="chat-history">
                {chatHistory.length === 0 && <div className="chat-message empty">Upload documents, then use a function from the left sidebar or ask a question below to begin.</div>}
                {chatHistory.map((item, index) => (
                    <div key={index} className={`chat-message ${item.type}`}>
                       <div className="message-content">
                            <strong>{item.type === 'query' ? 'You' : 'Assistant'}:</strong>
                            {item.type === 'answer' ? <ReactMarkdown>{item.text}</ReactMarkdown> : <p>{item.text}</p>}
                       </div>
                       {item.type === 'answer' && item.sources && item.sources.length > 0 && (
                           <div className="sources">
                               <button 
                                   className="sources-toggle"
                                   onClick={() => toggleSources(index)}
                               >
                                   <strong>Sources ({item.sources.length})</strong>
                                   <span className={`arrow ${expandedSources[index] ? 'expanded' : ''}`}>▼</span>
                               </button>
                               {expandedSources[index] && (
                                   <div className="sources-list">
                                       {item.sources.map((source, idx) => (
                                           <div key={idx} className="source-item">{source}</div>
                                       ))}
                                   </div>
                               )}
                           </div>
                       )}
                    </div>
                ))}
                {isQuerying && <div className="chat-message answer typing">Thinking...</div>}
                <div ref={chatEndRef} />
            </div>
            <form onSubmit={handleSubmit} className="prompt-form">
                <textarea 
                    value={query} 
                    onChange={(e) => setQuery(e.target.value)} 
                    placeholder="Ask a follow-up question..." 
                    rows="3"
                    disabled={isQuerying}
                />
                <button type="submit" disabled={isQuerying || !query.trim()}>Send</button>
            </form>
        </div>
    );
};

export default ProjectView;
