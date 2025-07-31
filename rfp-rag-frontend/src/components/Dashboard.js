/*
-------------------------------------------------------------------
File: src/components/Dashboard.js (Corrected)
-------------------------------------------------------------------
*/
import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import Modal from './Modal';
import ProjectSettings from './ProjectSettings';
import { useAuth } from '../context/AuthContext';

const Dashboard = ({ onNavigateToProject }) => {
  const [projects, setProjects] = useState([]);
  const [newProjectName, setNewProjectName] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [selectedProjectForSettings, setSelectedProjectForSettings] = useState(null);
  const { user } = useAuth();

  const fetchProjects = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    try {
      const response = await api.get('/rfps/');
      setProjects(response.data);
    } catch (e) {
      setError('Failed to fetch projects.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreateProject = async (e) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      await api.post('/rfps/', { name: newProjectName });
      setNewProjectName('');
      await fetchProjects();
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create project.');
    }
  };

  const openSettingsModal = (project, e) => {
    e.stopPropagation();
    setSelectedProjectForSettings(project);
    setIsSettingsModalOpen(true);
  };

  return (
    <div className="dashboard">
      {isSettingsModalOpen && (
        <Modal onClose={() => setIsSettingsModalOpen(false)} title="Project Settings">
            <ProjectSettings 
                project={selectedProjectForSettings} 
                onClose={() => setIsSettingsModalOpen(false)}
                onProjectUpdate={fetchProjects}
            />
        </Modal>
      )}
      <div className="user-header">
        <span>Welcome, <strong>{user.username}</strong>!</span>
      </div>
      <div className="card">
        <h2>Create New RFP Project</h2>
        <form onSubmit={handleCreateProject} className="create-project-form">
          <input type="text" value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} placeholder="Enter new project name" />
          <button type="submit">Create</button>
        </form>
      </div>
      <div className="card">
        <h2>Existing Projects</h2>
        {isLoading && <p>Loading projects...</p>}
        {error && <p className="error-message">{error}</p>}
        <div className="project-list">
          {projects.map((p) => (
              <div key={p.project_id} className="project-item" onClick={() => onNavigateToProject(p)}>
                <h3>{p.name}</h3>
                <button className="settings-button" onClick={(e) => openSettingsModal(p, e)}>⚙️</button>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;