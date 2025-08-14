import axios from 'axios';

// ---------- Base URL ----------
// Your original behavior:
// - development: http://localhost:8000 (hit backend directly)
// - production:  /api (assumes reverse proxy on the same origin)
let baseURL =
  process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:8000';

// Optional override (useful if prod FE and BE are on different origins)
const envBase =
  process.env.REACT_APP_API_BASE || (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE);
if (envBase) {
  baseURL = String(envBase).replace(/\/+$/, '');
}

const api = axios.create({
  baseURL,
  timeout: 240000,
});

// ---------- Auth helpers ----------
const TOKEN_KEYS = ['token', 'access_token', 'authToken'];

function getToken() {
  if (typeof window === 'undefined') return null;
  for (const k of TOKEN_KEYS) {
    const v = window.localStorage.getItem(k);
    if (v) return v;
  }
  return null;
}

export function setToken(token, key = 'token') {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(key, token);
  }
}

export function clearToken() {
  if (typeof window !== 'undefined') {
    TOKEN_KEYS.forEach((k) => window.localStorage.removeItem(k));
  }
}

// Attach Authorization header automatically if present
api.interceptors.request.use((config) => {
  const t = getToken();
  if (t && !config.headers?.Authorization) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

// ---------- Convenience API surface (PR2 endpoints) ----------
export const Api = {
  // Auth: POST /token  (form data)
  login(username, password) {
    const body = new URLSearchParams({ username, password });
    return api.post('/token', body);
  },

  // Projects & settings
  listProjects() {
    return api.get('/rfps/');
  },
  getSettings(projectId) {
    return api.get(`/rfps/${encodeURIComponent(projectId)}/settings`);
  },

  // Examples
  listExamples() {
    return api.get('/examples');
  },
  exampleSections(exampleId, { limit = 20, offset = 0 } = {}) {
    return api.get(`/examples/${encodeURIComponent(exampleId)}/sections`, {
      params: { limit, offset },
    });
  },
  uploadExamples(files, meta = {}) {
    const fd = new FormData();
    (files || []).forEach((f) => fd.append('files', f));
    Object.entries(meta).forEach(([k, v]) => {
      if (v != null) fd.append(k, v);
    });
    return api.post('/examples/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // Instruction sheets
  generateInstructions(projectId, payload) {
    // payload: { outline: [{title, key?}, ...], use_knowledge_base?: boolean }
    return api.post(
      `/rfps/${encodeURIComponent(projectId)}/sections/instructions`,
      payload
    );
  },

  // Drafting
  draftSection(projectId, sectionKey, payload) {
    // payload: { instruction, example_ids?, filters?, use_knowledge_base? }
    return api.post(
      `/rfps/${encodeURIComponent(projectId)}/sections/${encodeURIComponent(
        sectionKey
      )}/draft`,
      payload
    );
  },
};

export default api;
