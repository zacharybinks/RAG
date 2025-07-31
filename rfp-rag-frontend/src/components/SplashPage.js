/*
-------------------------------------------------------------------
File: src/components/SplashPage.js (Updated)
-------------------------------------------------------------------
*/
import React from 'react';
import { useAuth } from '../context/AuthContext';

const SplashPage = () => {
    const { setView } = useAuth();
    return (
        <div className="splash-page">
            <h1 className="splash-title">SOSSEC RFP Assistant</h1>
            <p className="splash-subtitle">
                Upload RFP documents, extract requirements,
                and draft compelling responses with the power of Retrieval-Augmented Generation.
            </p>
            <div className="splash-buttons">
                <button onClick={() => setView('login')} className="splash-button">Login</button>
                <button onClick={() => setView('register')} className="splash-button secondary">Register</button>
            </div>
        </div>
    );
};

export default SplashPage;