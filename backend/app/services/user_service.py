from app import db
from app.models.user import User
from app.models.client import Client
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from app.utils.token_manager import ActivationTokenManager
from app.services.mail_service import MailService
import secrets
import string


class UserService:
    def __init__(self):
        pass
    
    # =================== GESTION DES CLIENTS ===================
    
    def creer_client(self, donnees_client: Dict[str, Any], utilisateur_createur: User) -> Tuple[Optional[Dict], Optional[str]]:
        """Créer un nouveau client avec son admin automatiquement - SEUL LE SUPERADMIN PEUT"""
        try:
            # Vérification : seul le superadmin peut créer des clients
            if not utilisateur_createur.is_superadmin():
                return None, "Seul le superadmin peut créer des clients"
            
            # Validation des données requises pour le client
            champs_requis = ['nom_entreprise', 'email_contact']
            champs_manquants = [champ for champ in champs_requis if not donnees_client.get(champ)]
            if champs_manquants:
                return None, f"Champs requis manquants: {', '.join(champs_manquants)}"
            
            # Vérifier que l'email de contact n'existe pas déjà (table Client)
            email_contact_existant = Client.query.filter_by(
                email_contact=donnees_client['email_contact'].lower().strip()
            ).first()
            if email_contact_existant:
                return None, "Un client avec cet email de contact existe déjà"
            
            # Déterminer l'email de l'admin (soit spécifique, soit celui du contact)
            email_admin = donnees_client.get('email_admin', donnees_client['email_contact']).lower().strip()
            
            # Vérifier que l'email admin n'existe pas déjà (table User)
            email_admin_existant = User.query.filter_by(email=email_admin).first()
            if email_admin_existant:
                return None, f"Un utilisateur avec l'email {email_admin} existe déjà"
            
            # 🏢 ÉTAPE 1: Créer le client
            nouveau_client = Client(
                nom_entreprise=donnees_client['nom_entreprise'].strip(),
                email_contact=donnees_client['email_contact'].lower().strip(),
                telephone=donnees_client.get('telephone', '').strip() or None,
                adresse=donnees_client.get('adresse', '').strip() or None
            )
            
            db.session.add(nouveau_client)
            db.session.flush()  # Pour obtenir l'ID du client avant commit
            
            # 👤 ÉTAPE 2: Créer automatiquement l'admin du client
            prenom_admin = donnees_client.get('prenom_admin', 'Admin').strip()
            nom_admin = donnees_client.get('nom_admin', nouveau_client.nom_entreprise).strip()
            telephone_admin = donnees_client.get('telephone_admin', donnees_client.get('telephone', '')).strip() or None
            
            admin_client = User(
                prenom=prenom_admin,
                nom=nom_admin,
                email=email_admin,
                telephone=telephone_admin,
                role='admin',
                client_id=nouveau_client.id,
                actif=False  # ✅ CHANGEMENT : Créer inactif
            )
            
            # 🔐 CHANGEMENT : Créer avec un mot de passe temporaire (sera remplacé lors de l'activation)
            admin_client.set_password("temp_password_will_be_replaced")
            
            db.session.add(admin_client)
            db.session.flush()  # Pour obtenir l'ID de l'admin
            
            # 📧 NOUVEAU : Générer token d'activation et envoyer email
            from app.utils.token_manager import ActivationTokenManager
            from app.services.mail_service import MailService

            print(f"🔍 Génération token pour admin:")
            print(f"   - ID: {admin_client.id}")
            print(f"   - Email: {email_admin}")
            print(f"   - Prénom: {prenom_admin}")
            print(f"   - Nom: {nom_admin}")

            # Nouveau code correct avec la bonne variable
            token = ActivationTokenManager.generate_token(admin_client.id, email_admin, 86400)  # 24h
            print(f"🎫 Token généré: {token}")

            # Vérifier que le token est bien enregistré
            validation = ActivationTokenManager.validate_token(token)
            print(f"✅ Validation immédiate du token: {validation}")
                
            # Envoyer l'email d'activation
            email_result = MailService.send_admin_activation_email(
                user_email=email_admin,
                prenom=prenom_admin,
                nom=nom_admin,
                client_name=nouveau_client.nom_entreprise,
                activation_token=token,
                expires_hours=24
            )

            print(f"📧 Résultat envoi email: {email_result}")
            
            db.session.commit()
            
            # 🎉 Préparer le résultat modifié
            resultat = {
                'client': nouveau_client.to_dict(),
                'admin_client': admin_client.to_dict(),
                'token_activation': token,  # Pour debug/test seulement
                'email_result': email_result,
                'identifiants_connexion': {
                    'email': email_admin,
                    'status': 'En attente d\'activation'
                },
                'message_instructions': f"Un email d'activation a été envoyé à {email_admin}"
            }
            
            return resultat, None
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de la création: {str(e)}"
    
    def modifier_client(self, client_id: str, nouvelles_donnees: Dict[str, Any], utilisateur_modificateur: User) -> Tuple[Optional[Client], Optional[str]]:
        """Modifier un client existant"""
        try:
            # Vérification : seul le superadmin peut modifier des clients
            if not utilisateur_modificateur.is_superadmin():
                return None, "Seul le superadmin peut modifier des clients"
            
            client = Client.query.get(client_id)
            if not client:
                return None, "Client non trouvé"
            
            # Modifier les champs autorisés
            champs_modifiables = ['nom_entreprise', 'email_contact', 'telephone', 'adresse']
            
            for champ in champs_modifiables:
                if champ in nouvelles_donnees:
                    valeur = nouvelles_donnees[champ]
                    if valeur is not None:
                        valeur = str(valeur).strip()
                        if champ in ['nom_entreprise', 'email_contact'] and not valeur:
                            return None, f"Le champ {champ} ne peut pas être vide"
                        if champ == 'email_contact':
                            valeur = valeur.lower()
                    setattr(client, champ, valeur if valeur else None)
            
            db.session.commit()
            return client, None
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de la modification: {str(e)}"
    
    def lister_clients(self, utilisateur_demandeur: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Lister tous les clients - SEUL LE SUPERADMIN PEUT"""
        try:
            if not utilisateur_demandeur.is_superadmin():
                return None, "Seul le superadmin peut voir tous les clients"
            
            # ⚠️ Supprimer le filtre actif=True pour retourner aussi les clients inactifs
            clients = Client.query.order_by(Client.nom_entreprise).all()
            liste_clients = [client.to_dict() for client in clients]
            
            return liste_clients, None

        except Exception as e:
            return None, f"Erreur lors de la récupération: {str(e)}"

    
    def desactiver_client(self, client_id: str, utilisateur_desactivateur: User) -> Tuple[bool, str]:
        """Désactiver un client (et tous ses utilisateurs)"""
        try:
            if not utilisateur_desactivateur.is_superadmin():
                return False, "Seul le superadmin peut désactiver des clients"
            
            client = Client.query.get(client_id)
            if not client:
                return False, "Client non trouvé"
            
            # Désactiver le client
            client.actif = False
            
            # Désactiver tous les utilisateurs de ce client
            utilisateurs_client = User.query.filter_by(client_id=client_id).all()
            for utilisateur in utilisateurs_client:
                utilisateur.actif = False
            
            db.session.commit()
            return True, f"Client {client.nom_entreprise} et ses {len(utilisateurs_client)} utilisateurs désactivés"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la désactivation: {str(e)}"
    
    def supprimer_client(self, client_id: str, utilisateur_supprimeur: User, forcer: bool = False) -> Tuple[bool, str]:
        """Supprimer définitivement un client - SUPERADMIN SEULEMENT"""
        try:
            if not utilisateur_supprimeur.is_superadmin():
                return False, "Seul le superadmin peut supprimer des clients"
            
            client = Client.query.get(client_id)
            if not client:
                return False, "Client non trouvé"
            
            # Vérifier s'il y a des données liées
            nb_utilisateurs = User.query.filter_by(client_id=client_id).count()
            nb_sites = client.sites.count() if hasattr(client, 'sites') else 0
            nb_appareils = client.appareils.count() if hasattr(client, 'appareils') else 0
            nb_donnees = client.donnees.count() if hasattr(client, 'donnees') else 0
            
            # Empêcher la suppression si il y a des données importantes et forcer=False
            if not forcer and (nb_sites > 0 or nb_appareils > 0 or nb_donnees > 0):
                return False, (f"Impossible de supprimer: ce client a {nb_sites} sites, "
                             f"{nb_appareils} appareils et {nb_donnees} données. "
                             f"Utilisez forcer=True pour supprimer définitivement.")
            
            nom_client = client.nom_entreprise
            
            if forcer:
                # Suppression forcée avec CASCADE (vos modèles ont cascade='all, delete-orphan')
                # SQLAlchemy va automatiquement supprimer toutes les données liées
                db.session.delete(client)
                message = (f"Client '{nom_client}' et TOUTES ses données supprimés définitivement "
                          f"({nb_utilisateurs} utilisateurs, {nb_sites} sites, {nb_appareils} appareils)")
            else:
                # Suppression simple (seulement client + utilisateurs)
                # Supprimer d'abord les utilisateurs
                User.query.filter_by(client_id=client_id).delete()
                db.session.delete(client)
                message = f"Client '{nom_client}' et ses {nb_utilisateurs} utilisateurs supprimés"
            
            db.session.commit()
            return True, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la suppression: {str(e)}"
    
    def reactiver_client(self, client_id: str, utilisateur_reactivateur: User) -> Tuple[bool, str]:
        """Réactiver un client désactivé"""
        try:
            if not utilisateur_reactivateur.is_superadmin():
                return False, "Seul le superadmin peut réactiver des clients"
            
            client = Client.query.filter_by(id=client_id, actif=False).first()
            if not client:
                return False, "Client non trouvé ou déjà actif"
            
            # Réactiver le client
            client.actif = True
            
            # Optionnel: réactiver aussi les utilisateurs (demander confirmation)
            # Pour l'instant, on laisse les utilisateurs dans leur état actuel
            
            db.session.commit()
            return True, f"Client {client.nom_entreprise} réactivé (utilisateurs gardent leur état actuel)"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la réactivation: {str(e)}"
    
    # =================== NOUVELLES MÉTHODES POUR L'ACTIVATION ===================
    
    def activer_admin(self, token: str, mot_de_passe: str, confirmation_mot_de_passe: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Activer un compte admin avec définition du mot de passe"""
        try:
            print(f"🔍 === DEBUG ACTIVATION ===")
            print(f"🎫 Token reçu: {token}")
            print(f"🔒 Mot de passe fourni: {'*' * len(mot_de_passe)}")
            print(f"🔒 Confirmation fournie: {'*' * len(confirmation_mot_de_passe)}")
            
            # Validation du token avec debug complet
            print(f"🎫 Tentative d'import de ActivationTokenManager...")
            
            # Essayez différents imports pour identifier le bon
            try:
                from app.utils.token_manager import ActivationTokenManager
                print(f"✅ Import réussi depuis app.utils.token_manager")
            except ImportError as e:
                print(f"❌ Échec import app.utils.token_manager: {e}")
                try:
                    from app.utils.activation_token_manager import ActivationTokenManager
                    print(f"✅ Import réussi depuis app.utils.activation_token_manager")
                except ImportError as e2:
                    print(f"❌ Échec import app.utils.activation_token_manager: {e2}")
                    return None, f"Impossible d'importer ActivationTokenManager"
            
            print(f"🎫 Appel de ActivationTokenManager.validate_token...")
            print(f"🎫 Méthode validate_token: {ActivationTokenManager.validate_token}")
            
            validation = ActivationTokenManager.validate_token(token)
            
            print(f"🎫 === RÉSULTAT VALIDATION ===")
            print(f"Type: {type(validation)}")
            print(f"Contenu: {validation}")
            print(f"Clés disponibles: {list(validation.keys()) if isinstance(validation, dict) else 'Pas un dict'}")
            print(f"=== FIN VALIDATION ===")
            
            # Test de toutes les structures possibles
            user_id = None
            is_valid = False
            error_message = "Token invalide"
            
            if isinstance(validation, dict):
                print(f"✅ C'est un dictionnaire")
                
                # Structure 1: {'valid': True/False, 'user_id': '...', 'message': '...'}
                if 'valid' in validation:
                    print(f"📋 Structure avec 'valid': {validation['valid']}")
                    is_valid = validation['valid']
                    user_id = validation.get('user_id')
                    error_message = validation.get('message', 'Token invalide')
                    
                    # ✅ NOUVEAU : Structure spécifique avec admin_info
                    if is_valid and not user_id and 'admin_info' in validation:
                        print(f"📋 Structure avec admin_info détectée")
                        admin_info = validation['admin_info']
                        print(f"📋 Admin info: {admin_info}")
                        
                        # Récupérer l'user_id depuis la base via l'email
                        if 'email' in admin_info:
                            # SUPPRIMÉ: from app.models import User  # ← PROBLÈME ÉTAIT ICI
                            admin_user = User.query.filter_by(email=admin_info['email']).first()
                            if admin_user:
                                user_id = admin_user.id
                                print(f"📋 User ID trouvé via email: {user_id}")
                            else:
                                print(f"❌ Utilisateur non trouvé avec email: {admin_info['email']}")
                
                # Structure 2: {'success': True/False, 'data': {...}}
                elif 'success' in validation:
                    print(f"📋 Structure avec 'success': {validation['success']}")
                    is_valid = validation['success']
                    if 'data' in validation and isinstance(validation['data'], dict):
                        user_id = validation['data'].get('user_id')
                    else:
                        user_id = validation.get('user_id')
                    error_message = validation.get('message', 'Token invalide')
                
                # Structure 3: Directement les données
                elif 'user_id' in validation:
                    print(f"📋 Structure directe avec user_id")
                    is_valid = True
                    user_id = validation['user_id']
                    error_message = validation.get('message', 'Token valide')
                
                else:
                    print(f"❌ Structure inconnue")
                    print(f"Clés disponibles: {list(validation.keys())}")
                    return None, f"Structure de validation inconnue: {validation}"
            
            elif isinstance(validation, bool):
                print(f"📋 Validation est un boolean: {validation}")
                is_valid = validation
                if not is_valid:
                    return None, "Token invalide"
            
            elif validation is None:
                print(f"❌ Validation est None")
                return None, "Erreur de validation du token"
            
            else:
                print(f"❌ Type de validation inattendu: {type(validation)}")
                return None, f"Format de validation inattendu: {type(validation)}"
            
            print(f"🎯 Résultats de parsing:")
            print(f"   - is_valid: {is_valid}")
            print(f"   - user_id: {user_id}")
            print(f"   - error_message: {error_message}")
            
            if not is_valid:
                return None, error_message
            
            if not user_id:
                return None, "ID utilisateur manquant dans la validation"
            
            print(f"👤 Recherche utilisateur avec ID: {user_id}")
            
            # Récupérer l'utilisateur (User est déjà importé en haut du fichier)
            utilisateur = User.query.get(user_id)
            if not utilisateur:
                print(f"❌ Utilisateur non trouvé avec ID: {user_id}")
                return None, "Utilisateur non trouvé"
            
            print(f"✅ Utilisateur trouvé: {utilisateur.email} (actif: {utilisateur.actif})")
            
            # Vérifications
            if utilisateur.actif:
                return None, "Ce compte est déjà activé"
            
            if mot_de_passe != confirmation_mot_de_passe:
                return None, "Les mots de passe ne correspondent pas"
            
            if len(mot_de_passe) < 8:
                return None, "Le mot de passe doit contenir au moins 8 caractères"
            
            print(f"🔒 Activation du compte en cours...")
            
            # Activer le compte
            utilisateur.set_password(mot_de_passe)
            utilisateur.actif = True
            
            # Invalider le token
            ActivationTokenManager.use_token(token)
            
            db.session.commit()
            
            print(f"✅ Compte activé avec succès pour {utilisateur.email}")
            
            # 📧 Envoyer email de confirmation
            from app.services.mail_service import MailService
            
            # Récupérer les infos du client
            client_name = "SERTEC IoT"
            if utilisateur.client:
                client_name = utilisateur.client.nom_entreprise
            
            email_result = MailService.send_activation_confirmation_email(
                user_email=utilisateur.email,
                prenom=utilisateur.prenom,
                nom=utilisateur.nom,
                client_name=client_name
            )
            
            print(f"📧 Email de confirmation: {email_result}")
            
            resultat = {
                'utilisateur': utilisateur.to_dict(),
                'email_confirmation': email_result,
                'message': f"✅ Compte activé avec succès ! Un email de confirmation a été envoyé à {utilisateur.email}"
            }
            
            return resultat, None
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERREUR DANS ACTIVER_ADMIN: {str(e)}")
            import traceback
            print(f"❌ TRACEBACK:")
            traceback.print_exc()
            return None, f"Erreur lors de l'activation: {str(e)}"
    
    def valider_token_activation(self, token: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Valider un token d'activation sans le consommer (pour vérification côté frontend)"""
        try:
            from app.utils.token_manager import ActivationTokenManager
            
            token_data = ActivationTokenManager.validate_token(token)
            if not token_data:
                return None, "Token invalide ou expiré"
            
            # Récupérer les infos de l'admin
            admin = User.query.get(token_data['user_id'])
            if not admin:
                return None, "Utilisateur non trouvé"
            
            if admin.actif:
                return None, "Ce compte est déjà activé"
            
            # Calculer le temps restant
            import time
            temps_restant = int(token_data['expires_at'] - time.time())
            
            resultat = {
                'admin_info': {
                    'prenom': admin.prenom,
                    'nom': admin.nom,
                    'email': admin.email,
                    'entreprise': admin.client.nom_entreprise if admin.client else None
                },
                'temps_restant_secondes': temps_restant,
                'temps_restant_heures': round(temps_restant / 3600, 1)
            }
            
            return resultat, None
            
        except Exception as e:
            return None, f"Erreur lors de la validation: {str(e)}"
    
    def regenerer_token_activation(self, admin_id: str, utilisateur_regenerateur: User) -> Tuple[Optional[str], Optional[str]]:
        """Régénérer un token d'activation pour un admin inactif"""
        try:
            if not utilisateur_regenerateur.is_superadmin():
                return None, "Seul le superadmin peut régénérer des tokens"
            
            admin = User.query.get(admin_id)
            if not admin:
                return None, "Administrateur non trouvé"
            
            if admin.actif:
                return None, "Ce compte est déjà activé"
            
            if admin.role != 'admin':
                return None, "Cette action n'est disponible que pour les administrateurs"
            
            # Révoquer les anciens tokens de cet utilisateur
            from app.utils.token_manager import ActivationTokenManager
            from app.services.mail_service import MailService
            
            ActivationTokenManager.revoke_user_tokens(admin.id)
            
            # Générer nouveau token
            token = ActivationTokenManager.generate_token(admin.id, admin.email)
            
            # Renvoyer l'email
            email_result = MailService.send_admin_activation_email(
                user_email=admin.email,
                prenom=admin.prenom,
                nom=admin.nom,
                client_name=admin.client.nom_entreprise if admin.client else "Entreprise",
                activation_token=token,
                expires_hours=24
            )
            
            if email_result['success']:
                return token, None
            else:
                return token, f"Token généré mais email non envoyé: {email_result['message']}"
            
        except Exception as e:
            return None, f"Erreur lors de la régénération: {str(e)}"
    
    def lister_admins_en_attente(self, utilisateur_demandeur: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Lister les administrateurs en attente d'activation - SUPERADMIN SEULEMENT"""
        try:
            if not utilisateur_demandeur.is_superadmin():
                return None, "Seul le superadmin peut voir les admins en attente"
            
            admins_inactifs = User.query.filter_by(
                role='admin',
                actif=False
            ).order_by(User.date_creation.desc()).all()
            
            liste_admins = []
            for admin in admins_inactifs:
                admin_dict = admin.to_dict(include_sensitive=True)
                admin_dict['entreprise'] = admin.client.nom_entreprise if admin.client else None
                admin_dict['jours_depuis_creation'] = (datetime.utcnow() - admin.date_creation).days
                liste_admins.append(admin_dict)
            
            return liste_admins, None
            
        except Exception as e:
            return None, f"Erreur lors de la récupération: {str(e)}"
    
    def generer_et_envoyer_nouveau_mot_de_passe(self, utilisateur_id: str, utilisateur_generateur: User) -> Tuple[Optional[str], Optional[str]]:
        """Générer un nouveau mot de passe et l'envoyer par email (pour fonction reset existante)"""
        try:
            # Générer le nouveau mot de passe
            nouveau_mot_de_passe = self._generer_mot_de_passe_temporaire()
            succes, message = self.reinitialiser_mot_de_passe(utilisateur_id, nouveau_mot_de_passe, utilisateur_generateur)
            
            if not succes:
                return None, message
            
            # Récupérer l'utilisateur pour l'email
            utilisateur = User.query.get(utilisateur_id)
            if not utilisateur:
                return None, "Utilisateur non trouvé"
            
            # Envoyer par email
            from app.services.mail_service import MailService
            email_result = MailService.send_new_password_email(
                user_email=utilisateur.email,
                prenom=utilisateur.prenom,
                nom=utilisateur.nom,
                new_password=nouveau_mot_de_passe,
                admin_name=utilisateur_generateur.nom_complet if utilisateur_generateur.id != utilisateur.id else None
            )
            
            if email_result['success']:
                return nouveau_mot_de_passe, None
            else:
                return nouveau_mot_de_passe, f"Mot de passe généré mais email non envoyé: {email_result['message']}"
                
        except Exception as e:
            return None, f"Erreur lors de la génération: {str(e)}"
        

    # =================== GESTION DES UTILISATEURS ===================
    
    def creer_utilisateur(self, donnees_utilisateur: Dict[str, Any], utilisateur_createur: User) -> Tuple[Optional[User], Optional[str]]:
        """Créer un nouvel utilisateur selon les règles de permissions"""
        try:
            # Validation des données de base
            if not self._valider_donnees_utilisateur(donnees_utilisateur):
                return None, "Données utilisateur invalides"
            
            # Vérifier si l'email existe déjà
            email_existant = User.query.filter_by(email=donnees_utilisateur['email'].lower().strip()).first()
            if email_existant:
                return None, "Un utilisateur avec cet email existe déjà"
            
            # Déterminer le rôle et client_id selon les permissions
            role = donnees_utilisateur.get('role', 'user')
            client_id = donnees_utilisateur.get('client_id')
            
            # RÈGLES DE PERMISSIONS :
            if utilisateur_createur.is_superadmin():
                # SUPERADMIN peut créer n'importe qui, n'importe où
                if role == 'superadmin':
                    client_id = None
                elif role in ['admin', 'user'] and not client_id:
                    return None, "client_id requis pour les admin/user"
                
            elif utilisateur_createur.is_admin():
                # ADMIN peut créer seulement des USERS dans SON client
                if role != 'user':
                    return None, "Un admin ne peut créer que des utilisateurs 'user'"
                client_id = utilisateur_createur.client_id
                
            else:
                return None, "Permission insuffisante pour créer des utilisateurs"
            
            # Vérifier que le client existe si spécifié
            if client_id:
                client = Client.query.get(client_id)
                if not client or not client.actif:
                    return None, "Client non trouvé ou inactif"
            
            # Créer l'utilisateur
            nouvel_utilisateur = User(
                prenom=donnees_utilisateur['prenom'].strip(),
                nom=donnees_utilisateur['nom'].strip(),
                email=donnees_utilisateur['email'].lower().strip(),
                telephone=donnees_utilisateur.get('telephone', '').strip() or None,
                role=role,
                client_id=client_id
            )
            
            # Générer un mot de passe temporaire si pas fourni
            mot_de_passe = donnees_utilisateur.get('mot_de_passe')
            if not mot_de_passe:
                mot_de_passe = self._generer_mot_de_passe_temporaire()
            
            nouvel_utilisateur.set_password(mot_de_passe)
            
            db.session.add(nouvel_utilisateur)
            db.session.commit()
            
            return nouvel_utilisateur, mot_de_passe if not donnees_utilisateur.get('mot_de_passe') else None
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de la création: {str(e)}"
    
    def modifier_utilisateur(self, utilisateur_id: str, nouvelles_donnees: Dict[str, Any], utilisateur_modificateur: User) -> Tuple[Optional[User], Optional[str]]:
        """Modifier un utilisateur existant"""
        try:
            utilisateur_cible = User.query.get(utilisateur_id)
            if not utilisateur_cible:
                return None, "Utilisateur non trouvé"
            
            # Vérifier les permissions de modification
            if not self._peut_modifier_utilisateur(utilisateur_modificateur, utilisateur_cible):
                return None, "Permission insuffisante pour modifier cet utilisateur"
            
            # Champs modifiables selon le rôle
            if utilisateur_modificateur.is_superadmin():
                champs_modifiables = ['prenom', 'nom', 'email', 'telephone', 'role', 'client_id', 'actif']
            elif utilisateur_modificateur.is_admin():
                champs_modifiables = ['prenom', 'nom', 'email', 'telephone', 'actif']
            else:
                champs_modifiables = ['prenom', 'nom', 'telephone']
            
            # Appliquer les modifications
            for champ in champs_modifiables:
                if champ in nouvelles_donnees:
                    valeur = nouvelles_donnees[champ]
                    
                    # Validation spéciale pour certains champs
                    if champ in ['prenom', 'nom'] and not str(valeur).strip():
                        return None, f"Le champ {champ} ne peut pas être vide"
                    
                    if champ == 'email':
                        valeur = str(valeur).lower().strip()
                        # Vérifier unicité email
                        email_existant = User.query.filter(User.email == valeur, User.id != utilisateur_id).first()
                        if email_existant:
                            return None, "Cet email est déjà utilisé"
                    
                    if champ == 'role' and utilisateur_modificateur.is_superadmin():
                        # Validation des changements de rôle
                        if valeur not in ['superadmin', 'admin', 'user']:
                            return None, "Rôle invalide"
                    
                    setattr(utilisateur_cible, champ, valeur)
            
            db.session.commit()
            return utilisateur_cible, None
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de la modification: {str(e)}"
    
    def lister_utilisateurs(self, utilisateur_demandeur: User, client_id: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Lister les utilisateurs selon les permissions"""
        try:
            query = User.query
            
            if utilisateur_demandeur.is_superadmin():
                # SUPERADMIN voit tout
                if client_id:
                    query = query.filter_by(client_id=client_id)
                    
            elif utilisateur_demandeur.is_admin():
                # ADMIN voit seulement son client
                query = query.filter_by(client_id=utilisateur_demandeur.client_id)
                
            else:
                return None, "Permission insuffisante"
            
            # 🔁 SUPPRIME le filtre actif=True pour permettre au frontend de filtrer
            utilisateurs = query.order_by(User.prenom, User.nom).all()
            
            liste_utilisateurs = [user.to_dict(include_sensitive=True) for user in utilisateurs]
            
            return liste_utilisateurs, None

        except Exception as e:
            return None, f"Erreur lors de la récupération: {str(e)}"

    
    def obtenir_utilisateur(self, utilisateur_id: str, utilisateur_demandeur: User) -> Tuple[Optional[Dict], Optional[str]]:
        """Obtenir les détails d'un utilisateur"""
        try:
            utilisateur_cible = User.query.get(utilisateur_id)
            if not utilisateur_cible:
                return None, "Utilisateur non trouvé"
            
            # Vérifier les permissions de consultation
            if not self._peut_voir_utilisateur(utilisateur_demandeur, utilisateur_cible):
                return None, "Permission insuffisante"
            
            donnees_utilisateur = utilisateur_cible.to_dict(include_sensitive=True)
            
            # Ajouter des informations sur les permissions
            donnees_utilisateur['permissions'] = {
                'is_superadmin': utilisateur_cible.is_superadmin(),
                'is_admin': utilisateur_cible.is_admin(),
                'peut_modifier': self._peut_modifier_utilisateur(utilisateur_demandeur, utilisateur_cible),
                'peut_supprimer': self._peut_supprimer_utilisateur(utilisateur_demandeur, utilisateur_cible)
            }
            
            return donnees_utilisateur, None
            
        except Exception as e:
            return None, f"Erreur lors de la récupération: {str(e)}"
    
    def desactiver_utilisateur(self, utilisateur_id: str, utilisateur_desactivateur: User) -> Tuple[bool, str]:
        """Désactiver un utilisateur"""
        try:
            utilisateur_cible = User.query.get(utilisateur_id)
            if not utilisateur_cible:
                return False, "Utilisateur non trouvé"
            
            # Vérifier les permissions
            if not self._peut_supprimer_utilisateur(utilisateur_desactivateur, utilisateur_cible):
                return False, "Permission insuffisante"
            
            # Ne pas se désactiver soi-même
            if utilisateur_cible.id == utilisateur_desactivateur.id:
                return False, "Vous ne pouvez pas vous désactiver vous-même"
            
            utilisateur_cible.actif = False
            db.session.commit()
            
            return True, f"Utilisateur {utilisateur_cible.nom_complet} désactivé"
            
        except Exception as e:
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la désactivation: {str(e)}"
    
    def reactiver_utilisateur(self, utilisateur_id: str, utilisateur_reactivateur: User) -> Tuple[bool, str]:
        """Réactiver un utilisateur désactivé"""
        try:
            utilisateur_cible = User.query.filter_by(id=utilisateur_id, actif=False).first()
            if not utilisateur_cible:
                return False, "Utilisateur non trouvé ou déjà actif"
            
            # Vérifier les permissions (même logique que désactivation)
            if not self._peut_supprimer_utilisateur(utilisateur_reactivateur, utilisateur_cible):
                return False, "Permission insuffisante"
            
            utilisateur_cible.actif = True
            db.session.commit()
            
            return True, f"Utilisateur {utilisateur_cible.nom_complet} réactivé"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la réactivation: {str(e)}"
    
    def supprimer_utilisateur(self, utilisateur_id: str, utilisateur_supprimeur: User, forcer: bool = False) -> Tuple[bool, str]:
        """Supprimer définitivement un utilisateur - ADMIN+ SEULEMENT"""
        try:
            utilisateur_cible = User.query.get(utilisateur_id)
            if not utilisateur_cible:
                return False, "Utilisateur non trouvé"
            
            # Vérifier les permissions
            if not self._peut_supprimer_utilisateur(utilisateur_supprimeur, utilisateur_cible):
                return False, "Permission insuffisante"
            
            # Ne pas se supprimer soi-même
            if utilisateur_cible.id == utilisateur_supprimeur.id:
                return False, "Vous ne pouvez pas vous supprimer vous-même"
            
            # Vérifier s'il y a des données liées importantes
            nb_acces_appareils = utilisateur_cible.acces_appareils.count() if hasattr(utilisateur_cible, 'acces_appareils') else 0
            
            # Pour les admins, vérifier s'ils ont des utilisateurs sous eux
            nb_utilisateurs_crees = 0
            if utilisateur_cible.is_admin():
                nb_utilisateurs_crees = User.query.filter_by(client_id=utilisateur_cible.client_id).count() - 1  # -1 pour exclure l'admin lui-même
            
            # Empêcher la suppression si il y a des données importantes et forcer=False
            if not forcer and (nb_acces_appareils > 0 or nb_utilisateurs_crees > 0):
                return False, (f"Impossible de supprimer: cet utilisateur a {nb_acces_appareils} accès appareils "
                             f"et {nb_utilisateurs_crees} utilisateurs dans son client. "
                             f"Utilisez forcer=True pour supprimer définitivement.")
            
            nom_utilisateur = utilisateur_cible.nom_complet
            
            if forcer:
                # Suppression forcée - SQLAlchemy gère les CASCADE
                db.session.delete(utilisateur_cible)
                message = f"Utilisateur '{nom_utilisateur}' et toutes ses données supprimés définitivement"
            else:
                # Suppression simple
                db.session.delete(utilisateur_cible)
                message = f"Utilisateur '{nom_utilisateur}' supprimé"
            
            db.session.commit()
            return True, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la suppression: {str(e)}"
    
    def reinitialiser_mot_de_passe(self, utilisateur_id: str, nouveau_mot_de_passe: str, utilisateur_reinitalisateur: User) -> Tuple[bool, str]:
        """Réinitialiser le mot de passe d'un utilisateur"""
        try:
            utilisateur_cible = User.query.get(utilisateur_id)
            if not utilisateur_cible:
                return False, "Utilisateur non trouvé"
            
            # Vérifier les permissions
            if not self._peut_modifier_utilisateur(utilisateur_reinitalisateur, utilisateur_cible):
                return False, "Permission insuffisante"
            
            # Valider le mot de passe
            if not self._valider_mot_de_passe(nouveau_mot_de_passe):
                return False, "Le mot de passe doit contenir au moins 8 caractères"
            
            utilisateur_cible.set_password(nouveau_mot_de_passe)
            db.session.commit()
            
            return True, f"Mot de passe réinitialisé pour {utilisateur_cible.nom_complet}"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la réinitialisation: {str(e)}"
    
    def generer_mot_de_passe_temporaire_pour(self, utilisateur_id: str, utilisateur_generateur: User) -> Tuple[Optional[str], Optional[str]]:
        """Générer un nouveau mot de passe temporaire pour un utilisateur"""
        try:
            nouveau_mot_de_passe = self._generer_mot_de_passe_temporaire()
            succes, message = self.reinitialiser_mot_de_passe(utilisateur_id, nouveau_mot_de_passe, utilisateur_generateur)
            
            if succes:
                return nouveau_mot_de_passe, None
            else:
                return None, message
                
        except Exception as e:
            return None, f"Erreur lors de la génération: {str(e)}"
    
    # =================== STATISTIQUES ===================
    
    def obtenir_statistiques_utilisateurs(self, utilisateur_demandeur: User) -> Tuple[Optional[Dict], Optional[str]]:
        """Obtenir des statistiques sur les utilisateurs"""
        try:
            if not utilisateur_demandeur.is_admin():
                return None, "Permission insuffisante"
            
            stats = {}
            
            if utilisateur_demandeur.is_superadmin():
                # Stats globales pour superadmin
                stats = {
                    'total_clients': Client.query.filter_by(actif=True).count(),
                    'total_utilisateurs': User.query.filter_by(actif=True).count(),
                    'total_superadmins': User.query.filter_by(role='superadmin', actif=True).count(),
                    'total_admins': User.query.filter_by(role='admin', actif=True).count(),
                    'total_users': User.query.filter_by(role='user', actif=True).count(),
                    'utilisateurs_inactifs': User.query.filter_by(actif=False).count(),
                    'admins_en_attente': User.query.filter_by(role='admin', actif=False).count()
                }
            else:
                # Stats pour le client de l'admin
                stats = {
                    'utilisateurs_client': User.query.filter_by(client_id=utilisateur_demandeur.client_id, actif=True).count(),
                    'admins_client': User.query.filter_by(client_id=utilisateur_demandeur.client_id, role='admin', actif=True).count(),
                    'users_client': User.query.filter_by(client_id=utilisateur_demandeur.client_id, role='user', actif=True).count(),
                    'utilisateurs_inactifs_client': User.query.filter_by(client_id=utilisateur_demandeur.client_id, actif=False).count()
                }
            
            return stats, None
            
        except Exception as e:
            return None, f"Erreur lors du calcul des statistiques: {str(e)}"
    
    # =================== MÉTHODES PRIVÉES DE VALIDATION ===================
    
    def _valider_donnees_utilisateur(self, donnees: Dict[str, Any]) -> bool:
        """Valider les données utilisateur de base"""
        champs_requis = ['prenom', 'nom', 'email']
        
        for champ in champs_requis:
            if not donnees.get(champ) or not str(donnees[champ]).strip():
                return False
        
        # Valider l'email - CORRECTION ICI
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, donnees['email']):
            return False
    
        return True
    
    def _valider_mot_de_passe(self, mot_de_passe: str) -> bool:
        """Valider un mot de passe"""
        return mot_de_passe and len(mot_de_passe) >= 8
    
    def _generer_mot_de_passe_temporaire(self, longueur: int = 12) -> str:
        """Générer un mot de passe temporaire sécurisé"""
        caracteres = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(secrets.choice(caracteres) for _ in range(longueur))
    
    def _peut_voir_utilisateur(self, utilisateur_demandeur: User, utilisateur_cible: User) -> bool:
        """Vérifier si un utilisateur peut en voir un autre"""
        # Soi-même
        if utilisateur_demandeur.id == utilisateur_cible.id:
            return True
        
        # Superadmin voit tout
        if utilisateur_demandeur.is_superadmin():
            return True
        
        # Admin voit son client
        if utilisateur_demandeur.is_admin():
            return utilisateur_cible.client_id == utilisateur_demandeur.client_id
        
        return False
    
    def _peut_modifier_utilisateur(self, utilisateur_modificateur: User, utilisateur_cible: User) -> bool:
        """Vérifier si un utilisateur peut en modifier un autre"""
        # 1️⃣ Tout le monde peut modifier son propre profil
        if utilisateur_modificateur.id == utilisateur_cible.id:
            return True
        
        # 2️⃣ Superadmin peut tout modifier
        if utilisateur_modificateur.is_superadmin():
            return True
        
        # 3️⃣ Admin peut modifier les users de son client (pas les autres admins/superadmins)
        if utilisateur_modificateur.is_admin():
            return (utilisateur_cible.client_id == utilisateur_modificateur.client_id and 
                   utilisateur_cible.role == 'user')
        
        return False
    
    def _peut_supprimer_utilisateur(self, utilisateur_supprimeur: User, utilisateur_cible: User) -> bool:
        """Vérifier si un utilisateur peut en supprimer un autre"""
        # Même logique que modification pour le moment
        return self._peut_modifier_utilisateur(utilisateur_supprimeur, utilisateur_cible)
    
    # =================== MÉTHODES UTILITAIRES POUR DEBUG ===================
    
    def nettoyer_tokens_expires(self) -> Dict[str, int]:
        """Nettoyer les tokens expirés (méthode utilitaire)"""
        try:
            from app.utils.token_manager import ActivationTokenManager
            
            tokens_supprimes = ActivationTokenManager.cleanup_expired()
            stats = ActivationTokenManager.get_stats()
            
            return {
                'tokens_supprimes': tokens_supprimes,
                'stats_actuelles': stats
            }
        except Exception as e:
            return {'erreur': str(e)}
    
    def obtenir_stats_tokens(self) -> Dict[str, Any]:
        """Obtenir les statistiques des tokens (debug)"""
        try:
            from app.utils.token_manager import ActivationTokenManager
            return ActivationTokenManager.get_stats()
        except Exception as e:
            return {'erreur': str(e)}
    