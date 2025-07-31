/*
-------------------------------------------------------------------
File: src/components/PromptFunctionManager.js (New File)
Description: Modal for creating and updating prompt functions.
-------------------------------------------------------------------
*/
import React, { useState } from 'react';
import api from '../services/api';
import { useNotification } from '../context/NotificationContext';
import Modal from './Modal';

const PromptFunctionManager = ({ promptFunction, onClose, onFunctionsUpdate }) => {
    const [moduleName, setModuleName] = useState(promptFunction?.module_name || 'Write');
    const [functionName, setFunctionName] = useState(promptFunction?.function_name || '');
    const [buttonLabel, setButtonLabel] = useState(promptFunction?.button_label || '');
    const [description, setDescription] = useState(promptFunction?.description || '');
    const [promptText, setPromptText] = useState(promptFunction?.prompt_text || '');
    const { addNotification } = useNotification();

    const handleSubmit = async (e) => {
        e.preventDefault();
        const payload = { module_name: moduleName, function_name: functionName, button_label: buttonLabel, description, prompt_text: promptText };

        try {
            if (promptFunction) {
                // Update existing
                await api.put(`/prompt-functions/${promptFunction.id}`, payload);
                addNotification('Prompt function updated successfully!');
            } else {
                // Create new
                await api.post('/prompt-functions/', payload);
                addNotification('Prompt function created successfully!');
            }
            if(onFunctionsUpdate) onFunctionsUpdate();
            onClose();
        } catch (error) {
            addNotification(error.response?.data?.detail || 'An error occurred.', 'error');
        }
    };

    return (
        <Modal onClose={onClose} title={promptFunction ? 'Edit Prompt Function' : 'Create Prompt Function'}>
            <form onSubmit={handleSubmit} className="prompt-manager-form">
                <input type="text" placeholder="Module Name (e.g., Write)" value={moduleName} onChange={e => setModuleName(e.target.value)} required />
                <input type="text" placeholder="Function Name (Unique)" value={functionName} onChange={e => setFunctionName(e.target.value)} required />
                <input type="text" placeholder="Button Label" value={buttonLabel} onChange={e => setButtonLabel(e.target.value)} required />
                <input type="text" placeholder="Description (Tooltip)" value={description} onChange={e => setDescription(e.target.value)} />
                <textarea placeholder="Enter the full prompt text here..." value={promptText} onChange={e => setPromptText(e.target.value)} rows="12" required />
                <button type="submit">{promptFunction ? 'Update Function' : 'Create Function'}</button>
            </form>
        </Modal>
    );
};

export default PromptFunctionManager;