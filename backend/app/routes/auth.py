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

def superadmin_required(f):
    """Décorateur pour les routes superadmin uniquement"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_superadmin():
            return jsonify({'error': 'Permission superadmin requise'}), 403
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

# ✅ NOUVELLES ROUTES POUR LA GESTION DES TOKENS DE RÉINITIALISATION

@auth_bp.route('/verify-reset-token', methods=['POST'])
@validate_json_data(['token'])
def verify_reset_token(data):
    """
    Vérifier la validité d'un token de réinitialisation
    Utile pour valider côté frontend avant la soumission du nouveau mot de passe
    """
    try:
        token_info, error = auth_service.get_reset_token_info(data['token'])
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'success': True,
            'message': 'Token valide',
            'data': token_info
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/reset-password-confirm', methods=['POST'])
@validate_json_data(['token', 'new_password', 'confirm_password'])
def reset_password_confirm(data):
    """
    Réinitialiser le mot de passe avec confirmation
    Version améliorée avec vérification de confirmation
    """
    try:
        # Vérifier que les mots de passe correspondent
        if data['new_password'] != data['confirm_password']:
            return jsonify({
                'error': 'Les mots de passe ne correspondent pas'
            }), 400
        
        # Vérifier d'abord la validité du token
        token_info, token_error = auth_service.get_reset_token_info(data['token'])
        if token_error:
            return jsonify({'error': token_error}), 400
        
        # Procéder à la réinitialisation
        success, message = auth_service.reset_password(
            data['token'], 
            data['new_password']
        )
        
        return jsonify({
            'success': success,
            'message': message,
            'email': token_info.get('email') if success else None
        }), 200 if success else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/admin/cleanup-tokens', methods=['POST'])
@superadmin_required
def cleanup_expired_tokens(current_user):
    """
    Nettoyer les tokens de réinitialisation expirés
    ⚠️ SUPERADMIN UNIQUEMENT - Maintenance système critique
    """
    try:
        cleaned_count = auth_service.cleanup_expired_tokens()
        
        return jsonify({
            'success': True,
            'message': f'{cleaned_count} tokens expirés nettoyés par {current_user.nom_complet}',
            'cleaned_count': cleaned_count,
            'admin': current_user.email
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/refresh-token', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    """
    Renouveler le token d'accès avec le refresh token
    """
    try:
        user_id = get_jwt_identity()
        result, error = auth_service.refresh_token(user_id)
        
        if error:
            return jsonify({'error': error}), 401
        
        return jsonify({
            'success': True,
            'message': 'Token renouvelé',
            'data': result
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

# =================== ROUTES UTILITAIRES ===================

@auth_bp.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    """Vérifier la validité du token d'accès"""
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

@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """
    Statut du service d'authentification
    """
    return jsonify({
        'service': 'auth',
        'status': 'active',
        'features': {
            'registration': True,
            'login': True,
            'password_reset': True,
            'email_notifications': True,
            'token_refresh': True,
            'admin_functions': True
        },
        'security': {
            'token_expiry': '1 hour',
            'refresh_token_expiry': '8 hours',
            'reset_token_expiry': '5 minutes',
            'password_min_length': 8
        }
    }), 200

# ✅ ROUTES DE TEST (À SUPPRIMER EN PRODUCTION)

@auth_bp.route('/test/email-service', methods=['GET'])
def test_email_service():
    """
    Route de test pour vérifier le service email
    ⚠️ À supprimer en production
    """
    try:
        from app.services.mail_service import MailService
        
        if not MailService.is_enabled():
            return jsonify({
                'email_service': 'disabled',
                'message': 'Service email non configuré'
            }), 200
        
        return jsonify({
            'email_service': 'enabled',
            'message': 'Service email configuré et prêt'
        }), 200
        
    except Exception as e:
        return jsonify({
            'email_service': 'error',
            'error': str(e)
        }), 500

@auth_bp.route('/test/send-test-email', methods=['POST'])
@superadmin_required
@validate_json_data(['email'])
def send_test_email(current_user, data):
    """
    Envoyer un email de test
    ⚠️ SUPERADMIN UNIQUEMENT - À supprimer en production
    """
    try:
        from app.services.mail_service import MailService
        
        result = MailService.send_email(
            to=data['email'],
            subject="🧪 Test SERTEC IoT",
            body=f"Email de test envoyé par {current_user.nom_complet} (SuperAdmin) depuis l'API SERTEC IoT."
        )
        
        return jsonify({
            'success': result['success'],
            'message': result.get('message', 'Email envoyé'),
            'sent_by': current_user.email
        }), 200 if result['success'] else 500
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

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