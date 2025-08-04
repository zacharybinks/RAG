import axios from 'axios';

// Determine the base URL based on the environment.
// In local development (npm start), process.env.NODE_ENV is 'development'.
// In a production build (npm run build), it is 'production'.
const baseURL = process.env.NODE_ENV === 'production'
  ? '/api' // For the live Azure deployment with the Nginx reverse proxy
  : 'http://localhost:8000'; // For local development

const api = axios.create({
  baseURL: baseURL,
});

export default api;
