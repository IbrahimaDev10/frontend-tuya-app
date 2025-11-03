import axios from 'axios';

// Détection automatique de l'environnement
const isDevelopment = import.meta.env.MODE === 'development';
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (isDevelopment ? 'http://localhost:5000/api' : 'https://sertecingenierie.onrender.com/api');

console.log('🌐 API Base URL:', API_BASE_URL);
console.log('🔧 Mode:', import.meta.env.MODE);

// Configuration axios avec intercepteur pour les tokens
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 secondes
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important pour CORS avec credentials
});

// Intercepteur pour ajouter automatiquement le token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('❌ Erreur de requête:', error);
    return Promise.reject(error);
  }
);

// Intercepteur de réponse pour gérer les erreurs globalement
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Erreur de réponse du serveur
      const { status, data } = error.response;
      
      if (status === 401) {
        console.warn('⚠️ Token expiré ou invalide');
        // Optionnel : rediriger vers login
        // localStorage.removeItem('token');
        // window.location.href = '/login';
      } else if (status === 403) {
        console.warn('⚠️ Accès interdit');
      } else if (status >= 500) {
        console.error('❌ Erreur serveur:', data);
      }
    } else if (error.request) {
      // Pas de réponse du serveur
      console.error('❌ Pas de réponse du serveur:', error.message);
    } else {
      // Erreur de configuration
      console.error('❌ Erreur de configuration:', error.message);
    }
    
    return Promise.reject(error);
  }
);

/**
 * Authentification
 */
export const login = (email, password) =>
  apiClient.post('/auth/login', { email, password });

export const logout = () =>
  apiClient.post('/auth/logout');

export const getProfile = () =>
  apiClient.get('/auth/profile');

export const verifyToken = () =>
  apiClient.get('/auth/verify-token');

/**
 * Mise à jour du profil (utilisateur connecté)
 */
export const updateProfile = (data) =>
  apiClient.put('/auth/profile', data);

/**
 * Changement de mot de passe (utilisateur connecté)
 */
export const changePassword = (old_password, new_password) =>
  apiClient.post('/auth/change-password', {
    old_password,
    new_password
  });

/**
 * Réinitialisation de mot de passe (utilisateur anonyme)
 */
export const forgotPassword = (email) =>
  apiClient.post('/auth/forgot-password', { email });

export const resetPassword = (token_reset, new_password) =>
  apiClient.post('/auth/reset-password', {
    token: token_reset,
    new_password
  });

/**
 * Vérifier un token de réinitialisation (avant soumission)
 */
export const verifyResetToken = (token_reset) =>
  apiClient.post('/auth/verify-reset-token', { token: token_reset });

/**
 * Réinitialisation de mot de passe avec confirmation
 */
export const resetPasswordConfirm = (token_reset, new_password, confirm_password) =>
  apiClient.post('/auth/reset-password-confirm', {
    token: token_reset,
    new_password,
    confirm_password
  });

/**
 * Renouveler le token d'accès
 */
export const refreshToken = (refresh_token) =>
  apiClient.post('/auth/refresh-token', {}, {
    headers: { Authorization: `Bearer ${refresh_token}` }
  });

// Exporter aussi l'URL de base pour Socket.IO
export const API_BASE_URL_WITHOUT_API = API_BASE_URL.replace('/api', '');

// Exporter l'instance axios configurée
export { apiClient };
export default apiClient;