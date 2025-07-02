from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.user_service import UserService
from app.models.user import User
from functools import wraps
import time

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

# =================== NOUVELLES ROUTES POUR L'ACTIVATION ===================

@user_bp.route('/activer-admin/<token>', methods=['POST'])
@validate_json_data(['mot_de_passe', 'confirmpasse'])
def activer_admin(data, token):
    """Activer un compte administrateur avec token - ROUTE PUBLIQUE"""
    try:
        resultat, erreur = user_service.activer_admin(
            token, 
            data['mot_de_passe'],
            data['confirmpasse']
        )
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        # ✅ CORRECT - resultat est un dict avec: utilisateur, email_confirmation, message
        utilisateur_dict = resultat['utilisateur']  # Déjà un dictionnaire
        nom_complet = f"{utilisateur_dict['prenom']} {utilisateur_dict['nom']}"
        
        return jsonify({
            'success': True,
            'message': f'Compte administrateur {nom_complet} activé avec succès',
            'utilisateur': utilisateur_dict,
            'email_confirmation': resultat['email_confirmation'],
            'service_message': resultat['message'],
            'instructions': 'Vous pouvez maintenant vous connecter avec votre email et mot de passe'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/activer-utilisateur/<token>', methods=['POST'])
@validate_json_data(['mot_de_passe', 'confirmpasse'])
def activer_utilisateur_quelconque(data, token):
    """Activer n'importe quel type d'utilisateur (admin, user, superadmin) - ROUTE PUBLIQUE"""
    try:
        resultat, erreur = user_service.activer_utilisateur_quelconque(
            token, 
            data['mot_de_passe'],
            data['confirmpasse']
        )
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        # Même structure que activer_admin
        utilisateur_dict = resultat['utilisateur']
        nom_complet = f"{utilisateur_dict['prenom']} {utilisateur_dict['nom']}"
        
        return jsonify({
            'success': True,
            'message': f'Compte {utilisateur_dict["role"]} {nom_complet} activé avec succès',
            'utilisateur': utilisateur_dict,
            'email_confirmation': resultat['email_confirmation'],
            'service_message': resultat['message'],
            'instructions': 'Vous pouvez maintenant vous connecter avec votre email et mot de passe'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/valider-token-activation/<token>', methods=['GET'])
def valider_token_activation(token):
    """Valider un token d'activation sans le consommer - ROUTE PUBLIQUE"""
    try:
        resultat, erreur = user_service.valider_token_activation(token)
        
        if erreur:
            return jsonify({
                'valid': False,
                'error': erreur
            }), 400
        
        return jsonify({
            'valid': True,
            'admin_info': resultat['admin_info'],
            'temps_restant_secondes': resultat['temps_restant_secondes'],
            'temps_restant_heures': resultat['temps_restant_heures']
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<admin_id>/regenerer-token-activation', methods=['POST'])
@superadmin_required
def regenerer_token_activation(current_user, admin_id):
    """Régénérer un token d'activation pour un admin - SUPERADMIN SEULEMENT"""
    try:
        token, erreur = user_service.regenerer_token_activation(admin_id, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        return jsonify({
            'success': True,
            'message': 'Nouveau token d\'activation généré et email envoyé',
            'token': token  # Pour debug - à retirer en production
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/admins-en-attente', methods=['GET'])
@admin_required  # ✅ CHANGÉ : admin_required au lieu de superadmin_required
def lister_admins_en_attente(current_user):
    """Lister les administrateurs en attente d'activation selon les permissions"""
    try:
        # ✅ CORRECT : le service gère les permissions en interne
        admins_data, erreur = user_service.lister_admins_en_attente(current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 403
        
        # ✅ GESTION : Support des deux formats de retour
        if isinstance(admins_data, dict) and 'admins' in admins_data:
            # Nouveau format avec metadata
            return jsonify({
                'success': True,
                'data': admins_data['admins'],
                'metadata': admins_data['metadata'],
                'total': len(admins_data['admins'])
            }), 200
        else:
            # Format simple (liste directe)
            return jsonify({
                'success': True,
                'data': admins_data,
                'total': len(admins_data)
            }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/utilisateurs-en-attente', methods=['GET'])
@admin_required
def lister_utilisateurs_en_attente(current_user):
    """Lister les utilisateurs en attente d'activation selon les permissions"""
    try:
        # Paramètre optionnel pour inclure tous les rôles (superadmin seulement)
        inclure_tous_roles = request.args.get('inclure_tous_roles', 'false').lower() == 'true'
        
        utilisateurs_data, erreur = user_service.lister_utilisateurs_en_attente(current_user, inclure_tous_roles)
        
        if erreur:
            return jsonify({'error': erreur}), 403
        
        # Support des deux formats de retour
        if isinstance(utilisateurs_data, dict) and 'utilisateurs' in utilisateurs_data:
            return jsonify({
                'success': True,
                'data': utilisateurs_data['utilisateurs'],
                'metadata': utilisateurs_data['metadata'],
                'total': len(utilisateurs_data['utilisateurs'])
            }), 200
        else:
            return jsonify({
                'success': True,
                'data': utilisateurs_data,
                'total': len(utilisateurs_data)
            }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<utilisateur_id>/supprimer-en-attente', methods=['DELETE'])
@admin_required
def supprimer_utilisateur_en_attente(current_user, utilisateur_id):
    """Supprimer un utilisateur en attente d'activation"""
    try:
        succes, message = user_service.supprimer_utilisateur_en_attente(utilisateur_id, current_user)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/supprimer-batch-en-attente', methods=['POST'])
@admin_required
@validate_json_data(['utilisateurs_ids'])
def supprimer_batch_utilisateurs_en_attente(data, current_user):
    """Supprimer plusieurs utilisateurs en attente en une fois"""
    try:
        resultats = user_service.supprimer_batch_utilisateurs_en_attente(data['utilisateurs_ids'], current_user)
        
        return jsonify({
            'success': resultats['success'],
            'message': resultats['message'],
            'details': {
                'total_demande': resultats['total_demande'],
                'total_supprime': resultats['total_supprime'],
                'total_erreurs': resultats['total_erreurs'],
                'supprimes': resultats['supprimes'],
                'erreurs': resultats['erreurs']
            }
        }), 200 if resultats['success'] else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<utilisateur_id>/envoyer-nouveau-mot-de-passe', methods=['POST'])
@admin_required
def envoyer_nouveau_mot_de_passe(current_user, utilisateur_id):
    """Générer et envoyer un nouveau mot de passe par email"""
    try:
        mot_de_passe, erreur = user_service.generer_et_envoyer_nouveau_mot_de_passe(utilisateur_id, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        # Récupérer l'utilisateur pour l'email
        utilisateur = User.query.get(utilisateur_id)
        if not utilisateur:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Nouveau mot de passe généré et envoyé par email',
            'destinataire': utilisateur.email
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<utilisateur_id>/creer-activation', methods=['POST'])
@admin_required
def creer_et_envoyer_activation(current_user, utilisateur_id):
    """Créer et envoyer un token d'activation pour un utilisateur existant"""
    try:
        token, erreur = user_service.creer_et_envoyer_activation_utilisateur_simple(utilisateur_id, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        return jsonify({
            'success': True,
            'message': 'Token d\'activation créé et email envoyé',
            'token': token  # Pour debug
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

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
        
        # ✅ CORRECT : Adaptation au format du service
        return jsonify({
            'success': True,
            'message': f"✅ Client '{resultat['client']['nom_entreprise']}' créé avec succès",
            'data': {
                'client': resultat['client'],
                'admin_client': resultat['admin_client']
            },
            'instructions': {
                'action_suivante': resultat['message_instructions'],
                'email_envoye': resultat['email_result']['success'] if 'email_result' in resultat else False,
                'status_admin': 'En attente d\'activation par email',
                'securite': "L'admin doit activer son compte via l'email reçu"
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
        
        # ✅ CORRECT : client est un objet Client, utiliser to_dict()
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
def creer_utilisateur(data, current_user):
    """Créer un nouvel utilisateur avec site (version modifiée)"""
    try:
        # ✅ NOUVEAU : Valider site_id pour les utilisateurs simples
        role = data.get('role', 'user')
        site_id = data.get('site_id')
        
        # ✅ VALIDATION : site_id obligatoire pour user simple
        if role == 'user' and not site_id:
            return jsonify({
                'error': 'site_id requis pour les utilisateurs simples',
                'message': 'Veuillez sélectionner un site pour ce type d\'utilisateur'
            }), 400
        
        # ✅ VALIDATION : Vérifier que le site existe et appartient au bon client
        if site_id:
            from app.models.site import Site
            site = Site.query.get(site_id)
            
            if not site:
                return jsonify({'error': 'Site non trouvé'}), 404
            
            if not site.actif:
                return jsonify({'error': 'Site inactif'}), 400
            
            # Admin ne peut assigner que ses propres sites
            if not current_user.is_superadmin() and site.client_id != current_user.client_id:
                return jsonify({
                    'error': 'Site non autorisé',
                    'message': 'Vous ne pouvez assigner que des sites de votre client'
                }), 403
        
        # ✅ AJOUTER site_id aux données
        data_avec_site = data.copy()
        if site_id:
            data_avec_site['site_id'] = site_id
        
        # Appel service existant avec données enrichies
        resultat, erreur = user_service.creer_utilisateur(data_avec_site, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        # ✅ ENRICHIR la réponse avec info site
        utilisateur_dict = resultat['utilisateur']
        nom_complet = f"{utilisateur_dict['prenom']} {utilisateur_dict['nom']}"
        
        response_data = {
            'success': True,
            'message': f'Utilisateur {nom_complet} créé avec succès',
            'utilisateur': utilisateur_dict,
            'instructions': {
                'action_suivante': resultat['message_instructions'],
                'email_envoye': resultat['email_result']['success'],
                'status': 'En attente d\'activation par email'
            }
        }
        
        # ✅ AJOUTER info site si présent
        if site_id and 'site' in locals():
            response_data['site_info'] = {
                'id': site.id,
                'nom': site.nom_site,
                'adresse': site.adresse,
                'ville': site.ville
            }
            response_data['message'] += f' pour le site "{site.nom_site}"'
        
        # Token debug si disponible
        if 'token_activation' in resultat:
            response_data['debug_token'] = resultat['token_activation']
        
        return jsonify(response_data), 201
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

        
@user_bp.route('/', methods=['GET'])
@admin_required
def lister_utilisateurs(current_user):
    """Lister les utilisateurs selon les permissions"""
    try:
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
        
        # ✅ CORRECT : modifier_utilisateur retourne Tuple[Optional[User], Optional[str]]
        utilisateur, erreur = user_service.modifier_utilisateur(utilisateur_id, data, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        # ✅ CORRECT : utilisateur est un objet User, utiliser to_dict()
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
        forcer = request.args.get('forcer', 'false').lower() == 'true'
        
        succes, message = user_service.supprimer_utilisateur(utilisateur_id, current_user, forcer)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<superadmin_id>/supprimer-superadmin', methods=['DELETE'])
@superadmin_required
def supprimer_superadmin(current_user, superadmin_id):
    """Supprimer un superadmin - SEULEMENT PAR UN AUTRE SUPERADMIN"""
    try:
        forcer = request.args.get('forcer', 'false').lower() == 'true'
        
        succes, message = user_service.supprimer_superadmin(superadmin_id, current_user, forcer)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/<utilisateur_id>/reset-password', methods=['POST'])
@admin_required
@validate_json_data(['nouveau_mot_de_passe'])
def reinitialiser_mot_de_passe(data, current_user, utilisateur_id):
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
        
        # ✅ CORRECT : modifier_utilisateur retourne Tuple[Optional[User], Optional[str]]
        utilisateur, erreur = user_service.modifier_utilisateur(user_id, data, current_user)
        
        if erreur:
            return jsonify({'error': erreur}), 400
        
        # ✅ CORRECT : utilisateur est un objet User
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

# =================== ROUTES DE DEBUG ET MAINTENANCE ===================

@user_bp.route('/debug/tokens/stats', methods=['GET'])
@superadmin_required
def obtenir_stats_tokens(current_user):
    """Obtenir les statistiques des tokens - DEBUG SUPERADMIN"""
    try:
        stats = user_service.obtenir_stats_tokens()
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/debug/tokens/cleanup', methods=['POST'])
@superadmin_required
def nettoyer_tokens(current_user):
    """Nettoyer les tokens expirés - DEBUG SUPERADMIN"""
    try:
        resultat = user_service.nettoyer_tokens_expires()
        
        return jsonify({
            'success': True,
            'data': resultat
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/debug/tokens/all', methods=['GET'])
@superadmin_required
def debug_tous_tokens(current_user):
    """Voir tous les tokens d'activation - DEBUG SUPERADMIN SEULEMENT"""
    try:
        tokens_info = user_service.get_all_activation_tokens_debug()
        
        return jsonify({
            'success': True,
            'data': tokens_info
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/debug/tokens/force-cleanup', methods=['POST'])
@superadmin_required
def force_cleanup_tokens(current_user):
    """FORCER le nettoyage de TOUS les tokens - URGENCE SEULEMENT"""
    try:
        # Sécurité supplémentaire
        confirmation = request.get_json()
        if not confirmation or confirmation.get('confirm') != 'FORCE_DELETE_ALL_TOKENS':
            return jsonify({
                'error': 'Confirmation requise: {"confirm": "FORCE_DELETE_ALL_TOKENS"}'
            }), 400
        
        resultat = user_service.force_cleanup_all_tokens()
        
        return jsonify({
            'success': True,
            'data': resultat,
            'warning': 'TOUS les tokens d\'activation ont été supprimés !'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/debug/tokens/cleanup-orphelins', methods=['POST'])
@superadmin_required
def nettoyer_tokens_orphelins(current_user):
    """Nettoyer les tokens des utilisateurs supprimés - MAINTENANCE"""
    try:
        resultat = user_service.nettoyer_tokens_utilisateurs_supprimes()
        
        return jsonify({
            'success': True,
            'data': resultat
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/debug/tokens/expirant-bientot', methods=['GET'])
@superadmin_required
def tokens_expirant_bientot(current_user):
    """Lister les tokens qui vont expirer bientôt"""
    try:
        # Paramètre optionnel pour définir le délai (défaut: 2 heures)
        heures = int(request.args.get('heures', 2))
        
        tokens_expirants = user_service.lister_tokens_expirant_bientot(heures)
        
        return jsonify({
            'success': True,
            'data': tokens_expirants,
            'total': len(tokens_expirants),
            'critere': f'Expirant dans les {heures} prochaines heures'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/debug/tokens/<token>/prolonger', methods=['POST'])
@superadmin_required
def prolonger_token(current_user, token):
    """Prolonger la durée d'un token d'activation"""
    try:
        data = request.get_json() or {}
        nouvelles_heures = int(data.get('heures', 24))
        
        succes, message = user_service.prolonger_token_activation(token, nouvelles_heures)
        
        return jsonify({
            'success': succes,
            'message': message
        }), 200 if succes else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/debug/redis/test', methods=['GET'])
@superadmin_required
def test_redis_connection(current_user):
    """Tester la connexion Redis - DEBUG"""
    try:
        debug_info = user_service.debug_redis_connection()
        
        return jsonify({
            'success': True,
            'data': debug_info
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

# =================== ROUTES ADDITIONNELLES POUR CORRESPONDRE AU SERVICE ===================

@user_bp.route('/admin/test-permissions', methods=['GET'])
@admin_required
def test_permissions_admin(current_user):
    """Tester les permissions de l'admin connecté"""
    try:
        permissions = {
            'is_superadmin': current_user.is_superadmin(),
            'is_admin': current_user.is_admin(),
            'client_id': current_user.client_id,
            'peut_voir_tous_clients': current_user.is_superadmin(),
            'peut_creer_clients': current_user.is_superadmin(),
            'peut_voir_admins_autres_clients': current_user.is_superadmin()
        }
        
        return jsonify({
            'success': True,
            'utilisateur': current_user.to_dict(),
            'permissions': permissions
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@user_bp.route('/batch/actions', methods=['POST'])
@admin_required
@validate_json_data(['action', 'utilisateurs_ids'])
def actions_batch_utilisateurs(data, current_user):
    """Effectuer des actions en lot sur plusieurs utilisateurs"""
    try:
        action = data['action']
        utilisateurs_ids = data['utilisateurs_ids']
        
        if not isinstance(utilisateurs_ids, list) or not utilisateurs_ids:
            return jsonify({'error': 'Liste d\'IDs utilisateurs requise'}), 400
        
        resultats = {
            'action': action,
            'total_demande': len(utilisateurs_ids),
            'succes': [],
            'erreurs': [],
            'total_succes': 0,
            'total_erreurs': 0
        }
        
        # Actions supportées
        if action == 'supprimer_en_attente':
            # Utiliser la méthode batch du service
            resultats_batch = user_service.supprimer_batch_utilisateurs_en_attente(utilisateurs_ids, current_user)
            return jsonify(resultats_batch), 200 if resultats_batch['success'] else 400
            
        elif action == 'desactiver':
            for user_id in utilisateurs_ids:
                try:
                    succes, message = user_service.desactiver_utilisateur(user_id, current_user)
                    if succes:
                        resultats['succes'].append({'user_id': user_id, 'message': message})
                        resultats['total_succes'] += 1
                    else:
                        resultats['erreurs'].append({'user_id': user_id, 'erreur': message})
                        resultats['total_erreurs'] += 1
                except Exception as e:
                    resultats['erreurs'].append({'user_id': user_id, 'erreur': str(e)})
                    resultats['total_erreurs'] += 1
                    
        elif action == 'reactiver':
            for user_id in utilisateurs_ids:
                try:
                    succes, message = user_service.reactiver_utilisateur(user_id, current_user)
                    if succes:
                        resultats['succes'].append({'user_id': user_id, 'message': message})
                        resultats['total_succes'] += 1
                    else:
                        resultats['erreurs'].append({'user_id': user_id, 'erreur': message})
                        resultats['total_erreurs'] += 1
                except Exception as e:
                    resultats['erreurs'].append({'user_id': user_id, 'erreur': str(e)})
                    resultats['total_erreurs'] += 1
        else:
            return jsonify({'error': f'Action "{action}" non supportée'}), 400
        
        # Message de résumé
        resultats['success'] = resultats['total_succes'] > 0
        if resultats['total_succes'] > 0:
            resultats['message'] = f"{resultats['total_succes']} actions réussies"
            if resultats['total_erreurs'] > 0:
                resultats['message'] += f", {resultats['total_erreurs']} erreurs"
        else:
            resultats['message'] = f"Aucune action réussie. {resultats['total_erreurs']} erreurs"
        
        return jsonify(resultats), 200 if resultats['success'] else 400
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

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