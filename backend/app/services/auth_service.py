from flask_jwt_extended import create_access_token, create_refresh_token
from app import db
from app.models import User, Client
from datetime import datetime, timedelta
import secrets
import re

class AuthService:
    def __init__(self):
        # Stockage temporaire des tokens de reset (en production, utiliser Redis)
        self.reset_tokens = {}
    
    def register(self, user_data, created_by_user=None):
        """
        Enregistrer un nouvel utilisateur
        - Si created_by_user est None : création du premier superadmin
        - Si created_by_user existe : création selon les permissions
        """
        try:
            # Validation des données
            if not self._validate_user_data(user_data):
                return None, "Données utilisateur invalides"
            
            # Vérifier si l'email existe déjà
            existing_user = User.query.filter_by(email=user_data['email'].lower().strip()).first()
            if existing_user:
                return None, "Un utilisateur avec cet email existe déjà"
            
            # Déterminer le rôle et client_id
            role = user_data.get('role', 'user')
            client_id = user_data.get('client_id')
            
            # Gestion des permissions
            if created_by_user is None:
                # Premier superadmin (installation)
                role = 'superadmin'
                client_id = None
            elif created_by_user.is_superadmin():
                # Superadmin peut créer n'importe quel utilisateur
                if role == 'superadmin':
                    client_id = None
                elif not client_id and role != 'superadmin':
                    return None, "client_id requis pour les utilisateurs non-superadmin"
            elif created_by_user.is_admin():
                # Admin peut créer seulement des users de son client
                if role in ['superadmin', 'admin']:
                    return None, "Permission insuffisante pour créer ce type d'utilisateur"
                client_id = created_by_user.client_id
            else:
                return None, "Permission insuffisante"
            
            # ✅ Créer l'utilisateur selon TON modèle exact
            user = User(
                prenom=user_data['prenom'].strip(),
                nom=user_data['nom'].strip(),
                email=user_data['email'].lower().strip(),
                telephone=user_data.get('telephone', '').strip() or None,
                role=role,
                client_id=client_id
            )
            
            # Définir le mot de passe avec TA méthode
            password = user_data.get('password')
            if not password:
                password = self._generate_temp_password()
            
            user.set_password(password)  # Utilise ta méthode qui gère mot_de_passe_hash
            
            db.session.add(user)
            db.session.commit()
            
            return user, None
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de l'enregistrement: {str(e)}"
    
    def login(self, email, password):
        """Connexion utilisateur"""
        try:
            # Validation des entrées
            if not email or not password:
                return None, "Email et mot de passe requis"
            
            email = email.lower().strip()
            
            # Rechercher l'utilisateur avec TES champs
            user = User.query.filter_by(email=email, actif=True).first()
            if not user:
                return None, "Email ou mot de passe incorrect"
            
            # Vérifier le mot de passe avec TA méthode
            if not user.check_password(password):
                return None, "Email ou mot de passe incorrect"
            
            # Mettre à jour la dernière connexion avec TA méthode
            user.update_last_login()
            
            # Créer les tokens
            access_token = create_access_token(
                identity=user.id,
                additional_claims={
                    'role': user.role,
                    'client_id': user.client_id,
                    'email': user.email,
                    'nom_complet': user.nom_complet  # TA propriété
                },
                expires_delta=timedelta(hours=24)
            )
            
            refresh_token = create_refresh_token(
                identity=user.id,
                expires_delta=timedelta(days=30)
            )
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': user.to_dict(),  # TA méthode to_dict
                'expires_in': 24 * 3600
            }, None
            
        except Exception as e:
            return None, f"Erreur lors de la connexion: {str(e)}"
    
    def logout(self, user_id):
        """Déconnexion (côté serveur)"""
        try:
            # En production, ajouter le token à une blacklist
            user = User.query.get(user_id)
            if user:
                # Log optionnel de déconnexion
                pass
            
            return True, "Déconnexion réussie"
            
        except Exception as e:
            return False, f"Erreur lors de la déconnexion: {str(e)}"
    
    def get_profile(self, user_id):
        """Récupérer le profil utilisateur"""
        try:
            user = User.query.get(user_id)
            if not user or not user.actif:
                return None, "Utilisateur non trouvé"
            
            # Utiliser TA méthode to_dict avec include_sensitive
            profile_data = user.to_dict(include_sensitive=True)
            
            # Ajouter des informations sur les permissions avec TES méthodes
            profile_data['permissions'] = {
                'is_superadmin': user.is_superadmin(),
                'is_admin': user.is_admin(),
                'can_manage_users': user.is_admin(),
                'can_manage_devices': user.is_admin()
            }
            
            return profile_data, None
            
        except Exception as e:
            return None, f"Erreur lors de la récupération: {str(e)}"
    
    def update_profile(self, user_id, profile_data):
        """Mettre à jour le profil"""
        try:
            user = User.query.get(user_id)
            if not user:
                return None, "Utilisateur non trouvé"
            
            # Champs modifiables par l'utilisateur selon TON modèle
            allowed_fields = ['prenom', 'nom', 'telephone']
            
            for field in allowed_fields:
                if field in profile_data and profile_data[field] is not None:
                    value = str(profile_data[field]).strip()
                    if field in ['prenom', 'nom'] and not value:
                        return None, f"Le champ {field} ne peut pas être vide"
                    setattr(user, field, value if value else None)
            
            db.session.commit()
            
            return user.to_dict(), None  # TA méthode to_dict
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de la mise à jour: {str(e)}"
    
    def change_password(self, user_id, old_password, new_password):
        """Changer le mot de passe"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "Utilisateur non trouvé"
            
            # Vérifier l'ancien mot de passe avec TA méthode
            if not user.check_password(old_password):
                return False, "Ancien mot de passe incorrect"
            
            # Valider le nouveau mot de passe
            if not self._validate_password(new_password):
                return False, "Le nouveau mot de passe doit contenir au moins 8 caractères"
            
            # Changer le mot de passe avec TA méthode
            user.set_password(new_password)
            db.session.commit()
            
            return True, "Mot de passe modifié avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors du changement: {str(e)}"
    
    def forgot_password(self, email):
        """Demander la réinitialisation du mot de passe"""
        try:
            email = email.lower().strip()
            user = User.query.filter_by(email=email, actif=True).first()
            
            # Pour la sécurité, on retourne toujours success même si l'email n'existe pas
            if not user:
                return True, "Si cet email existe, vous recevrez un lien de réinitialisation"
            
            # Générer un token de réinitialisation
            reset_token = secrets.token_urlsafe(32)
            
            # Stocker le token avec expiration (1 heure)
            self.reset_tokens[reset_token] = {
                'user_id': user.id,
                'email': user.email,
                'expires_at': datetime.utcnow() + timedelta(hours=1)
            }
            
            # En production, envoyer un email ici
            # self._send_reset_email(user, reset_token)
            
            # Pour le développement, on retourne le token
            return True, f"Token de réinitialisation généré: {reset_token}"
            
        except Exception as e:
            return False, f"Erreur lors de la demande: {str(e)}"
    
    def reset_password(self, token, new_password):
        """Réinitialiser le mot de passe avec un token"""
        try:
            # Vérifier le token
            if token not in self.reset_tokens:
                return False, "Token invalide ou expiré"
            
            token_data = self.reset_tokens[token]
            
            # Vérifier l'expiration
            if datetime.utcnow() > token_data['expires_at']:
                del self.reset_tokens[token]
                return False, "Token expiré"
            
            # Valider le nouveau mot de passe
            if not self._validate_password(new_password):
                return False, "Le mot de passe doit contenir au moins 8 caractères"
            
            # Trouver l'utilisateur
            user = User.query.get(token_data['user_id'])
            if not user or not user.actif:
                del self.reset_tokens[token]
                return False, "Utilisateur non trouvé"
            
            # Changer le mot de passe avec TA méthode
            user.set_password(new_password)
            db.session.commit()
            
            # Supprimer le token utilisé
            del self.reset_tokens[token]
            
            return True, "Mot de passe réinitialisé avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la réinitialisation: {str(e)}"
    
    def admin_reset_password(self, target_email, new_password, admin_user):
        """Réinitialisation par un administrateur"""
        try:
            if not admin_user.is_admin():  # TA méthode
                return False, "Permission insuffisante"
            
            target_user = User.query.filter_by(email=target_email.lower().strip()).first()
            if not target_user:
                return False, "Utilisateur non trouvé"
            
            # Vérifier que l'admin peut gérer cet utilisateur avec TES méthodes
            if not admin_user.is_superadmin():
                if target_user.client_id != admin_user.client_id:
                    return False, "Vous ne pouvez gérer que les utilisateurs de votre organisation"
                
                if target_user.role in ['superadmin', 'admin']:
                    return False, "Permission insuffisante pour ce type d'utilisateur"
            
            # Valider le mot de passe
            if not self._validate_password(new_password):
                return False, "Le mot de passe doit contenir au moins 8 caractères"
            
            # Réinitialiser avec TA méthode
            target_user.set_password(new_password)
            db.session.commit()
            
            return True, f"Mot de passe réinitialisé pour {target_user.nom_complet}"  # TA propriété
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la réinitialisation: {str(e)}"
    
    def _validate_user_data(self, data):
        """Valider les données utilisateur selon TON modèle"""
        required_fields = ['prenom', 'nom', 'email']
        
        for field in required_fields:
            if not data.get(field) or not str(data[field]).strip():
                return False
        
        # Valider l'email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return False
        
        return True
    
    def _validate_password(self, password):
        """Valider le mot de passe"""
        return password and len(password) >= 8
    
    def _generate_temp_password(self, length=12):
        """Générer un mot de passe temporaire"""
        import string
        characters = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(secrets.choice(characters) for _ in range(length))