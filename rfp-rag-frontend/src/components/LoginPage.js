/*
-------------------------------------------------------------------
File: src/components/LoginPage.js (Updated with Debugging)
-------------------------------------------------------------------
*/
import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login, setView, sessionExpiredMessage } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    // DEBUG: Log to confirm the handler is firing
    console.log("Login form submitted with username:", username);
    setError('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      // DEBUG: Log the data being sent
      console.log("Sending login request to backend...");
      const response = await api.post('/token', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      
      // DEBUG: Log the successful response
      console.log("Login successful, received token:", response.data.access_token);
      login(response.data.access_token);

    } catch (err) {
      // DEBUG: Log the error from the backend
      console.error("Login failed:", err);
      setError('Invalid username or password.');
    }
  };

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h2>Login</h2>
        {sessionExpiredMessage && <p className="info-message">{sessionExpiredMessage}</p>}
        <form onSubmit={handleSubmit}>
          <input type="text" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <button type="submit">Login</button>
        </form>
        {error && <p className="error-message">{error}</p>}
        <p className="auth-switch">
          Don't have an account? <span onClick={() => setView('register')}>Register</span>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;