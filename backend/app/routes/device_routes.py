# app/routes/device_routes.py - Version mise à jour pour DeviceService v2.0
# ✅ Compatible avec cache Redis, extensions protection/analyse, et nouvelles fonctionnalités

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.protection_event import ProtectionEvent
from app.models.scheduled_action import ScheduledAction
from datetime import datetime, timedelta
from functools import wraps

# Créer le blueprint
device_bp = Blueprint('devices', __name__, url_prefix='/api/devices')

# Import du service avec gestion d'erreur ET extensions
try:
    from app.services.device_service import DeviceService
    device_service = DeviceService()
    
    # ✅ NOUVEAU : Initialiser les extensions si disponibles
    try:
        extensions_result = device_service.initialize_extensions()
        print(f"📋 Extensions DeviceService: {extensions_result}")
    except AttributeError:
        print("⚠️ Extensions non disponibles sur cette version de DeviceService")
        
except ImportError as e:
    print(f"⚠️ Erreur import DeviceService: {e}")
    device_service = None

# =================== FONCTIONS UTILITAIRES (mises à jour) ===================

def find_device_by_id_or_tuya_id(device_id):
    """Trouver un appareil par UUID ou tuya_device_id"""
    device = Device.query.get(device_id)
    if not device:
        device = Device.query.filter_by(tuya_device_id=device_id).first()
    return device

def admin_required(f):
    """Décorateur pour les routes admin"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            current_user = User.query.get(user_id)
            
            if not current_user or not current_user.actif or not current_user.is_admin():
                return jsonify({'error': 'Permission admin requise'}), 403
            
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': f'Erreur authentification: {str(e)}'}), 401
    return decorated_function

def superadmin_required(f):
    """Décorateur pour les routes superadmin uniquement"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            current_user = User.query.get(user_id)
            
            if not current_user or not current_user.actif or not current_user.is_superadmin():
                return jsonify({'error': 'Permission superadmin requise'}), 403
            
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': f'Erreur authentification: {str(e)}'}), 401
    return decorated_function

def validate_json_data(required_fields=None):
    """Décorateur pour valider les données JSON"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Données JSON requises'}), 400
            
            if required_fields:
                missing_fields = [field for field in required_fields if not data.get(field)]
                if missing_fields:
                    return jsonify({
                        'error': f'Champs requis manquants: {", ".join(missing_fields)}'
                    }), 400
            
            return f(data, *args, **kwargs)
        return decorated_function
    return decorator

def safe_device_service_call(method_name, *args, **kwargs):
    """Appel sécurisé d'une méthode du device_service avec cache"""
    if not device_service:
        return {'success': False, 'error': 'Service device non disponible'}
    
    if not hasattr(device_service, method_name):
        return {'success': False, 'error': f'Méthode {method_name} non disponible'}
    
    try:
        method = getattr(device_service, method_name)
        return method(*args, **kwargs)
    except Exception as e:
        print(f"Erreur service {method_name}: {e}")
        return {'success': False, 'error': str(e)}

# =================== ROUTES BASIQUES (améliorées) ===================

@device_bp.route('/health', methods=['GET'])
def health_check():
    """Vérification de santé du blueprint devices avec extensions"""
    try:
        # ✅ NOUVEAU : Vérifier santé service + extensions
        service_health = None
        extensions_status = None
        
        if device_service:
            # Test santé service principal
            try:
                service_health = device_service.get_service_health()
            except AttributeError:
                service_health = {"available": True, "version": "legacy"}
            
            # Test extensions
            try:
                extensions_status = device_service.get_extension_status()
            except AttributeError:
                extensions_status = {"extensions": {}, "total_active": 0}
        
        return jsonify({
            'success': True,
            'message': 'Device blueprint opérationnel',
            'device_service_available': device_service is not None,
            'service_health': service_health,
            'extensions_status': extensions_status,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@device_bp.route('/', methods=['GET'])
@admin_required
def lister_appareils(current_user):
    """Lister les appareils avec filtrage automatique par site utilisateur"""
    try:
        # ✅ NOUVEAUX paramètres
        site_id = request.args.get('site_id')
        inclure_non_assignes = request.args.get('inclure_non_assignes', 'false').lower() == 'true'
        refresh_status = request.args.get('refresh_status', 'true').lower() == 'true'
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # Seul le superadmin peut inclure les non-assignés
        if inclure_non_assignes and not current_user.is_superadmin():
            return jsonify({'error': 'Seul le superadmin peut voir les appareils non-assignés'}), 403
        
        # ✅ GESTION FILTRAGE PAR RÔLE UTILISATEUR
        if current_user.role == 'user':
            # User simple : gestion spéciale
            if not current_user.site_id:
                return jsonify({
                    'success': True,
                    'data': [],
                    'total': 0,
                    'message': 'Aucun site assigné à cet utilisateur',
                    'user_info': {
                        'role': current_user.role,
                        'site_assigned': False,
                        'needs_site_assignment': True
                    },
                    'stats': {
                        'total': 0,
                        'online': 0,
                        'offline': 0
                    }
                }), 200
            
            # ✅ FORCER le site_id au site de l'utilisateur
            if site_id and site_id != current_user.site_id:
                return jsonify({
                    'error': 'Accès interdit à ce site',
                    'message': f'Vous êtes assigné au site {current_user.site_id}',
                    'user_site_id': current_user.site_id,
                    'requested_site_id': site_id
                }), 403
            
            # Pour user simple, toujours filtrer par son site
            site_id = current_user.site_id
            print(f"👤 User simple {current_user.nom_complet} - filtrage automatique par site {site_id}")
        
        # ✅ UTILISER LE DEVICESERVICE AVEC GESTION SITE
        if device_service and hasattr(device_service, 'get_all_devices'):
            result = device_service.get_all_devices(
                utilisateur=current_user,
                include_non_assignes=inclure_non_assignes,
                refresh_status=refresh_status,
                use_cache=use_cache
            )
            
            if result.get('success'):
                # ✅ FILTRAGE SUPPLÉMENTAIRE par site si demandé ou forcé
                devices = result.get('devices', [])
                
                if site_id:
                    devices_filtered = [d for d in devices if d.get('site_id') == site_id]
                    
                    # Recalculer les stats après filtrage
                    online_count = sum(1 for d in devices_filtered if d.get('en_ligne'))
                    offline_count = len(devices_filtered) - online_count
                    
                    return jsonify({
                        'success': True,
                        'data': devices_filtered,
                        'total': len(devices_filtered),
                        'stats': {
                            'total': len(devices_filtered),
                            'online': online_count,
                            'offline': offline_count,
                            'protection_active': sum(1 for d in devices_filtered if d.get('protection', {}).get('active')),
                            'programmation_active': sum(1 for d in devices_filtered if d.get('programmation', {}).get('active'))
                        },
                        'user_info': {
                            'role': current_user.role,
                            'site_id': current_user.site_id if current_user.role == 'user' else None,
                            'site_nom': current_user.site.nom_site if current_user.role == 'user' and current_user.site else None,
                            'filtered_by_site': True
                        },
                        'site_filter': {
                            'applied': True,
                            'site_id': site_id,
                            'forced_by_user_role': current_user.role == 'user'
                        },
                        'last_sync': result.get('last_sync'),
                        'filtres': {
                            'site_id': site_id,
                            'inclure_non_assignes': inclure_non_assignes,
                            'refresh_status': refresh_status,
                            'use_cache': use_cache
                        },
                        'from_cache': result.get('stats', {}).get('sync_method') == 'cache'
                    }), 200
                else:
                    # Pas de filtrage par site spécifique
                    return jsonify({
                        'success': True,
                        'data': devices,
                        'total': len(devices),
                        'stats': result.get('stats', {}),
                        'user_info': result.get('user_info', {}),
                        'last_sync': result.get('last_sync'),
                        'filtres': {
                            'site_id': site_id,
                            'inclure_non_assignes': inclure_non_assignes,
                            'refresh_status': refresh_status,
                            'use_cache': use_cache
                        },
                        'from_cache': result.get('stats', {}).get('sync_method') == 'cache'
                    }), 200
            else:
                # Fallback vers méthode manuelle
                return _fallback_lister_appareils_avec_site(current_user, site_id, inclure_non_assignes)
        else:
            # Fallback si service non disponible
            return _fallback_lister_appareils_avec_site(current_user, site_id, inclure_non_assignes)
        
    except Exception as e:
        print(f"Erreur liste appareils: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

def _fallback_lister_appareils(current_user, site_id, inclure_non_assignes):
    """Méthode fallback pour lister appareils (legacy)"""
    try:
        # Construction de la requête legacy
        if current_user.is_superadmin():
            if inclure_non_assignes:
                query = Device.query
            else:
                query = Device.query.filter_by(statut_assignation='assigne')
        else:
            query = Device.query.filter_by(
                client_id=current_user.client_id,
                statut_assignation='assigne'
            )
        
        if site_id:
            query = query.filter_by(site_id=site_id)
        
        appareils = query.all()
        
        # Filtrer selon les permissions
        appareils_accessibles = [
            device for device in appareils 
            if device.peut_etre_vu_par_utilisateur(current_user)
        ]
        
        return jsonify({
            'success': True,
            'data': [device.to_dict(include_stats=True) for device in appareils_accessibles],
            'total': len(appareils_accessibles),
            'stats': {
                'total': len(appareils_accessibles),
                'online': sum(1 for d in appareils_accessibles if d.en_ligne),
                'offline': sum(1 for d in appareils_accessibles if not d.en_ligne)
            },
            'filtres': {
                'site_id': site_id,
                'inclure_non_assignes': inclure_non_assignes
            },
            'from_cache': False,
            'fallback_mode': True
        }), 200
        
    except Exception as e:
        print(f"Erreur fallback liste: {e}")
        return jsonify({'error': f'Erreur fallback: {str(e)}'}), 500



def _fallback_lister_appareils_avec_site(current_user, site_id, inclure_non_assignes):
    """Méthode fallback pour lister appareils avec gestion site (version améliorée)"""
    try:
        print(f"🔄 Fallback listing pour {current_user.role} - site_id: {site_id}")
        
        # ✅ CONSTRUCTION REQUÊTE selon le rôle
        if current_user.is_superadmin():
            if inclure_non_assignes:
                query = Device.query
            else:
                query = Device.query.filter_by(statut_assignation='assigne')
                
        elif current_user.is_admin():
            # Admin : tous les appareils de son client
            query = Device.query.filter_by(
                client_id=current_user.client_id,
                statut_assignation='assigne'
            )
            
        elif current_user.role == 'user':
            # ✅ User simple : OBLIGATOIREMENT filtré par son site
            if not current_user.site_id:
                return jsonify({
                    'success': True,
                    'data': [],
                    'total': 0,
                    'message': 'Utilisateur sans site assigné',
                    'fallback_mode': True
                }), 200
            
            query = Device.query.filter_by(
                client_id=current_user.client_id,
                site_id=current_user.site_id,  # ✅ FILTRAGE PAR SON SITE
                statut_assignation='assigne'
            )
        else:
            # Cas par défaut
            query = Device.query.filter_by(statut_assignation='non_assigne') if inclure_non_assignes else Device.query.filter(Device.id == None)
        
        # ✅ FILTRAGE SUPPLÉMENTAIRE par site si demandé (pour admin/superadmin)
        if site_id and current_user.role != 'user':  # User simple a déjà son site forcé
            query = query.filter_by(site_id=site_id)
        
        appareils = query.all()
        
        # ✅ DOUBLE VÉRIFICATION des permissions (sécurité)
        appareils_accessibles = []
        for device in appareils:
            if device.peut_etre_vu_par_utilisateur(current_user):
                appareils_accessibles.append(device)
            else:
                print(f"⚠️ Appareil {device.nom_appareil} filtré par permissions")
        
        # Statistiques
        online_count = sum(1 for d in appareils_accessibles if d.en_ligne)
        offline_count = len(appareils_accessibles) - online_count
        
        # ✅ INFO SITE pour user simple
        site_info = None
        if current_user.role == 'user' and current_user.site:
            site_info = {
                'id': current_user.site.id,
                'nom': current_user.site.nom_site,
                'adresse': current_user.site.adresse,
                'ville': current_user.site.ville
            }
        
        return jsonify({
            'success': True,
            'data': [device.to_dict(include_stats=True) for device in appareils_accessibles],
            'total': len(appareils_accessibles),
            'stats': {
                'total': len(appareils_accessibles),
                'online': online_count,
                'offline': offline_count
            },
            'user_info': {
                'role': current_user.role,
                'site_id': current_user.site_id if current_user.role == 'user' else None,
                'site_info': site_info
            },
            'filtres': {
                'site_id': site_id,
                'inclure_non_assignes': inclure_non_assignes,
                'forced_site_filter': current_user.role == 'user'
            },
            'from_cache': False,
            'fallback_mode': True
        }), 200
        
    except Exception as e:
        print(f"Erreur fallback liste avec site: {e}")
        return jsonify({'error': f'Erreur fallback: {str(e)}'}), 500


@device_bp.route('/<device_id>', methods=['GET'])
@admin_required
def obtenir_appareil(current_user, device_id):
    """Obtenir les détails d'un appareil avec enrichissement"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # ✅ NOUVEAU : Enrichir avec données temps réel et analyse
        device_dict = device.to_dict(
            include_stats=True, 
            include_tuya_info=True,
            include_protection=True,
            include_programmation=True
        )
        
        # Ajouter données temps réel si service disponible
        if device_service:
            try:
                real_time_result = safe_device_service_call(
                    'get_device_real_time_data', device.tuya_device_id, True
                )
                if real_time_result.get('success'):
                    device_dict['real_time_data'] = real_time_result
            except:
                pass
            
            # ✅ NOUVEAU : Ajouter résumé d'analyse si extension disponible
            try:
                if hasattr(device_service, '_analysis_extension'):
                    analysis_summary = device_service._analysis_extension.get_device_analysis_summary(
                        device.id, hours_back=6, use_cache=True
                    )
                    if analysis_summary.get('success'):
                        device_dict['analysis_summary'] = analysis_summary
            except:
                pass
        
        return jsonify({
            'success': True,
            'data': device_dict
        }), 200
        
    except Exception as e:
        print(f"Erreur obtenir appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== CONTRÔLE DES APPAREILS (amélioré) ===================

@device_bp.route('/<device_id>/toggle', methods=['POST'])
@admin_required
def toggle_appareil(current_user, device_id):
    """Basculer l'état d'un appareil avec vérification site utilisateur"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        # ✅ VÉRIFICATION STRICTE des permissions (inclut le site pour user simple)
        if not device.peut_etre_controle_par_utilisateur(current_user):
            error_msg = 'Accès en contrôle interdit pour cet appareil'
            
            # Message plus spécifique pour user simple
            if current_user.role == 'user':
                if device.site_id != current_user.site_id:
                    error_msg = f'Appareil non accessible - Vous êtes assigné au site {current_user.site_id}'
                elif device.client_id != current_user.client_id:
                    error_msg = 'Appareil non accessible - Client différent'
            
            return jsonify({'error': error_msg}), 403
        
        if not device.is_assigne():
            return jsonify({'error': 'Appareil non assigné à un client'}), 400
        
        data = request.get_json() or {}
        etat = data.get('etat')  # True=allumer, False=éteindre, None=toggle
        
        # ✅ VÉRIFICATIONS override programmation si extension disponible
        schedule_override = None
        if device_service and hasattr(device_service, '_protection_extension'):
            try:
                override_check = device_service._protection_extension.enhance_control_device_with_schedule_check(
                    device.id, "switch", etat
                )
                if override_check.get('override_required'):
                    schedule_override = override_check
            except:
                pass
        
        # Appel contrôle avec invalidation cache
        resultat = safe_device_service_call('control_device', device.tuya_device_id, "switch", etat, True)
        
        response_data = {
            'success': resultat.get('success', False),
            'message': resultat.get('message', 'Toggle exécuté'),
            'new_state': resultat.get('new_state'),
            'device_name': device.nom_appareil,
            'device_id': device.id,
            'tuya_device_id': device.tuya_device_id,
            'user_info': {
                'role': current_user.role,
                'site_id': current_user.site_id if current_user.role == 'user' else None
            }
        }
        
        # Ajouter info override si applicable
        if schedule_override:
            response_data['schedule_override'] = schedule_override
        
        return jsonify(response_data), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur toggle device {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


        
@device_bp.route('/<device_id>/controle', methods=['POST'])
@admin_required
@validate_json_data(['action'])
def controler_appareil(data, current_user, device_id):
    """Contrôler un appareil avec action spécifique"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_controle_par_utilisateur(current_user):
            return jsonify({'error': 'Accès en contrôle interdit pour cet appareil'}), 403
        
        action = data['action']
        valeur = data.get('valeur', True)
        
        # ✅ NOUVEAU : Contrôle avec cache et gestion protections
        resultat = safe_device_service_call('control_device', device.tuya_device_id, action, valeur, True)
        
        return jsonify({
            'success': resultat.get('success', False),
            'message': resultat.get('message', 'Commande envoyée'),
            'action_executee': action,
            'valeur': valeur,
            'response': resultat
        }), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur contrôle appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== GESTION DES DONNÉES (optimisée) ===================

@device_bp.route('/<device_id>/donnees', methods=['GET'])
@admin_required
def obtenir_donnees_appareil(current_user, device_id):
    """Obtenir l'historique des données d'un appareil avec cache"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # Paramètres
        limite = min(int(request.args.get('limite', 100)), 1000)
        page = max(int(request.args.get('page', 1)), 1)
        hours_back = int(request.args.get('hours_back', 24))
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # ✅ NOUVEAU : Utiliser get_device_history avec cache si disponible
        if device_service and hasattr(device_service, 'get_device_history'):
            history_result = device_service.get_device_history(
                device.tuya_device_id, 
                limit=limite, 
                hours_back=hours_back, 
                use_cache=use_cache
            )
            
            if history_result.get('success'):
                return jsonify({
                    'success': True,
                    'device_info': {
                        'uuid': device.id,
                        'tuya_device_id': device.tuya_device_id,
                        'nom': device.nom_appareil
                    },
                    'data': history_result.get('data', []),
                    'analysis': history_result.get('analysis', {}),
                    'period': history_result.get('period', {}),
                    'pagination': {
                        'page': page,
                        'limite': limite,
                        'total': history_result.get('count', 0)
                    },
                    'from_cache': history_result.get('from_cache', False)
                }), 200
        
        # Fallback méthode legacy
        start_time = datetime.utcnow() - timedelta(hours=hours_back)
        query = DeviceData.query.filter_by(appareil_id=device.id)\
                              .filter(DeviceData.horodatage >= start_time)\
                              .order_by(DeviceData.horodatage.desc())
        
        total = query.count()
        offset = (page - 1) * limite
        donnees = query.offset(offset).limit(limite).all()
        
        return jsonify({
            'success': True,
            'device_info': {
                'uuid': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom': device.nom_appareil
            },
            'data': [donnee.to_dict() for donnee in donnees],
            'pagination': {
                'page': page,
                'limite': limite,
                'total': total,
                'pages_total': (total + limite - 1) // limite
            },
            'from_cache': False,
            'fallback_mode': True
        }), 200
        
    except Exception as e:
        print(f"Erreur données appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/collecter-donnees', methods=['POST'])
@admin_required
def collecter_donnees(current_user, device_id):
    """Collecter manuellement les données d'un appareil avec enrichissement"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # ✅ NOUVEAU : Utiliser get_device_status enrichi
        use_cache = request.args.get('use_cache', 'false').lower() == 'true'  # Force fresh pour collecte manuelle
        
        resultat = safe_device_service_call('get_device_status', device.tuya_device_id, use_cache)
        
        response_data = {
            'success': resultat.get('success', False),
            'message': 'Données collectées avec succès' if resultat.get('success') else 'Erreur collecte',
            'data': resultat
        }
        
        # ✅ NOUVEAU : Ajouter analyse enrichie si extension disponible
        if resultat.get('success') and device_service:
            try:
                enhanced_status = device_service.enhance_get_device_status(resultat, device.tuya_device_id)
                if enhanced_status:
                    response_data['enhanced_data'] = enhanced_status
            except:
                pass
        
        return jsonify(response_data), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur collecte données {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== NOUVELLES ROUTES POUR PROTECTION & PROGRAMMATION ===================

@device_bp.route('/<device_id>/protection/config', methods=['GET', 'POST'])
@admin_required
def manage_protection_config(current_user, device_id):
    """Gérer la configuration de protection automatique"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        # ✅ Vérifier si extension protection disponible
        if not (device_service and hasattr(device_service, '_protection_extension')):
            return jsonify({
                'error': 'Extension protection non disponible',
                'message': 'Fonctionnalité protection automatique non activée'
            }), 501
        
        if request.method == 'GET':
            if not device.peut_etre_vu_par_utilisateur(current_user):
                return jsonify({'error': 'Accès interdit à cet appareil'}), 403
            
            # Récupérer config protection
            protection_config = device.get_protection_config()
            
            return jsonify({
                'success': True,
                'device_id': device.id,
                'device_name': device.nom_appareil,
                'protection_config': protection_config,
                'protection_active': device.protection_automatique_active
            }), 200
        
        else:  # POST
            if not device.peut_etre_configure_par_utilisateur(current_user):
                return jsonify({'error': 'Accès en configuration interdit pour cet appareil'}), 403
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Données JSON requises'}), 400
            
            # Configurer protection via extension
            config_result = device_service._protection_extension.configure_device_protection(
                device.id, data
            )
            
            return jsonify(config_result), 200 if config_result.get('success') else 400
        
    except Exception as e:
        print(f"Erreur protection config {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@device_bp.route('/<device_identifier>/protection/disable', methods=['POST'])
@admin_required
def disable_device_protection(current_user, device_identifier):
    """Désactiver complètement la protection"""
    try:
        # 🔧 RECHERCHE INTELLIGENTE : ID interne OU tuya_device_id
        device = None
        
        # Essayer d'abord par ID interne (UUID format)
        if len(device_identifier) == 36 and '-' in device_identifier:
            device = Device.query.get(device_identifier)
            print(f"🔍 Recherche par ID interne: {device_identifier}")
        
        # Si pas trouvé, essayer par tuya_device_id
        if not device:
            device = Device.query.filter_by(tuya_device_id=device_identifier).first()
            print(f"🔍 Recherche par tuya_device_id: {device_identifier}")
        
        if not device:
            return jsonify({
                "success": False, 
                "error": f"Appareil non trouvé avec l'identifiant: {device_identifier}",
                "searched_by": ["internal_id", "tuya_device_id"]
            }), 404
        
        print(f"✅ Appareil trouvé: {device.nom_appareil} (ID: {device.id}, Tuya: {device.tuya_device_id})")
        
        # Force désactivation
        success = device.disable_protection()
        
        if success:
            return jsonify({
                "success": True,
                "device_id": device.id,
                "tuya_device_id": device.tuya_device_id,
                "device_name": device.nom_appareil,
                "message": "Protection désactivée avec succès",
                "monitoring_active": False,
                "protection_config": {
                    "courant_protection": {"enabled": False},
                    "puissance_protection": {"enabled": False}, 
                    "temperature_protection": {"enabled": False},
                    "tension_protection": {"enabled": False}
                }
            }), 200
        else:
            return jsonify({"success": False, "error": "Erreur désactivation"}), 400
            
    except Exception as e:
        print(f"❌ Erreur disable protection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
@device_bp.route('/<device_id>/programmation/config', methods=['GET', 'POST'])
@admin_required
def manage_programmation_config(current_user, device_id):
    """Gérer la configuration de programmation horaire"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        # ✅ CORRECTION 1 : Vérifier si extension disponible ET initialisée
        if not (device_service and hasattr(device_service, '_protection_extension') 
                and device_service._protection_extension is not None):
            
            # ✅ SOLUTION A : Initialiser l'extension si pas fait
            try:
                from app.services.device_service_protection_extension import DeviceServiceProtectionExtension
                
                if not hasattr(device_service, '_protection_extension'):
                    print("🔧 Initialisation de l'extension protection...")
                    device_service._protection_extension = DeviceServiceProtectionExtension(device_service)
                    print("✅ Extension protection initialisée")
                
            except Exception as e:
                print(f"❌ Erreur initialisation extension: {e}")
                return jsonify({
                    'error': 'Extension programmation non disponible',
                    'message': f'Impossible d\'initialiser l\'extension: {str(e)}',
                    'debug': 'Vérifiez que device_service_protection_extension.py est accessible'
                }), 501
        
        if request.method == 'GET':
            if not device.peut_etre_vu_par_utilisateur(current_user):
                return jsonify({'error': 'Accès interdit à cet appareil'}), 403
            
            # ✅ CORRECTION 2 : Utiliser la méthode correcte
            # Au lieu de : device_service._protection_extension.get_device_schedule_status(device.id)
            # Utiliser : device_service._protection_extension.get_device_schedule_status(device_id)
            
            schedule_result = device_service._protection_extension.get_device_schedule_status(device_id)
            
            return jsonify(schedule_result), 200 if schedule_result.get('success') else 400
        
        else:  # POST
            if not device.peut_etre_configure_par_utilisateur(current_user):
                return jsonify({'error': 'Accès en configuration interdit pour cet appareil'}), 403
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Données JSON requises'}), 400
            
            action = data.get('action', 'configure')
            
            if action == 'configure':
                # ✅ CORRECTION 3 : Utiliser device_id au lieu de device.id
                config_result = device_service._protection_extension.configure_device_schedule(
                    device_id, data  # device_id au lieu de device.id
                )
            elif action == 'disable':
                # ✅ CORRECTION 4 : Utiliser device_id au lieu de device.id
                config_result = device_service._protection_extension.disable_device_schedule(device_id)
            else:
                return jsonify({'error': f'Action {action} non reconnue'}), 400
            
            return jsonify(config_result), 200 if config_result.get('success') else 400
    
    except Exception as e:
        print(f"Erreur programmation config {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500
    
@device_bp.route('/<device_id>/programmation/details', methods=['GET'])
@admin_required
def get_programmation_details(current_user, device_id):
    """Récupérer les détails complets de programmation"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        from app.models.scheduled_action import ScheduledAction
        
        # Récupérer toutes les actions
        actions = ScheduledAction.get_actions_by_device(device.id)
        
        result = {
            "success": True,
            "device_id": device.id,
            "device_name": device.nom_appareil,
            "programmation_active": getattr(device, 'programmation_active', False),
            "total_actions": len(actions),
            "actions": []
        }
        
        for action in actions:
            action_data = {
                "id": action.id,
                "nom": action.nom_action,
                "description": action.description,
                "type": action.action_type,
                "heure": action.heure_execution.strftime('%H:%M') if action.heure_execution else None,
                "jours_semaine": action.get_jours_semaine_list(),
                "jours_semaine_noms": action.get_jours_semaine_noms(),
                "actif": action.actif,
                "priorite": action.priorite,
                "mode_execution": action.mode_execution,
                "prochaine_execution": action.prochaine_execution.isoformat() if action.prochaine_execution else None,
                "derniere_execution": action.derniere_execution.isoformat() if action.derniere_execution else None,
                "derniere_execution_success": action.derniere_execution_success,
                "statistiques": {
                    "executions_totales": action.executions_totales,
                    "executions_reussies": action.executions_reussies,
                    "executions_echouees": action.executions_echouees,
                    "taux_reussite": action.get_taux_reussite()
                },
                "retry_config": {
                    "retry_enabled": action.retry_enabled,
                    "retry_attempts": action.retry_attempts,
                    "retry_delay_minutes": action.retry_delay_minutes
                }
            }
            
            # Temps jusqu'à prochaine exécution
            if action.prochaine_execution:
                now = datetime.utcnow()
                if action.prochaine_execution > now:
                    delta = action.prochaine_execution - now
                    total_minutes = int(delta.total_seconds() / 60)
                    heures = total_minutes // 60
                    minutes = total_minutes % 60
                    
                    if heures > 0:
                        action_data["temps_jusqu_execution"] = f"{heures}h {minutes}min"
                    else:
                        action_data["temps_jusqu_execution"] = f"{minutes}min"
            
            result["actions"].append(action_data)
        
        # Statistiques globales
        result["statistiques"] = {
            "actions_actives": len([a for a in actions if a.actif]),
            "actions_inactives": len([a for a in actions if not a.actif]),
            "prochaines_24h": len([
                a for a in actions 
                if a.prochaine_execution and a.prochaine_execution <= datetime.utcnow() + timedelta(hours=24)
            ]),
            "executions_totales": sum(a.executions_totales for a in actions),
            "taux_reussite_global": round(
                sum(a.executions_reussies for a in actions) / max(1, sum(a.executions_totales for a in actions)) * 100, 2
            )
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@device_bp.route('/<device_id>/programmation/sync-actions', methods=['POST'])
@admin_required
def sync_programmation_actions(current_user, device_id):
    """Synchroniser les actions depuis la config horaires"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        if not device:
            return jsonify({'error': 'Appareil non trouvé'}), 404
        
        from app.models.scheduled_action import ScheduledAction
        from datetime import time
        
        # Récupérer la config depuis l'extension
        schedule_result = device_service._protection_extension.get_device_schedule_status(device_id)
        
        if not schedule_result.get('success'):
            return jsonify({'error': 'Pas de config trouvée'}), 400
        
        schedule_config = schedule_result.get('schedule_config', {})
        actions_creees = []
        
        # Créer action allumage
        if schedule_config.get('allumage', {}).get('enabled'):
            allumage_config = schedule_config['allumage']
            time_str = allumage_config.get('time', '07:00')
            hour, minute = map(int, time_str.split(':'))
            
            action_allumage = ScheduledAction(
                appareil_id=device.id,
                client_id=device.client_id,
                action_type="turn_on",
                heure_execution=time(hour, minute),
                jours_semaine=','.join(map(str, allumage_config.get('days', [1,2,3,4,5]))),
                nom_action="Allumage automatique",
                description=f"Allumage tous les jours ouvrés à {time_str}",
                actif=True,
                mode_execution='weekly'
            )
            action_allumage.calculer_prochaine_execution()
            db.session.add(action_allumage)
            actions_creees.append(f"Allumage {time_str}")
        
        # Créer action extinction
        if schedule_config.get('extinction', {}).get('enabled'):
            extinction_config = schedule_config['extinction']
            time_str = extinction_config.get('time', '22:00')
            hour, minute = map(int, time_str.split(':'))
            
            action_extinction = ScheduledAction(
                appareil_id=device.id,
                client_id=device.client_id,
                action_type="turn_off",
                heure_execution=time(hour, minute),
                jours_semaine=','.join(map(str, extinction_config.get('days', [1,2,3,4,5,6,7]))),
                nom_action="Extinction automatique",
                description=f"Extinction tous les jours à {time_str}",
                actif=True,
                mode_execution='weekly'
            )
            action_extinction.calculer_prochaine_execution()
            db.session.add(action_extinction)
            actions_creees.append(f"Extinction {time_str}")
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"{len(actions_creees)} actions créées",
            "actions_creees": actions_creees
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@device_bp.route('/<device_id>/programmation/force-create-actions', methods=['POST'])
@admin_required
def force_create_actions(current_user, device_id):
    """Créer des actions de programmation par force"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        if not device:
            return jsonify({'error': 'Appareil non trouvé'}), 404
        
        from app.models.scheduled_action import ScheduledAction
        from datetime import time
        
        # Supprimer anciennes actions pour ce device
        ScheduledAction.query.filter_by(appareil_id=device.id).delete()
        
        actions_creees = []
        
        # Créer action allumage 8h00 Lun-Ven
        action_allumage = ScheduledAction(
            appareil_id=device.id,
            client_id=device.client_id,
            action_type="turn_on",
            heure_execution=time(8, 0),
            jours_semaine="1,2,3,4,5",  # Lun-Ven
            nom_action="Allumage Bureau",
            description="Allumage automatique bureau 8h",
            actif=True,
            mode_execution='weekly',
            priorite=5,
            timezone="Africa/Dakar"
        )
        action_allumage.calculer_prochaine_execution()
        db.session.add(action_allumage)
        actions_creees.append("Allumage 08:00 Lun-Ven")
        
        # Créer action extinction 18h00 Tous les jours
        action_extinction = ScheduledAction(
            appareil_id=device.id,
            client_id=device.client_id,
            action_type="turn_off",
            heure_execution=time(18, 0),
            jours_semaine="1,2,3,4,5,6,7",  # Tous les jours
            nom_action="Extinction Soir",
            description="Extinction automatique soir 18h",
            actif=True,
            mode_execution='weekly',
            priorite=5,
            timezone="Africa/Dakar"
        )
        action_extinction.calculer_prochaine_execution()
        db.session.add(action_extinction)
        actions_creees.append("Extinction 18:00 Tous les jours")
        
        # Sauvegarder
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"{len(actions_creees)} actions créées avec succès",
            "actions_creees": actions_creees,
            "device_id": device.id,
            "device_name": device.nom_appareil
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
# =================== NOUVELLES ROUTES D'ANALYSE ===================

@device_bp.route('/<device_id>/analyse', methods=['GET'])
@admin_required
def get_device_analysis(current_user, device_id):
    """Récupérer analyse complète d'un appareil"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # ✅ Vérifier si extension analyse disponible
        if not (device_service and hasattr(device_service, '_analysis_extension')):
            return jsonify({
                'error': 'Extension analyse non disponible',
                'message': 'Fonctionnalité analyse avancée non activée'
            }), 501
        
        # Paramètres
        hours_back = int(request.args.get('hours_back', 24))
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # Récupérer résumé d'analyse
        analysis_result = device_service._analysis_extension.get_device_analysis_summary(
            device.id, hours_back=hours_back, use_cache=use_cache
        )
        
        return jsonify(analysis_result), 200 if analysis_result.get('success') else 400
        
    except Exception as e:
        print(f"Erreur analyse device {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/anomalies', methods=['GET'])
@admin_required
def get_device_anomalies(current_user, device_id):
    """Récupérer anomalies récentes d'un appareil"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # ✅ Vérifier si extension analyse disponible
        if not (device_service and hasattr(device_service, '_analysis_extension')):
            return jsonify({
                'error': 'Extension analyse non disponible',
                'message': 'Fonctionnalité détection anomalies non activée'
            }), 501
        
        # Paramètres
        hours_back = int(request.args.get('hours_back', 24))
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # Récupérer anomalies
        anomalies_result = device_service._analysis_extension.get_device_anomalies_recent(
            device.id, hours_back=hours_back, use_cache=use_cache
        )
        
        return jsonify(anomalies_result), 200 if anomalies_result.get('success') else 400
        
    except Exception as e:
        print(f"Erreur anomalies device {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/quality-score', methods=['GET'])
@admin_required
def get_device_quality_score(current_user, device_id):
    """Récupérer score de qualité réseau (triphasé uniquement)"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # ✅ Vérifier si extension analyse disponible
        if not (device_service and hasattr(device_service, '_analysis_extension')):
            return jsonify({
                'error': 'Extension analyse non disponible',
                'message': 'Fonctionnalité score qualité non activée'
            }), 501
        
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # Récupérer score qualité
        quality_result = device_service._analysis_extension.get_device_quality_score(
            device.id, use_cache=use_cache
        )
        
        return jsonify(quality_result), 200 if quality_result.get('success') else 400
        
    except Exception as e:
        print(f"Erreur quality score device {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/recommendations', methods=['GET'])
@admin_required
def get_device_recommendations(current_user, device_id):
    """Récupérer recommandations intelligentes pour un appareil"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # ✅ Vérifier si extension analyse disponible
        if not (device_service and hasattr(device_service, '_analysis_extension')):
            return jsonify({
                'error': 'Extension analyse non disponible',
                'message': 'Fonctionnalité recommandations non activée'
            }), 501
        
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # Récupérer recommandations
        recommendations_result = device_service._analysis_extension.get_device_recommendations(
            device.id, use_cache=use_cache
        )
        
        return jsonify(recommendations_result), 200 if recommendations_result.get('success') else 400
        
    except Exception as e:
        print(f"Erreur recommandations device {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTES GRAPHIQUES (optimisées) ===================

@device_bp.route('/<device_id>/graphique/<metric_type>', methods=['GET'])
@admin_required
def get_graphique_metric(current_user, device_id, metric_type):
    """Obtenir les données pour graphiques avec cache"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # Paramètres temporels
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        if not start_time or not end_time:
            # Par défaut : dernières 24h
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(hours=24)
        else:
            start_dt = datetime.fromtimestamp(int(start_time) / 1000)
            end_dt = datetime.fromtimestamp(int(end_time) / 1000)
        
        # Mapper le type de métrique vers le champ de la base
        metric_mapping = {
            'tension': 'tension',
            'courant': 'courant', 
            'puissance': 'puissance',
            'energie': 'energie',
            'temperature': 'temperature'
        }
        
        if metric_type not in metric_mapping:
            return jsonify({'error': f'Type de métrique non supporté: {metric_type}'}), 400
        
        field_name = metric_mapping[metric_type]
        
        # ✅ NOUVEAU : Essayer d'utiliser cache service si disponible
        cache_hit = False
        if use_cache and device_service and hasattr(device_service, 'redis') and device_service.redis:
            try:
                import hashlib
                cache_key = f"graph_data:{device.id}:{field_name}:{int(start_dt.timestamp())}:{int(end_dt.timestamp())}"
                cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
                
                cached_data = device_service.redis.get(f"graph:{cache_hash}")
                if cached_data:
                    import json
                    cached_result = json.loads(cached_data)
                    cached_result['from_cache'] = True
                    return jsonify(cached_result), 200
            except:
                pass
        
        # Requête avec filtre dynamique
        query = DeviceData.query.filter(
            DeviceData.appareil_id == device.id,
            DeviceData.horodatage >= start_dt,
            DeviceData.horodatage <= end_dt
        )
        
        # Ajouter filtre pour que le champ ne soit pas NULL
        query = query.filter(getattr(DeviceData, field_name).isnot(None))
        
        donnees_bdd = query.order_by(DeviceData.horodatage.asc()).all()
        
        result = {
            'success': True,
            'device_info': {
                'uuid': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom': device.nom_appareil
            },
            'metric_type': metric_type,
            'period': {
                'start_time': int(start_dt.timestamp() * 1000),
                'end_time': int(end_dt.timestamp() * 1000)
            },
            'data': [
                {
                    'timestamp': d.horodatage.isoformat(),
                    'value': float(getattr(d, field_name)) if getattr(d, field_name) else None,
                    'horodatage': int(d.horodatage.timestamp() * 1000)
                } for d in donnees_bdd
            ],
            'count': len(donnees_bdd),
            'from_cache': cache_hit
        }
        
        # ✅ NOUVEAU : Mettre en cache le résultat
        if use_cache and device_service and hasattr(device_service, 'redis') and device_service.redis:
            try:
                import json
                cache_ttl = 300  # 5 minutes
                device_service.redis.setex(f"graph:{cache_hash}", cache_ttl, json.dumps(result))
            except:
                pass
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Erreur graphique {metric_type} {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


# =================== NOUVELLE ROUTE POUR INFO SITE UTILISATEUR ===================

@device_bp.route('/mon-site', methods=['GET'])
@admin_required
def get_mon_site_info(current_user):
    """Récupérer les informations du site de l'utilisateur"""
    try:
        if current_user.role != 'user':
            return jsonify({
                'success': False,
                'error': 'Cette route est réservée aux utilisateurs simples',
                'user_role': current_user.role,
                'message': 'Les administrateurs ont accès à tous les sites'
            }), 400
        
        if not current_user.site_id:
            return jsonify({
                'success': False,
                'error': 'Aucun site assigné',
                'message': 'Contactez votre administrateur pour obtenir l\'assignation à un site',
                'user_id': current_user.id,
                'user_name': current_user.nom_complet
            }), 404
        
        from app.models.site import Site
        site = Site.query.get(current_user.site_id)
        
        if not site:
            return jsonify({
                'success': False,
                'error': 'Site non trouvé en base de données',
                'site_id': current_user.site_id,
                'message': 'Problème de cohérence des données - contactez l\'administrateur'
            }), 404
        
        # ✅ COMPTER les appareils du site de l'utilisateur
        appareils_site = Device.query.filter_by(
            client_id=current_user.client_id,
            site_id=current_user.site_id,
            statut_assignation='assigne'
        ).all()
        
        # Filtrer par permissions (sécurité)
        appareils_accessibles = [
            device for device in appareils_site 
            if device.peut_etre_vu_par_utilisateur(current_user)
        ]
        
        online_count = sum(1 for d in appareils_accessibles if d.en_ligne)
        offline_count = len(appareils_accessibles) - online_count
        
        # Statistiques par type d'appareil
        types_count = {}
        for device in appareils_accessibles:
            device_type = device.type_appareil
            types_count[device_type] = types_count.get(device_type, 0) + 1
        
        # Dernière activité
        derniere_activite = None
        if appareils_accessibles:
            devices_avec_donnees = [d for d in appareils_accessibles if d.derniere_donnee]
            if devices_avec_donnees:
                device_plus_recent = max(devices_avec_donnees, key=lambda d: d.derniere_donnee)
                derniere_activite = {
                    'timestamp': device_plus_recent.derniere_donnee.isoformat(),
                    'device_name': device_plus_recent.nom_appareil
                }
        
        return jsonify({
            'success': True,
            'user_info': {
                'id': current_user.id,
                'nom_complet': current_user.nom_complet,
                'email': current_user.email,
                'role': current_user.role,
                'date_creation': current_user.date_creation.isoformat() if current_user.date_creation else None
            },
            'site_info': site.to_dict(include_stats=True),
            'appareils_stats': {
                'total': len(appareils_accessibles),
                'online': online_count,
                'offline': offline_count,
                'par_type': types_count,
                'derniere_activite': derniere_activite,
                'taux_disponibilite': round((online_count / len(appareils_accessibles)) * 100, 2) if appareils_accessibles else 0
            },
            'permissions': {
                'peut_voir_appareils': True,
                'peut_controler_appareils': True,
                'peut_configurer_appareils': True,  # Selon vos règles business
                'limites': 'Accès uniquement aux appareils de ce site'
            },
            'navigation': {
                'appareils_url': '/api/devices/',
                'site_map_link': site.get_map_link() if hasattr(site, 'get_map_link') else None
            }
        }), 200
        
    except Exception as e:
        print(f"Erreur info site utilisateur: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTE POUR LISTER SITES ACCESSIBLES ===================

@device_bp.route('/sites-accessibles', methods=['GET'])
@admin_required
def get_sites_accessibles(current_user):
    """Récupérer les sites accessibles selon le rôle utilisateur"""
    try:
        from app.models.site import Site
        
        if current_user.is_superadmin():
            # Superadmin : tous les sites
            sites = Site.query.filter_by(actif=True).all()
            scope = "superadmin"
            
        elif current_user.is_admin():
            # Admin : sites de son client
            sites = Site.query.filter_by(
                client_id=current_user.client_id,
                actif=True
            ).all()
            scope = "admin"
            
        elif current_user.role == 'user':
            # User simple : uniquement son site
            if current_user.site_id and current_user.site:
                sites = [current_user.site]
            else:
                sites = []
            scope = "user"
            
        else:
            sites = []
            scope = "unknown"
        
        sites_data = []
        for site in sites:
            # Compter les appareils par site
            appareils_count = Device.query.filter_by(
                site_id=site.id,
                statut_assignation='assigne'
            ).count()
            
            appareils_online = Device.query.filter_by(
                site_id=site.id,
                statut_assignation='assigne',
                en_ligne=True
            ).count()
            
            site_dict = site.to_dict()
            site_dict.update({
                'appareils_stats': {
                    'total': appareils_count,
                    'online': appareils_online,
                    'offline': appareils_count - appareils_online
                },
                'accessible': True,
                'user_can_access': True
            })
            
            sites_data.append(site_dict)
        
        return jsonify({
            'success': True,
            'sites': sites_data,
            'total': len(sites_data),
            'user_scope': scope,
            'user_info': {
                'role': current_user.role,
                'assigned_site_id': current_user.site_id if current_user.role == 'user' else None
            },
            'message': f'{len(sites_data)} sites accessibles'
        }), 200
        
    except Exception as e:
        print(f"Erreur sites accessibles: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500



# =================== ROUTES D'ADMINISTRATION (améliorées) ===================

@device_bp.route('/import-tuya', methods=['POST'])
@superadmin_required
def import_appareils_tuya(current_user):
    """Importer tous les appareils depuis Tuya avec options avancées"""
    try:
        # ✅ SOLUTION DÉFINITIVE: Ignorer Content-Type
        data = {}
        
        # Essayer de récupérer JSON s'il y en a, sinon dict vide
        try:
            if request.data:  # S'il y a des données
                data = request.get_json(force=True) or {}
        except:
            data = {}
        
        use_cache = data.get('use_cache', True)
        force_refresh = data.get('force_refresh', False)
        
        print(f"🔍 Import Tuya - use_cache: {use_cache}, force_refresh: {force_refresh}")
        
        # Votre code existant...
        if hasattr(device_service, 'import_tuya_devices'):
            resultat = device_service.import_tuya_devices(
                use_cache=use_cache, 
                force_refresh=force_refresh
            )
        else:
            resultat = safe_device_service_call('import_tuya_devices')
        
        if not resultat.get('success'):
            return jsonify({'error': resultat.get('error', 'Erreur import')}), 400
        
        return jsonify({
            'success': True,
            'message': resultat['message'],
            'statistiques': resultat.get('statistiques', {}),
            'options_used': {
                'use_cache': use_cache,
                'force_refresh': force_refresh
            }
        }), 200
        
    except Exception as e:
        print(f"Erreur import Tuya: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500
    
@device_bp.route('/sync-tuya', methods=['POST'])
@admin_required
def synchroniser_tuya(current_user):
    """Synchroniser les statuts avec Tuya avec options"""
    try:
        # ✅ SOLUTION DÉFINITIVE: Ignorer Content-Type comme import-tuya
        data = {}
        
        # Essayer de récupérer JSON s'il y en a, sinon dict vide
        try:
            if request.data:  # S'il y a des données
                data = request.get_json(force=True) or {}
        except:
            data = {}
        
        force_refresh = data.get('force_refresh', True)
        use_cache = data.get('use_cache', True)
        
        print(f"🔄 Sync Tuya - force_refresh: {force_refresh}, use_cache: {use_cache}")
        
        # ✅ NOUVEAU : Sync avec force_refresh
        if hasattr(device_service, 'sync_all_devices'):
            resultat = device_service.sync_all_devices(force_refresh=force_refresh)
        else:
            resultat = safe_device_service_call('sync_all_devices')
        
        if not resultat.get('success'):
            return jsonify({'error': resultat.get('error', 'Erreur synchronisation')}), 400
        
        return jsonify({
            'success': True,
            'message': resultat['message'],
            'statistiques': resultat.get('final_stats', {}),
            'scheduled_actions': resultat.get('scheduled_actions'),
            'import_stats': resultat.get('import_stats', {}),
            'options_used': {
                'force_refresh': force_refresh,
                'use_cache': use_cache
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur sync Tuya: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500
    
@device_bp.route('/non-assignes', methods=['GET'])
@superadmin_required
def lister_non_assignes(current_user):
    """Lister les appareils non-assignés avec cache"""
    try:
        refresh = request.args.get('refresh', 'true').lower() == 'true'
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # ✅ NOUVEAU : Utiliser get_non_assigned_devices optimisé
        if device_service and hasattr(device_service, 'get_non_assigned_devices'):
            resultat = device_service.get_non_assigned_devices(
                refresh_status=refresh, 
                use_cache=use_cache
            )
            
            if resultat.get('success'):
                return jsonify({
                    'success': True,
                    'data': resultat.get('devices', []),
                    'total': resultat.get('count', 0),
                    'stats': resultat.get('stats', {}),
                    'last_refresh': resultat.get('last_refresh'),
                    'message': resultat.get('message', 'Appareils récupérés'),
                    'options_used': {
                        'refresh': refresh,
                        'use_cache': use_cache
                    }
                }), 200
        
        # Fallback méthode legacy
        appareils_non_assignes = Device.query.filter_by(statut_assignation='non_assigne').all()
        
        return jsonify({
            'success': True,
            'data': [device.to_dict() for device in appareils_non_assignes],
            'total': len(appareils_non_assignes),
            'message': f'{len(appareils_non_assignes)} appareils non-assignés trouvés',
            'fallback_mode': True
        }), 200
        
    except Exception as e:
        print(f"Erreur liste non-assignés: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/assigner', methods=['POST'])
@superadmin_required
@validate_json_data(['client_id', 'site_id'])
def assigner_appareil(data, current_user, device_id):
    """Assigner un appareil à un client/site"""
    try:
        resultat = safe_device_service_call(
            'assign_device_to_client',
            device_id, 
            data['client_id'], 
            data['site_id'], 
            current_user.id
        )
        
        return jsonify({
            'success': resultat.get('success', False),
            'message': resultat.get('message', 'Erreur assignation'),
            'device': resultat.get('device')
        }), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur assignation appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/desassigner', methods=['POST'])
@superadmin_required
def desassigner_appareil(current_user, device_id):
    """Désassigner un appareil"""
    try:
        resultat = safe_device_service_call('unassign_device', device_id)
        
        return jsonify({
            'success': resultat.get('success', False),
            'message': resultat.get('message', 'Erreur désassignation'),
            'device': resultat.get('device')
        }), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur désassignation appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTES DE STATUT ET DIAGNOSTICS (enrichies) ===================

@device_bp.route('/<device_id>/statut', methods=['GET'])
@admin_required
def get_device_status(current_user, device_id):
    """Obtenir le statut actuel d'un appareil avec enrichissement"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # ✅ NOUVEAU : Utiliser get_device_real_time_data enrichi
        real_time_result = {}
        if device_service and hasattr(device_service, 'get_device_real_time_data'):
            real_time_result = device_service.get_device_real_time_data(
                device.tuya_device_id, use_cache=use_cache
            )
        else:
            # Fallback
            status_result = safe_device_service_call('get_device_status', device.tuya_device_id, use_cache)
            real_time_result = {
                'success': status_result.get('success', False),
                'data': status_result.get('values', {}),
                'is_online': device.en_ligne
            }
        
        response = {
            'success': True,
            'device_info': {
                'uuid': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom': device.nom_appareil
            },
            'statut_bdd': device.to_dict(include_stats=True, include_tuya_info=True),
            'real_time_status': real_time_result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # ✅ NOUVEAU : Ajouter enrichissements si extensions disponibles
        if device_service:
            # Analyse récente
            try:
                if hasattr(device_service, '_analysis_extension'):
                    analysis_summary = device_service._analysis_extension.get_device_analysis_summary(
                        device.id, hours_back=1, use_cache=True
                    )
                    if analysis_summary.get('success'):
                        response['recent_analysis'] = analysis_summary
            except:
                pass
            
            # Statut protection/programmation
            try:
                if hasattr(device_service, '_protection_extension'):
                    if device.protection_automatique_active:
                        response['protection_status'] = device.get_protection_config()
                    
                    if device.programmation_active:
                        schedule_status = device_service._protection_extension.get_device_schedule_status(device.id)
                        if schedule_status.get('success'):
                            response['schedule_status'] = schedule_status
            except:
                pass
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Erreur statut appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/ping', methods=['POST'])
@admin_required
def ping_device(current_user, device_id):
    """Tester la connectivité d'un appareil"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # ✅ NOUVEAU : Test ping avec vérification statut
        start_time = datetime.utcnow()
        
        if device_service and hasattr(device_service, 'check_device_online_status'):
            resultat = device_service.check_device_online_status(device.tuya_device_id)
        else:
            resultat = safe_device_service_call('get_device_status', device.tuya_device_id, False)
        
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds() * 1000  # en ms
        
        return jsonify({
            'success': True,
            'device_id': device_id,
            'online': resultat.get('success', False) or resultat.get('is_online', False),
            'response_time_ms': round(response_time, 2),
            'timestamp': datetime.utcnow().isoformat(),
            'ping_result': resultat
        }), 200
        
    except Exception as e:
        print(f"Erreur ping appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTES DE RECHERCHE ET STATISTIQUES (optimisées) ===================

@device_bp.route('/rechercher', methods=['GET', 'POST'])
@admin_required
def rechercher_appareils(current_user):
    """Rechercher des appareils par nom avec cache"""
    try:
        # Support GET et POST
        if request.method == 'GET':
            terme = request.args.get('q', '').strip()
        else:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Données JSON requises pour POST'}), 400
            terme = data.get('q', '').strip()
        
        if not terme or len(terme) < 2:
            return jsonify({'error': 'Terme de recherche requis (min 2 caractères)'}), 400
        
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # ✅ NOUVEAU : Recherche avec cache si service disponible
        if use_cache and device_service and hasattr(device_service, 'redis') and device_service.redis:
            try:
                import hashlib
                search_key = f"search:{current_user.id}:{hashlib.md5(terme.encode()).hexdigest()}"
                cached_result = device_service.redis.get(search_key)
                
                if cached_result:
                    import json
                    result = json.loads(cached_result)
                    result['from_cache'] = True
                    return jsonify(result), 200
            except:
                pass
        
        # Obtenir les appareils accessibles
        if current_user.is_superadmin():
            devices = Device.query.all()
        else:
            devices = Device.query.filter_by(client_id=current_user.client_id).all()
        
        # Filtrer selon les permissions et le terme de recherche
        terme_lower = terme.lower()
        resultats = []
        
        for device in devices:
            if not device.peut_etre_vu_par_utilisateur(current_user):
                continue
                
            # Vérifier correspondance
            device_dict = device.to_dict()
            nom = (device_dict.get('nom_appareil') or '').lower()
            type_app = (device_dict.get('type_appareil') or '').lower()
            emplacement = (device_dict.get('emplacement') or '').lower()
            tuya_id = (device_dict.get('tuya_device_id') or '').lower()
            
            if (terme_lower in nom or 
                terme_lower in type_app or 
                terme_lower in emplacement or
                terme_lower in tuya_id):
                resultats.append(device_dict)
        
        result = {
            'success': True,
            'data': resultats[:20],  # Limiter à 20 résultats
            'total': len(resultats),
            'terme_recherche': terme,
            'from_cache': False
        }
        
        # ✅ NOUVEAU : Mettre en cache
        if use_cache and device_service and hasattr(device_service, 'redis') and device_service.redis:
            try:
                import json
                device_service.redis.setex(search_key, 300, json.dumps(result))  # 5 minutes
            except:
                pass
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Erreur recherche appareils: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/statistiques', methods=['GET'])
@admin_required
def obtenir_statistiques(current_user):
    """Obtenir des statistiques sur les appareils avec cache"""
    try:
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        include_advanced = request.args.get('include_advanced', 'true').lower() == 'true'
        
        # ✅ NOUVEAU : Utiliser get_device_statistics enrichi
        if device_service and hasattr(device_service, 'get_device_statistics'):
            resultat = device_service.get_device_statistics(include_advanced=include_advanced)
            
            if resultat.get('success'):
                # Filtrer par permissions utilisateur si nécessaire
                stats = resultat.get('statistiques', {})
                
                if not current_user.is_superadmin():
                    # Recalculer pour le client seulement
                    client_devices = Device.query.filter_by(client_id=current_user.client_id).all()
                    accessible_devices = [
                        d for d in client_devices 
                        if d.peut_etre_vu_par_utilisateur(current_user)
                    ]
                    
                    # Statistiques client
                    client_stats = {
                        'total': len(accessible_devices),
                        'en_ligne': sum(1 for d in accessible_devices if d.en_ligne),
                        'hors_ligne': sum(1 for d in accessible_devices if not d.en_ligne),
                        'assignes': len(accessible_devices),  # Tous sont assignés au client
                        'actifs': sum(1 for d in accessible_devices if d.actif)
                    }
                    
                    if include_advanced:
                        client_stats.update({
                            'protection_active': sum(1 for d in accessible_devices if d.protection_automatique_active),
                            'programmation_active': sum(1 for d in accessible_devices if d.programmation_active)
                        })
                    
                    stats = client_stats
                
                return jsonify({
                    'success': True,
                    'data': stats,
                    'user_scope': 'superadmin' if current_user.is_superadmin() else 'client',
                    'include_advanced': include_advanced
                }), 200
        
        # Fallback calcul direct
        if current_user.is_superadmin():
            query = Device.query
        else:
            query = Device.query.filter_by(client_id=current_user.client_id)
        
        devices = query.all()
        
        # Filtrer par permissions
        accessible_devices = [
            d for d in devices 
            if d.peut_etre_vu_par_utilisateur(current_user)
        ]
        
        stats = {
            'total': len(accessible_devices),
            'assignes': sum(1 for d in accessible_devices if d.is_assigne()),
            'non_assignes': sum(1 for d in accessible_devices if not d.is_assigne()),
            'en_ligne': sum(1 for d in accessible_devices if d.en_ligne),
            'hors_ligne': sum(1 for d in accessible_devices if not d.en_ligne),
            'par_type': {},
            'protection_active': sum(1 for d in accessible_devices if d.protection_automatique_active),
            'programmation_active': sum(1 for d in accessible_devices if d.programmation_active)
        }
        
        # Statistiques par type
        for device in accessible_devices:
            device_type = device.type_appareil
            if device_type not in stats['par_type']:
                stats['par_type'][device_type] = 0
            stats['par_type'][device_type] += 1
        
        return jsonify({
            'success': True,
            'data': stats,
            'fallback_mode': True
        }), 200
        
    except Exception as e:
        print(f"Erreur statistiques: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== NOUVELLES ROUTES BATCH & ADMINISTRATION ===================

@device_bp.route('/batch-operation', methods=['POST'])
@admin_required
@validate_json_data(['operation', 'device_ids'])
def batch_operation(data, current_user):
    """Opération en lot sur plusieurs appareils avec cache"""
    try:
        operation = data['operation']
        device_ids = data['device_ids']
        use_cache = data.get('use_cache', True)
        
        if not isinstance(device_ids, list) or len(device_ids) == 0:
            return jsonify({'error': 'device_ids doit être une liste non vide'}), 400
        
        if len(device_ids) > 50:  # Limite de sécurité
            return jsonify({'error': 'Maximum 50 appareils par opération'}), 400
        
        # ✅ NOUVEAU : Utiliser batch_check_devices_status si disponible
        if operation in ['check_status', 'refresh_status'] and device_service:
            if hasattr(device_service, 'batch_check_devices_status'):
                batch_result = device_service.batch_check_devices_status(device_ids, use_cache)
                
                if batch_result.get('success'):
                    return jsonify({
                        'success': True,
                        'operation': operation,
                        'total_devices': len(device_ids),
                        'batch_result': batch_result,
                        'message': 'Vérification batch effectuée'
                    }), 200
        
        # ✅ NOUVEAU : Utiliser analyse batch si extension disponible et operation = 'analyze'
        if operation == 'analyze' and device_service and hasattr(device_service, '_analysis_extension'):
            try:
                analysis_result = device_service._analysis_extension.batch_analyze_devices(
                    device_ids, use_cache
                )
                
                if analysis_result.get('success'):
                    return jsonify({
                        'success': True,
                        'operation': operation,
                        'batch_analysis': analysis_result,
                        'message': 'Analyse batch effectuée'
                    }), 200
            except:
                pass
        
        # Fallback opérations individuelles
        resultats = []
        
        for device_id in device_ids:
            try:
                device = find_device_by_id_or_tuya_id(device_id)
                
                if not device:
                    resultats.append({
                        'device_id': device_id,
                        'success': False,
                        'error': 'Appareil non trouvé'
                    })
                    continue
                
                if not device.peut_etre_vu_par_utilisateur(current_user):
                    resultats.append({
                        'device_id': device_id,
                        'success': False,
                        'error': 'Accès interdit'
                    })
                    continue
                
                # Exécuter l'opération selon le type
                if operation == 'collecte_donnees':
                    resultat = safe_device_service_call('get_device_status', device.tuya_device_id, use_cache)
                elif operation == 'toggle_on':
                    if device.peut_etre_controle_par_utilisateur(current_user):
                        resultat = safe_device_service_call('control_device', device.tuya_device_id, 'switch', True, True)
                    else:
                        resultat = {'success': False, 'error': 'Pas de permission de contrôle'}
                elif operation == 'toggle_off':
                    if device.peut_etre_controle_par_utilisateur(current_user):
                        resultat = safe_device_service_call('control_device', device.tuya_device_id, 'switch', False, True)
                    else:
                        resultat = {'success': False, 'error': 'Pas de permission de contrôle'}
                else:
                    resultat = {'success': False, 'error': f'Opération {operation} non supportée'}
                
                resultats.append({
                    'device_id': device_id,
                    'device_name': device.nom_appareil,
                    'success': resultat.get('success', False),
                    'message': resultat.get('message', ''),
                    'result': resultat
                })
                
            except Exception as e:
                resultats.append({
                    'device_id': device_id,
                    'success': False,
                    'error': str(e)
                })
        
        # Statistiques
        succes = sum(1 for r in resultats if r['success'])
        echecs = len(resultats) - succes
        
        return jsonify({
            'success': True,
            'operation': operation,
            'total_devices': len(device_ids),
            'succes': succes,
            'echecs': echecs,
            'resultats': resultats,
            'options_used': {
                'use_cache': use_cache
            }
        }), 200
        
    except Exception as e:
        print(f"Erreur opération batch: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== NOUVELLES ROUTES DE CACHE & ADMINISTRATION ===================

@device_bp.route('/cache/statistics', methods=['GET'])
@admin_required
def get_cache_statistics(current_user):
    """Statistiques du cache DeviceService"""
    try:
        if not current_user.is_superadmin():
            return jsonify({'error': 'Accès superadmin requis'}), 403
        
        cache_stats = {}
        
        # ✅ NOUVEAU : Statistiques service principal
        if device_service and hasattr(device_service, 'get_cache_statistics'):
            main_stats = device_service.get_cache_statistics()
            cache_stats['device_service'] = main_stats
        
        # ✅ NOUVEAU : Statistiques extensions
        if device_service:
            # Protection Extension
            try:
                if hasattr(device_service, '_protection_extension'):
                    protection_stats = device_service._protection_extension.get_protection_cache_statistics()
                    cache_stats['protection_extension'] = protection_stats
            except:
                pass
            
            # Analysis Extension
            try:
                if hasattr(device_service, '_analysis_extension'):
                    analysis_stats = device_service._analysis_extension.get_analysis_cache_statistics()
                    cache_stats['analysis_extension'] = analysis_stats
            except:
                pass
        
        return jsonify({
            'success': True,
            'cache_statistics': cache_stats,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Erreur stats cache: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/cache/cleanup', methods=['POST'])
@admin_required
def cleanup_cache(current_user):
    """Nettoyer le cache DeviceService"""
    try:
        if not current_user.is_superadmin():
            return jsonify({'error': 'Accès superadmin requis'}), 403
        
        data = request.get_json() or {}
        cache_type = data.get('cache_type')  # None = tout nettoyer
        service_scope = data.get('service_scope', 'all')  # 'main', 'protection', 'analysis', 'all'
        
        cleanup_results = {}
        
        # ✅ NOUVEAU : Nettoyage par service
        if service_scope in ['main', 'all'] and device_service:
            try:
                if hasattr(device_service, 'cleanup_cache'):
                    main_cleanup = device_service.cleanup_cache(cache_type)
                    cleanup_results['device_service'] = main_cleanup
            except Exception as e:
                cleanup_results['device_service'] = {'success': False, 'error': str(e)}
        
        if service_scope in ['protection', 'all'] and device_service:
            try:
                if hasattr(device_service, '_protection_extension'):
                    protection_cleanup = device_service._protection_extension.cleanup_protection_cache(cache_type)
                    cleanup_results['protection_extension'] = protection_cleanup
            except Exception as e:
                cleanup_results['protection_extension'] = {'success': False, 'error': str(e)}
        
        if service_scope in ['analysis', 'all'] and device_service:
            try:
                if hasattr(device_service, '_analysis_extension'):
                    analysis_cleanup = device_service._analysis_extension.cleanup_analysis_cache(cache_type)
                    cleanup_results['analysis_extension'] = analysis_cleanup
            except Exception as e:
                cleanup_results['analysis_extension'] = {'success': False, 'error': str(e)}
        
        # Compter total des clés supprimées
        total_deleted = sum(
            result.get('deleted_keys', 0) 
            for result in cleanup_results.values() 
            if isinstance(result, dict)
        )
        
        return jsonify({
            'success': True,
            'message': f'Cache nettoyé - {total_deleted} clés supprimées',
            'cleanup_results': cleanup_results,
            'options_used': {
                'cache_type': cache_type,
                'service_scope': service_scope
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Erreur nettoyage cache: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/service/health', methods=['GET'])
@admin_required
def get_service_health(current_user):
    """Vérification santé complète du DeviceService"""
    try:
        if not current_user.is_superadmin():
            return jsonify({'error': 'Accès superadmin requis'}), 403
        
        health_results = {}
        
        # ✅ NOUVEAU : Santé service principal
        if device_service and hasattr(device_service, 'get_service_health'):
            main_health = device_service.get_service_health()
            health_results['device_service'] = main_health
        
        # ✅ NOUVEAU : Santé extensions
        if device_service:
            # Protection Extension
            try:
                if hasattr(device_service, '_protection_extension'):
                    protection_health = device_service._protection_extension.get_protection_service_health()
                    health_results['protection_extension'] = protection_health
            except:
                health_results['protection_extension'] = {
                    'success': False, 
                    'error': 'Extension non disponible'
                }
            
            # Analysis Extension
            try:
                if hasattr(device_service, '_analysis_extension'):
                    analysis_health = device_service._analysis_extension.get_analysis_service_health()
                    health_results['analysis_extension'] = analysis_health
            except:
                health_results['analysis_extension'] = {
                    'success': False, 
                    'error': 'Extension non disponible'
                }
        
        # Déterminer statut global
        all_services_healthy = all(
            result.get('health', {}).get('overall_status') in ['healthy', 'degraded']
            for result in health_results.values()
            if isinstance(result, dict) and result.get('success')
        )
        
        overall_status = 'healthy' if all_services_healthy else 'error'
        
        return jsonify({
            'success': True,
            'overall_status': overall_status,
            'health_checks': health_results,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Erreur health check: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== NOUVELLES ROUTES D'ANALYSE BATCH ===================



@device_bp.route('/analyze-client/<client_id>', methods=['POST'])
@admin_required
def analyze_client_devices(current_user, client_id):
    """Analyser tous les appareils d'un client"""
    try:
        if not current_user.is_superadmin() and current_user.client_id != client_id:
            return jsonify({'error': 'Accès interdit à ce client'}), 403
        
        data = request.get_json() or {}
        use_cache = data.get('use_cache', True)
        
        # ✅ NOUVEAU : Utiliser AlertService si disponible
        if device_service and hasattr(device_service, '_analysis_extension'):
            # Vérifier si AlertService est disponible
            try:
                if hasattr(device_service, '_alert_service'):
                    client_analysis = device_service._alert_service.analyser_client_complet(
                        client_id, {'use_cache': use_cache}
                    )
                    
                    if client_analysis.get('success'):
                        return jsonify(client_analysis), 200
                    else:
                        return jsonify(client_analysis), 400
            except:
                pass
        
        # Fallback
        return jsonify({
            'success': False,
            'error': 'Service analyse client non disponible',
            'message': 'Fonctionnalité analyse client non activée'
        }), 501
        
    except Exception as e:
        print(f"Erreur analyse client {client_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== NOUVELLES ROUTES ACTIONS PROGRAMMÉES ===================

@device_bp.route('/scheduled-actions/pending', methods=['GET'])
@admin_required
def get_pending_scheduled_actions(current_user):
    """Récupérer les actions programmées en attente"""
    try:
        limit = int(request.args.get('limit', 10))
        
        # ✅ NOUVEAU : Utiliser extension protection si disponible
        if device_service and hasattr(device_service, '_protection_extension'):
            actions_result = device_service._protection_extension.get_next_scheduled_actions(limit)
            
            if actions_result.get('success'):
                return jsonify(actions_result), 200
        
        # Fallback direct DB
        from app.models.scheduled_action import ScheduledAction
        
        upcoming_actions = ScheduledAction.query.filter(
            ScheduledAction.status == "pending",
            ScheduledAction.scheduled_time > datetime.utcnow()
        ).order_by(ScheduledAction.scheduled_time.asc()).limit(limit).all()
        
        actions_list = []
        for action in upcoming_actions:
            device = Device.query.get(action.appareil_id)
            if device and device.peut_etre_vu_par_utilisateur(current_user):
                actions_list.append({
                    "action_id": action.id,
                    "device_id": action.appareil_id,
                    "device_name": device.nom_appareil,
                    "action_type": action.action_type,
                    "scheduled_time": action.scheduled_time.isoformat(),
                    "time_until": str(action.scheduled_time - datetime.utcnow()),
                    "action_data": action.action_data
                })
        
        return jsonify({
            'success': True,
            'upcoming_actions': actions_list,
            'count': len(actions_list),
            'fallback_mode': True
        }), 200
        
    except Exception as e:
        print(f"Erreur actions programmées: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/execute-scheduled-actions', methods=['POST'])
@admin_required
def execute_scheduled_actions(current_user):
    """Exécuter les actions programmées en attente"""
    try:
        if not current_user.is_superadmin():
            return jsonify({'error': 'Accès superadmin requis'}), 403
        
        data = request.get_json() or {}
        max_actions = data.get('max_actions', 50)
        
        # ✅ NOUVEAU : Utiliser extension protection si disponible
        if device_service and hasattr(device_service, '_protection_extension'):
            execution_result = device_service._protection_extension.execute_scheduled_actions(max_actions)
            
            if execution_result.get('success'):
                return jsonify(execution_result), 200
            else:
                return jsonify(execution_result), 400
        
        return jsonify({
            'success': False,
            'error': 'Extension programmation non disponible',
            'message': 'Fonctionnalité exécution actions non activée'
        }), 501
        
    except Exception as e:
        print(f"Erreur exécution actions: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTES DE TEST ET DEBUG (améliorées) ===================

@device_bp.route('/test-tuya-connection', methods=['GET'])
@admin_required
def test_connexion_tuya(current_user):
    """Tester la connexion Tuya avec diagnostic détaillé"""
    try:
        # Test via device_service si disponible
        if device_service and hasattr(device_service, 'tuya_client'):
            info_connexion = device_service.tuya_client.get_connection_info()
            test_ok = device_service.tuya_client.check_connection()
        else:
            # Test direct
            try:
                from app.services.tuya_service import TuyaClient
                tuya_client = TuyaClient()
                connected = tuya_client.auto_connect_from_env()
                info_connexion = tuya_client.get_connection_info()
                test_ok = tuya_client.check_connection() if connected else False
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Erreur création client Tuya: {str(e)}'
                }), 500
        
        return jsonify({
            'success': True,
            'connection_info': info_connexion,
            'test_connection': test_ok,
            'message': 'Connexion Tuya OK' if test_ok else 'Connexion Tuya KO',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Erreur test connexion: {str(e)}")
        return jsonify({'error': f'Erreur test connexion: {str(e)}'}), 500

@device_bp.route('/debug/<device_id>', methods=['GET'])
@admin_required
def debug_device(current_user, device_id):
    """Debug complet d'un appareil"""
    try:
        if not current_user.is_superadmin():
            return jsonify({'error': 'Accès superadmin requis'}), 403
        
        debug_results = {}
        
        # ✅ NOUVEAU : Debug service principal
        if device_service and hasattr(device_service, 'diagnose_tuya_inconsistency'):
            main_debug = device_service.diagnose_tuya_inconsistency(device_id)
            debug_results['tuya_consistency'] = main_debug
        
        # ✅ NOUVEAU : Debug extensions
        if device_service:
            # Debug analyse
            try:
                if hasattr(device_service, '_analysis_extension'):
                    analysis_debug = device_service._analysis_extension.debug_device_analysis(device_id)
                    debug_results['analysis_debug'] = analysis_debug
            except:
                pass
            
            # Debug analyseur triphasé si disponible
            try:
                if hasattr(device_service, '_analyseur_triphase'):
                    triphase_debug = device_service._analyseur_triphase.debug_device_analysis(
                        device_id, show_cache_details=True
                    )
                    debug_results['triphase_debug'] = triphase_debug
            except:
                pass
        
        return jsonify({
            'success': True,
            'device_id': device_id,
            'debug_results': debug_results,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Erreur debug device {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== GESTION DES ERREURS (inchangée) ===================

@device_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Requête incorrecte'}), 400

@device_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Non autorisé'}), 401

@device_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Accès interdit'}), 403

@device_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource non trouvée'}), 404

@device_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur serveur interne'}), 500