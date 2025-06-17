import { apiClient } from './authService';

class SiteService {
  async creerSite(donnees) {
    return apiClient.post('/sites/', donnees)
  }

  async listerSites(clientId = null) {
    const params = clientId ? { client_id: clientId } : {}
    return apiClient.get('/sites/', { params })
  }

  async obtenirSite(siteId) {
    return apiClient.get(`/sites/${siteId}`)
  }

  async modifierSite(siteId, donnees) {
    return apiClient.put(`/sites/${siteId}`, donnees)
  }

  async desactiverSite(siteId) {
    return apiClient.post(`/sites/${siteId}/desactiver`)
  }

  async reactiverSite(siteId) {
    return apiClient.post(`/sites/${siteId}/reactiver`)
  }

  async supprimerSite(siteId, forcer = false) {
    return apiClient.delete(`/sites/${siteId}`, {
      params: { forcer }
    })
  }

  async geocoderSite(siteId) {
    return apiClient.post(`/sites/${siteId}/geocoder`)
  }

  async sitesProches(siteId, radiusKm = 10) {
    return apiClient.get(`/sites/${siteId}/sites-proches`, {
      params: { radius: radiusKm }
    })
  }

  async obtenirStatistiques(clientId = null) {
    const params = clientId ? { client_id: clientId } : {}
    return apiClient.get('/sites/statistiques', { params })
  }

  async rechercherSites(terme) {
    return apiClient.get('/sites/rechercher', {
      params: { q: terme }
    })
  }

  async listerSitesInactifs(clientId = null) {
    const params = clientId ? { client_id: clientId } : {}
    return apiClient.get('/sites/inactifs', { params })
  }

  async obtenirSitesPourCarte(clientId = null) {
    const params = clientId ? { client_id: clientId } : {}
    return apiClient.get('/sites/carte', { params })
  }
}

export default new SiteService()