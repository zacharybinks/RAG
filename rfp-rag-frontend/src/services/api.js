/*
-------------------------------------------------------------------
File: src/services/api.js (Create this new file)
Description: Centralized Axios instance for API calls.
-------------------------------------------------------------------
*/
// In src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
});

export default api;