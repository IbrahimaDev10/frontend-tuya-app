from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.site_service import SiteService
from app.models.user import User
from functools import wraps

# Créer le blueprint
site_bp = Blueprint('sites', __name__, url_prefix='/api/sites')

# Instance du service
site_service = SiteService()

def admin_required(f):
    """Décorateur pour les routes admin"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            current_user = User.query.get(user_id)
            
            if not current_user:
                return jsonify({'error': 'Utilisateur non trouvé'}), 401
            
            if not current_user.actif:
                return jsonify({'error': 'Compte désactivé'}), 401
            
            if not current_user.is_admin():
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
            
            if not current_user:
                return jsonify({'error': 'Utilisateur non trouvé'}), 401
            
            if not current_user.actif:
                return jsonify({'error': 'Compte désactivé'}), 401
            
            if not current_user.is_superadmin():
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
                missing_fields = []
                for field in required_fields:
                    if not data.get(field):
                        missing_fields.append(field)
                
                if missing_fields:
                    return jsonify({
                        'error': f'Champs requis manquants: {", ".join(missing_fields)}'
                    }), 400
            
            return f(data, *args, **kwargs)
        return decorated_function
    return decorator

# =================== GESTION CRUD DES SITES ===================

@site_bp.route('/', methods=['POST'])
@superadmin_required
@validate_json_data(['nom_site', 'adresse', 'client_id'])
def creer_site(data, current_user):  # ✅ CORRIGÉ : data en premier
    """Créer un nouveau site - SUPERADMIN SEULEMENT"""
    try:
        site, erreur = site_service.creer_site(data, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        return jsonify({
            'success': True,
            'message': f"Site '{site.nom_site}' créé avec succès",
            'site': site.to_dict(include_map_link=True)
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@site_bp.route('/', methods=['GET'])
@admin_required
def lister_sites(current_user):
    """Lister les sites selon les permissions"""
    try:
        # Paramètre optionnel pour filtrer par client (superadmin seulement)
        client_id = request.args.get('client_id')
        
        # Vérification des permissions pour le filtre client_id
        if client_id and not current_user.is_superadmin():
            return jsonify({'error': 'Seul le superadmin peut filtrer par client'}), 403
        
        sites, erreur = site_service.lister_sites(current_user, client_id)
        
        if erreur:
            return jsonify({'error': erreur}), 403
        
        return jsonify({
            'success': True,
            'data': sites,
            'total': len(sites),
            'client_id_filtre': client_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@site_bp.route('/<site_id>', methods=['GET'])
@admin_required
def obtenir_site(current_user, site_id):
    """Obtenir les détails d'un site"""
    try:
        site, erreur = site_service.obtenir_site(site_id, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 404 if 'non trouvé' in erreur else 403
        
        return jsonify({
            'success': True,
            'data': site
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@site_bp.route('/<site_id>', methods=['PUT'])
@superadmin_required
def modifier_site(current_user, site_id):
    """Modifier un site existant - SUPERADMIN SEULEMENT"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        site, erreur = site_service.modifier_site(site_id, data, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        return jsonify({
            'success': True,
            'message': f"Site '{site.nom_site}' modifié avec succès",
            'site': site.to_dict(include_map_link=True)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@site_bp.route('/<site_id>/desactiver', methods=['POST'])
@superadmin_required
def desactiver_site(current_user, site_id):
    """Désactiver un site - SUPERADMIN SEULEMENT"""
    try:
        succes, message = site_service.desactiver_site(site_id, current_user)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@site_bp.route('/<site_id>/reactiver', methods=['POST'])
@superadmin_required
def reactiver_site(current_user, site_id):
    """Réactiver un site désactivé - SUPERADMIN SEULEMENT"""
    try:
        succes, message = site_service.reactiver_site(site_id, current_user)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@site_bp.route('/<site_id>', methods=['DELETE'])
@superadmin_required
def supprimer_site(current_user, site_id):
    """Supprimer définitivement un site - SUPERADMIN SEULEMENT"""
    try:
        # Paramètre optionnel pour forcer la suppression
        forcer = request.args.get('forcer', 'false').lower() == 'true'
        
        succes, message = site_service.supprimer_site(site_id, current_user, forcer)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== FONCTIONNALITÉS GÉOGRAPHIQUES ===================

@site_bp.route('/<site_id>/geocoder', methods=['POST'])
@superadmin_required
def geocoder_site(current_user, site_id):
    """Forcer le géocodage d'un site - SUPERADMIN SEULEMENT"""
    try:
        succes, message = site_service.geocoder_site(site_id, current_user)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@site_bp.route('/<site_id>/sites-proches', methods=['GET'])
@admin_required
def sites_proches(current_user, site_id):
    """Trouver les sites proches d'un site donné"""
    try:
        # Paramètre rayon (par défaut 10km, max selon permissions)
        try:
            radius_km = int(request.args.get('radius', 10))
            if radius_km <= 0:
                raise ValueError("Le rayon doit être positif")
        except (ValueError, TypeError):
            return jsonify({'error': 'Paramètre radius invalide (entier positif requis)'}), 400
        
        sites_proches_data, erreur = site_service.sites_proches(site_id, radius_km, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        return jsonify({
            'success': True,
            'site_reference_id': site_id,
            'radius_km': radius_km,
            'sites_proches': sites_proches_data,
            'total': len(sites_proches_data)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@site_bp.route('/carte', methods=['GET'])
@admin_required
def sites_pour_carte(current_user):
    """Obtenir les sites avec coordonnées pour affichage carte"""
    try:
        # Paramètre optionnel pour filtrer par client (superadmin seulement)
        client_id = request.args.get('client_id')
        
        if client_id and not current_user.is_superadmin():
            return jsonify({'error': 'Seul le superadmin peut filtrer par client'}), 403
        
        sites, erreur = site_service.lister_sites(current_user, client_id)
        
        if erreur:
            return jsonify({'error': erreur}), 403
        
        # Filtrer seulement les sites avec coordonnées
        sites_avec_coords = [
            site for site in sites 
            if site.get('has_coordinates', False)
        ]
        
        # Format optimisé pour carte
        sites_carte = []
        for site in sites_avec_coords:
            sites_carte.append({
                'id': site['id'],
                'nom_site': site['nom_site'],
                'latitude': site['latitude'],
                'longitude': site['longitude'],
                'adresse': site['adresse'],
                'ville': site['ville'],
                'nb_appareils': site['nb_appareils'],
                'client_nom': site.get('client_nom'),
                'map_link': site.get('map_link'),
                'stats': site.get('stats', {})
            })
        
        return jsonify({
            'success': True,
            'sites': sites_carte,
            'total_sites': len(sites),
            'sites_avec_coordonnees': len(sites_carte),
            'taux_geocodage': round(len(sites_carte) / len(sites) * 100, 2) if sites else 0
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== STATISTIQUES ===================

@site_bp.route('/statistiques', methods=['GET'])
@admin_required
def obtenir_statistiques(current_user):
    """Obtenir des statistiques sur les sites"""
    try:
        # Paramètre optionnel pour client spécifique (superadmin seulement)
        client_id = request.args.get('client_id')
        
        if client_id and not current_user.is_superadmin():
            return jsonify({'error': 'Seul le superadmin peut voir les stats par client'}), 403
        
        stats, erreur = site_service.obtenir_statistiques_sites(current_user, client_id)
        
        if erreur:
            return jsonify({'error': erreur}), 403
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTES UTILITAIRES ===================

@site_bp.route('/rechercher', methods=['GET', 'POST'])
@admin_required
def rechercher_sites(current_user):
    """Rechercher des sites par nom ou adresse"""
    try:
        # Support GET (query string) et POST (JSON)
        if request.method == 'GET':
            terme = request.args.get('q', '').strip()
        else:  # POST
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Données JSON requises pour POST'}), 400
            terme = data.get('q', '').strip()
        
        if not terme:
            return jsonify({'error': 'Paramètre de recherche "q" requis'}), 400
        
        if len(terme) < 2:
            return jsonify({'error': 'Le terme de recherche doit contenir au moins 2 caractères'}), 400
        
        # Obtenir d'abord tous les sites accessibles
        sites, erreur = site_service.lister_sites(current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 403
        
        # Filtrer par recherche textuelle
        terme_lower = terme.lower()
        resultats = []
        
        for site in sites:
            # Recherche dans nom_site, adresse, ville, quartier
            texte_recherche = ' '.join([
                site.get('nom_site', ''),
                site.get('adresse', ''),
                site.get('ville', ''),
                site.get('quartier', ''),
                site.get('adresse_complete', '')
            ]).lower()
            
            if terme_lower in texte_recherche:
                resultats.append(site)
        
        # Limiter à 20 résultats
        resultats = resultats[:20]
        
        return jsonify({
            'success': True,
            'data': resultats,
            'total': len(resultats),
            'terme_recherche': terme,
            'methode': request.method
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@site_bp.route('/inactifs', methods=['GET'])
@superadmin_required
def lister_sites_inactifs(current_user):
    """Lister les sites désactivés - SUPERADMIN SEULEMENT"""
    try:
        from app.models.site import Site
        
        # Paramètre optionnel pour filtrer par client
        client_id = request.args.get('client_id')
        
        query = Site.query.filter_by(actif=False)
        
        if client_id:
            query = query.filter_by(client_id=client_id)
        
        sites_inactifs = query.order_by(Site.nom_site).all()
        
        return jsonify({
            'success': True,
            'data': [site.to_dict() for site in sites_inactifs],
            'total': len(sites_inactifs)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTE DE TEST ===================

@site_bp.route('/test-geocodage', methods=['POST'])
@superadmin_required
@validate_json_data(['adresse'])
def test_geocodage(current_user, data):
    """Tester le géocodage d'une adresse - SUPERADMIN SEULEMENT"""
    try:
        import requests
        
        adresse = data['adresse'].strip()
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': adresse,
            'format': 'json',
            'limit': 3,
            'countrycodes': 'sn',
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': 'SERTEC-IoT-Platform/1.0 (commercial@sertecingenierie.com)'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            resultats = response.json()
            
            return jsonify({
                'success': True,
                'adresse_recherchee': adresse,
                'resultats_geocodage': resultats,
                'total_resultats': len(resultats)
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': f'Erreur API géocodage: {response.status_code}'
            }), 400
        
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'message': 'Timeout géocodage'}), 400
    except Exception as e:
        return jsonify({'error': f'Erreur test géocodage: {str(e)}'}), 500

# =================== GESTION DES ERREURS ===================

@site_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Requête incorrecte'}), 400

@site_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Non autorisé'}), 401

@site_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Accès interdit'}), 403

@site_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource non trouvée'}), 404

@site_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur serveur interne'}), 500