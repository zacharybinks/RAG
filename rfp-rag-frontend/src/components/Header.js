/*
-------------------------------------------------------------------
File: src/components/Header.js (Updated)
-------------------------------------------------------------------
*/
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';

const Header = () => {
    const { user, logout } = useAuth();
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const dropdownRef = useRef(null);

    const handleLogout = () => {
        logout();
        setDropdownOpen(false);
    };

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
                <div className="logo-container">
                    <img src="/scaira-small.png" alt="Logo" />
                    
                </div>
                {user && (
                    <div className="user-menu" ref={dropdownRef}>
                        <button onClick={() => setDropdownOpen(!dropdownOpen)} className="user-button">
                            Welcome, {user.username} ▼
                        </button>
                        {dropdownOpen && (
                            <div className="dropdown-menu">
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