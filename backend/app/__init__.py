from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .config import Config
from .routes import api

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configuration
    app.config.from_object(Config)

    # Initialize JWT
    jwt = JWTManager(app)

    # Register blueprints
    app.register_blueprint(api)

    return app