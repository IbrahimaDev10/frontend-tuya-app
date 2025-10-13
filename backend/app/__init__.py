from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_socketio import SocketIO
import os
import time
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import redis
from redis.connection import ConnectionPool

# Extensions Flask
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()
socketio = SocketIO()

# Instance globale du planificateur
scheduler = BackgroundScheduler(daemon=True)

# Variables Redis optimisées
redis_pool = None
redis_client = None

def create_app():
    """Factory pour créer l'application Flask - Version optimisée Redis"""

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
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['https://sertecingenierie.vercel.app'] ))

    # Initialize JWT avec tes paramètres existants
    jwt.init_app(app)

    # Initialize nouvelles extensions (base de données)
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize Flask-Mail
    mail.init_app(app)

    # Le paramètre async_mode='threading' est souvent plus compatible avec les déploiements standards.
    # 'eventlet' ou 'gevent' sont plus performants mais nécessitent une configuration serveur spécifique.
    socketio.init_app(app, async_mode='eventlet', cors_allowed_origins="*")

    # Initialize Redis ultra-optimisé
    setup_redis(app)

    # Configure and start the scheduler
    setup_scheduler_with_all_jobs(app)

    # Ne démarrer Pulsar QUE si pas en mode migration
    if not os.environ.get("DISABLE_PULSAR"):
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
            setup_pulsar_listener(app)
        else:
            app.logger.info("⏭️ [PULSAR] Mode debug - Pulsar non démarré")
    else:
        app.logger.info("⏭️ [PULSAR] Désactivé (mode migration)")

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

    try:
        from . import socket_events
        app.logger.info("✅ Événements WebSocket importés.")
    except ImportError as e:
        app.logger.warning(f"⚠️ Fichier socket_events.py non trouvé ou erreur d'import: {e}")    

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
                # db.create_all()
                app.logger.info("✅ Tables de base de données créées ET GÉRÉES PAR FLASK-MIGRATE")
            except Exception as e:
                app.logger.error(f"⚠️ Erreur création tables: {e}")

    app.logger.info("🚀 Application SERTEC IoT initialisée avec succès (avec support WebSocket)")
    return app

def setup_pulsar_listener(app): # Renommez la fonction pour plus de clarté
    """
    Initialise et démarre le listener PULSAR Tuya en arrière-plan.
    """
    app.logger.info("🚀 Initialisation du service temps réel (PULSAR)...")
    try:
        # Importer le nouveau listener
        from app.services.pulsar_listener import TuyaPulsarListener 
        import os

        # Récupérer vos identifiants depuis les variables d'environnement
        ACCESS_ID = os.getenv('ACCESS_ID')
        ACCESS_KEY = os.getenv('ACCESS_KEY')
        
        # Définir les constantes pour Pulsar
        PULSAR_SERVER_URL = "pulsar+ssl://mqe.tuyaeu.com:7285" # Pour l'Europe
        MQ_ENV = "event" # "event" pour la production

        # Créer et démarrer le listener
        listener = TuyaPulsarListener(ACCESS_ID, ACCESS_KEY, PULSAR_SERVER_URL, MQ_ENV, app)
        listener.start()
        
        app.logger.info("✅ Service temps réel (PULSAR) démarré et à l'écoute en arrière-plan.")

    except Exception as e:
        app.logger.critical(f"❌ [PULSAR] Erreur majeure lors du démarrage du service temps réel: {e}")

        
def setup_scheduler_with_all_jobs(app):
    """
    [HARMONISÉ] Configure et démarre le planificateur avec des tâches optimisées
    pour la performance et l'économie d'appels API.
    """
    global scheduler

    if scheduler.running:
        app.logger.info("✅ [SCHEDULER] Planificateur déjà en cours d'exécution.")
        return
    
    # Nettoyer les jobs existants avant d'en ajouter de nouveaux
    scheduler.remove_all_jobs()

    # --- Tâche 1 : Exécution des actions programmées (ON/OFF) ---
    def execute_scheduled_actions_job():
        with app.app_context():
            app.logger.info("⏰ [SCHEDULER] Vérification des actions programmées...")
            try:
                from app.services.schedule_executor_service import ScheduleExecutorService
                executor = ScheduleExecutorService() 
                result = executor.execute_pending_actions_optimized()
                if result.get("executed_count", 0) > 0:
                    app.logger.info(f"  -> {result['executed_count']} action(s) programmée(s) exécutée(s).")
            except Exception as e:
                app.logger.error(f"❌ [SCHEDULER] Erreur dans la tâche d'exécution des actions: {e}", exc_info=True)

    # --- Tâche 2 : Synchronisation de la liste des appareils (Online/Offline) ---
    def sync_device_list_job():
        with app.app_context():
            app.logger.info("🔄 [SCHEDULER] Synchronisation de la liste des appareils (online/offline)...")
            try:
                from app.services.device_service import DeviceService
                service = DeviceService()
                result = service.import_tuya_devices(use_cache=False, force_refresh=True, auto_delete_missing=False)
                if result.get("success"):
                    stats = result.get("statistiques", {})
                    app.logger.info(f"  -> Sync liste OK. Nouveaux: {stats.get('nouveaux_appareils', 0)}, Mis à jour: {stats.get('appareils_mis_a_jour', 0)}.")
                else:
                    app.logger.error(f"  -> Échec de la synchronisation de la liste: {result.get('error')}")
            except Exception as e:
                app.logger.error(f"❌ [SCHEDULER] Erreur dans la tâche de synchronisation de la liste: {e}", exc_info=True)

    try:
        # Ajout de la Tâche 1 (fréquente et légère)
        scheduler.add_job(
            func=execute_scheduled_actions_job,
            trigger='interval',
            minutes=1,
            id='execute_scheduled_actions_job',
            name='Exécuter les programmations horaires',
            replace_existing=True
        )

        # Ajout de la Tâche 2 (moins fréquente, un seul appel API)
        scheduler.add_job(
            func=sync_device_list_job,
            trigger='interval',
            minutes=10,
            id='sync_device_list_job',
            name='Synchroniser la liste des appareils (online/offline)',
            replace_existing=True,
            next_run_time=datetime.now() + timedelta(seconds=30)
        )

        scheduler.start()
        app.logger.info("🚀 [SCHEDULER] Planificateur démarré avec des tâches optimisées.")
        app.logger.info("   - Tâche 1: Exécution des programmations (toutes les minutes).")
        app.logger.info("   - Tâche 2: Sync de la liste des appareils (toutes les 10 minutes).")

    except Exception as e:
        app.logger.error(f"❌ [SCHEDULER] Erreur lors du démarrage du planificateur: {e}", exc_info=True)


def setup_redis(app):
    """Setup Redis ultra-optimisé pour performance - VERSION FINALE CORRIGÉE"""
    global redis_client, redis_pool

    try:
        from config.settings import get_config
        config_class = get_config()

        if not config_class.is_redis_configured():
            app.logger.info("ℹ️ Redis non configuré")
            redis_client = None
            return

        app.logger.info("🚀 Initialisation Redis optimisé...")

        redis_config = config_class.get_redis_config_optimized()
        redis_url = redis_config.pop('url')

        redis_pool = ConnectionPool.from_url(
            redis_url,
            max_connections=redis_config.get('max_connections', 15),
            retry_on_timeout=redis_config.get('retry_on_timeout', True),
            socket_connect_timeout=redis_config.get('socket_connect_timeout', 5),
            socket_timeout=redis_config.get('socket_timeout', 10),
            socket_keepalive=redis_config.get('socket_keepalive', True),
            socket_keepalive_options={},
            health_check_interval=redis_config.get('health_check_interval', 30),
            decode_responses=redis_config.get('decode_responses', False)
        )

        redis_client = redis.Redis(connection_pool=redis_pool)

        start_time = time.time()
        redis_client.ping()
        connection_time = (time.time() - start_time) * 1000

        test_key = "perf_test"
        start_time = time.time()
        redis_client.set(test_key, "test", ex=5)
        value = redis_client.get(test_key)
        redis_client.delete(test_key)
        rw_time = (time.time() - start_time) * 1000

        info = redis_client.info('server')
        memory_info = redis_client.info('memory')

        app.logger.info(f"✅ Redis connecté - Performance:")
        app.logger.info(f"   Connexion: {connection_time:.1f}ms")
        app.logger.info(f"   Read/Write: {rw_time:.1f}ms")
        app.logger.info(f"   Pool: {redis_config.get('max_connections', 15)} connexions")
        app.logger.info(f"   Mémoire: {memory_info.get('used_memory_human')}")

        if connection_time > 50:
            app.logger.warning(f"⚠️ Connexion Redis lente ({connection_time:.1f}ms)")
        if rw_time > 10:
            app.logger.warning(f"⚠️ Read/Write Redis lent ({rw_time:.1f}ms)")

    except redis.ConnectionError as e:
        app.logger.warning(f"⚠️ Redis non disponible: {e}")
        app.logger.info("   L'application fonctionnera sans cache Redis")
        redis_client = None
        redis_pool = None

    except redis.AuthenticationError as e:
        app.logger.error(f"❌ Erreur authentification Redis: {e}")
        app.logger.error("   Vérifiez le mot de passe dans REDIS_URL")
        redis_client = None
        redis_pool = None

    except Exception as e:
        app.logger.warning(f"⚠️ Erreur Redis inattendue: {e}")
        app.logger.info("   L'application fonctionnera sans cache Redis")
        redis_client = None
        redis_pool = None

def get_redis():
    """Client Redis optimisé avec pool"""
    return redis_client

def get_redis_pipeline():
    """Pipeline Redis pour opérations batch"""
    if redis_client:
        return redis_client.pipeline()
    return None

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
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/sertec_iot.log'),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(level=logging.DEBUG)

def register_blueprints(app):
    """Enregistrer tous les blueprints"""
    import importlib.util
    import os

    current_file = os.path.abspath(__file__)
    app_dir = os.path.dirname(current_file)
    routes_dir = os.path.join(app_dir, 'routes')

    # 🔐 BLUEPRINT AUTH
    try:
        app.logger.info("🔍 Import du blueprint auth...")
        auth_file_path = os.path.join(routes_dir, 'auth.py')
        if os.path.exists(auth_file_path):
            spec = importlib.util.spec_from_file_location("app.routes.auth", auth_file_path)
            auth_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(auth_module)
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
            spec = importlib.util.spec_from_file_location("app.routes.user_routes", user_routes_file_path)
            user_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(user_module)
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
            spec = importlib.util.spec_from_file_location("app.routes.site_routes", site_routes_file_path)
            site_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(site_module)
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
            spec = importlib.util.spec_from_file_location("app.routes.alert_routes", alert_routes_file_path)
            alert_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(alert_module)
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
            spec = importlib.util.spec_from_file_location("app.routes.device_routes", device_routes_file_path)
            device_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(device_module)
            device_bp = device_module.device_bp
            app.register_blueprint(device_bp)
            app.logger.info("✅ Blueprint devices enregistré sur /api/devices")
        else:
            app.logger.error(f"❌ Fichier device_routes non trouvé: {device_routes_file_path}")
    except Exception as e:
        app.logger.error(f"❌ Erreur import blueprint devices: {e}")

    # 📊 BLUEPRINT EXPORT
    try:
        app.logger.info("Import du blueprint export...")
        
        # Méthode 1 : Import direct (RECOMMANDÉ - plus simple et fiable)
        from app.routes.export_routes import export_bp
        app.register_blueprint(export_bp)
        app.logger.info("Blueprint export enregistré sur /api/export")
        
    except ImportError as e:
        app.logger.error(f"Erreur import blueprint export: {e}")
        app.logger.warning("Le module export_routes.py est manquant ou contient des erreurs")
        
    except Exception as e:
        app.logger.error(f"Erreur inattendue lors de l'enregistrement du blueprint export: {e}")

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

    @app.route('/debug/redis')
    def debug_redis():
        """Route pour vérifier l'état de Redis"""
        try:
            if redis_client is None:
                return {
                    'redis_service': 'not_configured',
                    'message': 'Redis non configuré ou indisponible'
                }

            redis_client.ping()

            info = redis_client.info('server')
            memory_info = redis_client.info('memory')

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
                'test_write_read': test_result == b"debug_value",
                'config_url': app.config.get('REDIS_URL', '').split('@')[1] if '@' in app.config.get('REDIS_URL', '') else 'localhost:6379'
            }

        except Exception as e:
            return {
                'redis_service': 'error',
                'error': str(e)
            }, 500

    @app.route('/debug/redis-performance')
    def debug_redis_performance():
        """Monitoring performance Redis en temps réel"""
        try:
            if redis_client is None:
                return {
                    'status': 'disconnected',
                    'error': 'Redis non disponible'
                }, 500

            start = time.time()
            connected = redis_client.ping()
            ping_time = (time.time() - start) * 1000

            if not connected:
                return {
                    'status': 'disconnected',
                    'ping_ms': None,
                    'error': 'Redis ping failed'
                }, 500

            start = time.time()
            test_data = {'test': True, 'timestamp': time.time()}
            redis_client.set('perf_test_write', str(test_data), ex=10)
            write_time = (time.time() - start) * 1000

            start = time.time()
            read_data = redis_client.get('perf_test_write')
            read_time = (time.time() - start) * 1000

            start = time.time()
            pipe = redis_client.pipeline()
            for i in range(10):
                pipe.set(f'batch_test_{i}', f'value_{i}', ex=10)
            pipe.execute()
            batch_time = (time.time() - start) * 1000

            redis_client.delete('perf_test_write')
            for i in range(10):
                redis_client.delete(f'batch_test_{i}')

            info = redis_client.info()

            return {
                'status': 'connected',
                'performance_tests': {
                    'ping_ms': round(ping_time, 2),
                    'write_ms': round(write_time, 2),
                    'read_ms': round(read_time, 2),
                    'batch_10_items_ms': round(batch_time, 2)
                },
                'system_stats': {
                    'used_memory_human': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients'),
                    'hit_rate': round(
                        info.get('keyspace_hits', 0) /
                        max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100,
                        1
                    )
                },
                'health_check': {
                    'ping': '✅' if ping_time < 10 else '⚠️' if ping_time < 50 else '❌',
                    'write': '✅' if write_time < 5 else '⚠️' if write_time < 20 else '❌',
                    'read': '✅' if read_time < 5 else '⚠️' if read_time < 20 else '❌',
                    'batch': '✅' if batch_time < 20 else '⚠️' if batch_time < 50 else '❌'
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }, 500

    @app.route('/debug/scheduler')
    def debug_scheduler():
        """Route pour vérifier l'état du système de programmation"""
        try:
            try:
                from app.tasks.simple_scheduler import simple_scheduler
                scheduler_status = simple_scheduler.get_status()
                scheduler_available = True
            except ImportError:
                scheduler_status = {"running": False, "error": "Service non disponible"}
                scheduler_available = False

            try:
                from app.services.schedule_executor_service import ScheduleExecutorService
                executor = ScheduleExecutorService()
                health = executor.get_execution_health()
                executor_available = True
            except ImportError:
                health = {"healthy": False, "error": "Service non disponible"}
                executor_available = False

            try:
                from app.models.scheduled_action import ScheduledAction
                total_actions = ScheduledAction.query.filter_by(actif=True).count()

                upcoming = ScheduledAction.query.filter(
                    ScheduledAction.actif == True,
                    ScheduledAction.prochaine_execution.isnot(None)
                ).order_by(ScheduledAction.prochaine_execution).limit(5).all()

                next_actions = []
                for action in upcoming:
                    from app.models.device import Device
                    device = Device.query.get(action.appareil_id)
                    next_actions.append({
                        "device_name": device.nom_appareil if device else "Inconnu",
                        "action_type": action.action_type,
                        "scheduled_time": action.prochaine_execution.isoformat() if action.prochaine_execution else None,
                        "nom_action": action.nom_action
                    })

                db_stats = {
                    "total_active_actions": total_actions,
                    "next_actions": next_actions
                }

            except Exception as e:
                db_stats = {"error": str(e)}

            return {
                'scheduler_service': 'available' if scheduler_available else 'not_available',
                'scheduler_status': scheduler_status,
                'executor_service': 'available' if executor_available else 'not_available',
                'execution_health': health,
                'database_stats': db_stats,
                'system_status': 'healthy' if (scheduler_available and executor_available and health.get('healthy')) else 'degraded'
            }

        except Exception as e:
            return {
                'scheduler_service': 'error',
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
        mail_status = 'configured' if app.config.get('MAIL_USERNAME') else 'not_configured'
        redis_status = 'connected' if is_redis_available() else 'not_available'

        scheduler_status = 'not_available'
        try:
            from app.tasks.simple_scheduler import simple_scheduler
            if simple_scheduler.is_running():
                scheduler_status = 'running'
            else:
                scheduler_status = 'stopped'
        except ImportError:
            scheduler_status = 'not_configured'
        except Exception:
            scheduler_status = 'error'

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
                'redis': redis_status,
                'scheduler': scheduler_status
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
                'redis': '/debug/redis',
                'redis_performance': '/debug/redis-performance',
                'scheduler': '/debug/scheduler',
                'scheduler_execute': '/debug/scheduler/execute-now',
                'scheduler_control': '/debug/scheduler/control/{action}'
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
