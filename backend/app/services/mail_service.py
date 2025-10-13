from flask_mail import Message
from flask import current_app, render_template
from datetime import datetime
import logging

class MailService:
    @staticmethod
    def is_enabled():
        """Vérifie si le service mail est activé"""
        return current_app.config.get('MAIL_USERNAME') is not None
    
    @staticmethod
    def send_email(to, subject, template=None, body=None, **kwargs):
        """
        Envoie un email avec vérification de configuration
        :param to: destinataire(s) - str ou list
        :param subject: sujet de l'email
        :param template: template HTML (optionnel)
        :param body: corps du message texte
        :param kwargs: variables pour le template
        """
        if not MailService.is_enabled():
            logging.warning("Service mail non configuré - email non envoyé")
            return {"success": False, "message": "Service mail non configuré"}
        
        try:
            from app import mail  # Import ici pour éviter les imports circulaires
            
            # Créer le message
            msg = Message(
                subject=subject,
                sender=current_app.config['MAIL_DEFAULT_SENDER'],
                recipients=[to] if isinstance(to, str) else to
            )
            
            # Corps du message
            if template:
                try:
                    # Ajouter l'année courante aux variables du template
                    kwargs['current_year'] = datetime.now().year
                    msg.html = render_template(f'emails/{template}.html', **kwargs)
                except Exception as e:
                    logging.warning(f"Template {template} non trouvé, utilisation du body texte: {e}")
                    msg.body = body or "Email depuis SERTEC IoT"
            else:
                msg.body = body or "Email depuis SERTEC IoT"
            
            # Envoyer l'email
            mail.send(msg)
            
            logging.info(f"Email envoyé avec succès à {to}")
            return {"success": True, "message": "Email envoyé avec succès"}
            
        except Exception as e:
            logging.error(f"Erreur envoi email: {e}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def send_welcome_email(user_email, username):
        """Envoie un email de bienvenue"""
        return MailService.send_email(
            to=user_email,
            subject="🎉 Bienvenue sur SERTEC IoT",
            template="welcome",
            username=username,
            platform_name="SERTEC IoT"
        )
    
    @staticmethod
    def send_password_reset_email(user_email, username, reset_token, expires_minutes=5):
        """
        Envoie un email de réinitialisation de mot de passe
        :param user_email: email du destinataire
        :param username: nom de l'utilisateur
        :param reset_token: token de réinitialisation
        :param expires_minutes: durée de validité en minutes (défaut: 5)
        """
        if not MailService.is_enabled():
            logging.warning("Service mail non configuré - email de réinitialisation non envoyé")
            return {"success": False, "message": "Service mail non configuré"}
        
        try:
            # URL de réinitialisation (à adapter selon votre frontend)
            frontend_url = current_app.config.get('FRONTEND_URL', 'https://sertecingenierie.vercel.app')
            reset_url = f"{frontend_url}/reset-password?token={reset_token}"
            
            result = MailService.send_email(
                to=user_email,
                subject="🔐 Réinitialisation de votre mot de passe - SERTEC IoT",
                template="password_reset",
                username=username,
                reset_token=reset_token,
                reset_url=reset_url,
                expires_minutes=expires_minutes,
                support_email=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            
            if result['success']:
                logging.info(f"Email de réinitialisation envoyé à {user_email}")
            else:
                logging.error(f"Échec envoi email réinitialisation à {user_email}: {result['message']}")
                
            return result
            
        except Exception as e:
            logging.error(f"Erreur envoi email réinitialisation: {e}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def send_password_changed_notification(user_email, username):
        """
        Envoie une notification de changement de mot de passe
        """
        if not MailService.is_enabled():
            return {"success": False, "message": "Service mail non configuré"}
        
        try:
            result = MailService.send_email(
                to=user_email,
                subject="🔐 Mot de passe modifié - SERTEC IoT",
                template="password_changed",
                username=username,
                timestamp=datetime.now().strftime("%d/%m/%Y à %H:%M"),
                support_email=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            return result
        except Exception as e:
            logging.error(f"Erreur envoi notification changement mot de passe: {e}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def send_device_alert(user_email, device_name, alert_type, alert_message):
        """Envoie une alerte device"""
        if not MailService.is_enabled():
            return {"success": False, "message": "Service mail non configuré"}
        
        try:
            result = MailService.send_email(
                to=user_email,
                subject=f"🚨 Alerte {device_name}",
                template="device_alert",
                device_name=device_name,
                alert_type=alert_type,
                alert_message=alert_message,
                timestamp=datetime.now().strftime("%d/%m/%Y à %H:%M")
            )
            return result
        except Exception as e:
            logging.error(f"Erreur envoi alerte device: {e}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def send_activation_email(user_email, username, client_name, activation_token, expires_minutes=15):
        """
        Envoie un email d'activation de compte avec votre template existant
        :param user_email: email du destinataire
        :param username: nom de l'utilisateur
        :param client_name: nom de l'entreprise/client
        :param activation_token: token d'activation
        :param expires_minutes: durée de validité en minutes (défaut: 15)
        """
        if not MailService.is_enabled():
            logging.warning("Service mail non configuré - email d'activation non envoyé")
            return {"success": False, "message": "Service mail non configuré"}
        
        try:
            # URL d'activation (à adapter selon votre frontend)
            frontend_url = current_app.config.get('FRONTEND_URL', 'https://sertecingenierie.vercel.app')
            activation_url = f"{frontend_url}/activation?token={activation_token}"
            
            result = MailService.send_email(
                to=user_email,
                subject=f"🎉 Activation de votre compte administrateur - {client_name}",
                template="account_activation",
                username=username,
                client_name=client_name,
                user_email=user_email,  # Pour l'affichage dans le template
                activation_token=activation_token,
                activation_url=activation_url,
                expires_minutes=expires_minutes,
                support_email=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            
            if result['success']:
                logging.info(f"Email d'activation envoyé à {user_email} pour {client_name}")
            else:
                logging.error(f"Échec envoi email activation à {user_email}: {result['message']}")
                
            return result
            
        except Exception as e:
            logging.error(f"Erreur envoi email d'activation: {e}")
            return {"success": False, "message": str(e)}
        

    # Ajoutez ces deux méthodes à la fin de votre classe MailService

    @staticmethod
    def send_admin_activation_email(user_email, prenom, nom, client_name, activation_token, expires_hours=24):
        """
        Envoie un email d'activation spécifique pour les administrateurs
        Utilise le système en deux phases : activation + définition du mot de passe
        
        :param user_email: email de l'administrateur
        :param prenom: prénom de l'administrateur
        :param nom: nom de l'administrateur
        :param client_name: nom de l'entreprise/client
        :param activation_token: token d'activation
        :param expires_hours: durée de validité en heures (défaut: 24h)
        """
        if not MailService.is_enabled():
            logging.warning("Service mail non configuré - email d'activation admin non envoyé")
            return {"success": False, "message": "Service mail non configuré"}
        
        try:
            # URL d'activation pour admin (différente de l'activation normale)
            frontend_url = current_app.config.get('FRONTEND_URL', 'https://sertecingenierie.vercel.app')
            activation_url = f"{frontend_url}/activer-admin/{activation_token}"
            
            # Nom complet pour affichage
            full_name = f"{prenom} {nom}"
            
            result = MailService.send_email(
                to=user_email,
                subject=f"🎉 Activation de votre compte administrateur - {client_name}",
                template="admin_activation",  # Nouveau template spécifique
                username=full_name,
                prenom=prenom,
                nom=nom,
                client_name=client_name,
                user_email=user_email,
                activation_token=activation_token,
                activation_url=activation_url,
                expires_hours=expires_hours,
                support_email=current_app.config.get('MAIL_DEFAULT_SENDER'),
                platform_name="SERTEC IoT"
            )
            
            if result['success']:
                logging.info(f"Email d'activation admin envoyé à {user_email} pour {client_name}")
            else:
                logging.error(f"Échec envoi email activation admin à {user_email}: {result['message']}")
                
            return result
            
        except Exception as e:
            logging.error(f"Erreur envoi email d'activation admin: {e}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def send_new_password_email(user_email, prenom, nom, new_password, admin_name=None):
        """
        Envoie un email avec un nouveau mot de passe généré
        Pour la fonctionnalité "mot de passe oublié" ou reset par admin
        
        :param user_email: email du destinataire
        :param prenom: prénom de l'utilisateur
        :param nom: nom de l'utilisateur
        :param new_password: nouveau mot de passe temporaire
        :param admin_name: nom de l'admin qui a fait le reset (optionnel)
        """
        if not MailService.is_enabled():
            logging.warning("Service mail non configuré - email nouveau mot de passe non envoyé")
            return {"success": False, "message": "Service mail non configuré"}
        
        try:
            # Nom complet pour affichage
            full_name = f"{prenom} {nom}"
            
            # Déterminer qui a effectué le reset
            reset_by = f"par {admin_name}" if admin_name else "automatiquement"
            
            result = MailService.send_email(
                to=user_email,
                subject="🔐 Nouveau mot de passe - SERTEC IoT",
                template="new_password",  # Nouveau template
                username=full_name,
                prenom=prenom,
                nom=nom,
                new_password=new_password,
                reset_by=reset_by,
                admin_name=admin_name,
                timestamp=datetime.now().strftime("%d/%m/%Y à %H:%M"),
                support_email=current_app.config.get('MAIL_DEFAULT_SENDER'),
                platform_name="SERTEC IoT"
            )
            
            if result['success']:
                logging.info(f"Email nouveau mot de passe envoyé à {user_email}")
            else:
                logging.error(f"Échec envoi email nouveau mot de passe à {user_email}: {result['message']}")
                
            return result
            
        except Exception as e:
            logging.error(f"Erreur envoi email nouveau mot de passe: {e}")
            return {"success": False, "message": str(e)}
        


    @staticmethod
    def send_activation_confirmation_email(user_email, prenom, nom, client_name, login_url=None):
        """
        Envoie un email de confirmation après activation réussie
        Informe l'utilisateur qu'il peut maintenant se connecter
        
        :param user_email: email de l'administrateur
        :param prenom: prénom de l'administrateur
        :param nom: nom de l'administrateur
        :param client_name: nom de l'entreprise/client
        :param login_url: URL de connexion (optionnel)
        """
        if not MailService.is_enabled():
            logging.warning("Service mail non configuré - email de confirmation activation non envoyé")
            return {"success": False, "message": "Service mail non configuré"}
        
        try:
            # URL de connexion
            frontend_url = current_app.config.get('FRONTEND_URL', 'https://sertecingenierie.vercel.app')
            login_url = login_url or f"{frontend_url}/login"
            
            # Nom complet pour affichage
            full_name = f"{prenom} {nom}"
            
            result = MailService.send_email(
                to=user_email,
                subject=f"✅ Compte activé avec succès - {client_name}",
                template="activation_success",  # Nouveau template
                username=full_name,
                prenom=prenom,
                nom=nom,
                client_name=client_name,
                user_email=user_email,
                login_url=login_url,
                timestamp=datetime.now().strftime("%d/%m/%Y à %H:%M"),
                support_email=current_app.config.get('MAIL_DEFAULT_SENDER'),
                platform_name="SERTEC IoT"
            )
            
            if result['success']:
                logging.info(f"Email de confirmation activation envoyé à {user_email} pour {client_name}")
            else:
                logging.error(f"Échec envoi email confirmation activation à {user_email}: {result['message']}")
                
            return result
            
        except Exception as e:
            logging.error(f"Erreur envoi email confirmation activation: {e}")
            return {"success": False, "message": str(e)}
        

    @staticmethod
    def send_user_activation_email(user_email, prenom, nom, client_name, activation_token, expires_hours=24, site_name=None):
        """
        Envoie un email d'activation spécifique pour les utilisateurs standards
            
        :param user_email: email de l'utilisateur
        :param prenom: prénom de l'utilisateur
        :param nom: nom de l'utilisateur
        :param client_name: nom de l'entreprise/client
        :param activation_token: token d'activation
        :param expires_hours: durée de validité en heures (défaut: 24h)
        :param site_name: nom du site assigné (optionnel) ✅ NOUVEAU
        """
        if not MailService.is_enabled():
            logging.warning("Service mail non configuré - email d'activation utilisateur non envoyé")
            return {"success": False, "message": "Service mail non configuré"}
            
        try:
            # URL d'activation pour utilisateur standard
            frontend_url = current_app.config.get('FRONTEND_URL', 'https://sertecingenierie.vercel.app')
            activation_url = f"{frontend_url}/activer-utilisateur/{activation_token}"
                
            # Nom complet pour affichage
            full_name = f"{prenom} {nom}"
            
            # ✅ NOUVEAU : Sujet enrichi avec site si disponible
            if site_name:
                subject = f"🎉 Activation de votre compte - {client_name} (Site: {site_name})"
            else:
                subject = f"🎉 Activation de votre compte utilisateur - {client_name}"
                
            result = MailService.send_email(
                to=user_email,
                subject=subject,
                template="user_activation",  # Template spécifique pour utilisateurs
                username=full_name,
                prenom=prenom,
                nom=nom,
                client_name=client_name,
                site_name=site_name,  # ✅ NOUVEAU : Passer site_name au template
                user_email=user_email,
                activation_token=activation_token,
                activation_url=activation_url,
                expires_hours=expires_hours,
                support_email=current_app.config.get('MAIL_DEFAULT_SENDER'),
                platform_name="SERTEC IoT"
            )
                
            if result['success']:
                site_info = f" pour le site {site_name}" if site_name else ""
                logging.info(f"Email d'activation utilisateur envoyé à {user_email} pour {client_name}{site_info}")
            else:
                logging.error(f"Échec envoi email activation utilisateur à {user_email}: {result['message']}")
                    
            return result
                
        except Exception as e:
            logging.error(f"Erreur envoi email d'activation utilisateur: {e}")
            return {"success": False, "message": str(e)}


    @staticmethod
    def send_superadmin_activation_email(user_email, prenom, nom, activation_token, expires_hours=24):
        """
        Envoie un email d'activation spécifique pour les superadministrateurs
        
        :param user_email: email du superadmin
        :param prenom: prénom du superadmin
        :param nom: nom du superadmin
        :param activation_token: token d'activation
        :param expires_hours: durée de validité en heures (défaut: 24h)
        """
        if not MailService.is_enabled():
            logging.warning("Service mail non configuré - email d'activation superadmin non envoyé")
            return {"success": False, "message": "Service mail non configuré"}
        
        try:
            # URL d'activation pour superadmin
            frontend_url = current_app.config.get('FRONTEND_URL', 'https://sertecingenierie.vercel.app')
            activation_url = f"{frontend_url}/activer-superadmin/{activation_token}"
            
            # Nom complet pour affichage
            full_name = f"{prenom} {nom}"
            
            result = MailService.send_email(
                to=user_email,
                subject="🎉 Activation de votre compte superadministrateur - SERTEC IoT",
                template="superadmin_activation",  # Template spécifique pour superadmins
                username=full_name,
                prenom=prenom,
                nom=nom,
                client_name="SERTEC IoT",  # Les superadmins n'ont pas de client spécifique
                user_email=user_email,
                activation_token=activation_token,
                activation_url=activation_url,
                expires_hours=expires_hours,
                support_email=current_app.config.get('MAIL_DEFAULT_SENDER'),
                platform_name="SERTEC IoT"
            )
            
            if result['success']:
                logging.info(f"Email d'activation superadmin envoyé à {user_email}")
            else:
                logging.error(f"Échec envoi email activation superadmin à {user_email}: {result['message']}")
                
            return result
            
        except Exception as e:
            logging.error(f"Erreur envoi email d'activation superadmin: {e}")
            return {"success": False, "message": str(e)}