from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.device_service import DeviceService
from app.models.user import User
from app.models.device import Device
from datetime import datetime, timedelta
from functools import wraps

# Créer le blueprint
device_bp = Blueprint('devices', __name__, url_prefix='/api/devices')

# Instance du service
device_service = DeviceService()

# =================== FONCTION UTILITAIRE AJOUTÉE ===================

def find_device_by_id_or_tuya_id(device_id):
    """Trouver un appareil par UUID ou tuya_device_id"""
    # D'abord essayer par UUID (ID primaire)
    device = Device.query.get(device_id)
    
    if not device:
        # Ensuite essayer par tuya_device_id
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

# =================== IMPORT ET SYNCHRONISATION TUYA ===================

@device_bp.route('/import-tuya', methods=['POST'])
@superadmin_required
def import_appareils_tuya(current_user):
    """Importer tous les appareils depuis Tuya - SUPERADMIN SEULEMENT"""
    try:
        resultat = device_service.import_tuya_devices()
        
        if not resultat.get('success'):
            return jsonify({'error': resultat.get('error', 'Erreur import')}), 400
        
        return jsonify({
            'success': True,
            'message': resultat['message'],
            'statistiques': resultat.get('statistiques', {})
        }), 200
        
    except Exception as e:
        print(f"Erreur import Tuya: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/sync-tuya', methods=['POST'])
@admin_required
def synchroniser_tuya(current_user):
    """Synchroniser les statuts avec Tuya"""
    try:
        resultat = device_service.sync_all_devices()
        
        if not resultat.get('success'):
            return jsonify({'error': resultat.get('error', 'Erreur synchronisation')}), 400
        
        return jsonify({
            'success': True,
            'message': resultat['message'],
            'statistiques': resultat
        }), 200
        
    except Exception as e:
        print(f"Erreur sync Tuya: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== GESTION DES ASSIGNATIONS ===================

@device_bp.route('/non-assignes', methods=['GET'])
@superadmin_required
def lister_non_assignes(current_user):
    """Lister les appareils non-assignés avec statuts réels - SUPERADMIN SEULEMENT"""
    try:
        # ✅ AJOUT: Paramètre pour contrôler le refresh
        refresh = request.args.get('refresh', 'true').lower() == 'true'
        
        resultat = device_service.get_non_assigned_devices(refresh_status=refresh)
        
        if not resultat.get('success'):
            return jsonify({'error': resultat.get('error', 'Erreur récupération')}), 400
        
        appareils = resultat.get('devices', [])
        
        return jsonify({
            'success': True,
            'data': appareils,
            'total': len(appareils),
            'stats': resultat.get('stats', {}),
            'last_refresh': resultat.get('last_refresh'),
            'message': resultat.get('message', f'{len(appareils)} appareils non-assignés trouvés')
        }), 200
        
    except Exception as e:
        print(f"Erreur liste non-assignés: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@device_bp.route('/<device_id>/assigner', methods=['POST'])
@superadmin_required
@validate_json_data(['client_id', 'site_id'])
def assigner_appareil(data, current_user, device_id):
    """Assigner un appareil à un client/site - SUPERADMIN SEULEMENT"""
    try:
        resultat = device_service.assign_device_to_client(
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
    """Désassigner un appareil - SUPERADMIN SEULEMENT"""
    try:
        resultat = device_service.unassign_device(device_id)
        
        return jsonify({
            'success': resultat.get('success', False),
            'message': resultat.get('message', 'Erreur désassignation'),
            'device': resultat.get('device')
        }), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur désassignation appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== GESTION CRUD DES APPAREILS ===================

@device_bp.route('/', methods=['GET'])
@admin_required
def lister_appareils(current_user):
    """Lister les appareils selon les permissions avec statuts réels"""
    try:
        # Paramètres optionnels
        site_id = request.args.get('site_id')
        inclure_non_assignes = request.args.get('inclure_non_assignes', 'false').lower() == 'true'
        refresh = request.args.get('refresh', 'true').lower() == 'true'  # ✅ AJOUT
        
        # Seul le superadmin peut inclure les non-assignés
        if inclure_non_assignes and not current_user.is_superadmin():
            return jsonify({'error': 'Seul le superadmin peut voir les appareils non-assignés'}), 403
        
        resultat = device_service.get_all_devices(
            current_user, 
            inclure_non_assignes, 
            refresh_status=refresh  # ✅ AJOUT
        )
        
        if not resultat.get('success'):
            return jsonify({'error': resultat.get('error', 'Erreur récupération')}), 403
        
        appareils = resultat.get('devices', [])
        
        # Filtrer par site_id si demandé
        if site_id:
            appareils = [a for a in appareils if a.get('site_id') == site_id]
        
        return jsonify({
            'success': True,
            'data': appareils,
            'total': len(appareils),
            'stats': resultat.get('stats', {}),  # ✅ AJOUT
            'last_sync': resultat.get('last_sync'),  # ✅ AJOUT
            'filtres': {
                'site_id': site_id,
                'inclure_non_assignes': inclure_non_assignes,
                'refresh': refresh  # ✅ AJOUT
            }
        }), 200
        
    except Exception as e:
        print(f"Erreur liste appareils: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@device_bp.route('/<device_id>', methods=['GET'])
@admin_required
def obtenir_appareil(current_user, device_id):
    """Obtenir les détails d'un appareil"""
    try:
        # ✅ CORRIGÉ: Utilise la fonction utilitaire
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        # Vérifier les permissions
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        return jsonify({
            'success': True,
            'data': device.to_dict(include_stats=True, include_tuya_info=True)
        }), 200
        
    except Exception as e:
        print(f"Erreur obtenir appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== CONTRÔLE DES APPAREILS ===================

@device_bp.route('/<device_id>/controle', methods=['POST'])
@admin_required
@validate_json_data(['action'])
def controler_appareil(data, current_user, device_id):
    """Contrôler un appareil (allumer, éteindre, etc.)"""
    try:
        # ✅ CORRIGÉ: Utilise la fonction utilitaire
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        action = data['action']
        valeur = data.get('valeur', True)
        
        # Utilise device_service pour contrôler
        if hasattr(device_service, 'control_device'):
            resultat = device_service.control_device(device.tuya_device_id, action, valeur)
        else:
            # Fallback si control_device n'existe pas
            resultat = device_service.toggle_device(device.tuya_device_id)
        
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

@device_bp.route('/<device_id>/toggle', methods=['POST'])
@admin_required
def toggle_appareil(current_user, device_id):
    """Basculer l'état d'un appareil (allumer/éteindre)"""
    try:
        # ✅ CORRIGÉ: Utilise la fonction utilitaire
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # Vérification assignation
        if not device.is_assigne():
            return jsonify({'error': 'Appareil non assigné à un client'}), 400
        
        # Récupérer l'état spécifique si fourni
        data = request.get_json() or {}
        etat = data.get('etat')  # True=allumer, False=éteindre, None=toggle
        
        # Toggle avec Tuya - utilise control_device si existe, sinon toggle_device
        if hasattr(device_service, 'control_device'):
            resultat = device_service.control_device(device.tuya_device_id, 'toggle', etat)
        else:
            resultat = device_service.toggle_device(device.tuya_device_id)
        
        return jsonify({
            'success': resultat.get('success', False),
            'message': resultat.get('message', 'Toggle exécuté'),
            'new_state': resultat.get('new_state'),
            'action': resultat.get('action'),
            'device_name': device.nom_appareil,
            'device_id': device.id,
            'tuya_device_id': device.tuya_device_id
        }), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur toggle device {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== COLLECTE DE DONNÉES ===================

@device_bp.route('/<device_id>/collecter-donnees', methods=['POST'])
@admin_required
def collecter_donnees(current_user, device_id):
    """Collecter manuellement les données d'un appareil"""
    try:
        # ✅ CORRIGÉ: Utilise la fonction utilitaire
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        resultat = device_service.get_device_status(device.tuya_device_id)
        
        return jsonify({
            'success': resultat.get('success', False),
            'message': 'Données collectées avec succès' if resultat.get('success') else 'Erreur collecte',
            'data': resultat
        }), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur collecte données {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== HISTORIQUE DES DONNÉES - CORRIGÉ ===================

@device_bp.route('/<device_id>/donnees', methods=['GET'])
@admin_required
def obtenir_donnees_appareil(current_user, device_id):
    """Obtenir l'historique des données d'un appareil"""
    try:
        # Paramètres de pagination et filtrage
        limite = int(request.args.get('limite', 100))
        page = int(request.args.get('page', 1))
        
        # Validation
        if limite > 1000:
            limite = 1000
        if page < 1:
            page = 1
        
        # ✅ CORRIGÉ: Utilise la fonction utilitaire
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # ✅ CORRIGÉ: Utilise device.id (UUID de la BDD)
        from app.models.device_data import DeviceData
        
        query = DeviceData.query.filter_by(appareil_id=device.id)\
                               .order_by(DeviceData.horodatage.desc())
        
        # Pagination
        offset = (page - 1) * limite
        donnees = query.offset(offset).limit(limite).all()
        total = query.count()
        
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
            }
        }), 200
        
    except Exception as e:
        print(f"Erreur données appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== GRAPHIQUES CORRIGÉS ===================

@device_bp.route('/<device_id>/graphique/tension', methods=['GET'])
@admin_required
def get_graphique_tension(current_user, device_id):
    """Obtenir les données de tension pour graphique"""
    try:
        # ✅ CORRIGÉ: Utilise la fonction utilitaire
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # Paramètres temporels
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        
        if not start_time or not end_time:
            # Par défaut : dernières 24h
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(hours=24)
            start_time = int(start_dt.timestamp() * 1000)
            end_time = int(end_dt.timestamp() * 1000)
        else:
            start_time = int(start_time)
            end_time = int(end_time)
        
        # ✅ CORRIGÉ: Utilise device.id au lieu de device_id
        from app.models.device_data import DeviceData
        start_dt = datetime.fromtimestamp(start_time / 1000)
        end_dt = datetime.fromtimestamp(end_time / 1000)
        
        donnees_bdd = DeviceData.query.filter(
            DeviceData.appareil_id == device.id,  # ✅ device.id au lieu de device_id
            DeviceData.horodatage >= start_dt,
            DeviceData.horodatage <= end_dt,
            DeviceData.tension.isnot(None)
        ).order_by(DeviceData.horodatage.asc()).all()
        
        # Optionnel : données Tuya en temps réel
        donnees_tuya = []
        try:
            if hasattr(device_service.tuya_client, 'get_device_logs_formatted'):
                tuya_result = device_service.tuya_client.get_device_logs_formatted(
                    device.tuya_device_id, "cur_voltage", 24
                )
                if tuya_result.get('success'):
                    donnees_tuya = tuya_result.get('data', [])
        except:
            pass  # Ignorer erreurs Tuya pour le graphique
        
        return jsonify({
            'success': True,
            'device_info': {
                'uuid': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom': device.nom_appareil
            },
            'period': {'start_time': start_time, 'end_time': end_time},
            'donnees_bdd': [
                {
                    'timestamp': d.horodatage.isoformat(),
                    'value': d.tension,
                    'horodatage': int(d.horodatage.timestamp() * 1000)
                } for d in donnees_bdd
            ],
            'donnees_tuya': donnees_tuya,
            'count_bdd': len(donnees_bdd),
            'count_tuya': len(donnees_tuya)
        }), 200
        
    except Exception as e:
        print(f"Erreur graphique tension {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/graphique/courant', methods=['GET'])
@admin_required
def get_graphique_courant(current_user, device_id):
    """Obtenir les données de courant pour graphique"""
    try:
        # ✅ CORRIGÉ: Utilise la fonction utilitaire
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        
        if not start_time or not end_time:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(hours=24)
            start_time = int(start_dt.timestamp() * 1000)
            end_time = int(end_dt.timestamp() * 1000)
        else:
            start_time = int(start_time)
            end_time = int(end_time)
        
        from app.models.device_data import DeviceData
        start_dt = datetime.fromtimestamp(start_time / 1000)
        end_dt = datetime.fromtimestamp(end_time / 1000)
        
        donnees_bdd = DeviceData.query.filter(
            DeviceData.appareil_id == device.id,  # ✅ device.id
            DeviceData.horodatage >= start_dt,
            DeviceData.horodatage <= end_dt,
            DeviceData.courant.isnot(None)
        ).order_by(DeviceData.horodatage.asc()).all()
        
        return jsonify({
            'success': True,
            'device_info': {
                'uuid': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom': device.nom_appareil
            },
            'period': {'start_time': start_time, 'end_time': end_time},
            'donnees_bdd': [
                {
                    'timestamp': d.horodatage.isoformat(),
                    'value': d.courant,
                    'horodatage': int(d.horodatage.timestamp() * 1000)
                } for d in donnees_bdd
            ]
        }), 200
        
    except Exception as e:
        print(f"Erreur graphique courant {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/graphique/puissance', methods=['GET'])
@admin_required
def get_graphique_puissance(current_user, device_id):
    """Obtenir les données de puissance pour graphique"""
    try:
        # ✅ CORRIGÉ: Utilise la fonction utilitaire
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        
        if not start_time or not end_time:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(hours=24)
            start_time = int(start_dt.timestamp() * 1000)
            end_time = int(end_dt.timestamp() * 1000)
        else:
            start_time = int(start_time)
            end_time = int(end_time)
        
        from app.models.device_data import DeviceData
        start_dt = datetime.fromtimestamp(start_time / 1000)
        end_dt = datetime.fromtimestamp(end_time / 1000)
        
        donnees_bdd = DeviceData.query.filter(
            DeviceData.appareil_id == device.id,  # ✅ device.id
            DeviceData.horodatage >= start_dt,
            DeviceData.horodatage <= end_dt,
            DeviceData.puissance.isnot(None)
        ).order_by(DeviceData.horodatage.asc()).all()
        
        return jsonify({
            'success': True,
            'device_info': {
                'uuid': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom': device.nom_appareil
            },
            'period': {'start_time': start_time, 'end_time': end_time},
            'donnees_bdd': [
                {
                    'timestamp': d.horodatage.isoformat(),
                    'value': d.puissance,
                    'horodatage': int(d.horodatage.timestamp() * 1000)
                } for d in donnees_bdd
            ]
        }), 200
        
    except Exception as e:
        print(f"Erreur graphique puissance {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/statut', methods=['GET'])
@admin_required
def get_device_status_enhanced(current_user, device_id):
    """Obtenir le statut actuel d'un appareil avec vérification en temps réel"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # ✅ AMÉLIORATION: Vérifier le statut en ligne d'abord
        check_online = device_service.check_device_online_status(device.tuya_device_id)
        
        # ✅ AMÉLIORATION: Données temps réel si en ligne
        real_time_data = {}
        if check_online.get('is_online', False):
            real_time_result = device_service.get_device_real_time_data(device.tuya_device_id)
            if real_time_result.get('success'):
                real_time_data = real_time_result.get('data', {})
        
        return jsonify({
            'success': True,
            'device_id': device_id,
            'device_info': {
                'uuid': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom': device.nom_appareil
            },
            'statut_bdd': device.to_dict(include_stats=True, include_tuya_info=True),
            'statut_online': {
                'is_online': check_online.get('is_online', False),
                'checked_at': check_online.get('checked_at'),
                'changed': check_online.get('changed', False)
            },
            'real_time_data': real_time_data,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Erreur statut appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== STATISTIQUES ===================

@device_bp.route('/statistiques', methods=['GET'])
@admin_required
def obtenir_statistiques(current_user):
    """Obtenir des statistiques sur les appareils"""
    try:
        if hasattr(device_service, 'get_device_statistics'):
            resultat = device_service.get_device_statistics()
        else:
            # Fallback : statistiques basiques
            from app.models.device import Device
            total = Device.query.count()
            assignes = Device.query.filter_by(statut_assignation='assigne').count()
            non_assignes = Device.query.filter_by(statut_assignation='non_assigne').count()
            
            resultat = {
                'success': True,
                'statistiques': {
                    'total': total,
                    'assignes': assignes,
                    'non_assignes': non_assignes
                }
            }
        
        if not resultat.get('success'):
            return jsonify({'error': resultat.get('error', 'Erreur statistiques')}), 400
        
        return jsonify({
            'success': True,
            'data': resultat.get('statistiques', {})
        }), 200
        
    except Exception as e:
        print(f"Erreur statistiques: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500



@device_bp.route('/statistiques-temps-reel', methods=['GET'])
@admin_required
def statistiques_temps_reel(current_user):
    """Obtenir les statistiques en temps réel avec refresh des statuts"""
    try:
        # Refresh les statuts avant de calculer les stats
        if current_user.is_superadmin():
            refresh_result = device_service.refresh_all_device_statuses()
        
        # Récupérer les stats
        if hasattr(device_service, 'get_device_statistics'):
            resultat = device_service.get_device_statistics()
        else:
            # Fallback
            from app.models.device import Device
            
            if current_user.is_superadmin():
                total = Device.query.count()
                assignes = Device.query.filter_by(statut_assignation='assigne').count()
                non_assignes = Device.query.filter_by(statut_assignation='non_assigne').count()
                en_ligne = Device.query.filter_by(en_ligne=True).count()
                hors_ligne = Device.query.filter_by(en_ligne=False).count()
            else:
                user_devices = Device.query.filter_by(client_id=current_user.client_id).all()
                total = len(user_devices)
                assignes = total
                non_assignes = 0
                en_ligne = sum(1 for d in user_devices if d.en_ligne)
                hors_ligne = total - en_ligne
            
            resultat = {
                'success': True,
                'statistiques': {
                    'total': total,
                    'assignes': assignes,
                    'non_assignes': non_assignes,
                    'en_ligne': en_ligne,
                    'hors_ligne': hors_ligne
                }
            }
        
        # Ajouter métadonnées
        stats = resultat.get('statistiques', {})
        stats['last_refresh'] = datetime.utcnow().isoformat()
        stats['user_type'] = 'superadmin' if current_user.is_superadmin() else 'client'
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        print(f"Erreur statistiques temps réel: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500        

# =================== ROUTES UTILITAIRES ===================

@device_bp.route('/rechercher', methods=['GET', 'POST'])
@admin_required
def rechercher_appareils(current_user):
    """Rechercher des appareils par nom"""
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
        
        # Obtenir tous les appareils accessibles
        if hasattr(device_service, 'get_all_devices'):
            resultat = device_service.get_all_devices(current_user)
            if not resultat.get('success'):
                return jsonify({'error': resultat.get('error', 'Erreur récupération')}), 403
            appareils = resultat.get('devices', [])
        else:
            # Fallback : requête directe
            if current_user.is_superadmin():
                devices = Device.query.all()
            else:
                devices = Device.query.filter_by(client_id=current_user.client_id).all()
            appareils = [d.to_dict() for d in devices]
        
        # Filtrer par terme de recherche
        terme_lower = terme.lower()
        resultats = []
        
        for appareil in appareils:
            # ✅ CORRIGÉ: Gestion des valeurs None
            nom = (appareil.get('nom_appareil') or '').lower()
            type_app = (appareil.get('type_appareil') or '').lower()
            emplacement = (appareil.get('emplacement') or '').lower()
            tuya_id = (appareil.get('tuya_device_id') or '').lower()
            
            if (terme_lower in nom or 
                terme_lower in type_app or 
                terme_lower in emplacement or
                terme_lower in tuya_id):
                resultats.append(appareil)
        
        return jsonify({
            'success': True,
            'data': resultats[:20],  # Limiter à 20 résultats
            'total': len(resultats),
            'terme_recherche': terme
        }), 200
        
    except Exception as e:
        print(f"Erreur recherche appareils: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTES DE TEST ===================

@device_bp.route('/test-tuya-connection', methods=['GET'])
@admin_required
def test_connexion_tuya(current_user):
    """Tester la connexion Tuya - FORCÉ NOUVELLE INSTANCE"""
    try:
        # FORCE une nouvelle instance au lieu d'utiliser device_service.tuya_client
        from app.services.tuya_service import TuyaClient
        tuya_client = TuyaClient()  # ← NOUVELLE INSTANCE
        
        # Test de connexion
        connected = tuya_client.auto_connect_from_env()
        
        # Info connexion
        info_connexion = tuya_client.get_connection_info()
        
        # Test simple
        test_ok = tuya_client.check_connection() if connected else False
        
        return jsonify({
            'success': True,
            'connection_info': info_connexion,
            'test_connection': test_ok,
            'message': 'Connexion Tuya OK' if test_ok else 'Connexion Tuya KO'
        }), 200
        
    except Exception as e:
        print(f"Erreur test connexion: {str(e)}")
        return jsonify({'error': f'Erreur test connexion: {str(e)}'}), 500

@device_bp.route('/debug-direct', methods=['GET'])
@admin_required
def debug_direct(current_user):
    """Debug direct avec prints en live"""
    try:
        print("🔧 DEBUG DIRECT - DÉBUT")
        
        # Test 1: TuyaClient direct
        from app.services.tuya_service import TuyaClient
        client = TuyaClient()
        
        print(f"🔧 TuyaClient créé:")
        print(f"   Access ID: {client.access_id}")
        print(f"   Access Secret: {client.access_secret[:10] if client.access_secret else 'None'}...")
        print(f"   Endpoint: {client.endpoint}")
        
        # Test 2: Connexion manuelle
        print("🔧 Test connexion manuelle...")
        result = client.auto_connect_from_env()
        print(f"   Résultat connexion: {result}")
        
        # Test 3: Info après connexion
        info = client.get_connection_info()
        print(f"   Info connexion: {info}")
        
        # Test 4: Test check_connection
        check = False
        if result:
            check = client.check_connection()
            print(f"   Check connexion: {check}")
        
        return jsonify({
            'test_results': {
                'client_created': True,
                'connection_result': result,
                'connection_info': info,
                'check_result': check
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur debug direct: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

@device_bp.route('/debug-files', methods=['GET'])
@admin_required
def debug_files(current_user):
    """Debug pour voir les fichiers et imports"""
    try:
        import os
        import sys
        
        # Info système
        info_systeme = {
            'python_version': sys.version,
            'working_directory': os.getcwd(),
            'python_path': sys.path[:5]  # Premiers 5 chemins
        }
        
        # Test imports
        imports_test = {}
        try:
            from app.services.tuya_service import TuyaClient
            imports_test['TuyaClient'] = 'OK'
        except Exception as e:
            imports_test['TuyaClient'] = f'ERREUR: {str(e)}'
        
        try:
            from app.services.device_service import DeviceService
            imports_test['DeviceService'] = 'OK'
        except Exception as e:
            imports_test['DeviceService'] = f'ERREUR: {str(e)}'
        
        try:
            from app.models.device import Device
            imports_test['Device'] = 'OK'
        except Exception as e:
            imports_test['Device'] = f'ERREUR: {str(e)}'
        
        # Variables d'environnement
        env_vars = {
            'ACCESS_ID': os.getenv('ACCESS_ID', 'NON_DEFINI')[:10] + '...' if os.getenv('ACCESS_ID') else 'NON_DEFINI',
            'ACCESS_KEY': 'DEFINI' if os.getenv('ACCESS_KEY') else 'NON_DEFINI',
            'TUYA_ENDPOINT': os.getenv('TUYA_ENDPOINT', 'NON_DEFINI')
        }
        
        return jsonify({
            'success': True,
            'info_systeme': info_systeme,
            'imports_test': imports_test,
            'env_vars': env_vars,
            'device_service_methods': [method for method in dir(device_service) if not method.startswith('_')]
        })
        
    except Exception as e:
        print(f"Erreur debug files: {str(e)}")
        return jsonify({'error': f'Erreur debug: {str(e)}'}), 500

# =================== ROUTES SUPPLÉMENTAIRES UTILES ===================

@device_bp.route('/<device_id>/historique', methods=['GET'])
@admin_required
def get_device_history(current_user, device_id):
    """Obtenir l'historique complet d'un appareil"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # Paramètres
        limit = int(request.args.get('limit', 100))
        hours_back = int(request.args.get('hours_back', 24))
        
        # Utilise device_service si disponible
        if hasattr(device_service, 'get_device_history'):
            resultat = device_service.get_device_history(device.tuya_device_id, limit, hours_back)
        else:
            # Fallback : récupération directe
            from app.models.device_data import DeviceData
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            data = DeviceData.query.filter_by(appareil_id=device.id)\
                                  .filter(DeviceData.horodatage >= start_time)\
                                  .order_by(DeviceData.horodatage.desc())\
                                  .limit(limit).all()
            
            resultat = {
                'success': True,
                'device_id': device.tuya_device_id,
                'hours_back': hours_back,
                'count': len(data),
                'data': [d.to_dict() for d in data]
            }
        
        return jsonify(resultat), 200
        
    except Exception as e:
        print(f"Erreur historique appareil {device_id}: {str(e)}")
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
        
        # Test simple de connectivité via Tuya
        start_time = datetime.utcnow()
        resultat = device_service.get_device_status(device.tuya_device_id)
        end_time = datetime.utcnow()
        
        response_time = (end_time - start_time).total_seconds() * 1000  # en ms
        
        return jsonify({
            'success': True,
            'device_id': device_id,
            'online': resultat.get('success', False),
            'response_time_ms': round(response_time, 2),
            'timestamp': datetime.utcnow().isoformat(),
            'ping_result': resultat
        }), 200
        
    except Exception as e:
        print(f"Erreur ping appareil {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/batch-operation', methods=['POST'])
@admin_required
@validate_json_data(['operation', 'device_ids'])
def batch_operation(data, current_user):
    """Opération en lot sur plusieurs appareils"""
    try:
        operation = data['operation']
        device_ids = data['device_ids']
        
        if not isinstance(device_ids, list) or len(device_ids) == 0:
            return jsonify({'error': 'device_ids doit être une liste non vide'}), 400
        
        if len(device_ids) > 50:  # Limite de sécurité
            return jsonify({'error': 'Maximum 50 appareils par opération'}), 400
        
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
                    resultat = device_service.get_device_status(device.tuya_device_id)
                elif operation == 'toggle_on':
                    resultat = device_service.control_device(device.tuya_device_id, 'switch', True)
                elif operation == 'toggle_off':
                    resultat = device_service.control_device(device.tuya_device_id, 'switch', False)
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
            'resultats': resultats
        }), 200
        
    except Exception as e:
        print(f"Erreur opération batch: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500




# =================== ROUTES MANQUANTES À AJOUTER ===================

@device_bp.route('/refresh-all-statuses', methods=['POST'])
@admin_required
def refresh_all_statuses(current_user):
    """Forcer la synchronisation de tous les statuts d'appareils"""
    try:
        resultat = device_service.refresh_all_device_statuses()
        
        return jsonify({
            'success': resultat.get('success', False),
            'message': resultat.get('message', 'Synchronisation effectuée'),
            'stats': resultat.get('stats', {}),
            'timestamp': resultat.get('timestamp')
        }), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur refresh statuts: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/check-status', methods=['GET'])
@admin_required
def check_device_status(current_user, device_id):
    """Vérifier rapidement le statut en ligne d'un appareil"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        resultat = device_service.check_device_online_status(device.tuya_device_id)
        
        return jsonify({
            'success': resultat.get('success', False),
            'device_info': {
                'uuid': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom': device.nom_appareil
            },
            'is_online': resultat.get('is_online', False),
            'changed': resultat.get('changed', False),
            'checked_at': resultat.get('checked_at')
        }), 200
        
    except Exception as e:
        print(f"Erreur check status {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/force-status-update', methods=['POST'])
@admin_required
def force_status_update(current_user, device_id):
    """Forcer la mise à jour du statut depuis l'endpoint liste Tuya"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        resultat = device_service.force_status_from_list_endpoint(device.tuya_device_id)
        
        return jsonify({
            'success': resultat.get('success', False),
            'device_info': {
                'uuid': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom': device.nom_appareil
            },
            'old_status': resultat.get('old_status'),
            'new_status': resultat.get('new_status'),
            'changed': resultat.get('changed', False),
            'source': resultat.get('source')
        }), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur force status {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/<device_id>/real-time-data', methods=['GET'])
@admin_required
def get_real_time_data(current_user, device_id):
    """Récupérer les données en temps réel avec statut"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        resultat = device_service.get_device_real_time_data(device.tuya_device_id)
        
        return jsonify({
            'success': resultat.get('success', False),
            'device_info': {
                'uuid': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom': device.nom_appareil
            },
            'is_online': resultat.get('is_online', False),
            'data': resultat.get('data', {}),
            'timestamp': resultat.get('timestamp'),
            'message': resultat.get('message', '')
        }), 200
        
    except Exception as e:
        print(f"Erreur real-time data {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/batch-status-check', methods=['POST'])
@admin_required
@validate_json_data(['device_ids'])
def batch_status_check(data, current_user):
    """Vérifier le statut de plusieurs appareils en une fois"""
    try:
        device_ids = data['device_ids']
        
        if not isinstance(device_ids, list) or len(device_ids) == 0:
            return jsonify({'error': 'device_ids doit être une liste non vide'}), 400
        
        if len(device_ids) > 50:
            return jsonify({'error': 'Maximum 50 appareils par vérification'}), 400
        
        # Convertir les UUIDs en tuya_device_ids si nécessaire
        tuya_device_ids = []
        device_mapping = {}
        
        for device_id in device_ids:
            device = find_device_by_id_or_tuya_id(device_id)
            if device and device.peut_etre_vu_par_utilisateur(current_user):
                tuya_device_ids.append(device.tuya_device_id)
                device_mapping[device.tuya_device_id] = {
                    'uuid': device.id,
                    'nom': device.nom_appareil,
                    'original_id': device_id
                }
        
        # Vérification batch via device_service
        resultat = device_service.batch_check_devices_status(tuya_device_ids)
        
        # Enrichir les résultats avec les infos des appareils
        if resultat.get('success'):
            enriched_results = []
            for result in resultat.get('results', []):
                tuya_id = result['device_id']
                device_info = device_mapping.get(tuya_id, {})
                
                enriched_results.append({
                    **result,
                    'device_uuid': device_info.get('uuid'),
                    'device_nom': device_info.get('nom'),
                    'original_device_id': device_info.get('original_id')
                })
            
            resultat['results'] = enriched_results
        
        return jsonify(resultat), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur batch status check: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/debug/tuya-inconsistency/<device_id>', methods=['GET'])
@admin_required
def debug_tuya_inconsistency(current_user, device_id):
    """Diagnostiquer les incohérences entre endpoints Tuya"""
    try:
        device = find_device_by_id_or_tuya_id(device_id)
        
        if not device:
            return jsonify({'error': f'Appareil non trouvé: {device_id}'}), 404
        
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        resultat = device_service.diagnose_tuya_inconsistency(device.tuya_device_id)
        
        return jsonify({
            'success': resultat.get('success', False),
            'device_info': {
                'uuid': device.id,
                'tuya_device_id': device.tuya_device_id,
                'nom': device.nom_appareil
            },
            'diagnostic': {
                'endpoint_liste': resultat.get('endpoint_liste', {}),
                'endpoint_individuel': resultat.get('endpoint_individuel', {}),
                'consistent': resultat.get('consistent', False),
                'recommended_source': resultat.get('recommended_source')
            }
        }), 200
        
    except Exception as e:
        print(f"Erreur diagnostic Tuya {device_id}: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@device_bp.route('/smart-sync', methods=['POST'])
@admin_required
def smart_sync(current_user):
    """Synchronisation intelligente selon les permissions utilisateur"""
    try:
        data = request.get_json() or {}
        force_full_sync = data.get('force_full_sync', False)
        
        if current_user.is_superadmin():
            # Superadmin peut faire une sync complète
            if force_full_sync:
                resultat = device_service.sync_all_devices()
            else:
                resultat = device_service.refresh_all_device_statuses()
        else:
            # Utilisateur normal : refresh seulement ses appareils
            resultat = device_service.get_all_devices(current_user, False, True)
            # Transformer en format sync
            if resultat.get('success'):
                stats = resultat.get('stats', {})
                resultat = {
                    'success': True,
                    'message': f"Synchronisation utilisateur: {stats.get('total', 0)} appareils",
                    'stats': stats,
                    'sync_type': 'user_devices_only'
                }
        
        return jsonify({
            'success': resultat.get('success', False),
            'message': resultat.get('message', 'Synchronisation effectuée'),
            'stats': resultat.get('stats', {}),
            'sync_type': resultat.get('sync_type', 'full' if current_user.is_superadmin() else 'user'),
            'timestamp': datetime.utcnow().isoformat()
        }), 200 if resultat.get('success') else 400
        
    except Exception as e:
        print(f"Erreur smart sync: {str(e)}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== GESTION DES ERREURS ===================

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