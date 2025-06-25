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
    
    # ==================== CONFIGURATION REDIS ====================
    # ✅ NOUVEAU : Configuration Redis simple et efficace
    REDIS_URL = os.getenv('REDIS_URL')
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    # Configuration Redis avancée
    REDIS_SOCKET_TIMEOUT = int(os.getenv('REDIS_SOCKET_TIMEOUT', 5))
    REDIS_SOCKET_CONNECT_TIMEOUT = int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', 5))
    REDIS_HEALTH_CHECK_INTERVAL = int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', 30))
    
    # TTL par défaut pour différents types de cache (en secondes)
    REDIS_DEFAULT_TTL = {
        'device_status': 30,        # Status des appareils IoT
        'user_session': 3600,       # Sessions utilisateur (1h)
        'auth_tokens': 86400,       # Tokens d'activation (24h)
        'device_data': 300,         # Données device historiques (5min)
        'api_cache': 60,            # Cache API générique (1min)
        'alerts': 1800             # Cache des alertes (30min)
    }
    
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
    
    # ✅ NOUVEAU : Méthodes Redis
    @staticmethod
    def is_redis_configured():
        """Vérifie si Redis est configuré"""
        redis_url = os.getenv('REDIS_URL')
        redis_password = os.getenv('REDIS_PASSWORD')
        
        # Redis configuré si on a une URL complète OU un mot de passe
        return redis_url is not None or redis_password is not None
    
    @staticmethod
    def get_redis_url():
        """Construire l'URL Redis complète avec authentification"""
        redis_url = os.getenv('REDIS_URL')
        
        # Si URL complète fournie, l'utiliser directement
        if redis_url:
            return redis_url
        
        # Sinon, construire depuis les composants
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', 6379))
        password = os.getenv('REDIS_PASSWORD')
        db = int(os.getenv('REDIS_DB', 0))
        
        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        else:
            return f"redis://{host}:{port}/{db}"
    
    @staticmethod
    def get_redis_config():
        """Retourner la configuration Redis complète pour le client"""
        return {
            'url': Config.get_redis_url(),
            'decode_responses': True,
            'socket_timeout': Config.REDIS_SOCKET_TIMEOUT,
            'socket_connect_timeout': Config.REDIS_SOCKET_CONNECT_TIMEOUT,
            'health_check_interval': Config.REDIS_HEALTH_CHECK_INTERVAL,
            'retry_on_timeout': True,
            'retry_on_error': [ConnectionError, TimeoutError]
        }
    
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
        
        # ✅ NOUVEAU : Validation Redis
        if Config.is_redis_configured():
            print(f"✅ Configuration Redis détectée")
            redis_url = Config.get_redis_url()
            # Masquer le mot de passe dans les logs
            safe_url = redis_url.split('@')[1] if '@' in redis_url else redis_url
            print(f"   Redis URL: {safe_url}")
        else:
            print(f"ℹ️  Redis non configuré - l'application fonctionnera sans cache")
        
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
    
    # ✅ NOUVEAU : Redis en développement
    # TTL plus courts pour le développement (refresh plus rapide)
    REDIS_DEFAULT_TTL = {
        'device_status': 15,        # 15 secondes au lieu de 30
        'user_session': 1800,       # 30 minutes au lieu d'1h
        'auth_tokens': 3600,        # 1h au lieu de 24h
        'device_data': 120,         # 2min au lieu de 5min
        'api_cache': 30,            # 30s au lieu de 1min
        'alerts': 300               # 5min au lieu de 30min
    }

class ProductionConfig(Config):
    """Configuration production"""
    DEBUG = False
    
    # En production, sécurité renforcée
    MAIL_SUPPRESS_SEND = False
    MAIL_DEBUG = False
    
    # Limites plus strictes en production
    MAIL_MAX_EMAILS = int(os.getenv('MAIL_MAX_EMAILS', 50))
    
    # ✅ NOUVEAU : Redis en production
    # TTL plus longs pour la production (moins de charge)
    REDIS_DEFAULT_TTL = {
        'device_status': 60,        # 1 minute
        'user_session': 7200,       # 2 heures
        'auth_tokens': 86400,       # 24 heures
        'device_data': 600,         # 10 minutes
        'api_cache': 300,           # 5 minutes
        'alerts': 3600              # 1 heure
    }
    
    # Configuration Redis production plus robuste
    REDIS_SOCKET_TIMEOUT = 10
    REDIS_SOCKET_CONNECT_TIMEOUT = 10
    REDIS_HEALTH_CHECK_INTERVAL = 60
    
    @staticmethod
    def validate_config():
        """Validation plus stricte en production"""
        Config.validate_config()
        
        # En production, la config mail est obligatoire
        if not Config.is_mail_configured():
            raise ValueError("Configuration mail complète requise en production!")
        
        # ✅ NOUVEAU : Redis recommandé en production
        if not Config.is_redis_configured():
            print("⚠️  Redis non configuré - performances sous-optimales en production")
        
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
    
    # ✅ NOUVEAU : Redis pour les tests
    # Utiliser une base Redis différente pour les tests
    REDIS_DB = 1  # Base 1 au lieu de 0
    
    # TTL très courts pour les tests
    REDIS_DEFAULT_TTL = {
        'device_status': 5,         # 5 secondes
        'user_session': 300,        # 5 minutes
        'auth_tokens': 600,         # 10 minutes
        'device_data': 30,          # 30 secondes
        'api_cache': 10,            # 10 secondes
        'alerts': 60                # 1 minute
    }

# Factory pour récupérer la config
def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    return configs.get(env, DevelopmentConfig)