# routes/__init__.py
# Package pour organiser toutes les routes de l'API

__version__ = "1.0.0"
__author__ = "SERTEC"

# Import des blueprints existants
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

# Import des nouvelles routes sites
try:
    from .site_routes import site_bp
    site_blueprints = ['site_bp']
except ImportError:
    site_blueprints = []    

# Import des routes Devices
try:
    from .device_routes import device_bp
    device_blueprints = ['device_bp']
except ImportError:
    device_blueprints = []

# Inclure tous les blueprints dans __all__
__all__ = auth_blueprints + user_blueprints + site_blueprints + device_blueprints

# Futures routes à ajouter
# from .client_routes import client_bp  
# from .alert_routes import alert_bp

# Fonction utilitaire pour enregistrer tous les blueprints
def register_blueprints(app):
    """
    Enregistre tous les blueprints disponibles dans l'application Flask
    
    Args:
        app: Instance de l'application Flask
    """
    
    blueprints_registered = 0
    blueprints_failed = 0
  
    # Blueprints d'authentification
    if 'auth_bp' in auth_blueprints:
        try:
            from .auth import auth_bp
            app.register_blueprint(auth_bp)
            print("✅ Blueprint 'auth_bp' enregistré")
            blueprints_registered += 1
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement du blueprint 'auth_bp': {e}")
            blueprints_failed += 1
    
    # Blueprints de gestion des utilisateurs
    if 'user_bp' in user_blueprints:
        try:
            from .user_routes import user_bp
            app.register_blueprint(user_bp)
            print("✅ Blueprint 'user_bp' enregistré")
            blueprints_registered += 1
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement du blueprint 'user_bp': {e}")
            blueprints_failed += 1
    
    # Blueprints de gestion des sites
    if 'site_bp' in site_blueprints:
        try:
            from .site_routes import site_bp
            app.register_blueprint(site_bp)
            print("✅ Blueprint 'site_bp' enregistré")
            blueprints_registered += 1
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement du blueprint 'site_bp': {e}")
            blueprints_failed += 1

    # Blueprints de gestion des devices
    if 'device_bp' in device_blueprints:
        try:
            from .device_routes import device_bp
            app.register_blueprint(device_bp)
            print("✅ Blueprint 'device_bp' enregistré sur /api/devices")
            blueprints_registered += 1
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement du blueprint 'device_bp': {e}")
            blueprints_failed += 1        
    
    print(f"\n📊 RÉSUMÉ BLUEPRINTS: {blueprints_registered} enregistrés, {blueprints_failed} échoués")
    return blueprints_registered > 0

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
    },
    'sites': {
        'prefix': '/api/sites',
        'routes': [
            # CRUD Sites (SuperAdmin seulement)
            'POST / - Créer site (superadmin)',
            'PUT /<id> - Modifier site (superadmin)',
            'DELETE /<id> - Supprimer site (superadmin)',
            'POST /<id>/desactiver - Désactiver site (superadmin)',
            'POST /<id>/reactiver - Réactiver site (superadmin)',
            
            # Consultation (selon permissions)
            'GET / - Lister sites (admin+)',
            'GET /<id> - Détails site (admin+)',
            'GET /rechercher - Recherche sites (admin+)',
            'GET /inactifs - Sites désactivés (superadmin)',
            
            # Fonctionnalités géographiques
            'POST /<id>/geocoder - Forcer géocodage (superadmin)',
            'GET /<id>/sites-proches - Sites dans un rayon (admin+)',
            'GET /carte - Données pour carte interactive (admin+)',
            
            # Statistiques et utils
            'GET /statistiques - Statistiques sites (admin+)',
            'POST /test-geocodage - Tester géocodage adresse (superadmin)'
        ]
    },
    'devices': {
        'prefix': '/api/devices',
        'routes': [
            # Import et synchronisation Tuya
            'POST /import-tuya - Importer appareils depuis Tuya (superadmin)',
            'POST /sync-tuya - Synchroniser statuts avec Tuya (admin+)',
            
            # Gestion des assignations
            'GET /non-assignes - Lister appareils non-assignés (superadmin)',
            'POST /<id>/assigner - Assigner appareil à client/site (superadmin)',
            'POST /<id>/desassigner - Désassigner appareil (superadmin)',
            
            # CRUD appareils
            'GET / - Lister appareils selon permissions (admin+)',
            'GET /<id> - Détails appareil (admin+)',
            
            # Contrôle des appareils
            'POST /<id>/controle - Contrôler appareil (action personnalisée) (admin+)',
            'POST /<id>/toggle - Allumer/éteindre appareil (admin+)',
            
            # Collecte de données
            'POST /<id>/collecter-donnees - Collecter données manuellement (admin+)',
            'GET /<id>/donnees - Historique données avec pagination (admin+)',
            
            # Graphiques et analytics
            'GET /<id>/graphique/tension - Données tension pour graphique (admin+)',
            'GET /<id>/graphique/courant - Données courant pour graphique (admin+)',
            'GET /<id>/graphique/puissance - Données puissance pour graphique (admin+)',
            'GET /<id>/statut - Statut temps réel appareil (admin+)',
            
            # Utilitaires
            'GET /statistiques - Statistiques appareils (admin+)',
            'GET /rechercher - Recherche appareils par nom (admin+)',
            'POST /rechercher - Recherche appareils par nom (POST) (admin+)',
            'GET /test-tuya-connection - Tester connexion Tuya (admin+)'
        ]
    }
}

def print_routes_info():
    """Affiche les informations sur toutes les routes disponibles"""
    print("\n" + "="*70)
    print("📋 ROUTES DISPONIBLES - SERTEC IoT API")
    print("="*70)
    
    for module, info in URL_PATTERNS.items():
        print(f"\n🔹 MODULE: {module.upper()}")
        print(f"   Préfixe: {info['prefix']}")
        print("   Routes:")
        for route in info['routes']:
            print(f"   • {route}")
    
    print("\n" + "="*70)
    print("🔐 NIVEAUX DE PERMISSION:")
    print("   • (superadmin) = Superadmin uniquement")
    print("   • (admin+) = Admin et Superadmin")
    print("   • (user+) = Tout utilisateur connecté")
    print("="*70)

def check_blueprints_status():
    """Vérifie quels blueprints sont disponibles"""
    status = {
        'auth': len(auth_blueprints) > 0,
        'users': len(user_blueprints) > 0,
        'sites': len(site_blueprints) > 0,
        'devices': len(device_blueprints) > 0
    }
    
    print("\n📊 STATUT DES BLUEPRINTS:")
    for module, available in status.items():
        status_icon = "✅" if available else "❌"
        print(f"   {status_icon} {module.capitalize()}: {'Disponible' if available else 'Non disponible'}")
    
    total_available = sum(status.values())
    total_modules = len(status)
    print(f"\n📈 RÉSUMÉ: {total_available}/{total_modules} modules disponibles")
    
    return status

def get_routes_summary():
    """Retourne un résumé des routes pour l'API"""
    summary = {}
    
    for module, info in URL_PATTERNS.items():
        summary[module] = {
            'prefix': info['prefix'],
            'total_routes': len(info['routes']),
            'routes': info['routes']
        }
    
    return summary

# ✅ NOUVELLE FONCTION : Vérifier que tous les services requis sont disponibles
def check_services_health():
    """Vérifie l'état des services requis"""
    health_status = {
        'database': False,
        'tuya_client': False,
        'auth_service': False,
        'device_service': False
    }
    
    # Test connexion base de données
    try:
        from app import db
        db.session.execute('SELECT 1')
        health_status['database'] = True
    except:
        pass
    
    # Test TuyaClient
    try:
        from app.services.tuya_service import TuyaClient
        tuya = TuyaClient()
        health_status['tuya_client'] = True
    except:
        pass
    
    # Test AuthService
    try:
        from app.services.auth_service import Auth
        health_status['auth_service'] = True
    except:
        pass
    
    # Test DeviceService
    try:
        from app.services.device_service import DeviceService
        health_status['device_service'] = True
    except:
        pass
    
    print("\n💊 SANTÉ DES SERVICES:")
    for service, status in health_status.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {service}: {'OK' if status else 'ERREUR'}")
    
    return health_status