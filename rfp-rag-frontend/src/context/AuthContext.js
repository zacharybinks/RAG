/*
-------------------------------------------------------------------
File: src/context/AuthContext.js (Corrected)
Description: Global state management for authentication.
-------------------------------------------------------------------
*/
import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { jwtDecode } from 'jwt-decode';
import api from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [view, setView] = useState('splash');
  const [selectedProject, setSelectedProject] = useState(null);
  const [sessionExpiredMessage, setSessionExpiredMessage] = useState('');

  const logout = useCallback((message = '') => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setSelectedProject(null);
    if (message && typeof message === 'string') {
      setSessionExpiredMessage(message);
    }
    setView('login');
    delete api.defaults.headers.common['Authorization'];
  }, []);

  useEffect(() => {
    const interceptor = api.interceptors.response.use(
      response => response,
      error => {
        if (error.response && error.response.status === 401) {
          logout('Your session has expired. Please log in again.');
        }
        return Promise.reject(error);
      }
    );

    return () => {
      api.interceptors.response.eject(interceptor);
    };
  }, [logout]);

  useEffect(() => {
    if (token) {
      try {
        const decoded = jwtDecode(token);
        if (decoded.exp * 1000 > Date.now()) {
          setUser({ username: decoded.sub });
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          if (view === 'login' || view === 'register' || view === 'splash') {
            setView('dashboard');
          }
        } else {
          logout('Your session has expired. Please log in again.');
        }
      } catch (error) {
        console.error("Invalid token:", error);
        logout();
      }
    } else {
        setUser(null);
        if (view !== 'login' && view !== 'register') {
            setView('splash');
        }
    }
  }, [token, view, logout]); // **FIX**: Added 'view' back to the dependency array

  const login = (newToken) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setSessionExpiredMessage('');
  };

  const value = { user, token, login, logout, view, setView, selectedProject, setSelectedProject, sessionExpiredMessage };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  return useContext(AuthContext);
};