from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail  
import os
import time
import logging

# ✅ NOUVEAU : Import Redis optimisé
import redis
from redis.connection import ConnectionPool

# Extensions Flask
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()

# ✅ NOUVEAU : Variables Redis optimisées
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
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['http://localhost:5173']))
    
    # Initialize JWT avec tes paramètres existants
    jwt.init_app(app)
    
    # Initialize nouvelles extensions (base de données)
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize Flask-Mail
    mail.init_app(app)
    
    # ✅ NOUVEAU : Initialize Redis ultra-optimisé
    setup_redis(app)
    
    # ✅ NOUVEAU : Initialize le système de programmation horaire
    setup_schedule_system(app)


    # ✅ NOUVEAU : Initialize le service de synchronisation temps réel
    # setup_real_time_sync(app)
    
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
        
        # ✅ CONFIGURATION FINALE CORRIGÉE
        redis_config = config_class.get_redis_config_optimized()
        redis_url = redis_config.pop('url')
        
        # ✅ CRÉER POOL AVEC PARAMÈTRES VALIDES SEULEMENT - VERSION FINALE
        redis_pool = ConnectionPool.from_url(
            redis_url,
            max_connections=redis_config.get('max_connections', 15),
            retry_on_timeout=redis_config.get('retry_on_timeout', True),
            socket_connect_timeout=redis_config.get('socket_connect_timeout', 5),
            socket_timeout=redis_config.get('socket_timeout', 5),
            socket_keepalive=redis_config.get('socket_keepalive', True),
            socket_keepalive_options={},
            health_check_interval=redis_config.get('health_check_interval', 30),
            decode_responses=redis_config.get('decode_responses', False)
        )
        
        # Client Redis avec pool
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        # Test connexion rapide
        start_time = time.time()
        redis_client.ping()
        connection_time = (time.time() - start_time) * 1000  # en ms
        
        # Test performance read/write
        test_key = "perf_test"
        start_time = time.time()
        redis_client.set(test_key, "test", ex=5)
        value = redis_client.get(test_key)
        redis_client.delete(test_key)
        rw_time = (time.time() - start_time) * 1000  # en ms
        
        # Infos performance
        info = redis_client.info('server')
        memory_info = redis_client.info('memory')
        
        app.logger.info(f"✅ Redis connecté - Performance:")
        app.logger.info(f"   Connexion: {connection_time:.1f}ms")
        app.logger.info(f"   Read/Write: {rw_time:.1f}ms")
        app.logger.info(f"   Pool: {redis_config.get('max_connections', 15)} connexions")
        app.logger.info(f"   Mémoire: {memory_info.get('used_memory_human')}")
        
        # Warning si lent
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

def setup_schedule_system(app):
    """
    ✅ VERSION CORRIGÉE : Pas de routes dupliquées
    Compatible Flask 2.3+ avec démarrage automatique garanti
    """
    try:
        app.logger.info("🕐 Initialisation du système de programmation horaire...")
        
        # Vérifier que les modèles nécessaires existent
        try:
            from app.models.scheduled_action import ScheduledAction
            from app.models.device import Device
            app.logger.info("✅ Modèles ScheduledAction et Device disponibles")
        except ImportError as e:
            app.logger.warning(f"⚠️ Modèles programmation non disponibles: {e}")
            return
        
        # ✅ VARIABLE GLOBALE pour s'assurer du démarrage unique
        scheduler_started = False
        
        def start_scheduler_once():
            """Fonction pour démarrer le scheduler une seule fois"""
            nonlocal scheduler_started
            
            if scheduler_started:
                return
            
            try:
                # Import et démarrage du scheduler simple
                from app.tasks.simple_scheduler import simple_scheduler
                
                # ✅ CORRECTION : Passer l'app Flask au scheduler
                simple_scheduler.set_app(app)
                
                # ✅ CORRECTION : Utiliser l'attribut, pas la méthode
                if not simple_scheduler.is_running:
                    simple_scheduler.start()
                    app.logger.info("🚀 Scheduler automatique démarré avec succès")
                else:
                    app.logger.info("✅ Scheduler déjà en cours d'exécution")
                
                scheduler_started = True
                
                # Test de santé initial
                try:
                    from app.services.schedule_executor_service import ScheduleExecutorService
                    executor = ScheduleExecutorService()
                    health = executor.get_execution_health()
                    
                    if health.get('healthy'):
                        stats = health.get('stats', {})
                        app.logger.info(f"✅ Système programmation sain: {stats.get('total_active_actions', 0)} actions actives")
                    else:
                        app.logger.warning(f"⚠️ Système programmation dégradé: {health.get('error', 'Raison inconnue')}")
                except ImportError:
                    app.logger.info("✅ Scheduler démarré (service executor non disponible)")
                    
            except ImportError as e:
                app.logger.warning(f"⚠️ Services programmation non disponibles: {e}")
                scheduler_started = True  # Marquer comme tenté
            except Exception as e:
                app.logger.error(f"❌ Erreur démarrage système programmation: {e}")
                scheduler_started = True  # Marquer comme tenté
        
        # ✅ DÉMARRAGE AUTOMATIQUE à la première requête
        @app.before_request
        def auto_start_scheduler():
            """Démarrer le scheduler avant la première requête"""
            start_scheduler_once()
        
        # ✅ COMMANDES CLI SEULEMENT (pas de routes ici)
        @app.cli.command()
        def start_scheduler():
            """Commande CLI pour démarrer le scheduler manuellement"""
            try:
                from app.tasks.simple_scheduler import simple_scheduler
                
                if not simple_scheduler.is_running():
                    simple_scheduler.start()
                    print("🚀 Scheduler démarré via CLI")
                else:
                    print("✅ Scheduler déjà en cours d'exécution")
                    
            except ImportError as e:
                print(f"⚠️ Services programmation non disponibles: {e}")
            except Exception as e:
                print(f"❌ Erreur démarrage scheduler: {e}")
        
        @app.cli.command()
        def stop_scheduler():
            """Commande CLI pour arrêter le scheduler"""
            try:
                from app.tasks.simple_scheduler import simple_scheduler
                simple_scheduler.stop()
                print("🛑 Scheduler arrêté")
            except Exception as e:
                print(f"❌ Erreur arrêt scheduler: {e}")
        
        # ✅ Hook pour arrêt propre
        @app.teardown_appcontext
        def cleanup_schedule_system(exception):
            """Nettoyage lors de l'arrêt du contexte"""
            if exception:
                app.logger.error(f"Erreur context avec programmation: {exception}")
        
        app.logger.info("✅ Système de programmation horaire configuré avec démarrage automatique")
        app.logger.info("   📋 Le scheduler se lancera automatiquement à la première requête")
        app.logger.info("   🎛️ Commandes CLI: flask start-scheduler / flask stop-scheduler")
        
    except Exception as e:
        app.logger.error(f"❌ Erreur configuration système programmation: {e}")


# def setup_real_time_sync(app):
#     """Setup du service de synchronisation temps réel"""
#     try:
#         app.logger.info("🔄 Initialisation du service de synchronisation temps réel...")
        
#         # Variable globale pour le service
#         app.device_service = None
        
#         def start_sync_service():
#             """Démarrer le service de synchronisation"""
#             try:
#                 from app.services.device_service import DeviceService
                
#                 # Créer le service
#                 app.device_service = DeviceService()
                
#                 # Démarrer la synchronisation automatique
#                 result = app.device_service.start_real_time_sync()
                
#                 if result.get('success'):
#                     app.logger.info("✅ Synchronisation temps réel démarrée automatiquement")
#                 else:
#                     app.logger.error(f"❌ Erreur sync temps réel: {result.get('error')}")
                    
#             except Exception as e:
#                 app.logger.error(f"❌ Erreur démarrage sync service: {e}")
        
#         # Démarrer à la première requête
#         @app.before_request
#         def auto_start_sync():
#             if not hasattr(app, 'sync_started'):
#                 start_sync_service()
#                 app.sync_started = True
        
#         # Arrêt propre
#         @app.teardown_appcontext
#         def cleanup_sync_service(exception):
#             if hasattr(app, 'device_service') and app.device_service:
#                 try:
#                     app.device_service.stop_real_time_sync()
#                 except:
#                     pass
        
#         app.logger.info("✅ Service de synchronisation temps réel configuré")
        
#     except Exception as e:
#         app.logger.error(f"❌ Erreur configuration sync temps réel: {e}")

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
    
    # ✅ NOUVEAU : Route de debug Redis avec tests performance
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
    
    # ✅ NOUVEAU : Route monitoring performance Redis temps réel
    @app.route('/debug/redis-performance')
    def debug_redis_performance():
        """Monitoring performance Redis en temps réel"""
        try:
            if redis_client is None:
                return {
                    'status': 'disconnected',
                    'error': 'Redis non disponible'
                }, 500
            
            # Tests performance
            # Test 1: Ping
            start = time.time()
            connected = redis_client.ping()
            ping_time = (time.time() - start) * 1000
            
            if not connected:
                return {
                    'status': 'disconnected',
                    'ping_ms': None,
                    'error': 'Redis ping failed'
                }, 500
            
            # Test 2: Write performance
            start = time.time()
            test_data = {'test': True, 'timestamp': time.time()}
            redis_client.set('perf_test_write', str(test_data), ex=10)
            write_time = (time.time() - start) * 1000
            
            # Test 3: Read performance
            start = time.time()
            read_data = redis_client.get('perf_test_write')
            read_time = (time.time() - start) * 1000
            
            # Test 4: Batch performance
            start = time.time()
            pipe = redis_client.pipeline()
            for i in range(10):
                pipe.set(f'batch_test_{i}', f'value_{i}', ex=10)
            pipe.execute()
            batch_time = (time.time() - start) * 1000
            
            # Nettoyage
            redis_client.delete('perf_test_write')
            for i in range(10):
                redis_client.delete(f'batch_test_{i}')
            
            # Stats système
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
    
    # ✅ NOUVEAU : Route de debug du système de programmation
    @app.route('/debug/scheduler')
    def debug_scheduler():
        """Route pour vérifier l'état du système de programmation"""
        try:
            # Vérifier si le scheduler simple fonctionne
            try:
                from app.tasks.simple_scheduler import simple_scheduler
                scheduler_status = simple_scheduler.get_status()
                scheduler_available = True
            except ImportError:
                scheduler_status = {"running": False, "error": "Service non disponible"}
                scheduler_available = False
            
            # Vérifier le service d'exécution
            try:
                from app.services.schedule_executor_service import ScheduleExecutorService
                executor = ScheduleExecutorService()
                health = executor.get_execution_health()
                executor_available = True
            except ImportError:
                health = {"healthy": False, "error": "Service non disponible"}
                executor_available = False
            
            # Statistiques des actions programmées
            try:
                from app.models.scheduled_action import ScheduledAction
                total_actions = ScheduledAction.query.filter_by(actif=True).count()
                
                # Prochaines actions (5 prochaines)
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
    
    # ✅ NOUVEAU : Route pour déclencher manuellement l'exécution
    @app.route('/debug/scheduler/execute-now')
    def debug_execute_scheduler():
        """Déclencher manuellement l'exécution des actions programmées"""
        try:
            from app.services.schedule_executor_service import ScheduleExecutorService
            
            executor = ScheduleExecutorService()
            result = executor.execute_pending_actions_optimized()
            
            return {
                'execution_triggered': True,
                'result': result,
                'timestamp': result.get('execution_timestamp', 'N/A')
            }
            
        except ImportError:
            return {
                'execution_triggered': False,
                'error': 'Service d\'exécution non disponible'
            }, 500
        except Exception as e:
            return {
                'execution_triggered': False,
                'error': str(e)
            }, 500
    
    # ✅ NOUVEAU : Route pour contrôler le scheduler
    @app.route('/debug/scheduler/control/<action>')
    def debug_control_scheduler(action):
        """Contrôler le scheduler (start/stop/restart)"""
        try:
            from app.tasks.simple_scheduler import simple_scheduler
            
            if action == 'start':
                if not simple_scheduler.is_running():
                    simple_scheduler.start()
                    return {'action': 'start', 'status': 'success', 'message': 'Scheduler démarré'}
                else:
                    return {'action': 'start', 'status': 'already_running', 'message': 'Scheduler déjà actif'}
            
            elif action == 'stop':
                if simple_scheduler.is_running():
                    simple_scheduler.stop()
                    return {'action': 'stop', 'status': 'success', 'message': 'Scheduler arrêté'}
                else:
                    return {'action': 'stop', 'status': 'already_stopped', 'message': 'Scheduler déjà arrêté'}
            
            elif action == 'restart':
                simple_scheduler.stop()
                simple_scheduler.start()
                return {'action': 'restart', 'status': 'success', 'message': 'Scheduler redémarré'}
            
            elif action == 'status':
                status = simple_scheduler.get_status()
                return {'action': 'status', 'scheduler_status': status}
            
            else:
                return {'error': f'Action inconnue: {action}. Utilisez start/stop/restart/status'}, 400
                
        except ImportError:
            return {'error': 'Service scheduler non disponible'}, 500
        except Exception as e:
            return {'error': str(e)}, 500
    
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


    # ✅ NOUVEAU : Routes de debug pour la synchronisation
    # @app.route('/debug/sync')
    # def debug_sync():
    #     """Route pour vérifier l'état de la synchronisation"""
    #     try:
    #         if hasattr(app, 'device_service') and app.device_service:
    #             status = app.device_service.get_sync_status()
    #             return {
    #                 'sync_service': 'available',
    #                 'status': status,
    #                 'timestamp': datetime.utcnow().isoformat()
    #             }
    #         else:
    #             return {
    #                 'sync_service': 'not_initialized',
    #                 'message': 'Service de synchronisation non initialisé'
    #             }
    #     except Exception as e:
    #         return {
    #             'sync_service': 'error',
    #             'error': str(e)
    #         }, 500
    
    # @app.route('/debug/sync/force')
    # def debug_force_sync():
    #     """Forcer une synchronisation immédiate"""
    #     try:
    #         if hasattr(app, 'device_service') and app.device_service:
    #             result = app.device_service.force_sync_now()
    #             return {
    #                 'sync_forced': True,
    #                 'result': result,
    #                 'timestamp': datetime.utcnow().isoformat()
    #             }
    #         else:
    #             return {
    #                 'sync_forced': False,
    #                 'error': 'Service non initialisé'
    #             }, 500
    #     except Exception as e:
    #         return {
    #             'sync_forced': False,
    #             'error': str(e)
    #         }, 500
    
    # @app.route('/debug/sync/control/<action>')
    # def debug_control_sync(action):
    #     """Contrôler la synchronisation (start/stop/restart)"""
    #     try:
    #         if not hasattr(app, 'device_service') or not app.device_service:
    #             return {
    #                 'error': 'Service de synchronisation non initialisé'
    #             }, 500
            
    #         if action == 'start':
    #             result = app.device_service.start_real_time_sync()
    #             return {'action': 'start', 'result': result}
            
    #         elif action == 'stop':
    #             result = app.device_service.stop_real_time_sync()
    #             return {'action': 'stop', 'result': result}
            
    #         elif action == 'restart':
    #             stop_result = app.device_service.stop_real_time_sync()
    #             start_result = app.device_service.start_real_time_sync()
    #             return {
    #                 'action': 'restart',
    #                 'stop_result': stop_result,
    #                 'start_result': start_result
    #             }
            
    #         elif action == 'status':
    #             status = app.device_service.get_sync_status()
    #             return {'action': 'status', 'status': status}
            
    #         else:
    #             return {
    #                 'error': f'Action inconnue: {action}. Utilisez start/stop/restart/status'
    #             }, 400
                
    #     except Exception as e:
    #         return {'error': str(e)}, 500
    
    @app.route('/certif')
    def health_check():
        """Route de santé pour vérifier que l'API fonctionne"""
        # Vérifier le statut des services
        mail_status = 'configured' if app.config.get('MAIL_USERNAME') else 'not_configured'
        redis_status = 'connected' if is_redis_available() else 'not_available'
        
        # ✅ NOUVEAU : Vérifier le statut du scheduler
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
        
        # ✅ NOUVEAU : Vérifier le statut de la synchronisation temps réel
        sync_status = 'not_available'
        try:
            if hasattr(app, 'device_service') and app.device_service:
                sync_status_info = app.device_service.get_sync_status()
                if sync_status_info.get('sync_active'):
                    service_status = sync_status_info.get('service_status', {})
                    if service_status.get('is_running'):
                        sync_status = 'running'
                    else:
                        sync_status = 'stopped'
                else:
                    sync_status = 'inactive'
            else:
                sync_status = 'not_initialized'
        except ImportError:
            sync_status = 'not_configured'
        except Exception:
            sync_status = 'error'
        
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
                'scheduler': scheduler_status,
                # 'sync': sync_status  # ✅ NOUVEAU
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
                'scheduler': '/debug/scheduler',  # ✅ NOUVEAU
                'scheduler_execute': '/debug/scheduler/execute-now',  # ✅ NOUVEAU
                'scheduler_control': '/debug/scheduler/control/{action}'  # ✅ NOUVEAU
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