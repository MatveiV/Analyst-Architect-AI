import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: API_URL, headers: { 'Content-Type': 'application/json' } });

// Attach JWT token (if present) to every request made through this instance.
api.interceptors.request.use((config) => {
  try {
    const raw = localStorage.getItem('ag_auth');
    if (raw) {
      const { access_token } = JSON.parse(raw);
      if (access_token) {
        config.headers = config.headers || {};
        config.headers['Authorization'] = `Bearer ${access_token}`;
      }
    }
  } catch {}
  return config;
});

// On 401 (expired/invalid token), clear session so the user is returned to Login.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem('ag_auth');
      // Full reload lets AuthContext re-initialize into the logged-out state.
      if (!window.location.pathname.startsWith('/login')) {
        window.location.reload();
      }
    }
    return Promise.reject(error);
  }
);

// ── Documents ────────────────────────────────────────────────────────────────
export const createDocument = (data: any) => api.post('/documents', data);
export const listDocuments = (doc_type?: string) =>
  api.get('/documents', { params: doc_type ? { doc_type } : {} });
export const getDocument = (id: string) => api.get(`/documents/${id}`);
export const reviewDocument = (id: string, reasoning_mode = 'direct') =>
  api.post(`/documents/${id}/review?reasoning_mode=${reasoning_mode}`);
export const generateURS = (id: string, project_name?: string) =>
  api.post(`/documents/${id}/generate-urs?project_name=${project_name || ''}`);
export const generateSRS = (id: string, project_name?: string) =>
  api.post(`/documents/${id}/generate-srs?project_name=${project_name || ''}`);
export const generateADR = (id: string, project_name?: string) =>
  api.post(`/documents/${id}/generate-adr?project_name=${project_name || ''}`);
export const recommendArchitecture = (id: string, project_name?: string) =>
  api.post(`/documents/${id}/recommend-architecture?project_name=${project_name || ''}`);
export const designAPI = (id: string, project_name?: string) =>
  api.post(`/documents/${id}/design-api?project_name=${project_name || ''}`);
export const generateDiagrams = (id: string, project_name?: string) =>
  api.post(`/documents/${id}/generate-diagrams?project_name=${project_name || ''}`);
export const exportDocx = (id: string) =>
  api.get(`/documents/${id}/export/docx`, { responseType: 'blob' });
export const exportMarkdown = (id: string) =>
  api.get(`/documents/${id}/export/markdown`, { responseType: 'blob' });
export const uploadMarkdown = (file: File, projectName?: string) => {
  const fd = new FormData();
  fd.append('file', file);
  if (projectName) fd.append('project_name', projectName);
  return api.post('/documents/upload-markdown', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// ── Reviews ──────────────────────────────────────────────────────────────────
export const listReviews = (needs_review?: boolean) =>
  api.get('/reviews', { params: needs_review !== undefined ? { needs_review } : {} });
export const getReview = (id: string) => api.get(`/reviews/${id}`);
export const directReview = (text: string) => api.post('/ai/review', { text });
export const exportReviewJson = (id: string) => api.get(`/reviews/${id}/export/json`, { responseType: 'blob' });
export const exportReviewCsv = (id: string) => api.get(`/reviews/${id}/export/csv`, { responseType: 'blob' });

// ── Knowledge Base ───────────────────────────────────────────────────────────
export const addKBDocument = (data: any) => api.post('/kb/documents', data);
export const listKBDocuments = () => api.get('/kb/documents');
export const askKB = (question: string) => api.post('/kb/ask', { question });
export const getQAHistory = (needs_review?: boolean) =>
  api.get('/kb/history', { params: needs_review !== undefined ? { needs_review } : {} });
export const reindexKB = () => api.post('/kb/reindex');

// ── Memory ───────────────────────────────────────────────────────────────────
export const storeMemory = (data: any) => api.post('/memory/store', data);
export const searchMemory = (data: any) => api.post('/memory/search', data);
export const getRecentMemory = (memory_type?: string) =>
  api.get('/memory/recent', { params: memory_type ? { memory_type } : {} });
export const consolidateMemory = () => api.post('/memory/consolidate');

// ── Diagrams ─────────────────────────────────────────────────────────────────
export const getDocumentDiagrams = (doc_id: string) => api.get(`/diagrams/document/${doc_id}`);
export const generateC4 = (doc_id: string) => api.post(`/diagrams/generate-c4?doc_id=${doc_id}`);
export const generateUML = (doc_id: string) => api.post(`/diagrams/generate-uml?doc_id=${doc_id}`);
export const generateERD = (doc_id: string) => api.post(`/diagrams/generate-erd?doc_id=${doc_id}`);

// ── Architecture ─────────────────────────────────────────────────────────────
export const getArchReviews = (doc_id: string) =>
  api.get('/documents', { params: { doc_type: doc_id } }); // placeholder

// ── Audit ─────────────────────────────────────────────────────────────────────
export const getAuditRuns = (params?: { action?: string; status?: string; limit?: number; offset?: number }) =>
  api.get('/audit', { params });
export const getAuditStats = () => api.get('/audit/stats');

export default api;

// ── Settings ─────────────────────────────────────────────────────────────────
export const listProviders = () => api.get('/settings/providers');
export const saveProvider = (data: any) => api.post('/settings/providers', data);
export const activateProvider = (provider: string) =>
  api.post(`/settings/providers/activate?provider=${provider}`);
export const getActiveProvider = () => api.get('/settings/active');
export const testProvider = (provider: string) =>
  api.post(`/settings/test?provider=${provider}`);

// ── Economics module (Build Projects, Task Estimates, ROI) ───────────────────
export const createBuildProject = (data: { document_id: string; name: string; description?: string }) =>
  api.post('/build-projects', data);
export const listBuildProjects = () => api.get('/build-projects');
export const getBuildProject = (id: string) => api.get(`/build-projects/${id}`);
export const estimateProjectTasks = (id: string) => api.post(`/build-projects/${id}/estimate-tasks`);
export const createEconomicEstimate = (id: string, data: any) =>
  api.post(`/build-projects/${id}/economic-estimate`, data);
export const addEconomicActual = (id: string, data: any) =>
  api.post(`/build-projects/${id}/actuals`, data);
export const getProjectReport = (id: string) => api.get(`/build-projects/${id}/report`);
export const exportBusinessCase = (id: string) =>
  api.get(`/build-projects/${id}/export/docx`, { responseType: 'blob' });
export const exportBusinessCasePdf = (id: string) =>
  api.get(`/build-projects/${id}/export/pdf`, { responseType: 'blob' });

// ── Dashboard ──────────────────────────────────────────────────────────────────
export const getDashboardStats = () => api.get('/dashboard/stats');
export const getRecentActivity = (limit?: number) =>
  api.get('/dashboard/recent-activity', { params: limit ? { limit } : {} });

// ── Seed / demo data (admin only) ─────────────────────────────────────────────
export const seedDocuments = () => api.post('/seed/documents');
export const seedKbDocuments = () => api.post('/seed/kb-documents');
export const seedAll = () => api.post('/seed/all');
export const seedExamples = () => api.post('/seed/examples');
