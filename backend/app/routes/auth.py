from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.auth_service import AuthService
from app.models import User
from functools import wraps

# Créer le blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Instance du service
auth_service = AuthService()

def admin_required(f):
    """Décorateur pour les routes admin"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin():
            return jsonify({'error': 'Permission admin requise'}), 403
        return f(current_user, *args, **kwargs)
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

# =================== ROUTES D'AUTHENTIFICATION ===================

@auth_bp.route('/register', methods=['POST'])
@validate_json_data(['prenom', 'nom', 'email', 'password'])
def register(data):
    """Enregistrer un nouvel utilisateur"""
    try:
        # Pour cette route, on assume qu'un admin crée l'utilisateur
        # En production, ajouter l'authentification de l'admin
        
        user, error = auth_service.register(data, created_by_user=None)
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'success': True,
            'message': 'Utilisateur créé avec succès',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/register-user', methods=['POST'])
@admin_required
@validate_json_data(['prenom', 'nom', 'email'])
def register_user_by_admin(current_user, data):
    """Créer un utilisateur par un admin"""
    try:
        user, error = auth_service.register(data, created_by_user=current_user)
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'success': True,
            'message': 'Utilisateur créé avec succès',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
@validate_json_data(['email', 'password'])
def login(data):
    """Connexion utilisateur"""
    try:
        result, error = auth_service.login(data['email'], data['password'])
        
        if error:
            return jsonify({'error': error}), 401
        
        return jsonify({
            'success': True,
            'message': 'Connexion réussie',
            'data': result
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Déconnexion utilisateur"""
    try:
        user_id = get_jwt_identity()
        success, message = auth_service.logout(user_id)
        
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Récupérer le profil utilisateur"""
    try:
        user_id = get_jwt_identity()
        profile_data, error = auth_service.get_profile(user_id)
        
        if error:
            return jsonify({'error': error}), 404
        
        return jsonify({
            'success': True,
            'data': profile_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Mettre à jour le profil"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        profile_data, error = auth_service.update_profile(user_id, data)
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'success': True,
            'message': 'Profil mis à jour avec succès',
            'data': profile_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
@validate_json_data(['old_password', 'new_password'])
def change_password(data):
    """Changer le mot de passe"""
    try:
        user_id = get_jwt_identity()
        success, message = auth_service.change_password(
            user_id, 
            data['old_password'], 
            data['new_password']
        )
        
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
@validate_json_data(['email'])
def forgot_password(data):
    """Demander la réinitialisation du mot de passe"""
    try:
        success, message = auth_service.forgot_password(data['email'])
        
        return jsonify({
            'success': success,
            'message': message
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/reset-password', methods=['POST'])
@validate_json_data(['token', 'new_password'])
def reset_password(data):
    """Réinitialiser le mot de passe avec un token"""
    try:
        success, message = auth_service.reset_password(
            data['token'], 
            data['new_password']
        )
        
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/admin/reset-password', methods=['POST'])
@admin_required
@validate_json_data(['email', 'new_password'])
def admin_reset_password(current_user, data):
    """Réinitialiser le mot de passe par un admin"""
    try:
        success, message = auth_service.admin_reset_password(
            data['email'], 
            data['new_password'], 
            current_user
        )
        
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTES UTILITAIRES ===================

@auth_bp.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    """Vérifier la validité du token"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.actif:
            return jsonify({'error': 'Token invalide'}), 401
        
        return jsonify({
            'success': True,
            'message': 'Token valide',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Token invalide: {str(e)}'}), 401

# =================== GESTION DES ERREURS ===================

@auth_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Requête incorrecte'}), 400

@auth_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Non autorisé'}), 401

@auth_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Accès interdit'}), 403

@auth_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource non trouvée'}), 404

@auth_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur serveur interne'}), 500