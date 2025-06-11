from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.user_service import UserService
from app.models.user import User
from functools import wraps

# Créer le blueprint
user_bp = Blueprint('users', __name__, url_prefix='/api/users')

# Instance du service
user_service = UserService()

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

# =================== GESTION DES CLIENTS ===================

@user_bp.route('/clients', methods=['POST'])
@superadmin_required
@validate_json_data(['nom_entreprise', 'email_contact'])
def creer_client(data, current_user):
    """Créer un nouveau client avec son admin automatiquement - SUPERADMIN SEULEMENT"""
    try:
        resultat, erreur = user_service.creer_client(data, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        # Réponse enrichie avec toutes les informations
        return jsonify({
            'success': True,
            'message': f"✅ Client '{resultat['client']['nom_entreprise']}' et admin '{resultat['admin_client']['nom_complet']}' créés avec succès",
            'data': {
                'client': resultat['client'],
                'admin_client': resultat['admin_client'],
                'identifiants_admin': resultat['identifiants_connexion']
            },
            'instructions': {
                'action_suivante': resultat['message_instructions'],
                'connexion_admin': f"L'admin peut se connecter avec : {resultat['identifiants_connexion']['email']} / {resultat['identifiants_connexion']['mot_de_passe']}",
                'securite': "⚠️ L'admin doit changer son mot de passe à la première connexion"
            }
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/clients', methods=['GET'])
@superadmin_required
def lister_clients(current_user):
    """Lister tous les clients - SUPERADMIN SEULEMENT"""
    try:
        clients, erreur = user_service.lister_clients(current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 403
        
        return jsonify({
            'success': True,
            'data': clients,
            'total': len(clients)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/clients/<client_id>', methods=['PUT'])
@superadmin_required
def modifier_client(current_user, client_id):
    """Modifier un client - SUPERADMIN SEULEMENT"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        client, erreur = user_service.modifier_client(client_id, data, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        return jsonify({
            'success': True,
            'message': f'Client {client.nom_entreprise} modifié avec succès',
            'client': client.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/clients/<client_id>/desactiver', methods=['POST'])
@superadmin_required
def desactiver_client(current_user, client_id):
    """Désactiver un client et tous ses utilisateurs - SUPERADMIN SEULEMENT"""
    try:
        succes, message = user_service.desactiver_client(client_id, current_user)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/clients/<client_id>/reactiver', methods=['POST'])
@superadmin_required
def reactiver_client(current_user, client_id):
    """Réactiver un client désactivé - SUPERADMIN SEULEMENT"""
    try:
        succes, message = user_service.reactiver_client(client_id, current_user)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/clients/<client_id>/supprimer', methods=['DELETE'])
@superadmin_required
def supprimer_client(current_user, client_id):
    """Supprimer définitivement un client - SUPERADMIN SEULEMENT"""
    try:
        # Paramètre optionnel pour forcer la suppression
        forcer = request.args.get('forcer', 'false').lower() == 'true'
        
        succes, message = user_service.supprimer_client(client_id, current_user, forcer)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== GESTION DES UTILISATEURS ===================

@user_bp.route('/', methods=['POST'])
@admin_required
@validate_json_data(['prenom', 'nom', 'email'])
def creer_utilisateur(data, current_user):  # ✅ CORRIGÉ : data en premier
    """Créer un nouvel utilisateur"""
    try:
        utilisateur, mot_de_passe_temporaire = user_service.creer_utilisateur(data, current_user)
        
        if not utilisateur:
            return jsonify({'error': mot_de_passe_temporaire}), 400
        
        response_data = {
            'success': True,
            'message': f'Utilisateur {utilisateur.nom_complet} créé avec succès',
            'utilisateur': utilisateur.to_dict()
        }
        
        # Inclure le mot de passe temporaire si généré automatiquement
        if mot_de_passe_temporaire:
            response_data['mot_de_passe_temporaire'] = mot_de_passe_temporaire
            response_data['message'] += f' - Mot de passe temporaire: {mot_de_passe_temporaire}'
        
        return jsonify(response_data), 201
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/', methods=['GET'])
@admin_required
def lister_utilisateurs(current_user):
    """Lister les utilisateurs selon les permissions"""
    try:
        # Paramètre optionnel pour filtrer par client (superadmin seulement)
        client_id = request.args.get('client_id')
        
        utilisateurs, erreur = user_service.lister_utilisateurs(current_user, client_id)
        
        if erreur:
            return jsonify({'error': erreur}), 403
        
        return jsonify({
            'success': True,
            'data': utilisateurs,
            'total': len(utilisateurs)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<utilisateur_id>', methods=['GET'])
@admin_required
def obtenir_utilisateur(current_user, utilisateur_id):
    """Obtenir les détails d'un utilisateur"""
    try:
        utilisateur, erreur = user_service.obtenir_utilisateur(utilisateur_id, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 404 if 'non trouvé' in erreur else 403
        
        return jsonify({
            'success': True,
            'data': utilisateur
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<utilisateur_id>', methods=['PUT'])
@admin_required
def modifier_utilisateur(current_user, utilisateur_id):
    """Modifier un utilisateur existant"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        utilisateur, erreur = user_service.modifier_utilisateur(utilisateur_id, data, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        return jsonify({
            'success': True,
            'message': f'Utilisateur {utilisateur.nom_complet} modifié avec succès',
            'utilisateur': utilisateur.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<utilisateur_id>/desactiver', methods=['POST'])
@admin_required
def desactiver_utilisateur(current_user, utilisateur_id):
    """Désactiver un utilisateur"""
    try:
        succes, message = user_service.desactiver_utilisateur(utilisateur_id, current_user)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<utilisateur_id>/reactiver', methods=['POST'])
@admin_required
def reactiver_utilisateur(current_user, utilisateur_id):
    """Réactiver un utilisateur désactivé"""
    try:
        succes, message = user_service.reactiver_utilisateur(utilisateur_id, current_user)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<utilisateur_id>/supprimer', methods=['DELETE'])
@admin_required
def supprimer_utilisateur(current_user, utilisateur_id):
    """Supprimer définitivement un utilisateur"""
    try:
        # Paramètre optionnel pour forcer la suppression
        forcer = request.args.get('forcer', 'false').lower() == 'true'
        
        succes, message = user_service.supprimer_utilisateur(utilisateur_id, current_user, forcer)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<utilisateur_id>/reset-password', methods=['POST'])
@admin_required
@validate_json_data(['nouveau_mot_de_passe'])
def reinitialiser_mot_de_passe(data, current_user, utilisateur_id):  # ✅ CORRIGÉ : data en premier
    """Réinitialiser le mot de passe d'un utilisateur"""
    try:
        succes, message = user_service.reinitialiser_mot_de_passe(
            utilisateur_id, 
            data['nouveau_mot_de_passe'], 
            current_user
        )
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<utilisateur_id>/generer-mot-de-passe', methods=['POST'])
@admin_required
def generer_mot_de_passe_temporaire(current_user, utilisateur_id):
    """Générer un nouveau mot de passe temporaire pour un utilisateur"""
    try:
        mot_de_passe, erreur = user_service.generer_mot_de_passe_temporaire_pour(utilisateur_id, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        return jsonify({
            'success': True,
            'message': 'Nouveau mot de passe temporaire généré',
            'mot_de_passe_temporaire': mot_de_passe
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTES POUR L'UTILISATEUR CONNECTÉ ===================

@user_bp.route('/mon-profil', methods=['GET'])
@jwt_required()
def obtenir_mon_profil():
    """Obtenir son propre profil"""
    try:
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)
        
        if not current_user or not current_user.actif:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        utilisateur, erreur = user_service.obtenir_utilisateur(user_id, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 404
        
        return jsonify({
            'success': True,
            'data': utilisateur
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/Updateprofil', methods=['PUT'])
@jwt_required()
def modifier_mon_profil():
    """Modifier son propre profil"""
    try:
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)
        
        if not current_user or not current_user.actif:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        utilisateur, erreur = user_service.modifier_utilisateur(user_id, data, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        return jsonify({
            'success': True,
            'message': 'Profil modifié avec succès',
            'utilisateur': utilisateur.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== STATISTIQUES ===================

@user_bp.route('/statistiques', methods=['GET'])
@admin_required
def obtenir_statistiques(current_user):
    """Obtenir des statistiques sur les utilisateurs"""
    try:
        stats, erreur = user_service.obtenir_statistiques_utilisateurs(current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 403
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTES UTILITAIRES ===================

@user_bp.route('/rechercher', methods=['GET', 'POST'])
@admin_required
def rechercher_utilisateurs(current_user):
    """Rechercher des utilisateurs par nom ou email"""
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
        
        # Construction de la requête selon les permissions
        query = User.query.filter(User.actif == True)
        
        if not current_user.is_superadmin():
            # Admin ne voit que son client
            query = query.filter(User.client_id == current_user.client_id)
        
        # Recherche par nom ou email
        from sqlalchemy import or_, and_
        terme_recherche = f"%{terme}%"
        query = query.filter(
            or_(
                User.prenom.ilike(terme_recherche),
                User.nom.ilike(terme_recherche),
                User.email.ilike(terme_recherche),
                and_(
                    User.prenom.ilike(f"%{terme.split()[0]}%"),
                    User.nom.ilike(f"%{terme.split()[-1]}%") if len(terme.split()) > 1 else True
                )
            )
        )
        
        resultats = query.limit(20).all()  # Limiter à 20 résultats
        
        return jsonify({
            'success': True,
            'data': [user.to_dict() for user in resultats],
            'total': len(resultats),
            'terme_recherche': terme,
            'methode': request.method
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/inactifs', methods=['GET'])
@admin_required
def lister_utilisateurs_inactifs(current_user):
    """Lister les utilisateurs désactivés"""
    try:
        query = User.query.filter(User.actif == False)
        
        if not current_user.is_superadmin():
            # Admin ne voit que son client
            query = query.filter(User.client_id == current_user.client_id)
        
        utilisateurs_inactifs = query.order_by(User.prenom, User.nom).all()
        
        return jsonify({
            'success': True,
            'data': [user.to_dict() for user in utilisateurs_inactifs],
            'total': len(utilisateurs_inactifs)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTE DE TEST ===================

@user_bp.route('/test-superadmin', methods=['GET'])
def test_superadmin():
    """Route de test pour vérifier que le superadmin fonctionne"""
    try:
        superadmin = User.query.filter_by(role='superadmin').first()
        
        if not superadmin:
            return jsonify({'error': 'Aucun superadmin trouvé'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Superadmin trouvé',
            'superadmin': {
                'id': superadmin.id,
                'email': superadmin.email,
                'nom_complet': superadmin.nom_complet,
                'role': superadmin.role,
                'actif': superadmin.actif,
                'is_superadmin': superadmin.is_superadmin()
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur: {str(e)}'}), 500

# =================== GESTION DES ERREURS ===================

@user_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Requête incorrecte'}), 400

@user_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Non autorisé'}), 401

@user_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Accès interdit'}), 403

@user_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource non trouvée'}), 404

@user_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur serveur interne'}), 500