/*
-------------------------------------------------------------------
File: src/components/Breadcrumbs.js (Included for completeness)
-------------------------------------------------------------------
*/
import React from 'react';
import { useAuth } from '../context/AuthContext';

const Breadcrumbs = ({ project, onNavigateToDashboard }) => {
  const { view } = useAuth();

  const handleDashboardClick = (e) => {
    e.preventDefault();
    onNavigateToDashboard();
  };

  return (
    <nav className="breadcrumbs">
      {view === 'dashboard' && <span>Dashboard</span>}
      {view === 'project' && (
        <>
          <a href="#dashboard" onClick={handleDashboardClick}>Dashboard</a>
          <span> / </span>
          <span>{project?.name || 'Project'}</span>
        </>
      )}
    </nav>
  );
};

export default Breadcrumbs;
