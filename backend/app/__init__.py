from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

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
    
    # Initialize CORS avec tes paramètres existants
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['http://localhost:5173']))
    
    # Initialize JWT avec tes paramètres existants
    jwt.init_app(app)
    
    # Initialize nouvelles extensions (base de données)
    db.init_app(app)
    migrate.init_app(app, db)
    
    # ✅ AJOUTÉ : Importer tous les modèles pour que Flask-Migrate les trouve
    from app import models
    
    # Register blueprints - On va adapter ton routes.py existant
    register_blueprints(app)
    
    # Gestionnaires d'erreurs
    register_error_handlers(app)
    
    # Créer les tables en mode développement
    with app.app_context():
        if app.config['DEBUG']:
            try:
                db.create_all()
                print("✅ Tables de base de données créées")
            except Exception as e:
                print(f"⚠️ Erreur création tables: {e}")
    
    return app

def register_blueprints(app):
    """Enregistrer tous les blueprints"""
    
    # Pour l'instant, on garde ton blueprint existant
    # Et on ajoute progressivement les nouveaux
    try:
        # Ton blueprint existant (temporaire)
        from app.routes import api
        app.register_blueprint(api)
        print("✅ Blueprint existant enregistré")
    except ImportError as e:
        print(f"⚠️ Erreur import blueprint existant: {e}")
    
    # Nouveaux blueprints (on les ajoutera progressivement)
    try:
        from app.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        print("✅ Blueprint auth enregistré")
    except ImportError:
        print("ℹ️ Blueprint auth pas encore créé")
    
    try:
        from app.routes.devices import devices_bp
        app.register_blueprint(devices_bp, url_prefix='/api/devices')
        print("✅ Blueprint devices enregistré")
    except ImportError:
        print("ℹ️ Blueprint devices pas encore créé")
    
    # Route de santé
    @app.route('/health')
    def health_check():
        return {
            'status': 'OK',
            'message': 'SERTEC IoT API Backend',
            'version': '1.0.0'
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