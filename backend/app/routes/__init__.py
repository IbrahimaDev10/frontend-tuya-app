# routes/__init__.py
# Package pour organiser toutes les routes de l'API

__version__ = "1.0.0"
__author__ = "SERTEC"

# Import des blueprints existants et nouveaux
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

# Combinaison de tous les blueprints disponibles
__all__ = api_blueprints + auth_blueprints

# Futures routes à ajouter
# from .user_routes import user_bp
# from .client_routes import client_bp  
# from .device_routes import device_bp
# from .alert_routes import alert_bp