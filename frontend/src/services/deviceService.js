import { apiClient } from './authService';

class DeviceService {
  // =================== IMPORT ET SYNCHRONISATION TUYA ===================
  
  async importerAppareilsTuya() {
    return apiClient.post('/devices/import-tuya');
  }

  async synchroniserTuya() {
    return apiClient.post('/devices/sync-tuya');
  }

  // =================== GESTION DES ASSIGNATIONS ===================
  
  async listerNonAssignes() {
    return apiClient.get('/devices/non-assignes');
  }

  async assignerAppareil(tuyaDeviceId, clientId, siteId) {
    return apiClient.post(`/devices/${tuyaDeviceId}/assigner`, {
      client_id: clientId,
      site_id: siteId
    });
  }

  async desassignerAppareil(tuyaDeviceId) {
    return apiClient.post(`/devices/${tuyaDeviceId}/desassigner`);
  }

  // =================== GESTION CRUD DES APPAREILS ===================
  
  async listerAppareils(siteId = null, inclureNonAssignes = false) {
    const params = {};
    if (siteId) params.site_id = siteId;
    if (inclureNonAssignes) params.inclure_non_assignes = 'true';
    
    return apiClient.get('/devices/', { params });
  }

  async obtenirAppareil(deviceId) {
    return apiClient.get(`/devices/${deviceId}`);
  }

  // =================== CONTRÔLE DES APPAREILS ===================
  
  async controlerAppareil(deviceId, action, valeur = null) {
    return apiClient.post(`/devices/${deviceId}/controle`, {
      action,
      valeur
    });
  }

  async toggleAppareil(deviceId, etat = null) {
    const data = etat !== null ? { etat } : {};
    return apiClient.post(`/devices/${deviceId}/toggle`, data);
  }

  // =================== COLLECTE DE DONNÉES ===================
  
  async collecterDonnees(deviceId) {
    return apiClient.post(`/devices/${deviceId}/collecter-donnees`);
  }

  async obtenirDonneesAppareil(deviceId, limite = 100, page = 1) {
    return apiClient.get(`/devices/${deviceId}/donnees`, {
      params: { limite, page }
    });
  }

  // =================== GRAPHIQUES ===================
  
  async obtenirGraphiqueTension(deviceId, startTime = null, endTime = null) {
    const params = {};
    if (startTime) params.start_time = startTime;
    if (endTime) params.end_time = endTime;
    
    return apiClient.get(`/devices/${deviceId}/graphique/tension`, { params });
  }

  async obtenirGraphiqueCourant(deviceId, startTime = null, endTime = null) {
    const params = {};
    if (startTime) params.start_time = startTime;
    if (endTime) params.end_time = endTime;
    
    return apiClient.get(`/devices/${deviceId}/graphique/courant`, { params });
  }

  async obtenirGraphiquePuissance(deviceId, startTime = null, endTime = null) {
    const params = {};
    if (startTime) params.start_time = startTime;
    if (endTime) params.end_time = endTime;
    
    return apiClient.get(`/devices/${deviceId}/graphique/puissance`, { params });
  }

  async obtenirStatutAppareil(deviceId) {
    return apiClient.get(`/devices/${deviceId}/statut`);
  }

  // =================== STATISTIQUES ET RECHERCHE ===================
  
  async obtenirStatistiques() {
    return apiClient.get('/devices/statistiques');
  }

  async rechercherAppareils(terme) {
    return apiClient.post('/devices/rechercher', { q: terme });
  }

  async obtenirHistorique(deviceId, limit = 100, hoursBack = 24) {
    return apiClient.get(`/devices/${deviceId}/historique`, {
      params: { limit, hours_back: hoursBack }
    });
  }

  async pingAppareil(deviceId) {
    return apiClient.post(`/devices/${deviceId}/ping`);
  }

  async operationBatch(operation, deviceIds) {
    return apiClient.post('/devices/batch-operation', {
      operation,
      device_ids: deviceIds
    });
  }

  // =================== TESTS ===================
  
  async testerConnexionTuya() {
    return apiClient.get('/devices/test-tuya-connection');
  }

  async debugDirect() {
    return apiClient.get('/devices/debug-direct');
  }

  async debugFiles() {
    return apiClient.get('/devices/debug-files');
  }
}

export default new DeviceService();