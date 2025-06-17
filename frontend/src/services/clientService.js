import { apiClient } from './authService';

class ClientService {
  async creerClient(donneesClient) {
    return apiClient.post('/users/clients', donneesClient);
  }

  async listerClients() {
    return apiClient.get('/users/clients');
  }

  async modifierClient(clientId, nouvelleDonnees) {
    return apiClient.put(`/users/clients/${clientId}`, nouvelleDonnees);
  }

  async desactiverClient(clientId) {
    return apiClient.post(`/users/clients/${clientId}/desactiver`);
  }

  async reactiverClient(clientId) {
    return apiClient.post(`/users/clients/${clientId}/reactiver`);
  }

  async supprimerClient(clientId, forcer = false) {
    return apiClient.delete(`/users/clients/${clientId}/supprimer?forcer=${forcer}`);
  }
}

export default new ClientService();