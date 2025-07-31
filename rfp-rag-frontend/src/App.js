/*
-------------------------------------------------------------------
File: src/App.js (Corrected)
Description: Manages modals and the new Header component.
-------------------------------------------------------------------
*/
import React, { useState, useCallback, useEffect } from 'react';
import './App.css';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import Dashboard from './components/Dashboard';
import Workspace from './components/Workspace';
import SplashPage from './components/SplashPage';
import Notification from './components/Notification';
import Header from './components/Header';
import PromptFunctionManager from './components/PromptFunctionManager';
import api from './services/api';

function App() {
  return (
    <AuthProvider>
      <NotificationProvider>
        <MainApp />
      </NotificationProvider>
    </AuthProvider>
  );
}

function MainApp() {
  const { user, view, setView, selectedProject, setSelectedProject } = useAuth();
  const [isPromptModalOpen, setIsPromptModalOpen] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [functions, setFunctions] = useState([]);

  const fetchFunctions = useCallback(async () => {
    if (user) {
      try {
        const response = await api.get('/prompt-functions/');
        setFunctions(response.data);
      } catch (error) {
        console.error("Failed to fetch prompt functions:", error);
      }
    }
  }, [user]);

  useEffect(() => {
    fetchFunctions();
  }, [fetchFunctions]);

  const navigateToProject = (project) => {
    setSelectedProject(project);
    setView('project');
  };

  const navigateToDashboard = () => {
    setSelectedProject(null);
    setView('dashboard');
  };

  const openPromptModal = (prompt = null) => {
    setEditingPrompt(prompt);
    setIsPromptModalOpen(true);
  };

  const closePromptModal = () => {
    setIsPromptModalOpen(false);
    setEditingPrompt(null);
  };

  const renderContent = () => {
    if (!user) {
      switch (view) {
        case 'login': return <LoginPage />;
        case 'register': return <RegisterPage />;
        default: return <SplashPage />;
      }
    }

    switch (view) {
      case 'project':
        return selectedProject ? (
          <Workspace 
            project={selectedProject} 
            onNavigateToDashboard={navigateToDashboard}
            onOpenPromptModal={openPromptModal}
            functions={functions}
            fetchFunctions={fetchFunctions}
          />
        ) : (
          <Dashboard onNavigateToProject={navigateToProject} />
        );
      case 'dashboard':
      default:
        return <Dashboard onNavigateToProject={navigateToProject} />;
    }
  };

  return (
    <div className="App">
       <Notification />
       {isPromptModalOpen && (
        <PromptFunctionManager 
          promptFunction={editingPrompt} 
          onClose={closePromptModal} 
          onFunctionsUpdate={fetchFunctions}
        />
       )}
      <Header />
      <main>
        {renderContent()}
      </main>
    </div>
  );
}

export default App;