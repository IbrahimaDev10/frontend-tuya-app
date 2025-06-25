from flask_jwt_extended import create_access_token, create_refresh_token
from app import db, get_redis  # ✅ NOUVEAU : Import get_redis
from app.models import User, Client
from app.services.mail_service import MailService  
from datetime import datetime, timedelta
import secrets
import re
import logging
import json

class AuthService:
    def __init__(self):
        # ✅ MODIFIÉ : Redis d'abord, sinon mémoire comme fallback
        self.redis = get_redis()
        self.reset_tokens = {}  # Fallback si Redis indisponible
    
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
            
            # Créer l'utilisateur selon votre modèle exact
            user = User(
                prenom=user_data['prenom'].strip(),
                nom=user_data['nom'].strip(),
                email=user_data['email'].lower().strip(),
                telephone=user_data.get('telephone', '').strip() or None,
                role=role,
                client_id=client_id
            )
            
            # Définir le mot de passe avec votre méthode
            password = user_data.get('password')
            if not password:
                password = self._generate_temp_password()
            
            user.set_password(password)  # Utilise votre méthode qui gère mot_de_passe_hash
            
            db.session.add(user)
            db.session.commit()
            
            # Envoyer email de bienvenue
            if MailService.is_enabled():
                welcome_result = MailService.send_welcome_email(user.email, user.nom_complet)
                if welcome_result['success']:
                    logging.info(f"Email de bienvenue envoyé à {user.email}")
                else:
                    logging.warning(f"Échec envoi email bienvenue: {welcome_result['message']}")
            
            return user, None
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de l'enregistrement: {str(e)}"
    
    def login(self, email, password):
        """Connexion utilisateur avec sessions Redis"""
        try:
            # Validation des entrées
            if not email or not password:
                return None, "Email et mot de passe requis"
            
            email = email.lower().strip()
            
            # Rechercher l'utilisateur avec vos champs
            user = User.query.filter_by(email=email, actif=True).first()
            if not user:
                return None, "Email ou mot de passe incorrect"
            
            # Vérifier le mot de passe avec votre méthode
            if not user.check_password(password):
                return None, "Email ou mot de passe incorrect"
            
            # Mettre à jour la dernière connexion avec votre méthode
            user.update_last_login()
            
            # Créer les tokens JWT
            access_token = create_access_token(
                identity=user.id,
                additional_claims={
                    'role': user.role,
                    'client_id': user.client_id,
                    'email': user.email,
                    'nom_complet': user.nom_complet  # Votre propriété
                },
                expires_delta=timedelta(hours=1)  # 1 heure
            )
            
            refresh_token = create_refresh_token(
                identity=user.id,
                expires_delta=timedelta(hours=8)  # 8 heures
            )
            
            # ✅ NOUVEAU : Sauvegarder session dans Redis
            self._save_user_session(user, access_token)
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': user.to_dict(),  # Votre méthode to_dict
                'expires_in': 1 * 3600,        # 3600 secondes = 1 heure
                'refresh_expires_in': 8 * 3600  # 28800 secondes = 8 heures
            }, None
            
        except Exception as e:
            return None, f"Erreur lors de la connexion: {str(e)}"
    
    def refresh_token(self, user_id):
        """Renouveler le token d'accès"""
        try:
            user = User.query.get(user_id)
            if not user or not user.actif:
                return None, "Utilisateur non trouvé ou inactif"
            
            # Créer un nouveau access token
            new_access_token = create_access_token(
                identity=user.id,
                additional_claims={
                    'role': user.role,
                    'client_id': user.client_id,
                    'email': user.email,
                    'nom_complet': user.nom_complet
                },
                expires_delta=timedelta(hours=1)  # 1 heure
            )
            
            # ✅ NOUVEAU : Mettre à jour session Redis
            self._save_user_session(user, new_access_token)
            
            return {
                'access_token': new_access_token,
                'expires_in': 3600,  # 1 heure en secondes
                'user': user.to_dict()
            }, None
            
        except Exception as e:
            return None, f"Erreur lors du renouvellement: {str(e)}"
    
    def logout(self, user_id):
        """Déconnexion avec nettoyage Redis"""
        try:
            # ✅ NOUVEAU : Supprimer session Redis
            self._remove_user_session(user_id)
            
            user = User.query.get(user_id)
            if user:
                # Log optionnel de déconnexion
                logging.info(f"Déconnexion utilisateur: {user.email}")
            
            return True, "Déconnexion réussie"
            
        except Exception as e:
            return False, f"Erreur lors de la déconnexion: {str(e)}"
    
    def get_profile(self, user_id):
        """Récupérer le profil utilisateur"""
        try:
            user = User.query.get(user_id)
            if not user or not user.actif:
                return None, "Utilisateur non trouvé"
            
            # Utiliser votre méthode to_dict avec include_sensitive
            profile_data = user.to_dict(include_sensitive=True)
            
            # Ajouter des informations sur les permissions avec vos méthodes
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
            
            # Champs modifiables par l'utilisateur selon votre modèle
            allowed_fields = ['prenom', 'nom', 'telephone']
            
            for field in allowed_fields:
                if field in profile_data and profile_data[field] is not None:
                    value = str(profile_data[field]).strip()
                    if field in ['prenom', 'nom'] and not value:
                        return None, f"Le champ {field} ne peut pas être vide"
                    setattr(user, field, value if value else None)
            
            db.session.commit()
            
            # ✅ NOUVEAU : Mettre à jour session Redis avec nouvelles infos
            self._update_user_session(user)
            
            return user.to_dict(), None  # Votre méthode to_dict
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de la mise à jour: {str(e)}"
    
    def change_password(self, user_id, old_password, new_password):
        """Changer le mot de passe"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "Utilisateur non trouvé"
            
            # Vérifier l'ancien mot de passe avec votre méthode
            if not user.check_password(old_password):
                return False, "Ancien mot de passe incorrect"
            
            # Valider le nouveau mot de passe
            if not self._validate_password(new_password):
                return False, "Le nouveau mot de passe doit contenir au moins 8 caractères"
            
            # Changer le mot de passe avec votre méthode
            user.set_password(new_password)
            db.session.commit()
            
            # ✅ NOUVEAU : Invalider toutes les sessions de cet utilisateur
            self._invalidate_all_user_sessions(user_id)
            
            # Envoyer notification de changement
            if MailService.is_enabled():
                notification_result = MailService.send_password_changed_notification(
                    user.email, 
                    user.nom_complet
                )
                if notification_result['success']:
                    logging.info(f"Notification changement mot de passe envoyée à {user.email}")
            
            return True, "Mot de passe modifié avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors du changement: {str(e)}"
    
    def forgot_password(self, email):
        """
        Demander la réinitialisation du mot de passe avec Redis
        """
        try:
            email = email.lower().strip()
            user = User.query.filter_by(email=email, actif=True).first()
            
            # Pour la sécurité, on retourne toujours success même si l'email n'existe pas
            if not user:
                return True, "Si cet email existe, vous recevrez un lien de réinitialisation"
            
            # Générer un token de réinitialisation
            reset_token = secrets.token_urlsafe(32)
            
            # Expiration à 5 minutes
            expires_at = datetime.utcnow() + timedelta(minutes=5)
            
            # ✅ NOUVEAU : Stocker le token dans Redis OU mémoire
            self._save_reset_token(reset_token, {
                'user_id': user.id,
                'email': user.email,
                'expires_at': expires_at
            })
            
            # Envoyer l'email de réinitialisation
            if MailService.is_enabled():
                email_result = MailService.send_password_reset_email(
                    user_email=user.email,
                    username=user.nom_complet,
                    reset_token=reset_token,
                    expires_minutes=5
                )
                
                if email_result['success']:
                    logging.info(f"Email de réinitialisation envoyé à {user.email}")
                    return True, "Un email de réinitialisation a été envoyé. Le lien expire dans 5 minutes."
                else:
                    # Si l'email n'a pas pu être envoyé, supprimer le token
                    self._remove_reset_token(reset_token)
                    logging.error(f"Échec envoi email réinitialisation: {email_result['message']}")
                    return False, "Erreur lors de l'envoi de l'email. Veuillez réessayer."
            else:
                # Service mail non configuré - mode développement
                logging.warning("Service mail non configuré - token retourné pour développement")
                return True, f"Token de réinitialisation (dev): {reset_token}"
            
        except Exception as e:
            # Nettoyer le token en cas d'erreur
            if 'reset_token' in locals():
                self._remove_reset_token(reset_token)
            return False, f"Erreur lors de la demande: {str(e)}"
    
    def reset_password(self, token, new_password):
        """
        Réinitialiser le mot de passe avec token Redis
        """
        try:
            # ✅ MODIFIÉ : Récupérer token depuis Redis OU mémoire
            token_data = self._get_reset_token(token)
            
            if not token_data:
                return False, "Token invalide ou expiré"
            
            # Vérifier l'expiration (5 minutes)
            expires_at = token_data['expires_at']
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            
            if datetime.utcnow() > expires_at:
                self._remove_reset_token(token)
                return False, "Token expiré. Veuillez refaire une demande de réinitialisation."
            
            # Valider le nouveau mot de passe
            if not self._validate_password(new_password):
                return False, "Le mot de passe doit contenir au moins 8 caractères"
            
            # Trouver l'utilisateur
            user = User.query.get(token_data['user_id'])
            if not user or not user.actif:
                self._remove_reset_token(token)
                return False, "Utilisateur non trouvé"
            
            # Changer le mot de passe avec votre méthode
            user.set_password(new_password)
            db.session.commit()
            
            # ✅ NOUVEAU : Invalider toutes les sessions de cet utilisateur
            self._invalidate_all_user_sessions(user.id)
            
            # Envoyer notification de changement réussi
            if MailService.is_enabled():
                notification_result = MailService.send_password_changed_notification(
                    user.email, 
                    user.nom_complet
                )
                if notification_result['success']:
                    logging.info(f"Notification changement mot de passe envoyée à {user.email}")
            
            # Supprimer le token utilisé
            self._remove_reset_token(token)
            
            return True, "Mot de passe réinitialisé avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la réinitialisation: {str(e)}"
    
    def admin_reset_password(self, target_email, new_password, admin_user):
        """Réinitialisation par un administrateur"""
        try:
            if not admin_user.is_admin():  # Votre méthode
                return False, "Permission insuffisante"
            
            target_user = User.query.filter_by(email=target_email.lower().strip()).first()
            if not target_user:
                return False, "Utilisateur non trouvé"
            
            # Vérifier que l'admin peut gérer cet utilisateur avec vos méthodes
            if not admin_user.is_superadmin():
                if target_user.client_id != admin_user.client_id:
                    return False, "Vous ne pouvez gérer que les utilisateurs de votre organisation"
                
                if target_user.role in ['superadmin', 'admin']:
                    return False, "Permission insuffisante pour ce type d'utilisateur"
            
            # Valider le mot de passe
            if not self._validate_password(new_password):
                return False, "Le mot de passe doit contenir au moins 8 caractères"
            
            # Réinitialiser avec votre méthode
            target_user.set_password(new_password)
            db.session.commit()
            
            # ✅ NOUVEAU : Invalider toutes les sessions de l'utilisateur cible
            self._invalidate_all_user_sessions(target_user.id)
            
            # Envoyer notification à l'utilisateur
            if MailService.is_enabled():
                notification_result = MailService.send_password_changed_notification(
                    target_user.email, 
                    target_user.nom_complet
                )
                if notification_result['success']:
                    logging.info(f"Notification réinitialisation admin envoyée à {target_user.email}")
            
            return True, f"Mot de passe réinitialisé pour {target_user.nom_complet}"  # Votre propriété
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la réinitialisation: {str(e)}"
    
    def get_reset_token_info(self, token):
        """
        Vérifier les informations d'un token de réinitialisation
        """
        token_data = self._get_reset_token(token)
        
        if not token_data:
            return None, "Token invalide"
        
        expires_at = token_data['expires_at']
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        if datetime.utcnow() > expires_at:
            self._remove_reset_token(token)
            return None, "Token expiré"
        
        # Calculer le temps restant
        time_remaining = expires_at - datetime.utcnow()
        seconds_remaining = int(time_remaining.total_seconds())
        
        return {
            'valid': True,
            'email': token_data['email'],
            'seconds_remaining': seconds_remaining,
            'expires_at': expires_at.isoformat()
        }, None
    
    def cleanup_expired_tokens(self):
        """
        Nettoyer les tokens expirés (Redis + mémoire)
        """
        try:
            # ✅ NOUVEAU : Nettoyer les tokens Redis expirés
            if self.redis:
                # Redis TTL gère automatiquement l'expiration
                # Mais on peut compter combien on a nettoyé
                cleaned_count = 0
                
                # Scan les clés de reset tokens
                for key in self.redis.scan_iter("reset_token:*"):
                    if not self.redis.exists(key):
                        cleaned_count += 1
                
                logging.info(f"Redis: {cleaned_count} tokens expirés nettoyés automatiquement")
            
            # Nettoyer aussi la mémoire (fallback)
            current_time = datetime.utcnow()
            expired_tokens = []
            
            for token, data in self.reset_tokens.items():
                expires_at = data['expires_at']
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                if current_time > expires_at:
                    expired_tokens.append(token)
            
            for token in expired_tokens:
                del self.reset_tokens[token]
            
            if expired_tokens:
                logging.info(f"Mémoire: {len(expired_tokens)} tokens expirés nettoyés")
            
            return len(expired_tokens)
            
        except Exception as e:
            logging.error(f"Erreur nettoyage tokens: {e}")
            return 0
    
    # =================== MÉTHODES REDIS PRIVÉES ===================
    
    def _save_user_session(self, user, access_token):
        """Sauvegarder session utilisateur dans Redis"""
        try:
            if not self.redis:
                return  # Pas de Redis, skip
            
            session_data = {
                'user_id': user.id,
                'email': user.email,
                'role': user.role,
                'client_id': user.client_id,
                'nom_complet': user.nom_complet,
                'access_token': access_token,
                'login_time': datetime.utcnow().isoformat(),
                'last_activity': datetime.utcnow().isoformat()
            }
            
            # Clé: session:user_id
            key = f"session:{user.id}"
            
            # TTL = 1 heure (durée du access token)
            self.redis.setex(key, 3600, json.dumps(session_data))
            
            logging.debug(f"Session Redis sauvée pour {user.email}")
            
        except Exception as e:
            logging.error(f"Erreur sauvegarde session Redis: {e}")
    
    def _update_user_session(self, user):
        """Mettre à jour session utilisateur dans Redis"""
        try:
            if not self.redis:
                return
            
            key = f"session:{user.id}"
            
            # Récupérer session existante
            session_json = self.redis.get(key)
            if session_json:
                session_data = json.loads(session_json)
                
                # Mettre à jour les infos modifiables
                session_data.update({
                    'nom_complet': user.nom_complet,
                    'last_activity': datetime.utcnow().isoformat()
                })
                
                # Re-sauvegarder avec même TTL
                ttl = self.redis.ttl(key)
                if ttl > 0:
                    self.redis.setex(key, ttl, json.dumps(session_data))
                
        except Exception as e:
            logging.error(f"Erreur mise à jour session Redis: {e}")
    
    def _remove_user_session(self, user_id):
        """Supprimer session utilisateur de Redis"""
        try:
            if not self.redis:
                return
            
            key = f"session:{user_id}"
            self.redis.delete(key)
            
            logging.debug(f"Session Redis supprimée pour user {user_id}")
            
        except Exception as e:
            logging.error(f"Erreur suppression session Redis: {e}")
    
    def _invalidate_all_user_sessions(self, user_id):
        """Invalider toutes les sessions d'un utilisateur"""
        try:
            if not self.redis:
                return
            
            # Supprimer la session actuelle
            self._remove_user_session(user_id)
            
            # En production, on pourrait aussi ajouter à une blacklist JWT
            logging.info(f"Sessions invalidées pour user {user_id}")
            
        except Exception as e:
            logging.error(f"Erreur invalidation sessions: {e}")
    
    def _save_reset_token(self, token, data):
        """Sauvegarder token de reset dans Redis OU mémoire"""
        try:
            if self.redis:
                # Redis: TTL automatique = 5 minutes
                key = f"reset_token:{token}"
                
                # Convertir datetime en string pour JSON
                data_copy = data.copy()
                if isinstance(data_copy['expires_at'], datetime):
                    data_copy['expires_at'] = data_copy['expires_at'].isoformat()
                
                self.redis.setex(key, 300, json.dumps(data_copy))  # 300s = 5min
                logging.debug(f"Token reset Redis sauvé: {token}")
            else:
                # Fallback mémoire
                self.reset_tokens[token] = data
                logging.debug(f"Token reset mémoire sauvé: {token}")
                
        except Exception as e:
            logging.error(f"Erreur sauvegarde token reset: {e}")
            # Fallback mémoire en cas d'erreur Redis
            self.reset_tokens[token] = data
    
    def _get_reset_token(self, token):
        """Récupérer token de reset depuis Redis OU mémoire"""
        try:
            if self.redis:
                # Redis d'abord
                key = f"reset_token:{token}"
                token_json = self.redis.get(key)
                
                if token_json:
                    return json.loads(token_json)
            
            # Fallback mémoire
            return self.reset_tokens.get(token)
            
        except Exception as e:
            logging.error(f"Erreur récupération token reset: {e}")
            # Fallback mémoire en cas d'erreur Redis
            return self.reset_tokens.get(token)
    
    def _remove_reset_token(self, token):
        """Supprimer token de reset de Redis ET mémoire"""
        try:
            if self.redis:
                key = f"reset_token:{token}"
                self.redis.delete(key)
            
            # Supprimer aussi de la mémoire
            if token in self.reset_tokens:
                del self.reset_tokens[token]
                
        except Exception as e:
            logging.error(f"Erreur suppression token reset: {e}")
            # Au moins supprimer de la mémoire
            if token in self.reset_tokens:
                del self.reset_tokens[token]
    
    # =================== MÉTHODES DE VALIDATION ===================
    
    def _validate_user_data(self, data):
        """Valider les données utilisateur selon votre modèle"""
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