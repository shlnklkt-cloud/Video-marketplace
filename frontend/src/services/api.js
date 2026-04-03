import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth API
export const authAPI = {
  login: (credentials) => api.post('/auth/login', credentials),
  register: (userData) => api.post('/auth/register', userData),
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  refresh: () => api.post('/auth/refresh'),
};

// Videos API
export const videosAPI = {
  getAll: (filters) => api.get('/videos', { params: filters }),
  getById: (id) => api.get(`/videos/${id}`),
  create: (data) => api.post('/videos', data),
  update: (id, data) => api.put(`/videos/${id}`, data),
  delete: (id) => api.delete(`/videos/${id}`),
};

// Metadata API
export const metadataAPI = {
  getCategories: () => api.get('/categories'),
  getLinesOfBusiness: () => api.get('/lines-of-business'),
};

// Seed Data API
export const seedAPI = {
  seedData: () => api.post('/seed-data'),
};

export default api;
