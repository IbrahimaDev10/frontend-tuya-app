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
    
    # JWT - Configuration existante
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=20)
    
    # Base de données MySQL
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or \
        'mysql+pymysql://root:password@localhost:3306/sertec_iot'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # CORS (pour React)
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
    
    # Tuya Configuration - Settings existants
    TUYA_ACCESS_ID = os.getenv('ACCESS_ID')
    TUYA_ACCESS_KEY = os.getenv('ACCESS_KEY')
    TUYA_ENDPOINT = 'https://openapi.tuyaeu.com'
    TUYA_USERNAME = os.getenv('USERNAME')
    TUYA_PASSWORD = os.getenv('PASSWORD')
    TUYA_COUNTRY_CODE = os.getenv('COUNTRY_CODE', '221')
    
    # ==================== CONFIGURATION MAIL ====================
    # Flask-Mail Settings
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Configuration avancée pour les emails
    MAIL_MAX_EMAILS = int(os.getenv('MAIL_MAX_EMAILS', 10))  # Limite par connexion
    MAIL_SUPPRESS_SEND = os.getenv('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'  # Pour les tests
    MAIL_ASCII_ATTACHMENTS = False
    
    # URLs pour les templates d'emails
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
    
    # Configuration des notifications par email
    EMAIL_NOTIFICATIONS = {
        'welcome': True,
        'device_alerts': True,
        'daily_reports': True,
        'maintenance': True,
        'security': True
    }
    
    # Fréquence des rapports automatiques
    DAILY_REPORT_TIME = os.getenv('DAILY_REPORT_TIME', '08:00')  # Format HH:MM
    WEEKLY_REPORT_DAY = int(os.getenv('WEEKLY_REPORT_DAY', 1))  # 1=Lundi
    
    @staticmethod
    def validate_config():
        """Valide que toutes les variables requises sont présentes"""
        required_vars = [
            'JWT_SECRET_KEY', 'ACCESS_ID', 'ACCESS_KEY', 
            'USERNAME', 'PASSWORD'
        ]
        
        # Variables mail recommandées (pas obligatoires en dev)
        mail_vars = [
            'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER'
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        missing_mail = [var for var in mail_vars if not os.getenv(var)]
        
        if missing:
            raise ValueError(f"Variables d'environnement manquantes: {missing}")
        
        if missing_mail:
            print(f"⚠️  Variables mail manquantes (optionnelles): {missing_mail}")
            print("   Les fonctionnalités email seront désactivées.")
        
        return True
    
    @staticmethod
    def is_mail_configured():
        """Vérifie si la configuration mail est complète"""
        mail_vars = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER']
        return all(os.getenv(var) for var in mail_vars)

class DevelopmentConfig(Config):
    """Configuration développement"""
    DEBUG = True
    
    # En développement, on peut désactiver l'envoi réel d'emails
    MAIL_SUPPRESS_SEND = os.getenv('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'
    
    # Logs plus détaillés en dev
    MAIL_DEBUG = True

class ProductionConfig(Config):
    """Configuration production"""
    DEBUG = False
    
    # En production, sécurité renforcée
    MAIL_SUPPRESS_SEND = False
    MAIL_DEBUG = False
    
    # Limites plus strictes en production
    MAIL_MAX_EMAILS = int(os.getenv('MAIL_MAX_EMAILS', 50))
    
    @staticmethod
    def validate_config():
        """Validation plus stricte en production"""
        Config.validate_config()
        
        # En production, la config mail est obligatoire
        if not Config.is_mail_configured():
            raise ValueError("Configuration mail complète requise en production!")
        
        return True

class TestingConfig(Config):
    """Configuration pour les tests"""
    TESTING = True
    DEBUG = True
    
    # Base de données de test
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Désactiver l'envoi d'emails pendant les tests
    MAIL_SUPPRESS_SEND = True
    
    # JWT plus court pour les tests
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)

# Factory pour récupérer la config
def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    return configs.get(env, DevelopmentConfig)