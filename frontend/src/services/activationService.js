import UserService from './userService'

// Service d'activation qui utilise UserService pour les appels API
class ActivationService {
  async activerAdmin(token, motDePasse, confirmMotDePasse) {
    return UserService.activerAdmin(token, motDePasse, confirmMotDePasse)
  }

  async validerTokenActivation(token) {
    return UserService.validerTokenActivation(token)
  }

  async regenererTokenActivation(adminId) {
    return UserService.regenererTokenActivation(adminId)
  }

  async listerAdminsEnAttente() {
    return UserService.listerAdminsEnAttente()
  }

  async envoyerNouveauMotDePasse(utilisateurId) {
    return UserService.envoyerNouveauMotDePasse(utilisateurId)
  }
}

export default new ActivationService()