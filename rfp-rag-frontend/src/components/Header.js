// rfp-rag-frontend/src/components/Header.js

import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';

const Header = ({ onKnowledgeBaseClick }) => {
    const { user, logout, setView } = useAuth();
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const dropdownRef = useRef(null);

    const handleLogout = () => {
        logout();
        setDropdownOpen(false);
    };

    const handleDashboardClick = () => {
        setView('dashboard');
    }

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setDropdownOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    return (
        <header className="App-header">
            <div className="header-content">
                <div className="logo-container" onClick={handleDashboardClick} style={{ cursor: 'pointer' }}>
                    <img src="/scaira-small.png" alt="Logo" />
                </div>
                {user && (
                    <div className="user-menu" ref={dropdownRef}>
                        <button onClick={() => setDropdownOpen(!dropdownOpen)} className="user-button">
                            Welcome, {user.username} ▼
                        </button>
                        {dropdownOpen && (
                            <div className="dropdown-menu">
                                <button onClick={onKnowledgeBaseClick}>Knowledge Base</button>
                                <button onClick={handleLogout}>Logout</button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </header>
    );
};

export default Header;