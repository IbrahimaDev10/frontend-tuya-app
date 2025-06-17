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
            frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
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