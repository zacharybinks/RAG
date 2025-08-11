/*
-------------------------------------------------------------------
File: src/components/FunctionSidebar.js (Corrected and Updated)
Description: Adds the Proposal Builder button while keeping existing functionality.
-------------------------------------------------------------------
*/
import React, { useState, useMemo, useEffect } from 'react';

// The component now accepts `project` and `onSetView` for the new button
const FunctionSidebar = ({ onExecuteFunction, onOpenPromptModal, functions, fetchFunctions, project, onSetView }) => {
    const [expandedModules, setExpandedModules] = useState({});

    useEffect(() => {
        if (functions.length > 0 && Object.keys(expandedModules).length === 0) {
            setExpandedModules({ [functions[0].module_name]: true });
        }
    }, [functions, expandedModules]);

    const modules = useMemo(() => {
        return functions.reduce((acc, func) => {
            (acc[func.module_name] = acc[func.module_name] || []).push(func);
            return acc;
        }, {});
    }, [functions]);

    const toggleModule = (moduleName) => {
        setExpandedModules(prev => ({ ...prev, [moduleName]: !prev[moduleName] }));
    };

    return (
        <aside className="function-sidebar">
            <h3>Modules</h3>

            {/* --- ADDED BUTTON HERE --- */}
            <div className="proposal-builder-action">
                <button
                    onClick={() => onSetView('proposal')}
                    className="pb-btn-module"
                    disabled={!project}
                    title={!project ? 'Please select a project first' : 'Open Proposal Builder'}
                >
                    Open Proposal Builder
                </button>
            </div>

            {Object.entries(modules).map(([moduleName, funcs]) => (
                <div key={moduleName} className="module-accordion">
                    <button className="module-header" onClick={() => toggleModule(moduleName)}>
                        {moduleName}
                        <span className={`arrow ${expandedModules[moduleName] ? 'expanded' : ''}`}>▼</span>
                    </button>
                    {expandedModules[moduleName] && (
                        <div className="module-content">
                            {funcs.map(func => (
                                <div key={func.id} className="function-button-container">
                                    <button className="function-button" onClick={() => onExecuteFunction({ prompt_function_id: func.id, label: func.button_label })} title={func.description}>
                                        {func.button_label}
                                    </button>
                                    <button className="edit-button" onClick={() => onOpenPromptModal(func)} title="Edit Function">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                                    </button>
                                </div>
                            ))}
                             {moduleName === "Write" && (
                                <button className="function-button create-new" onClick={() => onOpenPromptModal()}>
                                    + Create New Prompt
                                </button>
                            )}
                        </div>
                    )}
                </div>
            ))}
        </aside>
    );
};

export default FunctionSidebar;