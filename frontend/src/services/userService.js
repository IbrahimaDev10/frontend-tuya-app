import { apiClient } from './authService';

class UserService {
  // =================== GESTION DES CLIENTS ===================
  
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

  // =================== GESTION DES UTILISATEURS ===================
  
  async creerUtilisateur(donneesUtilisateur) {
    return apiClient.post('/users/', donneesUtilisateur);
  }

  async listerUtilisateurs(clientId = null) {
    const params = clientId ? { client_id: clientId } : {};
    return apiClient.get('/users/', { params });
  }

  async obtenirUtilisateur(utilisateurId) {
    return apiClient.get(`/users/${utilisateurId}`);
  }

  async modifierUtilisateur(utilisateurId, nouvelleDonnees) {
    return apiClient.put(`/users/${utilisateurId}`, nouvelleDonnees);
  }

  async desactiverUtilisateur(utilisateurId) {
    return apiClient.post(`/users/${utilisateurId}/desactiver`);
  }

  async reactiverUtilisateur(utilisateurId) {
    return apiClient.post(`/users/${utilisateurId}/reactiver`);
  }

  async supprimerUtilisateur(utilisateurId, forcer = false) {
    return apiClient.delete(`/users/${utilisateurId}/supprimer?forcer=${forcer}`);
  }

  async supprimerSuperadmin(superadminId, forcer = false) {
    return apiClient.delete(`/users/${superadminId}/supprimer-superadmin?forcer=${forcer}`);
  }

  async reinitialiserMotDePasse(utilisateurId, nouveauMotDePasse) {
    return apiClient.post(`/users/${utilisateurId}/reset-password`, {
      nouveau_mot_de_passe: nouveauMotDePasse
    });
  }

  async genererMotDePasse(utilisateurId) {
    return apiClient.post(`/users/${utilisateurId}/envoyer-nouveau-mot-de-passe`);
  }

  // =================== PROFIL UTILISATEUR ===================
  
  async obtenirMonProfil() {
    return apiClient.get('/users/mon-profil');
  }

  async modifierMonProfil(donnees) {
    return apiClient.put('/users/Updateprofil', donnees);
  }

  // =================== STATISTIQUES ET RECHERCHE ===================
  
  async obtenirStatistiques() {
    return apiClient.get('/users/statistiques');
  }

  async rechercherUtilisateurs(terme) {
    return apiClient.post('/users/rechercher', { q: terme });
  }

  async listerUtilisateursInactifs() {
    return apiClient.get('/users/inactifs');
  }

  // =================== ACTIVATION ADMIN ===================
  
  async activerAdmin(token, motDePasse, confirmMotDePasse) {
    return apiClient.post(`/users/activer-admin/${token}`, {
      mot_de_passe: motDePasse,
      confirmpasse: confirmMotDePasse
    });
  }

  async activerUtilisateur(token, motDePasse, confirmMotDePasse) {
    return apiClient.post(`/users/activer-utilisateur/${token}`, {
      mot_de_passe: motDePasse,
      confirmpasse: confirmMotDePasse
    });
  }

  async validerTokenActivation(token) {
    return apiClient.get(`/users/valider-token-activation/${token}`);
  }

  async regenererTokenActivation(adminId) {
    return apiClient.post(`/users/${adminId}/regenerer-token-activation`);
  }

  /**
   * Créer et envoyer un token d'activation pour un utilisateur existant
   * @param {string} utilisateurId - ID de l'utilisateur
   */
  async creerActivationUtilisateur(utilisateurId) {
    return apiClient.post(`/users/${utilisateurId}/creer-activation`);
  }

   /**
   * Lister les utilisateurs en attente d'activation selon les permissions
   * @param {boolean} inclureTousRoles - Inclure tous les rôles 
   */
  async listerUtilisateursEnAttente(inclureTousRoles = false) {
    const params = inclureTousRoles ? { inclure_tous_roles: 'true' } : {};
    return apiClient.get('/users/utilisateurs-en-attente', { params });
  }


  async listerAdminsEnAttente() {
    return apiClient.get('/users/admins-en-attente');
  }

/**
   * Supprimer un utilisateur en attente d'activation
   * @param {string} utilisateurId - ID de l'utilisateur
   */
  async supprimerUtilisateurEnAttente(utilisateurId) {
    return apiClient.delete(`/users/${utilisateurId}/supprimer-en-attente`);
  }


  async envoyerNouveauMotDePasse(utilisateurId) {
    return apiClient.post(`/users/${utilisateurId}/envoyer-nouveau-mot-de-passe`);
  }
}

export default new UserService();