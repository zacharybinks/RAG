import axios from 'axios';

// This function reads the API URL from the global window object,
// which is populated by the config.js file created at runtime.
// It defaults to localhost for local development.
const getApiBaseUrl = () => {
  if (window.config && window.config.API_URL) {
    return window.config.API_URL;
  }
  return 'http://localhost:8000';
};

const api = axios.create({
  baseURL: getApiBaseUrl(),
});

export default api;
