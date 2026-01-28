import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL + '/api',
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const login = (username, password) => {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  return api.post('/token', formData);
};

export const register = (username, password) => {
    return api.post('/register', { username, password });
};

export const getMe = () => api.get('/users/me');

export const updateCredentials = (apiKey, apiSecret, numLots) => 
  api.post('/update_credentials', null, { params: { api_key: apiKey, api_secret: apiSecret, num_lots: numLots } });

export const generateToken = (requestToken) => 
  api.post('/generate_token', null, { params: { request_token: requestToken } });

export const toggleTrading = (status) => 
  api.post('/toggle_trading', null, { params: { status } });

export const getTrades = () => api.get('/trades');

export default api;
