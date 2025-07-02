from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail  
import os
import logging

# ✅ NOUVEAU : Import Redis
import redis

# Extensions Flask
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()

# ✅ NOUVEAU : Client Redis global (simple)
redis_client = None

def create_app():
    """Factory pour créer l'application Flask - Version améliorée avec Redis"""
    
    # Créer l'app Flask
    app = Flask(__name__)
    
    # Charger la configuration depuis le nouveau chemin
    from config.settings import get_config
    config = get_config()
    app.config.from_object(config)
    
    # Valider la configuration
    config.validate_config()
    
    # Setup logging
    setup_logging(app)
    
    # Initialize CORS avec tes paramètres existants
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['http://localhost:5173']))
    
    # Initialize JWT avec tes paramètres existants
    jwt.init_app(app)
    
    # Initialize nouvelles extensions (base de données)
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize Flask-Mail
    mail.init_app(app)
    
    # ✅ NOUVEAU : Initialize Redis (simple et robuste)
    setup_redis(app)
    
    # Vérifier et afficher le statut de la configuration mail
    if config.is_mail_configured():
        app.logger.info("✅ Service mail configuré et activé")
        app.logger.info(f"📧 SMTP: {app.config.get('MAIL_SERVER')}:{app.config.get('MAIL_PORT')}")
        app.logger.info(f"📧 Expéditeur: {app.config.get('MAIL_DEFAULT_SENDER')}")
    else:
        app.logger.warning("⚠️ Service mail non configuré - fonctionnalités email désactivées")
    
    # Importer tous les modèles pour que Flask-Migrate les trouve
    try:
        from app import models
        app.logger.info("✅ Modèles importés avec succès")
    except ImportError as e:
        app.logger.warning(f"⚠️ Erreur import modèles: {e}")
    
    # Importer les services pour s'assurer qu'ils sont disponibles
    try:
        from app.services.tuya_service import TuyaClient
        from app.services.device_service import DeviceService
        app.logger.info("✅ Services Tuya et Device importés avec succès")
    except ImportError as e:
        app.logger.warning(f"⚠️ Erreur import services: {e}")
    
    # Importer le service mail
    try:
        from app.services.mail_service import MailService
        app.logger.info("✅ Service Mail importé avec succès")
    except ImportError as e:
        app.logger.warning(f"⚠️ Erreur import service mail: {e}")
    
    # Register blueprints - Version améliorée
    register_blueprints(app)
    
    # Gestionnaires d'erreurs
    register_error_handlers(app)
    
    # JWT callbacks
    register_jwt_callbacks(app)
    
    # Créer les tables en mode développement
    with app.app_context():
        if app.config['DEBUG']:
            try:
                db.create_all()
                app.logger.info("✅ Tables de base de données créées")
            except Exception as e:
                app.logger.error(f"⚠️ Erreur création tables: {e}")
    
    app.logger.info("🚀 Application SERTEC IoT initialisée avec succès")
    return app

# ✅ NOUVEAU : Fonction simple pour configurer Redis
def setup_redis(app):
    """Configuration Redis simple et robuste"""
    global redis_client
    
    try:
        # ✅ UTILISATION : Configuration Redis depuis settings.py
        from config.settings import get_config
        config_class = get_config()
        
        if not config_class.is_redis_configured():
            app.logger.info("ℹ️ Redis non configuré - application fonctionnera sans cache")
            redis_client = None
            return
        
        # Récupérer la configuration Redis complète
        redis_config = config_class.get_redis_config()
        redis_url = redis_config.pop('url')  # Extraire l'URL
        
        app.logger.info(f"🔄 Tentative de connexion Redis...")
        
        # Créer le client Redis avec la configuration complète
        redis_client = redis.from_url(redis_url, **redis_config)
        
        # Test de connexion
        redis_client.ping()
        
        # Informations Redis
        info = redis_client.info('server')
        redis_version = info.get('redis_version', 'inconnue')
        
        app.logger.info(f"✅ Redis connecté avec succès")
        app.logger.info(f"   Version Redis: {redis_version}")
        app.logger.info(f"   Mode: {info.get('redis_mode', 'standalone')}")
        
        # Test d'écriture/lecture simple
        test_key = "sertec_init_test"
        redis_client.set(test_key, "OK", ex=10)  # Expire dans 10 secondes
        test_value = redis_client.get(test_key)
        
        if test_value == "OK":
            app.logger.info("✅ Test écriture/lecture Redis réussi")
            redis_client.delete(test_key)  # Nettoyage
        else:
            app.logger.warning("⚠️ Test écriture/lecture Redis échoué")
        
    except redis.ConnectionError as e:
        app.logger.warning(f"⚠️ Redis non disponible: {e}")
        app.logger.info("   L'application fonctionnera sans cache Redis")
        redis_client = None
        
    except redis.AuthenticationError as e:
        app.logger.error(f"❌ Erreur authentification Redis: {e}")
        app.logger.error("   Vérifiez le mot de passe dans REDIS_URL")
        redis_client = None
        
    except Exception as e:
        app.logger.warning(f"⚠️ Erreur Redis inattendue: {e}")
        app.logger.info("   L'application fonctionnera sans cache Redis")
        redis_client = None

# ✅ NOUVEAU : Fonction helper pour récupérer Redis (utilisée par vos services)
def get_redis():
    """Récupérer le client Redis - Peut retourner None si Redis indisponible"""
    return redis_client

# ✅ NOUVEAU : Fonction helper pour vérifier si Redis est disponible
def is_redis_available():
    """Vérifier si Redis est disponible et connecté"""
    if redis_client is None:
        return False
    
    try:
        redis_client.ping()
        return True
    except:
        return False

def setup_logging(app):
    """Configuration des logs"""
    if not app.debug:
        # Créer le dossier logs s'il n'existe pas
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Configuration du logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/sertec_iot.log'),
                logging.StreamHandler()
            ]
        )

def register_blueprints(app):
    """Enregistrer tous les blueprints"""
    
    import importlib.util
    import os
    
    # Chemin correct : app/routes/
    current_file = os.path.abspath(__file__)
    app_dir = os.path.dirname(current_file)
    routes_dir = os.path.join(app_dir, 'routes')
    
    # 🔐 BLUEPRINT AUTH
    try:
        app.logger.info("🔍 Import du blueprint auth...")
        
        auth_file_path = os.path.join(routes_dir, 'auth.py')
        
        if os.path.exists(auth_file_path):
            # Charger le module auth
            spec = importlib.util.spec_from_file_location("app.routes.auth", auth_file_path)
            auth_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(auth_module)
            
            # Récupérer et enregistrer le blueprint
            auth_bp = auth_module.auth_bp
            app.register_blueprint(auth_bp)
            app.logger.info("✅ Blueprint auth enregistré sur /api/auth")
            
        else:
            app.logger.error(f"❌ Fichier auth non trouvé: {auth_file_path}")
            
    except Exception as e:
        app.logger.error(f"❌ Erreur import blueprint auth: {e}")
    
    # 👥 BLUEPRINT USERS
    try:
        app.logger.info("🔍 Import du blueprint users...")
        
        user_routes_file_path = os.path.join(routes_dir, 'user_routes.py')
        
        if os.path.exists(user_routes_file_path):
            # Charger le module user_routes
            spec = importlib.util.spec_from_file_location("app.routes.user_routes", user_routes_file_path)
            user_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(user_module)
            
            # Récupérer et enregistrer le blueprint
            user_bp = user_module.user_bp
            app.register_blueprint(user_bp)
            app.logger.info("✅ Blueprint users enregistré sur /api/users")
            
        else:
            app.logger.warning(f"⚠️ Fichier user_routes non trouvé: {user_routes_file_path}")
            
    except Exception as e:
        app.logger.error(f"❌ Erreur import blueprint users: {e}")
    
    # 📍 BLUEPRINT SITES
    try:
        app.logger.info("🔍 Import du blueprint sites...")
        
        site_routes_file_path = os.path.join(routes_dir, 'site_routes.py')
        
        if os.path.exists(site_routes_file_path):
            # Charger le module site_routes
            spec = importlib.util.spec_from_file_location("app.routes.site_routes", site_routes_file_path)
            site_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(site_module)
            
            # Récupérer et enregistrer le blueprint
            site_bp = site_module.site_bp
            app.register_blueprint(site_bp)
            app.logger.info("✅ Blueprint sites enregistré sur /api/sites")
            
        else:
            app.logger.warning(f"⚠️ Fichier site_routes non trouvé: {site_routes_file_path}")
            
    except Exception as e:
        app.logger.error(f"❌ Erreur import blueprint sites: {e}")


    # 📍 BLUEPRINT ALERTS
    try:
        app.logger.info("🔍 Import du blueprint alerts...")
        
        alert_routes_file_path = os.path.join(routes_dir, 'alert_routes.py')
        
        if os.path.exists(alert_routes_file_path):
            # Charger le module alert_routes
            spec = importlib.util.spec_from_file_location("app.routes.alert_routes", alert_routes_file_path)
            alert_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(alert_module)
            
            # Récupérer et enregistrer le blueprint
            alert_bp = alert_module.alert_bp
            app.register_blueprint(alert_bp)
            app.logger.info("✅ Blueprint alerts enregistré sur /api/alerts")
            
        else:
            app.logger.warning(f"⚠️ Fichier alert_routes non trouvé: {alert_routes_file_path}")
            
    except Exception as e:
        app.logger.error(f"❌ Erreur import blueprint alerts: {e}")
    
    # 🔥 BLUEPRINT DEVICES (PRIORITÉ)
    try:
        app.logger.info("🔍 Import du blueprint devices...")
        
        device_routes_file_path = os.path.join(routes_dir, 'device_routes.py')
        
        if os.path.exists(device_routes_file_path):
            # Charger le module device_routes
            spec = importlib.util.spec_from_file_location("app.routes.device_routes", device_routes_file_path)
            device_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(device_module)
            
            # Récupérer et enregistrer le blueprint
            device_bp = device_module.device_bp
            app.register_blueprint(device_bp)
            app.logger.info("✅ Blueprint devices enregistré sur /api/devices")
            
        else:
            app.logger.error(f"❌ Fichier device_routes non trouvé: {device_routes_file_path}")
            
    except Exception as e:
        app.logger.error(f"❌ Erreur import blueprint devices: {e}")
    
    # 🔧 ROUTES DE DEBUG ET SANTÉ
    
    @app.route('/debug/routes')
    def debug_routes():
        """Route pour voir toutes les routes disponibles"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods - {'HEAD', 'OPTIONS'}) if rule.methods else [],
                'path': rule.rule
            })
        return {
            'total_routes': len(routes),
            'routes': sorted(routes, key=lambda x: x['path'])
        }
    
    # ✅ NOUVEAU : Route de debug Redis
    @app.route('/debug/redis')
    def debug_redis():
        """Route pour vérifier l'état de Redis"""
        try:
            if redis_client is None:
                return {
                    'redis_service': 'not_configured',
                    'message': 'Redis non configuré ou indisponible'
                }
            
            # Test ping
            redis_client.ping()
            
            # Informations Redis
            info = redis_client.info('server')
            memory_info = redis_client.info('memory')
            
            # Test d'écriture/lecture
            test_key = "debug_test"
            redis_client.set(test_key, "debug_value", ex=5)
            test_result = redis_client.get(test_key)
            redis_client.delete(test_key)
            
            return {
                'redis_service': 'connected',
                'version': info.get('redis_version'),
                'mode': info.get('redis_mode'),
                'uptime_seconds': info.get('uptime_in_seconds'),
                'used_memory_human': memory_info.get('used_memory_human'),
                'test_write_read': test_result == "debug_value",
                'config_url': app.config.get('REDIS_URL', '').split('@')[1] if '@' in app.config.get('REDIS_URL', '') else 'localhost:6379'
            }
            
        except Exception as e:
            return {
                'redis_service': 'error',
                'error': str(e)
            }, 500
    
    @app.route('/debug/tuya')
    def debug_tuya():
        """Route pour vérifier l'état de Tuya"""
        try:
            from app.services.tuya_service import TuyaClient
            tuya_client = TuyaClient()
            connection_info = tuya_client.get_connection_info()
            
            return {
                'tuya_service': 'available',
                'connection_info': connection_info,
                'auto_connect_test': tuya_client.auto_connect_from_env()
            }
        except Exception as e:
            return {
                'tuya_service': 'error',
                'error': str(e)
            }, 500
    
    @app.route('/debug/mail')
    def debug_mail():
        """Route pour vérifier l'état du service mail"""
        try:
            from app.services.mail_service import MailService
            
            config_status = app.config.get('MAIL_USERNAME') is not None
            
            return {
                'mail_service': 'available' if config_status else 'not_configured',
                'config': {
                    'server': app.config.get('MAIL_SERVER'),
                    'port': app.config.get('MAIL_PORT'),
                    'use_tls': app.config.get('MAIL_USE_TLS'),
                    'username_configured': app.config.get('MAIL_USERNAME') is not None,
                    'sender': app.config.get('MAIL_DEFAULT_SENDER')
                },
                'enabled': MailService.is_enabled() if hasattr(MailService, 'is_enabled') else config_status
            }
        except Exception as e:
            return {
                'mail_service': 'error',
                'error': str(e)
            }, 500
    
    @app.route('/certif')
    def health_check():
        """Route de santé pour vérifier que l'API fonctionne"""
        # Vérifier le statut des services
        mail_status = 'configured' if app.config.get('MAIL_USERNAME') else 'not_configured'
        redis_status = 'connected' if is_redis_available() else 'not_available'
        
        return {
            'status': 'certifier',
            'message': 'SERTEC IoT API est opérationnelle',
            'version': '1.0.0',
            'services': {
                'database': 'connected',
                'auth': 'active',
                'users': 'active',
                'sites': 'active',
                'devices': 'active',
                'tuya': 'active',
                'mail': mail_status,
                'redis': redis_status  # ✅ NOUVEAU
            }
        }, 200
    
    @app.route('/')
    def home():
        """Page d'accueil de l'API"""
        return {
            'message': 'Bienvenue sur l\'API SERTEC IoT',
            'version': '1.0.0',
            'documentation': '/debug/routes',
            'certifier': '/certif',
            'debug_endpoints': {
                'tuya': '/debug/tuya',
                'mail': '/debug/mail',
                'redis': '/debug/redis'  # ✅ NOUVEAU
            },
            'api_endpoints': {
                'auth': '/api/auth',
                'users': '/api/users',
                'sites': '/api/sites',
                'devices': '/api/devices'
            }
        }, 200

def register_error_handlers(app):
    """Gestionnaires d'erreurs globaux"""
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint non trouvé'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Erreur serveur: {error}')
        return {'error': 'Erreur interne du serveur'}, 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Requête invalide'}, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return {'error': 'Non autorisé'}, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return {'error': 'Accès interdit'}, 403

def register_jwt_callbacks(app):
    """Callbacks JWT pour une meilleure gestion"""
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {
            'error': 'Token expiré',
            'message': 'Veuillez vous reconnecter'
        }, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {
            'error': 'Token invalide',
            'message': 'Token malformé ou corrompu'
        }, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {
            'error': 'Token manquant',
            'message': 'Authentification requise'
        }, 401
    
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return {
            'error': 'Token non frais',
            'message': 'Une nouvelle authentification est requise'
        }, 401