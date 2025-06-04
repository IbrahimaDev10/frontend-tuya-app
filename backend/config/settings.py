from datetime import timedelta
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class Config:
    """Configuration de base"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-secret-key-changez-moi'
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JWT - Gardons ta configuration existante
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=20)  # Ton setting existant
    
    # Base de données MySQL (ajout)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or \
        'mysql+pymysql://root:password@localhost:3306/sertec_iot'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # CORS (pour React)
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')

    
    # Tuya Configuration - Tes settings existants
    TUYA_ACCESS_ID = os.getenv('ACCESS_ID')
    TUYA_ACCESS_KEY = os.getenv('ACCESS_KEY')
    TUYA_ENDPOINT = 'https://openapi.tuyaeu.com'
    
    # Ajouts pour ton projet
    TUYA_USERNAME = os.getenv('USERNAME')
    TUYA_PASSWORD = os.getenv('PASSWORD')
    TUYA_COUNTRY_CODE = os.getenv('COUNTRY_CODE', '221')
    
    @staticmethod
    def validate_config():
        """Valide que toutes les variables requises sont présentes"""
        required_vars = [
            'JWT_SECRET_KEY', 'ACCESS_ID', 'ACCESS_KEY', 
            'USERNAME', 'PASSWORD'
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Variables d'environnement manquantes: {missing}")
        
        return True

class DevelopmentConfig(Config):
    """Configuration développement"""
    DEBUG = True

class ProductionConfig(Config):
    """Configuration production"""
    DEBUG = False

# Factory pour récupérer la config
def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig
    }
    
    return configs.get(env, DevelopmentConfig)