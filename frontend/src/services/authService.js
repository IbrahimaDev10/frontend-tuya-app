import axios from 'axios';

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

// Configuration axios avec intercepteur pour les tokens
const apiClient = axios.create({
  baseURL: API,
});

// Intercepteur pour ajouter automatiquement le token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Authentification
 */
export const login = (email, password) =>
  axios.post(`${API}/auth/login`, { email, password });

export const logout = (token) =>
  axios.post(`${API}/auth/logout`, {}, {
    headers: { Authorization: `Bearer ${token}` }
  });

export const getProfile = (token) =>
  axios.get(`${API}/auth/profile`, {
    headers: { Authorization: `Bearer ${token}` }
  });

export const verifyToken = (token) =>
  axios.get(`${API}/auth/verify-token`, {
    headers: { Authorization: `Bearer ${token}` }
  });

/**
 * Mise à jour du profil (utilisateur connecté)
 */
export const updateProfile = (data, token) =>
  axios.put(`${API}/auth/profile`, data, {
    headers: { Authorization: `Bearer ${token}` }
  });

/**
 * Changement de mot de passe (utilisateur connecté)
 */
export const changePassword = (old_password, new_password, token) =>
  axios.post(`${API}/auth/change-password`, {
    old_password,
    new_password
  }, {
    headers: { Authorization: `Bearer ${token}` }
  });

/**
 * Réinitialisation de mot de passe (utilisateur anonyme)
 */
export const forgotPassword = (email) =>
  axios.post(`${API}/auth/forgot-password`, { email });

export const resetPassword = (token_reset, new_password) =>
  axios.post(`${API}/auth/reset-password`, {
    token: token_reset,
    new_password
  });

// ============== ✅ NOUVELLES FONCTIONS AJOUTÉES ==============

/**
 * Vérifier un token de réinitialisation (avant soumission)
 */
export const verifyResetToken = (token_reset) =>
  axios.post(`${API}/auth/verify-reset-token`, { token: token_reset });

/**
 * Réinitialisation de mot de passe avec confirmation
 */
export const resetPasswordConfirm = (token_reset, new_password, confirm_password) =>
  axios.post(`${API}/auth/reset-password-confirm`, {
    token: token_reset,
    new_password,
    confirm_password
  });

/**
 * Renouveler le token d'accès
 */
export const refreshToken = (refresh_token) =>
  axios.post(`${API}/auth/refresh-token`, {}, {
    headers: { Authorization: `Bearer ${refresh_token}` }
  });


// Exporter l'instance axios configurée pour d'autres services
export { apiClient };