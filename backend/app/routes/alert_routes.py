# app/routes/alert_routes.py - VERSION FINALE CORRIGÉE
# Routes pour consultation et gestion des alertes (créées automatiquement)

from flask import Blueprint, request, jsonify
from app.models.device import Device
from app.models.alert import Alert
from datetime import datetime, timedelta
import logging
from functools import wraps  # ✅ AJOUT CRITIQUE

# Créer le blueprint
alert_bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')

# ✅ FONCTION POUR RÉCUPÉRER DeviceService À LA DEMANDE
def get_device_service():
    """Récupérer DeviceService à la demande pour éviter imports circulaires"""
    try:
        from app.services.device_service import DeviceService
        # Créer une instance si elle n'existe pas
        if not hasattr(get_device_service, '_instance'):
            get_device_service._instance = DeviceService()
        return get_device_service._instance
    except ImportError:
        logging.warning("⚠️ DeviceService non disponible")
        return None
    except Exception as e:
        logging.error(f"❌ Erreur récupération DeviceService: {e}")
        return None

# Import conditionnel des décorateurs
try:
    from app.decorators import admin_required, login_required, validate_json_data
    logging.info("✅ Décorateurs officiels importés")
except ImportError:
    logging.warning("⚠️ Décorateurs officiels non disponibles - utilisation fallbacks")
    
    # 🔧 DÉCORATEURS DE FALLBACK CORRIGÉS
    def admin_required(f):
        @wraps(f)  # ✅ CRITIQUE : Préserve le nom de fonction
        def admin_wrapper_func(*args, **kwargs):  # ✅ NOM UNIQUE
            # ✅ CORRECTION : Créer MockUser et l'injecter comme premier argument
            class MockUser:
                def __init__(self):
                    self.id = "test_user"
                    self.client_id = None
                def is_superadmin(self):
                    return True
            
            # ✅ PASSER MockUser comme current_user (premier argument)
            return f(MockUser(), *args, **kwargs)
        return admin_wrapper_func
    
    def login_required(f):
        @wraps(f)  # ✅ CRITIQUE : Préserve le nom de fonction
        def login_wrapper_func(*args, **kwargs):  # ✅ NOM UNIQUE
            # ✅ CORRECTION : Créer MockUser et l'injecter comme premier argument
            class MockUser:
                def __init__(self):
                    self.id = "test_user"
                    self.client_id = None
                def is_superadmin(self):
                    return True
            
            # ✅ PASSER MockUser comme current_user (premier argument)
            return f(MockUser(), *args, **kwargs)
        return login_wrapper_func
    
    def validate_json_data(required_fields):
        def decorator(f):
            @wraps(f)  # ✅ CRITIQUE : Préserve le nom de fonction
            def validate_wrapper_func(*args, **kwargs):  # ✅ NOM UNIQUE
                data = request.get_json() or {}
                # ✅ CORRECTION : Passer data comme argument nommé
                return f(*args, data=data, **kwargs)
            return validate_wrapper_func
        return decorator

# =================== ROUTES DE TEST ===================

@alert_bp.route('/test', methods=['GET'])
def test_blueprint():
    """
    🧪 TEST - Vérifier que le blueprint fonctionne
    GET /api/alerts/test
    """
    device_service = get_device_service()
    
    return jsonify({
        'success': True,
        'message': 'Blueprint AlertService fonctionne !',
        'timestamp': datetime.utcnow().isoformat(),
        'blueprint_prefix': '/api/alerts',
        'device_service_status': {
            'available': device_service is not None,
            'has_alert_service': (
                device_service and 
                hasattr(device_service, '_alert_service') and 
                device_service._alert_service is not None
            ) if device_service else False
        }
    }), 200

@alert_bp.route('/test/device-import', methods=['GET'])
def test_device_import():
    """
    🧪 TEST - Vérifier import des modèles
    GET /api/alerts/test/device-import
    """
    try:
        device_service = get_device_service()
        
        # Test import Device
        device_count = Device.query.count()
        
        # Test import Alert
        alert_count = Alert.query.count()
        
        # Sample device
        sample_device = Device.query.first()
        
        return jsonify({
            'success': True,
            'imports': {
                'Device': 'OK',
                'Alert': 'OK'
            },
            'database': {
                'total_devices': device_count,
                'total_alerts': alert_count,
                'sample_device': {
                    'id': sample_device.id if sample_device else None,
                    'nom': sample_device.nom_appareil if sample_device else None,
                    'tuya_id': sample_device.tuya_device_id if sample_device else None
                } if sample_device else None
            },
            'device_service_status': {
                'imported': device_service is not None,
                'has_alert_service': (
                    device_service and 
                    hasattr(device_service, '_alert_service') and 
                    device_service._alert_service is not None
                ) if device_service else False
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'imports': {
                'Device': 'FAILED',
                'Alert': 'FAILED'
            }
        }), 500

# =================== ROUTES DE CONSULTATION ===================

@alert_bp.route('/device/<device_id>', methods=['GET'])
@login_required
def get_device_alerts(current_user, device_id):
    """
    📋 CONSULTER les alertes d'un appareil
    GET /api/alerts/device/{device_id}?hours_back=24&limit=50
    """
    try:
        logging.info(f"🔍 get_device_alerts appelée avec device_id: {device_id}")
        
        # ✅ RECHERCHE FLEXIBLE : par ID ou tuya_device_id
        device = Device.query.get(device_id)
        search_method = "database_id"
        
        if not device:
            device = Device.query.filter_by(tuya_device_id=device_id).first()
            search_method = "tuya_device_id"
        
        if not device:
            logging.warning(f"❌ Device non trouvé: {device_id}")
            return jsonify({
                'error': 'Appareil non trouvé', 
                'searched_id': device_id,
                'tried_methods': ['database_id', 'tuya_device_id']
            }), 404
        
        logging.info(f"✅ Device trouvé via {search_method}: {device.nom_appareil}")
        
        # Vérifier permissions (si méthode disponible)
        if hasattr(device, 'peut_etre_vu_par_utilisateur'):
            try:
                if not device.peut_etre_vu_par_utilisateur(current_user):
                    return jsonify({'error': 'Accès interdit'}), 403
            except Exception as perm_error:
                logging.warning(f"⚠️ Erreur vérification permissions: {perm_error}")
        
        # Paramètres
        hours_back = request.args.get('hours_back', 24, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        # ✅ UTILISER DeviceService À LA DEMANDE
        device_service = get_device_service()
        
        # Utiliser AlertService si disponible
        if device_service and hasattr(device_service, '_alert_service') and device_service._alert_service:
            logging.info("🔧 Utilisation AlertService")
            try:
                result = device_service._alert_service.get_alertes_recentes(
                    device.id, hours_back=hours_back, limit=limit
                )
                # Enrichir avec info device
                if result.get('success'):
                    result['device_info'] = {
                        'id': device.id,
                        'tuya_device_id': device.tuya_device_id,
                        'nom_appareil': device.nom_appareil,
                        'search_method': search_method
                    }
                return jsonify(result), 200 if result.get('success') else 400
            except Exception as alert_service_error:
                logging.error(f"❌ Erreur AlertService: {alert_service_error}")
                # Continue avec fallback
        
        # Fallback direct DB
        logging.info("🗄️ Utilisation fallback DB")
        start_time = datetime.utcnow() - timedelta(hours=hours_back)
        alertes = Alert.query.filter(
            Alert.appareil_id == device.id,
            Alert.date_creation >= start_time
        ).order_by(Alert.date_creation.desc()).limit(limit).all()
        
        alertes_data = []
        for alerte in alertes:
            try:
                if hasattr(alerte, 'to_dict'):
                    alertes_data.append(alerte.to_dict(include_details=True))
                else:
                    # Fallback basique
                    alertes_data.append({
                        'id': alerte.id,
                        'type_alerte': alerte.type_alerte,
                        'gravite': alerte.gravite,
                        'titre': alerte.titre,
                        'message': alerte.message,
                        'date_creation': alerte.date_creation.isoformat() if alerte.date_creation else None
                    })
            except Exception as serialize_error:
                logging.error(f"Erreur sérialisation alerte: {serialize_error}")
                continue
        
        return jsonify({
            'success': True,
            'device_info': {
                'id': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom_appareil': device.nom_appareil,
                'en_ligne': getattr(device, 'en_ligne', False),
                'search_method': search_method
            },
            'period_hours': hours_back,
            'total_alertes': len(alertes_data),
            'alertes': alertes_data,
            'data_source': 'database_fallback'
        }), 200
        
    except Exception as e:
        logging.error(f"❌ Erreur récupération alertes device {device_id}: {e}")
        return jsonify({'error': f'Erreur récupération alertes: {str(e)}'}), 500

@alert_bp.route('/device/<device_id>/stats', methods=['GET'])
@login_required
def get_device_alerts_stats(current_user, device_id):
    """
    📊 STATISTIQUES des alertes d'un appareil
    GET /api/alerts/device/{device_id}/stats?days=7
    """
    try:
        # Recherche flexible device
        device = Device.query.get(device_id)
        if not device:
            device = Device.query.filter_by(tuya_device_id=device_id).first()
        
        if not device:
            return jsonify({'error': 'Appareil non trouvé'}), 404
        
        # Vérifier permissions
        if hasattr(device, 'peut_etre_vu_par_utilisateur'):
            try:
                if not device.peut_etre_vu_par_utilisateur(current_user):
                    return jsonify({'error': 'Accès interdit'}), 403
            except:
                pass
        
        days = request.args.get('days', 7, type=int)
        
        # ✅ UTILISER DeviceService À LA DEMANDE
        device_service = get_device_service()
        
        # Utiliser AlertService
        if device_service and hasattr(device_service, '_alert_service') and device_service._alert_service:
            result = device_service._alert_service.get_statistiques_alertes(device.id, days=days)
            return jsonify(result), 200 if result.get('success') else 400
        
        # Fallback basique
        start_date = datetime.utcnow() - timedelta(days=days)
        alertes = Alert.query.filter(
            Alert.appareil_id == device.id,
            Alert.date_creation >= start_date
        ).all()
        
        # Statistiques basiques
        stats = {
            'total': len(alertes),
            'par_gravite': {'info': 0, 'warning': 0, 'critique': 0},
            'par_statut': {'nouvelle': 0, 'vue': 0, 'resolue': 0}
        }
        
        for alerte in alertes:
            if hasattr(alerte, 'gravite'):
                stats['par_gravite'][alerte.gravite] = stats['par_gravite'].get(alerte.gravite, 0) + 1
            if hasattr(alerte, 'statut'):
                stats['par_statut'][alerte.statut] = stats['par_statut'].get(alerte.statut, 0) + 1
        
        return jsonify({
            'success': True,
            'device_info': {
                'id': device.id,
                'nom_appareil': device.nom_appareil
            },
            'period_days': days,
            'stats': stats,
            'generated_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logging.error(f"Erreur statistiques alertes device {device_id}: {e}")
        return jsonify({'error': f'Erreur statistiques: {str(e)}'}), 500

@alert_bp.route('/device/<device_id>/active', methods=['GET'])
@login_required
def get_device_active_alerts(current_user, device_id):
    """
    🚨 ALERTES ACTIVES (non résolues) d'un appareil
    GET /api/alerts/device/{device_id}/active
    """
    try:
        # Recherche flexible device
        device = Device.query.get(device_id)
        if not device:
            device = Device.query.filter_by(tuya_device_id=device_id).first()
        
        if not device:
            return jsonify({'error': 'Appareil non trouvé'}), 404
        
        # Vérifier permissions
        if hasattr(device, 'peut_etre_vu_par_utilisateur'):
            try:
                if not device.peut_etre_vu_par_utilisateur(current_user):
                    return jsonify({'error': 'Accès interdit'}), 403
            except:
                pass
        
        # ✅ UTILISER DeviceService À LA DEMANDE
        device_service = get_device_service()
        
        # Utiliser AlertService
        if device_service and hasattr(device_service, '_alert_service') and device_service._alert_service:
            result = device_service._alert_service.get_alertes_actives_pour_device(device.id)
            return jsonify(result), 200 if result.get('success') else 400
        
        # Fallback direct
        alertes_actives = Alert.query.filter(
            Alert.appareil_id == device.id,
            Alert.statut.in_(['nouvelle', 'vue'])
        ).order_by(Alert.date_creation.desc()).all()
        
        alertes_data = []
        for alerte in alertes_actives:
            try:
                if hasattr(alerte, 'to_dict'):
                    alertes_data.append(alerte.to_dict(include_details=True))
                else:
                    alertes_data.append({
                        'id': alerte.id,
                        'type_alerte': alerte.type_alerte,
                        'gravite': alerte.gravite,
                        'titre': alerte.titre,
                        'message': alerte.message,
                        'statut': alerte.statut,
                        'date_creation': alerte.date_creation.isoformat() if alerte.date_creation else None
                    })
            except:
                continue
        
        return jsonify({
            'success': True,
            'device_info': {
                'id': device.id,
                'nom_appareil': device.nom_appareil
            },
            'total_actives': len(alertes_data),
            'alertes': alertes_data
        }), 200
        
    except Exception as e:
        logging.error(f"Erreur alertes actives device {device_id}: {e}")
        return jsonify({'error': f'Erreur alertes actives: {str(e)}'}), 500

# =================== ROUTES DE GESTION ===================

@alert_bp.route('/<alert_id>/resolve', methods=['POST'])
@login_required
@validate_json_data([])  # Pas de champs obligatoires
def resolve_alert(current_user, alert_id, data):
    """
    ✅ RÉSOUDRE une alerte
    POST /api/alerts/{alert_id}/resolve
    Body: {"commentaire": "Problème résolu"}
    """
    try:
        # Vérifier que l'alerte existe
        alerte = Alert.query.get(alert_id)
        if not alerte:
            return jsonify({'error': 'Alerte non trouvée'}), 404
        
        # Vérifier permissions sur l'appareil
        device = Device.query.get(alerte.appareil_id)
        if not device:
            return jsonify({'error': 'Appareil associé non trouvé'}), 404
        
        if hasattr(device, 'peut_etre_controle_par_utilisateur'):
            try:
                if not device.peut_etre_controle_par_utilisateur(current_user):
                    return jsonify({'error': 'Accès interdit'}), 403
            except:
                pass
        
        commentaire = data.get('commentaire', '')
        
        # ✅ UTILISER DeviceService À LA DEMANDE
        device_service = get_device_service()
        
        # Utiliser AlertService
        if device_service and hasattr(device_service, '_alert_service') and device_service._alert_service:
            result = device_service._alert_service.resoudre_alerte(
                alert_id, utilisateur_id=current_user.id, commentaire=commentaire
            )
            return jsonify(result), 200 if result.get('success') else 400
        
        # Fallback direct
        if alerte.statut == 'resolue':
            return jsonify({'error': 'Alerte déjà résolue'}), 400
        
        if hasattr(alerte, 'resolve'):
            alerte.resolve(user_id=current_user.id)
        else:
            # Fallback manuel
            alerte.statut = 'resolue'
            alerte.date_resolution = datetime.utcnow()
            if hasattr(alerte, 'resolu_par'):
                alerte.resolu_par = current_user.id
            from app import db
            db.session.add(alerte)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alerte résolue avec succès',
            'alert_id': alert_id,
            'resolved_by': current_user.id,
            'commentaire': commentaire
        }), 200
        
    except Exception as e:
        logging.error(f"Erreur résolution alerte {alert_id}: {e}")
        return jsonify({'error': f'Erreur résolution alerte: {str(e)}'}), 500

@alert_bp.route('/<alert_id>/mark-seen', methods=['POST'])
@login_required
def mark_alert_seen(current_user, alert_id):
    """
    👁️ MARQUER une alerte comme VUE
    POST /api/alerts/{alert_id}/mark-seen
    """
    try:
        alerte = Alert.query.get(alert_id)
        if not alerte:
            return jsonify({'error': 'Alerte non trouvée'}), 404
        
        device = Device.query.get(alerte.appareil_id)
        if not device:
            return jsonify({'error': 'Appareil associé non trouvé'}), 404
        
        if hasattr(device, 'peut_etre_vu_par_utilisateur'):
            try:
                if not device.peut_etre_vu_par_utilisateur(current_user):
                    return jsonify({'error': 'Accès interdit'}), 403
            except:
                pass
        
        # ✅ UTILISER DeviceService À LA DEMANDE
        device_service = get_device_service()
        
        # Utiliser AlertService
        if device_service and hasattr(device_service, '_alert_service') and device_service._alert_service:
            result = device_service._alert_service.marquer_alerte_vue(alert_id, utilisateur_id=current_user.id)
            return jsonify(result), 200 if result.get('success') else 400
        
        # Fallback direct
        if alerte.statut != 'nouvelle':
            return jsonify({'error': f'Alerte déjà {alerte.statut}'}), 400
        
        if hasattr(alerte, 'mark_as_seen'):
            alerte.mark_as_seen()
        else:
            # Fallback manuel
            alerte.statut = 'vue'
            from app import db
            db.session.add(alerte)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alerte marquée comme vue',
            'alert_id': alert_id,
            'marked_by': current_user.id
        }), 200
        
    except Exception as e:
        logging.error(f"Erreur marquage alerte {alert_id}: {e}")
        return jsonify({'error': f'Erreur marquage alerte: {str(e)}'}), 500

# =================== ROUTES D'ANALYSE PONCTUELLE ===================

@alert_bp.route('/analyze-client/<client_id>', methods=['POST'])
@admin_required
@validate_json_data([])
def analyze_client_alerts(current_user, client_id, data):
    """
    🔬 ANALYSE COMPLÈTE d'un client
    POST /api/alerts/analyze-client/{client_id}
    Body: {"use_cache": true}
    """
    try:
        # Vérifier permissions client
        if hasattr(current_user, 'is_superadmin') and hasattr(current_user, 'client_id'):
            try:
                if not current_user.is_superadmin() and current_user.client_id != client_id:
                    return jsonify({'error': 'Accès interdit à ce client'}), 403
            except:
                pass
        
        use_cache = data.get('use_cache', True)
        
        # ✅ UTILISER DeviceService À LA DEMANDE
        device_service = get_device_service()
        
        # Utiliser AlertService pour analyse complète
        if device_service and hasattr(device_service, '_alert_service') and device_service._alert_service:
            result = device_service._alert_service.analyser_client_complet(
                client_id, {'use_cache': use_cache}
            )
            return jsonify(result), 200 if result.get('success') else 400
        
        return jsonify({
            'success': False,
            'error': 'Service d\'analyse non disponible',
            'message': 'AlertService requis pour cette fonctionnalité'
        }), 501
        
    except Exception as e:
        logging.error(f"Erreur analyse client {client_id}: {e}")
        return jsonify({'error': f'Erreur analyse client: {str(e)}'}), 500

@alert_bp.route('/critical', methods=['GET'])
@admin_required
def get_critical_alerts(current_user):
    """
    🚨 ALERTES CRITIQUES système
    GET /api/alerts/critical?hours_back=24
    """
    try:
        hours_back = request.args.get('hours_back', 24, type=int)
        client_filter = None
        
        # Filtrer par client si pas superadmin
        if hasattr(current_user, 'is_superadmin') and hasattr(current_user, 'client_id'):
            try:
                client_filter = None if current_user.is_superadmin() else current_user.client_id
            except:
                pass
        
        # ✅ UTILISER DeviceService À LA DEMANDE
        device_service = get_device_service()
        
        # Utiliser AlertService
        if device_service and hasattr(device_service, '_alert_service') and device_service._alert_service:
            result = device_service._alert_service.get_alertes_critiques_recentes(
                heures=hours_back
            )
            
            # Filtrer par client si nécessaire
            if client_filter and result.get('success'):
                alertes_filtrees = [
                    a for a in result.get('alertes', []) 
                    if a.get('client_id') == client_filter
                ]
                result['alertes'] = alertes_filtrees
                result['total_critiques'] = len(alertes_filtrees)
            
            return jsonify(result), 200 if result.get('success') else 400
        
        # Fallback direct
        start_time = datetime.utcnow() - timedelta(hours=hours_back)
        query = Alert.query.filter(
            Alert.gravite == 'critique',
            Alert.date_creation >= start_time
        )
        
        if client_filter:
            query = query.filter_by(client_id=client_filter)
        
        alertes = query.order_by(Alert.date_creation.desc()).all()
        
        alertes_data = []
        for alerte in alertes:
            try:
                if hasattr(alerte, 'to_dict'):
                    alertes_data.append(alerte.to_dict(include_details=True))
                else:
                    alertes_data.append({
                        'id': alerte.id,
                        'appareil_id': alerte.appareil_id,
                        'type_alerte': alerte.type_alerte,
                        'gravite': alerte.gravite,
                        'titre': alerte.titre,
                        'message': alerte.message,
                        'date_creation': alerte.date_creation.isoformat() if alerte.date_creation else None
                    })
            except:
                continue
        
        return jsonify({
            'success': True,
            'total_critiques': len(alertes_data),
            'period_hours': hours_back,
            'alertes': alertes_data
        }), 200
        
    except Exception as e:
        logging.error(f"Erreur alertes critiques: {e}")
        return jsonify({'error': f'Erreur alertes critiques: {str(e)}'}), 500

@alert_bp.route('/health', methods=['GET'])
def health_check():
    """
    ❤️ SANTÉ du service AlertService
    GET /api/alerts/health
    """
    try:
        device_service = get_device_service()
        
        health_info = {
            'service': 'AlertService',
            'status': 'unknown',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {}
        }
        
        # Test AlertService
        if device_service and hasattr(device_service, '_alert_service') and device_service._alert_service:
            health_info['components']['alert_service'] = {
                'status': 'available',
                'loaded': True
            }
            
            # Test santé détaillée si méthode disponible
            if hasattr(device_service._alert_service, 'get_service_health'):
                try:
                    detailed_health = device_service._alert_service.get_service_health()
                    health_info['detailed_health'] = detailed_health
                except Exception as e:
                    health_info['detailed_health'] = {'error': str(e)}
        else:
            health_info['components']['alert_service'] = {
                'status': 'unavailable',
                'loaded': False
            }
        
        # Test Database
        try:
            alert_count = Alert.query.limit(1).count()
            device_count = Device.query.limit(1).count()
            health_info['components']['database'] = {
                'status': 'healthy',
                'connection': True,
                'test_counts': {
                    'alerts': alert_count,
                    'devices': device_count
                }
            }
        except Exception as e:
            health_info['components']['database'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Déterminer statut global
        all_healthy = all(
            comp.get('status') in ['healthy', 'available'] 
            for comp in health_info['components'].values()
        )
        
        health_info['status'] = 'healthy' if all_healthy else 'degraded'
        
        return jsonify(health_info), 200
        
    except Exception as e:
        return jsonify({
            'service': 'AlertService',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500