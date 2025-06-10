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
    
    # Register blueprints - On va adapter ton routes.py existant
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
    
    # Pour l'instant, on garde ton blueprint existant
    # Et on ajoute progressivement les nouveaux
    try:
        # Ton blueprint existant (temporaire)
        from app.routes import api
        app.register_blueprint(api)
        app.logger.info("✅ Blueprint existant enregistré")
    except ImportError as e:
        app.logger.warning(f"⚠️ Erreur import blueprint existant: {e}")
    
    # ✅ NOUVEAU : Blueprint auth depuis app/routes/ (structure réelle)
    try:
        app.logger.info("🔍 Tentative d'import du blueprint auth depuis app/routes/...")
        
        # Solution Windows : Import direct avec importlib
        import importlib.util
        import os
        
        # Chemin correct : app/routes/auth.py
        current_file = os.path.abspath(__file__)
        app_dir = os.path.dirname(current_file)
        routes_dir = os.path.join(app_dir, 'routes')
        auth_file_path = os.path.join(routes_dir, 'auth.py')
        
        app.logger.info(f"🔍 Fichier actuel: {current_file}")
        app.logger.info(f"🔍 Dossier app: {app_dir}")
        app.logger.info(f"🔍 Dossier routes: {routes_dir}")
        app.logger.info(f"🔍 Fichier auth recherché: {auth_file_path}")
        
        # Lister le contenu du dossier app/routes
        if os.path.exists(routes_dir):
            files_in_routes = os.listdir(routes_dir)
            app.logger.info(f"📁 Fichiers dans app/routes/: {files_in_routes}")
        else:
            app.logger.error(f"❌ Dossier routes n'existe pas: {routes_dir}")
        
        if os.path.exists(auth_file_path):
            # Charger le module directement
            spec = importlib.util.spec_from_file_location("app.routes.auth", auth_file_path)
            auth_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(auth_module)
            
            # Récupérer le blueprint
            auth_bp = auth_module.auth_bp
            app.logger.info(f"✅ Blueprint auth importé directement: {auth_bp}")
            
            app.register_blueprint(auth_bp)
            app.logger.info("✅ Blueprint auth enregistré sur /api/auth")
            
            # Debug: Compter les routes auth
            route_count = 0
            for rule in app.url_map.iter_rules():
                if rule.rule.startswith('/api/auth'):
                    route_count += 1
                    app.logger.info(f"📍 Route auth: {list(rule.methods)} {rule.rule}")
            
            app.logger.info(f"✅ Total routes auth enregistrées: {route_count}")
            
        else:
            app.logger.error(f"❌ Fichier non trouvé: {auth_file_path}")
            
    except Exception as e:
        app.logger.error(f"❌ Erreur import blueprint auth: {e}")
        import traceback
        app.logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    # Nouveaux blueprints futurs
    try:
        from routes.devices_routes import devices_bp
        app.register_blueprint(devices_bp, url_prefix='/api/devices')
        app.logger.info("✅ Blueprint devices enregistré")
    except ImportError:
        app.logger.info("ℹ️ Blueprint devices pas encore créé")
    
    # 🔧 ROUTE DE DEBUG TEMPORAIRE
    @app.route('/debug/routes')
    def debug_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods) if rule.methods else [],
                'path': rule.rule
            })
        return {
            'total_routes': len(routes),
            'routes': sorted(routes, key=lambda x: x['path'])
        }

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