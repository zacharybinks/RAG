/*
-------------------------------------------------------------------
File: src/components/RegisterPage.js (Complete)
Description: Uses the notification system for success messages and
             properly handles and displays backend validation errors.
-------------------------------------------------------------------
*/
import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import api from '../services/api';

const RegisterPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { setView } = useAuth();
  const { addNotification } = useNotification();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.post('/users/', { username, password });
      addNotification('Registration successful! Please log in.');
      setView('login');
    } catch (err) {
      // --- FIX: Intelligently parse FastAPI validation errors ---
      if (err.response && err.response.data && err.response.data.detail) {
        // Handle custom HTTPException details (like domain restriction)
        if (typeof err.response.data.detail === 'string') {
          setError(err.response.data.detail);
        }
        // Handle Pydantic validation errors (like invalid email format)
        else if (Array.isArray(err.response.data.detail)) {
          // Display the first validation error message
          setError(err.response.data.detail[0].msg || 'Invalid input.');
        } else {
          setError('An unexpected error occurred during registration.');
        }
      } else {
        setError('Registration failed. Please try again.');
      }
    }
  };

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h2>Register</h2>
        <p>Registration is restricted.</p>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Company Email"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit">Register</button>
        </form>
        {error && <p className="error-message">{error}</p>}
        <p className="auth-switch">
          Already have an account? <span onClick={() => setView('login')}>Login</span>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;