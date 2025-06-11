from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
import os

# Extensions Flask
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app():
    """Factory pour créer l'application Flask - Version améliorée"""
    
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
    
    # ✅ AJOUTÉ : Importer tous les modèles pour que Flask-Migrate les trouve
    try:
        from app import models
        app.logger.info("✅ Modèles importés avec succès")
    except ImportError as e:
        app.logger.warning(f"⚠️ Erreur import modèles: {e}")
    
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
    
    # Blueprint API existant (temporaire)
    try:
        from app.routes import api
        app.register_blueprint(api)
        app.logger.info("✅ Blueprint API existant enregistré")
    except ImportError as e:
        app.logger.warning(f"⚠️ Erreur import blueprint API existant: {e}")
    
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
            
            # Debug: Compter les routes users
            route_count = 0
            for rule in app.url_map.iter_rules():
                if rule.rule.startswith('/api/users'):
                    route_count += 1
                    app.logger.debug(f"📍 Route users: {list(rule.methods)} {rule.rule}")
            
            app.logger.info(f"✅ Total routes users enregistrées: {route_count}")
            
        else:
            app.logger.warning(f"⚠️ Fichier user_routes non trouvé: {user_routes_file_path}")
            app.logger.info("💡 Créez le fichier app/routes/user_routes.py pour activer la gestion des utilisateurs")
            
    except Exception as e:
        app.logger.error(f"❌ Erreur import blueprint users: {e}")
        import traceback
        app.logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
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
            
            # Debug: Compter les routes sites
            route_count = 0
            for rule in app.url_map.iter_rules():
                if rule.rule.startswith('/api/sites'):
                    route_count += 1
                    app.logger.debug(f"📍 Route sites: {list(rule.methods)} {rule.rule}")
            
            app.logger.info(f"✅ Total routes sites enregistrées: {route_count}")
            
        else:
            app.logger.warning(f"⚠️ Fichier site_routes non trouvé: {site_routes_file_path}")
            app.logger.info("💡 Créez le fichier app/routes/site_routes.py pour activer la gestion des sites")
            
    except Exception as e:
        app.logger.error(f"❌ Erreur import blueprint sites: {e}")
        import traceback
        app.logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    # 🔮 BLUEPRINTS FUTURS - Prêts pour l'expansion
    
    # Blueprint devices (à créer)
    try:
        device_routes_file_path = os.path.join(routes_dir, 'device_routes.py')
        if os.path.exists(device_routes_file_path):
            spec = importlib.util.spec_from_file_location("app.routes.device_routes", device_routes_file_path)
            device_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(device_module)
            
            device_bp = device_module.device_bp
            app.register_blueprint(device_bp)
            app.logger.info("✅ Blueprint devices enregistré sur /api/devices")
        else:
            app.logger.debug("ℹ️ Blueprint devices pas encore créé")
    except Exception as e:
        app.logger.debug(f"ℹ️ Blueprint devices non disponible: {e}")
    
    # Blueprint alerts (à créer)
    try:
        alert_routes_file_path = os.path.join(routes_dir, 'alert_routes.py')
        if os.path.exists(alert_routes_file_path):
            spec = importlib.util.spec_from_file_location("app.routes.alert_routes", alert_routes_file_path)
            alert_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(alert_module)
            
            alert_bp = alert_module.alert_bp
            app.register_blueprint(alert_bp)
            app.logger.info("✅ Blueprint alerts enregistré sur /api/alerts")
        else:
            app.logger.debug("ℹ️ Blueprint alerts pas encore créé")
    except Exception as e:
        app.logger.debug(f"ℹ️ Blueprint alerts non disponible: {e}")
    
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
    
    @app.route('/certif')
    def health_check():
        """Route de santé pour vérifier que l'API fonctionne"""
        return {
            'status': 'certifier',
            'message': 'SERTEC IoT API est opérationnelle',
            'version': '1.0.0',
            'services': {
                'database': 'connected',
                'auth': 'active',
                'users': 'active',
                'sites': 'active'
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
            'endpoints': {
                'auth': '/api/auth',
                'users': '/api/users',
                'sites': '/api/sites'
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