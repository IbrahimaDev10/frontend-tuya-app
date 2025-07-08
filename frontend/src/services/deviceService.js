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

async toggleAppareil(deviceId, etat = null) { // 'etat' est la valeur booléenne que vous voulez envoyer (True/False)
    const data = { etat: etat }; // Envoyez la valeur explicite
  
    try {
      // L'API Flask attend un POST avec un body JSON
      const res = await apiClient.post(`/devices/${deviceId}/toggle`, data);
      const response = res.data; // C'est la réponse JSON du backend
  
      if (response.success) { // Vérifiez directement response.success
        return {
          success: true,
          message: response.message || 'Action effectuée',
          newState: response.new_state, // <-- C'est ici que vous récupérez le new_state du backend
          // ... autres champs si votre backend les renvoie et que vous en avez besoin
        };
      } else {
        return {
          success: false,
          message: response.error || 'Échec de l’action', // Utilisez response.error pour les messages d'erreur
        };
      }
    } catch (error) {
      console.error('Erreur dans toggleAppareil:', error);
      return {
        success: false,
        message: 'Erreur réseau ou serveur',
      };
    }
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

  async rechercherAppareils(terme, siteId = null) {
    const data = { q: terme };
    if (siteId) data.site_id = siteId; // <-- AJOUTÉ
    return apiClient.post('/devices/rechercher', data); // Utilisation de POST avec un corps pour les paramètres
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


  // =================== PROTECTION AUTOMATIQUE ===================
  
  async configurerProtectionAutomatique(deviceId, protectionConfig) {
    return apiClient.post(`/devices/${deviceId}/protection/configure`, {
      protection_config: protectionConfig
    });
  }

  async obtenirStatutProtection(deviceId) {
    return apiClient.get(`/devices/${deviceId}/protection/status`);
  }

  // =================== PROGRAMMATION HORAIRES ===================
  
  async configurerProtectionAutomatique(deviceId, protectionConfig) {
  return apiClient.post(`/devices/${deviceId}/protection/configure`, {
    protection_config: protectionConfig
  });
}

async configurerProtectionAutomatique(deviceId, protectionConfig) {
  return apiClient.post(`/devices/${deviceId}/protection/config`, { // <-- Changement ici
    protection_config: protectionConfig // Le backend attend un objet avec la clé 'protection_config'
  });
}

async obtenirStatutProtection(deviceId) {
  return apiClient.get(`/devices/${deviceId}/protection/config`); // <-- Changement ici
}
async configurerProgrammationHoraires(deviceId, scheduleConfig) {
  return apiClient.post(`/devices/${deviceId}/schedule/configure`, {
    schedule_config: scheduleConfig
  });
}

async obtenirStatutProgrammation(deviceId) {
  return apiClient.get(`/devices/${deviceId}/schedule/status`);
}

async desactiverProgrammation(deviceId) {
  return apiClient.post(`/devices/${deviceId}/schedule/disable`);
}
// Dans DeviceService.js
async configurerProgrammationHoraires(deviceId, scheduleConfig) {
  return apiClient.post(`/devices/${deviceId}/programmation/config`, scheduleConfig); // <-- Changement ici. Le backend attend directement l'objet scheduleConfig, pas encapsulé dans 'schedule_config'
}

async obtenirStatutProgrammation(deviceId) {
  return apiClient.get(`/devices/${deviceId}/programmation/config`); // <-- Changement ici
}

async desactiverProgrammation(deviceId){
    // Appelle la même route avec l'action 'disable'
    const response = await apiClient.post(`/devices/${deviceId}/programmation/config`, { action: 'disable' });
    return response.data;
}

}

export default new DeviceService();