import { apiClient } from './authService';

class SiteService {
  // =================== GESTION CRUD DES SITES ===================
  
  async creerSite(donneesSite) {
    return apiClient.post('/sites/', donneesSite);
  }

  async listerSites(clientId = null) {
    const params = clientId ? { client_id: clientId } : {};
    return apiClient.get('/sites/', { params });
  }

  async obtenirSite(siteId) {
    return apiClient.get(`/sites/${siteId}`);
  }

  async modifierSite(siteId, nouvelleDonnees) {
    return apiClient.put(`/sites/${siteId}`, nouvelleDonnees);
  }

  async desactiverSite(siteId) {
    return apiClient.post(`/sites/${siteId}/desactiver`);
  }

  async reactiverSite(siteId) {
    return apiClient.post(`/sites/${siteId}/reactiver`);
  }

  async supprimerSite(siteId, forcer = false) {
    return apiClient.delete(`/sites/${siteId}?forcer=${forcer}`);
  }

  // =================== FONCTIONNALITÉS GÉOGRAPHIQUES ===================
  
  async geocoderSite(siteId) {
    return apiClient.post(`/sites/${siteId}/geocoder`);
  }

  async sitesProches(siteId, radiusKm = 10) {
    return apiClient.get(`/sites/${siteId}/sites-proches`, {
      params: { radius: radiusKm }
    });
  }

  async sitesPourCarte(clientId = null) {
    const params = clientId ? { client_id: clientId } : {};
    return apiClient.get('/sites/carte', { params });
  }

  // =================== STATISTIQUES ET RECHERCHE ===================
  
  async obtenirStatistiques(clientId = null) {
    const params = clientId ? { client_id: clientId } : {};
    return apiClient.get('/sites/statistiques', { params });
  }

  async rechercherSites(terme) {
    return apiClient.post('/sites/rechercher', { q: terme });
  }

  async listerSitesInactifs(clientId = null) {
    const params = clientId ? { client_id: clientId } : {};
    return apiClient.get('/sites/inactifs', { params });
  }

  async testerGeocodage(adresse) {
    return apiClient.post('/sites/test-geocodage', { adresse });
  }
}

export default new SiteService();
