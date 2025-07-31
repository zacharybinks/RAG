/*
-------------------------------------------------------------------
File: src/components/ProjectSettings.js (New File)
Description: Modal content for updating or deleting a project.
-------------------------------------------------------------------
*/
import React, { useState } from 'react';
import api from '../services/api';
import { useNotification } from '../context/NotificationContext';

const ProjectSettings = ({ project, onClose, onProjectUpdate }) => {
    const [projectName, setProjectName] = useState(project.name);
    const [confirmDelete, setConfirmDelete] = useState('');
    const { addNotification } = useNotification();

    const handleUpdate = async (e) => {
        e.preventDefault();
        try {
            await api.put(`/rfps/${project.project_id}`, { name: projectName });
            addNotification('Project updated successfully!');
            onProjectUpdate(); // This will trigger a refresh in the Dashboard
            onClose();
        } catch (error) {
            addNotification('Failed to update project.', 'error');
        }
    };

    const handleDelete = async () => {
        if (confirmDelete !== 'DELETE') {
            addNotification('Please type DELETE to confirm.', 'error');
            return;
        }
        try {
            await api.delete(`/rfps/${project.project_id}`);
            addNotification('Project deleted successfully!');
            onProjectUpdate();
            onClose();
        } catch (error) {
            addNotification('Failed to delete project.', 'error');
        }
    };

    return (
        <div className="project-settings">
            <form onSubmit={handleUpdate}>
                <label>Project Name</label>
                <input 
                    type="text" 
                    value={projectName} 
                    onChange={(e) => setProjectName(e.target.value)} 
                />
                <button type="submit">Save Changes</button>
            </form>
            <div className="delete-section">
                <h3>Delete Project</h3>
                <p>This action is irreversible. It will delete the project, all associated documents, and chat history.</p>
                <label>Type "DELETE" to confirm.</label>
                <input 
                    type="text" 
                    value={confirmDelete} 
                    onChange={(e) => setConfirmDelete(e.target.value)}
                />
                <button onClick={handleDelete} className="delete-button">Delete Project</button>
            </div>
        </div>
    );
};

export default ProjectSettings;