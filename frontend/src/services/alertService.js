import { apiClient } from './authService';

class AlertService {
  // =================== CONSULTATION DES ALERTES ===================
  
  async obtenirAlertesAppareil(deviceId, hoursBack = 24, limit = 50) {
    return apiClient.get(`/alerts/device/${deviceId}`, {
      params: { hours_back: hoursBack, limit }
    });
  }

  async obtenirStatistiquesAlertes(deviceId, days = 7) {
    return apiClient.get(`/alerts/device/${deviceId}/stats`, {
      params: { days }
    });
  }

  async obtenirAlertesActives(deviceId) {
    return apiClient.get(`/alerts/device/${deviceId}/active`);
  }

  async obtenirAlertesCritiques(hoursBack = 24) {
    return apiClient.get('/alerts/critical', {
      params: { hours_back: hoursBack }
    });
  }

  // =================== GESTION DES ALERTES ===================
  
  async resoudreAlerte(alertId, commentaire = '') {
    return apiClient.post(`/alerts/${alertId}/resolve`, {
      commentaire
    });
  }

  async marquerAlerteVue(alertId) {
    return apiClient.post(`/alerts/${alertId}/mark-seen`);
  }

  // =================== ANALYSE ET RAPPORTS ===================
  
  async analyserClient(clientId, useCache = true) {
    return apiClient.post(`/alerts/analyze-client/${clientId}`, {
      use_cache: useCache
    });
  }

  async obtenirSanteService() {
    return apiClient.get('/alerts/health');
  }

  // =================== TESTS ===================
  
  async testerService() {
    return apiClient.get('/alerts/test');
  }

  async testerImportModeles() {
    return apiClient.get('/alerts/test/device-import');
  }
}

export default new AlertService();
