# routes/__init__.py
# Package pour organiser toutes les routes de l'API

__version__ = "1.0.0"
__author__ = "SERTEC"

# Import des blueprints existants
try:
    from .api import api
    api_blueprints = ['api']
except ImportError:
    api_blueprints = []

try:
    from .auth import auth_bp
    auth_blueprints = ['auth_bp']
except ImportError:
    auth_blueprints = []

# Import des nouvelles routes utilisateurs
try:
    from .user_routes import user_bp
    user_blueprints = ['user_bp']
except ImportError:
    user_blueprints = []

# Combinaison de tous les blueprints disponibles
__all__ = api_blueprints + auth_blueprints + user_blueprints

# Futures routes à ajouter
# from .client_routes import client_bp  
# from .device_routes import device_bp
# from .alert_routes import alert_bp

# Fonction utilitaire pour enregistrer tous les blueprints
def register_blueprints(app):
    """
    Enregistre tous les blueprints disponibles dans l'application Flask
    
    Args:
        app: Instance de l'application Flask
    """
    
    # Blueprints API existants
    if 'api' in api_blueprints:
        try:
            from .api import api
            app.register_blueprint(api)
            print("✅ Blueprint 'api' enregistré")
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement du blueprint 'api': {e}")
    
    # Blueprints d'authentification
    if 'auth_bp' in auth_blueprints:
        try:
            from .auth import auth_bp
            app.register_blueprint(auth_bp)
            print("✅ Blueprint 'auth_bp' enregistré")
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement du blueprint 'auth_bp': {e}")
    
    # Blueprints de gestion des utilisateurs
    if 'user_bp' in user_blueprints:
        try:
            from .user_routes import user_bp
            app.register_blueprint(user_bp)
            print("✅ Blueprint 'user_bp' enregistré")
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement du blueprint 'user_bp': {e}")
    
    return True

# Configuration des URL patterns pour documentation
URL_PATTERNS = {
    'auth': {
        'prefix': '/api/auth',
        'routes': [
            'POST /register - Créer un utilisateur',
            'POST /login - Connexion',
            'POST /logout - Déconnexion',
            'GET /profile - Profil utilisateur',
            'PUT /profile - Modifier profil',
            'POST /change-password - Changer mot de passe',
            'POST /forgot-password - Mot de passe oublié',
            'POST /reset-password - Réinitialiser mot de passe'
        ]
    },
    'users': {
        'prefix': '/api/users',
        'routes': [
            # Gestion des clients
            'POST /clients - Créer client (superadmin)',
            'GET /clients - Lister clients (superadmin)',
            'PUT /clients/<id> - Modifier client (superadmin)',
            'POST /clients/<id>/desactiver - Désactiver client (superadmin)',
            'POST /clients/<id>/reactiver - Réactiver client (superadmin)',
            'DELETE /clients/<id>/supprimer - Supprimer client (superadmin)',
            
            # Gestion des utilisateurs
            'POST / - Créer utilisateur (admin+)',
            'GET / - Lister utilisateurs (admin+)',
            'GET /<id> - Détails utilisateur (admin+)',
            'PUT /<id> - Modifier utilisateur (admin+)',
            'POST /<id>/desactiver - Désactiver utilisateur (admin+)',
            'POST /<id>/reactiver - Réactiver utilisateur (admin+)',
            'DELETE /<id>/supprimer - Supprimer utilisateur (admin+)',
            'POST /<id>/reset-password - Reset mot de passe (admin+)',
            'POST /<id>/generer-mot-de-passe - Générer mot de passe (admin+)',
            
            # Profil personnel
            'GET /mon-profil - Mon profil (user+)',
            'PUT /mon-profil - Modifier mon profil (user+)',
            
            # Utilitaires
            'GET /statistiques - Statistiques (admin+)',
            'GET /rechercher - Recherche utilisateurs (admin+)',
            'GET /inactifs - Utilisateurs inactifs (admin+)'
        ]
    }
}

def print_routes_info():
    """Affiche les informations sur toutes les routes disponibles"""
    print("\n" + "="*60)
    print("📋 ROUTES DISPONIBLES - SERTEC IoT API")
    print("="*60)
    
    for module, info in URL_PATTERNS.items():
        print(f"\n🔹 MODULE: {module.upper()}")
        print(f"   Préfixe: {info['prefix']}")
        print("   Routes:")
        for route in info['routes']:
            print(f"   • {route}")
    
    print("\n" + "="*60)
    print("🔐 NIVEAUX DE PERMISSION:")
    print("   • (superadmin) = Superadmin uniquement")
    print("   • (admin+) = Admin et Superadmin")
    print("   • (user+) = Tout utilisateur connecté")
    print("="*60)