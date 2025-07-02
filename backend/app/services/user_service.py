from app import db, get_redis  # ✅ NOUVEAU : Import get_redis
from app.models.user import User
from app.models.client import Client
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from app.services.mail_service import MailService
import secrets
import string
import json

class UserService:
    def __init__(self):
        # ✅ NOUVEAU : Redis d'abord, sinon ActivationTokenManager comme fallback
        self.redis = get_redis()
    
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
                actif=False  # Créer inactif
            )
            
            # Créer avec un mot de passe temporaire (sera remplacé lors de l'activation)
            admin_client.set_password("temp_password_will_be_replaced")
            
            db.session.add(admin_client)
            db.session.flush()  # Pour obtenir l'ID de l'admin
            
            # ✅ NOUVEAU : Générer token d'activation avec Redis
            print(f"🔍 Génération token pour admin:")
            print(f"   - ID: {admin_client.id}")
            print(f"   - Email: {email_admin}")
            print(f"   - Prénom: {prenom_admin}")
            print(f"   - Nom: {nom_admin}")

            # Générer token d'activation
            token = self._generate_activation_token(admin_client.id, email_admin, 'admin', 86400)  # 24h
            print(f"🎫 Token généré: {token}")

            # Vérifier que le token est bien enregistré
            validation = self._validate_activation_token(token)
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
            
            # 🎉 Préparer le résultat
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
            
            # ✅ NOUVEAU : Invalider tous les tokens d'activation de ce client
            self._invalidate_client_tokens(client_id)
            
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
            
            # ✅ NOUVEAU : Supprimer tous les tokens d'activation de ce client
            self._invalidate_client_tokens(client_id)
            
            if forcer:
                # Suppression forcée avec CASCADE
                db.session.delete(client)
                message = (f"Client '{nom_client}' et TOUTES ses données supprimés définitivement "
                          f"({nb_utilisateurs} utilisateurs, {nb_sites} sites, {nb_appareils} appareils)")
            else:
                # Suppression simple (seulement client + utilisateurs)
                User.query.filter_by(client_id=client_id).delete()
                db.session.delete(client)
                message = f"Client '{nom_client}' et ses {nb_utilisateurs} utilisateurs supprimés"
            
            db.session.commit()
            return True, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la suppression: {str(e)}"
    
    def reactiver_client(self, client_id: str, utilisateur_reactivateur: User) -> Tuple[bool, str]:
        """Réactiver un client désactivé ET ses utilisateurs"""
        try:
            if not utilisateur_reactivateur.is_superadmin():
                return False, "Seul le superadmin peut réactiver des clients"
            
            client = Client.query.filter_by(id=client_id, actif=False).first()
            if not client:
                return False, "Client non trouvé ou déjà actif"
            
            print(f"🔄 Réactivation client {client.nom_entreprise}...")
            
            # ✅ 1. RÉACTIVER LE CLIENT
            client.actif = True
            
            # ✅ 2. RÉACTIVER TOUS LES UTILISATEURS DU CLIENT
            utilisateurs_inactifs = User.query.filter_by(
                client_id=client_id, 
                actif=False
            ).all()
            
            utilisateurs_reactives = []
            for utilisateur in utilisateurs_inactifs:
                # ✅ Sécurité : Ne pas réactiver d'autres superadmins
                if not utilisateur.is_superadmin():
                    utilisateur.actif = True
                    utilisateurs_reactives.append(utilisateur.nom_complet)
                    print(f"👤 Utilisateur {utilisateur.nom_complet} réactivé")
                else:
                    print(f"⚠️ Superadmin {utilisateur.nom_complet} ignoré (sécurité)")
            
            # ✅ 3. NETTOYER LES CACHES LIÉS (optionnel)
            self._cleanup_client_activation_caches(client_id)
            
            db.session.commit()
            
            # Message de confirmation détaillé
            if utilisateurs_reactives:
                message = (
                    f"Client {client.nom_entreprise} réactivé avec succès. "
                    f"{len(utilisateurs_reactives)} utilisateurs réactivés: "
                    f"{', '.join(utilisateurs_reactives[:3])}"
                    f"{'...' if len(utilisateurs_reactives) > 3 else ''}"
                )
            else:
                message = f"Client {client.nom_entreprise} réactivé (aucun utilisateur inactif trouvé)"
            
            print(f"✅ {message}")
            return True, message
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur réactivation client: {e}")
            return False, f"Erreur lors de la réactivation: {str(e)}"
    
    # =================== NOUVELLES MÉTHODES POUR L'ACTIVATION AVEC REDIS ===================
    
    def activer_admin(self, token: str, mot_de_passe: str, confirmation_mot_de_passe: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Activer un compte admin avec définition du mot de passe"""
        try:
            print(f"🔍 === DEBUG ACTIVATION ===")
            print(f"🎫 Token reçu: {token}")
            print(f"🔒 Mot de passe fourni: {'*' * len(mot_de_passe)}")
            print(f"🔒 Confirmation fournie: {'*' * len(confirmation_mot_de_passe)}")
            
            # ✅ NOUVEAU : Validation du token avec Redis
            validation = self._validate_activation_token(token)
            
            print(f"🎫 === RÉSULTAT VALIDATION ===")
            print(f"Type: {type(validation)}")
            print(f"Contenu: {validation}")
            print(f"=== FIN VALIDATION ===")
            
            if not validation or not validation.get('valid'):
                return None, validation.get('message', 'Token invalide ou expiré')
            
            user_id = validation.get('user_id')
            if not user_id:
                return None, "ID utilisateur manquant dans la validation"
            
            print(f"👤 Recherche utilisateur avec ID: {user_id}")
            
            # Récupérer l'utilisateur
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
            
            # ✅ NOUVEAU : Invalider le token dans Redis
            self._use_activation_token(token)
            
            db.session.commit()
            
            print(f"✅ Compte activé avec succès pour {utilisateur.email}")
            
            # Envoyer email de confirmation
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
            return None, f"Erreur lors de l'activation: {str(e)}"
    
    def valider_token_activation(self, token: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Valider un token d'activation sans le consommer (pour vérification côté frontend)"""
        try:
            # ✅ NOUVEAU : Validation avec Redis
            token_data = self._validate_activation_token(token)
            
            if not token_data or not token_data.get('valid'):
                return None, token_data.get('message', 'Token invalide ou expiré')
            
            user_id = token_data.get('user_id')
            if not user_id:
                return None, "Données utilisateur manquantes"
            
            # Récupérer les infos de l'admin
            admin = User.query.get(user_id)
            if not admin:
                return None, "Utilisateur non trouvé"
            
            if admin.actif:
                return None, "Ce compte est déjà activé"
            
            # Calculer le temps restant
            expires_at = token_data.get('expires_at')
            if expires_at:
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                temps_restant = int((expires_at - datetime.utcnow()).total_seconds())
            else:
                temps_restant = 0
            
            resultat = {
                'admin_info': {
                    'prenom': admin.prenom,
                    'nom': admin.nom,
                    'email': admin.email,
                    'entreprise': admin.client.nom_entreprise if admin.client else None
                },
                'temps_restant_secondes': max(0, temps_restant),
                'temps_restant_heures': round(max(0, temps_restant) / 3600, 1)
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
            
            # ✅ NOUVEAU : Révoquer les anciens tokens de cet utilisateur
            self._revoke_user_activation_tokens(admin.id)
            
            # Générer nouveau token
            token = self._generate_activation_token(admin.id, admin.email, 'admin', 86400)  # 24h
            
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
        """Lister les administrateurs en attente d'activation - SELON LES PERMISSIONS"""
        try:
            if utilisateur_demandeur.is_superadmin():
                # 🔧 SUPERADMIN : Voit TOUS les admins en attente de TOUS les clients
                admins_inactifs = User.query.filter_by(
                    role='admin',
                    actif=False
                ).order_by(User.date_creation.desc()).all()
                
                scope_message = "tous les clients"
                
            elif utilisateur_demandeur.is_admin():
                # 🏢 ADMIN CLIENT : Voit SEULEMENT les admins de SON client en attente
                admins_inactifs = User.query.filter_by(
                    role='admin',
                    actif=False,
                    client_id=utilisateur_demandeur.client_id  # ✅ RESTRICTION : Seulement son client
                ).order_by(User.date_creation.desc()).all()
                
                scope_message = f"client '{utilisateur_demandeur.client.nom_entreprise}'" if utilisateur_demandeur.client else "votre client"
                
            else:
                return None, "Permission insuffisante pour voir les admins en attente"
            
            liste_admins = []
            for admin in admins_inactifs:
                admin_dict = admin.to_dict(include_sensitive=True)
                admin_dict['entreprise'] = admin.client.nom_entreprise if admin.client else None
                admin_dict['jours_depuis_creation'] = (datetime.utcnow() - admin.date_creation).days
                
                # ✅ Ajouter info token d'activation
                admin_dict['has_activation_token'] = self._user_has_activation_token(admin.id)
                admin_dict['nb_tokens_actifs'] = self._count_user_activation_tokens(admin.id)
                
                # ✅ Permissions de suppression
                admin_dict['peut_etre_supprime'] = self._peut_supprimer_utilisateur_en_attente(utilisateur_demandeur, admin)
                
                # ✅ Indiquer si c'est dans le scope
                if utilisateur_demandeur.is_superadmin():
                    admin_dict['dans_mon_scope'] = True
                elif utilisateur_demandeur.is_admin():
                    admin_dict['dans_mon_scope'] = (admin.client_id == utilisateur_demandeur.client_id)
                
                liste_admins.append(admin_dict)
            
            # ✅ Métadonnées enrichies
            metadata = {
                'scope': scope_message,
                'total_admins': len(liste_admins),
                'permissions': {
                    'peut_voir_tous_clients': utilisateur_demandeur.is_superadmin(),
                    'client_restriction': utilisateur_demandeur.client_id if utilisateur_demandeur.is_admin() else None
                }
            }
            
            return {
                'admins': liste_admins,
                'metadata': metadata
            }, None
            
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
    
    def creer_utilisateur(self, donnees_utilisateur: Dict[str, Any], utilisateur_createur: User) -> Tuple[Optional[Dict], Optional[str]]:
        """Créer un nouvel utilisateur avec support site_id"""
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
            site_id = donnees_utilisateur.get('site_id')  # ✅ NOUVEAU
            
            # RÈGLES DE PERMISSIONS (inchangées)
            if utilisateur_createur.is_superadmin():
                if role == 'superadmin':
                    client_id = None
                elif role in ['admin', 'user'] and not client_id:
                    return None, "client_id requis pour les admin/user"
            
            elif utilisateur_createur.is_admin():
                if role != 'user':
                    return None, "Un admin ne peut créer que des utilisateurs 'user'"
                client_id = utilisateur_createur.client_id
            
            else:
                return None, "Permission insuffisante pour créer des utilisateurs"
            
            # ✅ NOUVEAU : Validation site_id
            site = None
            if site_id:
                from app.models.site import Site
                site = Site.query.get(site_id)
                if not site or not site.actif:
                    return None, "Site non trouvé ou inactif"
                
                # Vérifier que le site appartient au bon client
                if client_id and site.client_id != client_id:
                    return None, "Le site ne correspond pas au client"
            
            # Vérifier que le client existe si spécifié
            client = None
            if client_id:
                client = Client.query.get(client_id)
                if not client or not client.actif:
                    return None, "Client non trouvé ou inactif"
            
            # 👤 CRÉER L'UTILISATEUR avec site_id
            nouvel_utilisateur = User(
                prenom=donnees_utilisateur['prenom'].strip(),
                nom=donnees_utilisateur['nom'].strip(),
                email=donnees_utilisateur['email'].lower().strip(),
                telephone=donnees_utilisateur.get('telephone', '').strip() or None,
                role=role,
                client_id=client_id,
                site_id=site_id,  # ✅ NOUVEAU : Assigner le site
                actif=False
            )
            
            # Mot de passe temporaire
            nouvel_utilisateur.set_password("temp_password_will_be_replaced")
            
            db.session.add(nouvel_utilisateur)
            db.session.flush()
            
            # Génération token et envoi email (inchangé)
            token = self._generate_activation_token(nouvel_utilisateur.id, nouvel_utilisateur.email, role, 86400)
            
            # ✅ ENRICHIR l'email avec info site
            if role == 'admin':
                email_result = MailService.send_admin_activation_email(
                    user_email=nouvel_utilisateur.email,
                    prenom=nouvel_utilisateur.prenom,
                    nom=nouvel_utilisateur.nom,
                    client_name=client.nom_entreprise if client else "Système",
                    activation_token=token,
                    expires_hours=24
                )
            elif role == 'superadmin':
                email_result = MailService.send_superadmin_activation_email(
                    user_email=nouvel_utilisateur.email,
                    prenom=nouvel_utilisateur.prenom,
                    nom=nouvel_utilisateur.nom,
                    activation_token=token,
                    expires_hours=24
                )
            else:
                # ✅ User simple - ajouter info site dans l'email
                email_result = MailService.send_user_activation_email(
                    user_email=nouvel_utilisateur.email,
                    prenom=nouvel_utilisateur.prenom,
                    nom=nouvel_utilisateur.nom,
                    client_name=client.nom_entreprise if client else "Système",
                    site_name=site.nom_site if site else None,  # ✅ NOUVEAU
                    activation_token=token,
                    expires_hours=24
                )
            
            db.session.commit()
            
            # ✅ ENRICHIR le résultat avec info site
            resultat = {
                'utilisateur': nouvel_utilisateur.to_dict(),
                'utilisateur_objet': nouvel_utilisateur,
                'token_activation': token,
                'email_result': email_result,
                'identifiants_connexion': {
                    'email': nouvel_utilisateur.email,
                    'status': 'En attente d\'activation'
                },
                'message_instructions': f"Un email d'activation a été envoyé à {nouvel_utilisateur.email}",
                'client_info': client.to_dict() if client else None,
                'site_info': site.to_dict() if site else None  # ✅ NOUVEAU
            }
            
            return resultat, None
            
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
            
            # ✅ NOUVEAU : Ajouter info token d'activation si inactif
            if not utilisateur_cible.actif:
                donnees_utilisateur['has_activation_token'] = self._user_has_activation_token(utilisateur_cible.id)
            
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
            
            # ✅ NOUVEAU : Invalider tous les tokens d'activation de cet utilisateur
            self._revoke_user_activation_tokens(utilisateur_cible.id)
            
            db.session.commit()
            
            return True, f"Utilisateur {utilisateur_cible.nom_complet} désactivé"
            
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
            
            # ✅ NOUVEAU : Invalider tous les tokens d'activation de cet utilisateur
            self._revoke_user_activation_tokens(utilisateur_cible.id)
            
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
                    'admins_en_attente': User.query.filter_by(role='admin', actif=False).count(),
                    # ✅ NOUVEAU : Stats tokens d'activation
                    'tokens_activation_stats': self._get_activation_tokens_stats()
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
    
    # =================== MÉTHODES REDIS POUR TOKENS D'ACTIVATION ===================
    
    def _generate_activation_token(self, user_id: str, email: str, role: str, expires_in_seconds: int = 86400) -> str:
        """Générer un token d'activation et le stocker dans Redis"""
        try:
            # Générer un token unique
            token = secrets.token_urlsafe(32)
            
            # Calculer l'expiration
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
            
            # Données du token
            token_data = {
                'user_id': user_id,
                'email': email,
                'role': role,
                'type': 'activation',
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': expires_at.isoformat(),
                'used': False
            }
            
            # Stocker dans Redis avec TTL
            redis_key = f"activation_token:{token}"
            
            if self.redis:
                self.redis.setex(redis_key, expires_in_seconds, json.dumps(token_data))
                print(f"✅ Token stocké dans Redis: {redis_key}")
            else:
                # Fallback vers ActivationTokenManager si Redis indisponible
                print(f"⚠️ Redis indisponible, utilisation du fallback ActivationTokenManager")
                try:
                    from app.utils.token_manager import ActivationTokenManager
                    return ActivationTokenManager.generate_token(user_id, email, expires_in_seconds)
                except ImportError:
                    raise Exception("Redis indisponible et ActivationTokenManager non trouvé")
            
            return token
            
        except Exception as e:
            print(f"❌ Erreur génération token: {e}")
            raise
    
    def _validate_activation_token(self, token: str) -> Dict[str, Any]:
        """Valider un token d'activation depuis Redis"""
        try:
            redis_key = f"activation_token:{token}"
            
            if self.redis:
                # Récupérer depuis Redis
                token_data_str = self.redis.get(redis_key)
                
                if not token_data_str:
                    return {'valid': False, 'message': 'Token non trouvé ou expiré'}
                
                # Décoder les données
                token_data = json.loads(token_data_str)
                
                # Vérifier si déjà utilisé
                if token_data.get('used', False):
                    return {'valid': False, 'message': 'Token déjà utilisé'}
                
                # Vérifier l'expiration (double vérification)
                expires_at = datetime.fromisoformat(token_data['expires_at'])
                if datetime.utcnow() > expires_at:
                    # Supprimer le token expiré
                    self.redis.delete(redis_key)
                    return {'valid': False, 'message': 'Token expiré'}
                
                # Token valide
                return {
                    'valid': True,
                    'user_id': token_data['user_id'],
                    'email': token_data['email'],
                    'role': token_data['role'],
                    'expires_at': expires_at,
                    'message': 'Token valide'
                }
            
            else:
                # Fallback vers ActivationTokenManager
                print(f"⚠️ Redis indisponible, utilisation du fallback pour validation")
                try:
                    from app.utils.token_manager import ActivationTokenManager
                    return ActivationTokenManager.validate_token(token)
                except ImportError:
                    return {'valid': False, 'message': 'Service de validation indisponible'}
            
        except Exception as e:
            print(f"❌ Erreur validation token: {e}")
            return {'valid': False, 'message': f'Erreur de validation: {str(e)}'}
    
    def _use_activation_token(self, token: str) -> bool:
        """Marquer un token comme utilisé (ou le supprimer)"""
        try:
            redis_key = f"activation_token:{token}"
            
            if self.redis:
                # Supprimer le token de Redis (plus simple que de le marquer comme utilisé)
                result = self.redis.delete(redis_key)
                print(f"✅ Token supprimé de Redis: {redis_key} (résultat: {result})")
                return result > 0
            else:
                # Fallback
                try:
                    from app.utils.token_manager import ActivationTokenManager
                    ActivationTokenManager.use_token(token)
                    return True
                except ImportError:
                    return False
            
        except Exception as e:
            print(f"❌ Erreur utilisation token: {e}")
            return False
    
    def _revoke_user_activation_tokens(self, user_id: str) -> int:
        """Révoquer tous les tokens d'activation d'un utilisateur"""
        try:
            if self.redis:
                # Chercher tous les tokens de ce user_id
                pattern = "activation_token:*"
                keys = self.redis.keys(pattern)
                
                tokens_supprimés = 0
                for key in keys:
                    try:
                        token_data_str = self.redis.get(key)
                        if token_data_str:
                            token_data = json.loads(token_data_str)
                            if token_data.get('user_id') == user_id:
                                self.redis.delete(key)
                                tokens_supprimés += 1
                    except:
                        continue
                
                print(f"✅ {tokens_supprimés} tokens d'activation supprimés pour user {user_id}")
                return tokens_supprimés
            else:
                # Fallback
                try:
                    from app.utils.token_manager import ActivationTokenManager
                    ActivationTokenManager.revoke_user_tokens(user_id)
                    return 1  # On ne peut pas savoir combien exactement
                except ImportError:
                    return 0
            
        except Exception as e:
            print(f"❌ Erreur révocation tokens: {e}")
            return 0
    
    def _invalidate_client_tokens(self, client_id: str) -> int:
        """Invalider tous les tokens d'activation d'un client"""
        try:
            if self.redis:
                # Chercher tous les utilisateurs de ce client
                users = User.query.filter_by(client_id=client_id).all()
                total_supprimés = 0
                
                for user in users:
                    total_supprimés += self._revoke_user_activation_tokens(user.id)
                
                print(f"✅ {total_supprimés} tokens d'activation supprimés pour client {client_id}")
                return total_supprimés
            else:
                return 0
            
        except Exception as e:
            print(f"❌ Erreur invalidation tokens client: {e}")
            return 0
    
    def _user_has_activation_token(self, user_id: str) -> bool:
        """Vérifier si un utilisateur a un token d'activation actif"""
        try:
            if self.redis:
                pattern = "activation_token:*"
                keys = self.redis.keys(pattern)
                
                for key in keys:
                    try:
                        token_data_str = self.redis.get(key)
                        if token_data_str:
                            token_data = json.loads(token_data_str)
                            if token_data.get('user_id') == user_id and not token_data.get('used', False):
                                # Vérifier que le token n'est pas expiré
                                expires_at = datetime.fromisoformat(token_data['expires_at'])
                                if datetime.utcnow() <= expires_at:
                                    return True
                    except:
                        continue
                
                return False
            else:
                return False  # Sans Redis, on ne peut pas vérifier facilement
            
        except Exception as e:
            print(f"❌ Erreur vérification token utilisateur: {e}")
            return False
    
    def _get_activation_tokens_stats(self) -> Dict[str, int]:
        """Obtenir les statistiques des tokens d'activation"""
        try:
            if self.redis:
                pattern = "activation_token:*"
                keys = self.redis.keys(pattern)
                
                stats = {
                    'total_tokens': len(keys),
                    'tokens_admin': 0,
                    'tokens_user': 0,
                    'tokens_superadmin': 0,
                    'tokens_expires': 0
                }
                
                now = datetime.utcnow()
                
                for key in keys:
                    try:
                        token_data_str = self.redis.get(key)
                        if token_data_str:
                            token_data = json.loads(token_data_str)
                            
                            # Compter par rôle
                            role = token_data.get('role', 'user')
                            if role == 'admin':
                                stats['tokens_admin'] += 1
                            elif role == 'superadmin':
                                stats['tokens_superadmin'] += 1
                            else:
                                stats['tokens_user'] += 1
                            
                            # Compter les expirés
                            expires_at = datetime.fromisoformat(token_data['expires_at'])
                            if now > expires_at:
                                stats['tokens_expires'] += 1
                    except:
                        continue
                
                return stats
            else:
                return {'total_tokens': 0, 'error': 'Redis indisponible'}
            
        except Exception as e:
            return {'error': str(e)}
    
    def nettoyer_tokens_expires(self) -> Dict[str, int]:
        """Nettoyer les tokens expirés"""
        try:
            if self.redis:
                pattern = "activation_token:*"
                keys = self.redis.keys(pattern)
                
                tokens_supprimes = 0
                now = datetime.utcnow()
                
                for key in keys:
                    try:
                        token_data_str = self.redis.get(key)
                        if token_data_str:
                            token_data = json.loads(token_data_str)
                            expires_at = datetime.fromisoformat(token_data['expires_at'])
                            
                            if now > expires_at:
                                self.redis.delete(key)
                                tokens_supprimes += 1
                    except:
                        # Token corrompu, le supprimer aussi
                        self.redis.delete(key)
                        tokens_supprimes += 1
                
                stats_apres = self._get_activation_tokens_stats()
                
                return {
                    'tokens_supprimes': tokens_supprimes,
                    'stats_actuelles': stats_apres
                }
            else:
                # Fallback
                try:
                    from app.utils.token_manager import ActivationTokenManager
                    tokens_supprimes = ActivationTokenManager.cleanup_expired()
                    stats = ActivationTokenManager.get_stats()
                    return {
                        'tokens_supprimes': tokens_supprimes,
                        'stats_actuelles': stats
                    }
                except ImportError:
                    return {'error': 'Services indisponibles'}
        
        except Exception as e:
            return {'error': str(e)}
    
    def obtenir_stats_tokens(self) -> Dict[str, Any]:
        """Obtenir les statistiques des tokens (debug)"""
        try:
            if self.redis:
                return self._get_activation_tokens_stats()
            else:
                try:
                    from app.utils.token_manager import ActivationTokenManager
                    return ActivationTokenManager.get_stats()
                except ImportError:
                    return {'error': 'Services indisponibles'}
        except Exception as e:
            return {'error': str(e)}
    
    # =================== MÉTHODES PRIVÉES DE VALIDATION ===================
    
    def _valider_donnees_utilisateur(self, donnees: Dict[str, Any]) -> bool:
        """Valider les données utilisateur de base"""
        champs_requis = ['prenom', 'nom', 'email']
        
        for champ in champs_requis:
            if not donnees.get(champ) or not str(donnees[champ]).strip():
                return False
        
        # Valider l'email
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
        # Tout le monde peut modifier son propre profil
        if utilisateur_modificateur.id == utilisateur_cible.id:
            return True
        
        # Superadmin peut tout modifier
        if utilisateur_modificateur.is_superadmin():
            return True
        
        # Admin peut modifier les users de son client (pas les autres admins/superadmins)
        if utilisateur_modificateur.is_admin():
            return (utilisateur_cible.client_id == utilisateur_modificateur.client_id and 
                   utilisateur_cible.role == 'user')
        
        return False
    
    def _peut_supprimer_utilisateur(self, utilisateur_supprimeur: User, utilisateur_cible: User) -> bool:
        """Vérifier si un utilisateur peut en supprimer un autre"""
        # Même logique que modification pour le moment
        return self._peut_modifier_utilisateur(utilisateur_supprimeur, utilisateur_cible)

    # =================== MÉTHODES UTILITAIRES ET DEBUG ===================
    
    def debug_redis_connection(self) -> Dict[str, Any]:
        """Tester la connexion Redis (utilitaire de debug)"""
        try:
            if self.redis:
                # Test simple ping
                result = self.redis.ping()
                
                # Informations sur Redis
                info = {
                    'redis_available': True,
                    'ping_successful': result,
                    'redis_info': {
                        'version': self.redis.info().get('redis_version', 'unknown'),
                        'connected_clients': self.redis.info().get('connected_clients', 0),
                        'used_memory_human': self.redis.info().get('used_memory_human', 'unknown')
                    }
                }
                
                # Test d'écriture/lecture
                test_key = "test_key_activation_service"
                test_value = "test_value_123"
                
                self.redis.setex(test_key, 60, test_value)  # 1 minute
                retrieved = self.redis.get(test_key)
                self.redis.delete(test_key)  # Nettoyer
                
                info['write_read_test'] = {
                    'success': retrieved == test_value,
                    'written': test_value,
                    'retrieved': retrieved
                }
                
                return info
            else:
                return {
                    'redis_available': False,
                    'message': 'Redis connection not initialized'
                }
                
        except Exception as e:
            return {
                'redis_available': False,
                'error': str(e),
                'fallback_available': self._test_fallback_available()
            }
    
    def _test_fallback_available(self) -> bool:
        """Tester si le fallback ActivationTokenManager est disponible"""
        try:
            from app.utils.token_manager import ActivationTokenManager
            return True
        except ImportError:
            return False
    
    def get_all_activation_tokens_debug(self) -> Dict[str, Any]:
        """Récupérer tous les tokens d'activation pour debug (SUPERADMIN ONLY)"""
        try:
            if self.redis:
                pattern = "activation_token:*"
                keys = self.redis.keys(pattern)
                
                tokens_info = []
                for key in keys:
                    try:
                        token_data_str = self.redis.get(key)
                        if token_data_str:
                            token_data = json.loads(token_data_str)
                            
                            # Masquer des infos sensibles
                            token_info = {
                                'token_key': key.decode() if isinstance(key, bytes) else key,
                                'user_id': token_data.get('user_id'),
                                'email': token_data.get('email', '').replace('@', '@***'),  # Masquer partiellement
                                'role': token_data.get('role'),
                                'type': token_data.get('type'),
                                'created_at': token_data.get('created_at'),
                                'expires_at': token_data.get('expires_at'),
                                'used': token_data.get('used', False),
                                'expired': datetime.utcnow() > datetime.fromisoformat(token_data['expires_at'])
                            }
                            tokens_info.append(token_info)
                    except Exception as e:
                        tokens_info.append({
                            'token_key': key.decode() if isinstance(key, bytes) else key,
                            'error': f'Erreur parsing: {str(e)}'
                        })
                
                return {
                    'total_tokens': len(keys),
                    'tokens': tokens_info,
                    'stats': self._get_activation_tokens_stats()
                }
            else:
                return {
                    'error': 'Redis indisponible',
                    'fallback_stats': self.obtenir_stats_tokens()
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    def force_cleanup_all_tokens(self) -> Dict[str, int]:
        """Forcer le nettoyage de TOUS les tokens d'activation (URGENCE SEULEMENT)"""
        try:
            if self.redis:
                pattern = "activation_token:*"
                keys = self.redis.keys(pattern)
                
                tokens_supprimes = 0
                for key in keys:
                    self.redis.delete(key)
                    tokens_supprimes += 1
                
                return {
                    'tokens_supprimes': tokens_supprimes,
                    'message': f'TOUS les {tokens_supprimes} tokens d\'activation ont été supprimés'
                }
            else:
                return {'error': 'Redis indisponible'}
                
        except Exception as e:
            return {'error': str(e)}
    
    # =================== MÉTHODES SPÉCIFIQUES POUR DIFFÉRENTS TYPES D'ACTIVATION ===================
    
    def creer_et_envoyer_activation_utilisateur_simple(self, utilisateur_id: str, utilisateur_createur: User) -> Tuple[Optional[str], Optional[str]]:
        """Créer et envoyer un token d'activation pour un utilisateur existant (réactivation)"""
        try:
            if not utilisateur_createur.is_admin():
                return None, "Permission insuffisante"
            
            utilisateur = User.query.get(utilisateur_id)
            if not utilisateur:
                return None, "Utilisateur non trouvé"
            
            if utilisateur.actif:
                return None, "Cet utilisateur est déjà actif"
            
            # Vérifier les permissions (même client ou superadmin)
            if not utilisateur_createur.is_superadmin():
                if utilisateur.client_id != utilisateur_createur.client_id:
                    return None, "Vous ne pouvez créer des tokens que pour votre client"
            
            # Révoquer les anciens tokens
            self._revoke_user_activation_tokens(utilisateur.id)
            
            # Générer nouveau token
            token = self._generate_activation_token(utilisateur.id, utilisateur.email, utilisateur.role, 86400)
            
            # Envoyer l'email selon le rôle
            if utilisateur.role == 'admin':
                email_result = MailService.send_admin_activation_email(
                    user_email=utilisateur.email,
                    prenom=utilisateur.prenom,
                    nom=utilisateur.nom,
                    client_name=utilisateur.client.nom_entreprise if utilisateur.client else "Système",
                    activation_token=token,
                    expires_hours=24
                )
            elif utilisateur.role == 'superadmin':
                email_result = MailService.send_superadmin_activation_email(
                    user_email=utilisateur.email,
                    prenom=utilisateur.prenom,
                    nom=utilisateur.nom,
                    activation_token=token,
                    expires_hours=24
                )
            else:
                email_result = MailService.send_user_activation_email(
                    user_email=utilisateur.email,
                    prenom=utilisateur.prenom,
                    nom=utilisateur.nom,
                    client_name=utilisateur.client.nom_entreprise if utilisateur.client else "Système",
                    activation_token=token,
                    expires_hours=24
                )
            
            if email_result['success']:
                return token, None
            else:
                return token, f"Token généré mais email non envoyé: {email_result['message']}"
                
        except Exception as e:
            return None, f"Erreur lors de la création: {str(e)}"
    
    def activer_utilisateur_quelconque(self, token: str, mot_de_passe: str, confirmation_mot_de_passe: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Activer n'importe quel type d'utilisateur (admin, user, superadmin) avec le même endpoint"""
        try:
            print(f"🔍 === ACTIVATION UTILISATEUR GÉNÉRIQUE ===")
            print(f"🎫 Token reçu: {token[:10]}...")
            
            # Validation du token
            validation = self._validate_activation_token(token)
            
            if not validation or not validation.get('valid'):
                return None, validation.get('message', 'Token invalide ou expiré')
            
            user_id = validation.get('user_id')
            user_role = validation.get('role', 'user')
            
            if not user_id:
                return None, "ID utilisateur manquant dans la validation"
            
            print(f"👤 Activation utilisateur: {user_id} (rôle: {user_role})")
            
            # Récupérer l'utilisateur
            utilisateur = User.query.get(user_id)
            if not utilisateur:
                return None, "Utilisateur non trouvé"
            
            # Vérifications communes
            if utilisateur.actif:
                return None, "Ce compte est déjà activé"
            
            if mot_de_passe != confirmation_mot_de_passe:
                return None, "Les mots de passe ne correspondent pas"
            
            if len(mot_de_passe) < 8:
                return None, "Le mot de passe doit contenir au moins 8 caractères"
            
            # Activer le compte
            utilisateur.set_password(mot_de_passe)
            utilisateur.actif = True
            
            # Invalider le token
            self._use_activation_token(token)
            
            db.session.commit()
            
            print(f"✅ Compte {user_role} activé avec succès pour {utilisateur.email}")
            
            # Envoyer email de confirmation
            client_name = "SERTEC IoT"
            if utilisateur.client:
                client_name = utilisateur.client.nom_entreprise
            
            email_result = MailService.send_activation_confirmation_email(
                user_email=utilisateur.email,
                prenom=utilisateur.prenom,
                nom=utilisateur.nom,
                client_name=client_name
            )
            
            resultat = {
                'utilisateur': utilisateur.to_dict(),
                'email_confirmation': email_result,
                'message': f"✅ Compte {user_role} activé avec succès ! Un email de confirmation a été envoyé à {utilisateur.email}"
            }
            
            return resultat, None
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERREUR ACTIVATION GÉNÉRIQUE: {str(e)}")
            return None, f"Erreur lors de l'activation: {str(e)}"
    
    # =================== GESTION BATCH DES TOKENS ===================
    
    def nettoyer_tokens_utilisateurs_supprimes(self) -> Dict[str, int]:
        """Nettoyer les tokens d'activation des utilisateurs qui ont été supprimés de la DB"""
        try:
            if not self.redis:
                return {'error': 'Redis indisponible'}
            
            pattern = "activation_token:*"
            keys = self.redis.keys(pattern)
            
            tokens_supprimes = 0
            tokens_gardes = 0
            
            for key in keys:
                try:
                    token_data_str = self.redis.get(key)
                    if token_data_str:
                        token_data = json.loads(token_data_str)
                        user_id = token_data.get('user_id')
                        
                        if user_id:
                            # Vérifier si l'utilisateur existe encore
                            utilisateur = User.query.get(user_id)
                            if not utilisateur:
                                # Utilisateur supprimé, supprimer le token
                                self.redis.delete(key)
                                tokens_supprimes += 1
                            else:
                                tokens_gardes += 1
                        else:
                            # Token sans user_id, le supprimer
                            self.redis.delete(key)
                            tokens_supprimes += 1
                    else:
                        # Token corrompu
                        self.redis.delete(key)
                        tokens_supprimes += 1
                        
                except Exception:
                    # Erreur de parsing, supprimer le token corrompu
                    self.redis.delete(key)
                    tokens_supprimes += 1
            
            return {
                'tokens_supprimes': tokens_supprimes,
                'tokens_gardes': tokens_gardes,
                'message': f'{tokens_supprimes} tokens orphelins supprimés, {tokens_gardes} tokens valides gardés'
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def prolonger_token_activation(self, token: str, nouvelles_heures: int = 24) -> Tuple[bool, str]:
        """Prolonger la durée de validité d'un token d'activation"""
        try:
            if not self.redis:
                return False, "Redis indisponible"
            
            redis_key = f"activation_token:{token}"
            token_data_str = self.redis.get(redis_key)
            
            if not token_data_str:
                return False, "Token non trouvé"
            
            token_data = json.loads(token_data_str)
            
            if token_data.get('used', False):
                return False, "Token déjà utilisé"
            
            # Mettre à jour l'expiration
            nouvelle_expiration = datetime.utcnow() + timedelta(hours=nouvelles_heures)
            token_data['expires_at'] = nouvelle_expiration.isoformat()
            
            # Recalculer le TTL Redis
            nouveau_ttl = int(nouvelles_heures * 3600)
            
            # Remettre dans Redis avec le nouveau TTL
            self.redis.setex(redis_key, nouveau_ttl, json.dumps(token_data))
            
            return True, f"Token prolongé de {nouvelles_heures}h (expire le {nouvelle_expiration.strftime('%d/%m/%Y à %H:%M')})"
            
        except Exception as e:
            return False, f"Erreur lors de la prolongation: {str(e)}"
    
    def lister_tokens_expirant_bientot(self, heures: int = 2) -> List[Dict[str, Any]]:
        """Lister les tokens qui vont expirer dans les prochaines heures"""
        try:
            if not self.redis:
                return []
            
            pattern = "activation_token:*"
            keys = self.redis.keys(pattern)
            
            limite = datetime.utcnow() + timedelta(hours=heures)
            tokens_expirants = []
            
            for key in keys:
                try:
                    token_data_str = self.redis.get(key)
                    if token_data_str:
                        token_data = json.loads(token_data_str)
                        expires_at = datetime.fromisoformat(token_data['expires_at'])
                        
                        if expires_at <= limite and not token_data.get('used', False):
                            # Récupérer les infos utilisateur
                            user_id = token_data.get('user_id')
                            utilisateur = User.query.get(user_id) if user_id else None
                            
                            token_info = {
                                'user_id': user_id,
                                'email': token_data.get('email'),
                                'role': token_data.get('role'),
                                'expires_at': expires_at.isoformat(),
                                'heures_restantes': round((expires_at - datetime.utcnow()).total_seconds() / 3600, 1),
                                'utilisateur_existe': utilisateur is not None,
                                'utilisateur_actif': utilisateur.actif if utilisateur else None
                            }
                            
                            tokens_expirants.append(token_info)
                            
                except Exception:
                    continue
            
            # Trier par expiration (plus urgent en premier)
            tokens_expirants.sort(key=lambda x: x['expires_at'])
            
            return tokens_expirants
            
        except Exception as e:
            print(f"❌ Erreur listage tokens expirants: {e}")
            return []
    
    # =================== MÉTHODES SPÉCIALES DE SUPPRESSION ===================
    
    def supprimer_superadmin(self, superadmin_id: str, utilisateur_supprimeur: User, forcer: bool = False) -> Tuple[bool, str]:
        """Supprimer un superadmin - SEULEMENT PAR UN AUTRE SUPERADMIN"""
        try:
            # ✅ VÉRIFICATION : Seul un superadmin peut supprimer un superadmin
            if not utilisateur_supprimeur.is_superadmin():
                return False, "Seul un superadmin peut supprimer un autre superadmin"
            
            superadmin_cible = User.query.get(superadmin_id)
            if not superadmin_cible:
                return False, "Superadmin non trouvé"
            
            # ✅ VÉRIFICATION : S'assurer que c'est bien un superadmin
            if not superadmin_cible.is_superadmin():
                return False, "Cet utilisateur n'est pas un superadmin"
            
            # ✅ PROTECTION : Ne pas se supprimer soi-même
            if superadmin_cible.id == utilisateur_supprimeur.id:
                return False, "Vous ne pouvez pas vous supprimer vous-même"
            
            # ✅ SÉCURITÉ : Vérifier qu'il restera au moins un superadmin actif
            nb_superadmins_actifs = User.query.filter_by(role='superadmin', actif=True).count()
            if nb_superadmins_actifs <= 1 and superadmin_cible.actif:
                return False, "Impossible de supprimer le dernier superadmin actif du système"
            
            # ✅ VÉRIFIER : S'il y a des données critiques liées
            nb_clients_crees = 0
            nb_utilisateurs_crees = 0
            
            # Compter les clients créés par ce superadmin (si vous trackez qui a créé quoi)
            # Pour l'instant, on suppose que les superadmins peuvent avoir créé des données importantes
            
            # Si pas de forçage et que le superadmin est actif avec potentiellement des données
            if not forcer and superadmin_cible.actif:
                return False, (f"Impossible de supprimer le superadmin '{superadmin_cible.nom_complet}' actif sans forcer. "
                             f"Utilisez forcer=True pour confirmer la suppression définitive.")
            
            nom_superadmin = superadmin_cible.nom_complet
            email_superadmin = superadmin_cible.email
            
            # ✅ NOUVEAU : Invalider tous les tokens d'activation de ce superadmin
            tokens_supprimes = self._revoke_user_activation_tokens(superadmin_cible.id)
            
            # ✅ SUPPRESSION : Supprimer le superadmin
            db.session.delete(superadmin_cible)
            db.session.commit()
            
            message = (f"Superadmin '{nom_superadmin}' ({email_superadmin}) supprimé définitivement. "
                      f"{tokens_supprimes} tokens d'activation invalidés.")
            
            return True, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la suppression du superadmin: {str(e)}"
    
    def supprimer_utilisateur_en_attente(self, utilisateur_id: str, utilisateur_supprimeur: User) -> Tuple[bool, str]:
        """Supprimer un utilisateur en attente d'activation (compte inactif avec token)"""
        try:
            utilisateur_cible = User.query.get(utilisateur_id)
            if not utilisateur_cible:
                return False, "Utilisateur non trouvé"
            
            # ✅ VÉRIFICATION : L'utilisateur doit être inactif (en attente)
            if utilisateur_cible.actif:
                return False, "Impossible de supprimer un utilisateur actif avec cette méthode. Utilisez la méthode de suppression standard."
            
            # ✅ PERMISSIONS : Vérifier qui peut supprimer
            if utilisateur_supprimeur.is_superadmin():
                # Superadmin peut supprimer n'importe qui en attente
                pass
            elif utilisateur_supprimeur.is_admin():
                # Admin peut supprimer seulement les users de son client en attente
                if utilisateur_cible.client_id != utilisateur_supprimeur.client_id:
                    return False, "Vous ne pouvez supprimer que les utilisateurs en attente de votre client"
                
                # Admin ne peut pas supprimer un autre admin en attente
                if utilisateur_cible.is_admin():
                    return False, "Un admin ne peut pas supprimer un autre admin en attente"
                
                # Admin ne peut pas supprimer un superadmin en attente
                if utilisateur_cible.is_superadmin():
                    return False, "Un admin ne peut pas supprimer un superadmin en attente"
            else:
                return False, "Permission insuffisante pour supprimer des utilisateurs en attente"
            
            nom_utilisateur = utilisateur_cible.nom_complet
            email_utilisateur = utilisateur_cible.email
            role_utilisateur = utilisateur_cible.role
            client_info = ""
            
            if utilisateur_cible.client:
                client_info = f" (Client: {utilisateur_cible.client.nom_entreprise})"
            
            # ✅ NOUVEAU : Invalider tous les tokens d'activation de cet utilisateur
            tokens_supprimes = self._revoke_user_activation_tokens(utilisateur_cible.id)
            
            # ✅ VÉRIFIER : Si c'est un admin en attente, vérifier s'il n'y a pas d'autres données
            if utilisateur_cible.is_admin() and utilisateur_cible.client:
                # Vérifier s'il y a d'autres admins actifs dans ce client
                autres_admins_actifs = User.query.filter_by(
                    client_id=utilisateur_cible.client_id,
                    role='admin',
                    actif=True
                ).count()
                
                if autres_admins_actifs == 0:
                    # Vérifier s'il y a des utilisateurs dans ce client
                    nb_users_client = User.query.filter_by(client_id=utilisateur_cible.client_id).count()
                    if nb_users_client > 1:  # Plus que juste cet admin
                        return False, (f"Impossible de supprimer cet admin en attente : "
                                     f"il n'y a aucun autre admin actif dans le client '{utilisateur_cible.client.nom_entreprise}' "
                                     f"et il y a encore {nb_users_client - 1} utilisateurs dans ce client.")
            
            # ✅ SUPPRESSION : Supprimer l'utilisateur en attente
            db.session.delete(utilisateur_cible)
            db.session.commit()
            
            message = (f"Utilisateur en attente '{nom_utilisateur}' ({role_utilisateur}) "
                      f"<{email_utilisateur}>{client_info} supprimé définitivement. "
                      f"{tokens_supprimes} tokens d'activation invalidés.")
            
            return True, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la suppression de l'utilisateur en attente: {str(e)}"
    
    def lister_utilisateurs_en_attente(self, utilisateur_demandeur: User, inclure_tous_roles: bool = False) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Lister les utilisateurs en attente d'activation selon les permissions"""
        try:
            if utilisateur_demandeur.is_superadmin():
                # 🔧 SUPERADMIN : Voit TOUS les utilisateurs en attente de TOUS les clients
                query = User.query.filter_by(actif=False)
                
                if not inclure_tous_roles:
                    # Par défaut, exclure les superadmins pour éviter la confusion
                    query = query.filter(User.role != 'superadmin')
                
                scope_message = "tous les clients" if not inclure_tous_roles else "tous les clients (incluant superadmins)"
                
            elif utilisateur_demandeur.is_admin():
                # 🏢 ADMIN CLIENT : Voit SEULEMENT les utilisateurs de SON client en attente
                query = User.query.filter_by(
                    actif=False,
                    client_id=utilisateur_demandeur.client_id  # ✅ RESTRICTION : Seulement son client
                )
                
                # Admin ne voit JAMAIS les superadmins en attente (ils n'ont pas de client_id)
                query = query.filter(User.role != 'superadmin')
                
                scope_message = f"client '{utilisateur_demandeur.client.nom_entreprise}'" if utilisateur_demandeur.client else "votre client"
                
            else:
                return None, "Permission insuffisante pour voir les utilisateurs en attente"
            
            utilisateurs_en_attente = query.order_by(User.date_creation.desc()).all()
            
            liste_utilisateurs = []
            for user in utilisateurs_en_attente:
                user_dict = user.to_dict(include_sensitive=True)
                user_dict['entreprise'] = user.client.nom_entreprise if user.client else None
                user_dict['jours_depuis_creation'] = (datetime.utcnow() - user.date_creation).days
                
                # ✅ Ajouter info tokens d'activation
                user_dict['has_activation_token'] = self._user_has_activation_token(user.id)
                user_dict['nb_tokens_actifs'] = self._count_user_activation_tokens(user.id)
                
                # ✅ Informations sur les permissions de suppression
                user_dict['peut_etre_supprime'] = self._peut_supprimer_utilisateur_en_attente(utilisateur_demandeur, user)
                
                # ✅ NOUVEAU : Indiquer si c'est dans le scope de l'utilisateur demandeur
                if utilisateur_demandeur.is_superadmin():
                    user_dict['dans_mon_scope'] = True
                elif utilisateur_demandeur.is_admin():
                    user_dict['dans_mon_scope'] = (user.client_id == utilisateur_demandeur.client_id)
                
                liste_utilisateurs.append(user_dict)
            
            # ✅ NOUVEAU : Ajouter des métadonnées sur le scope
            metadata = {
                'scope': scope_message,
                'total_utilisateurs': len(liste_utilisateurs),
                'permissions': {
                    'peut_voir_tous_clients': utilisateur_demandeur.is_superadmin(),
                    'peut_voir_superadmins': utilisateur_demandeur.is_superadmin() and inclure_tous_roles,
                    'client_restriction': utilisateur_demandeur.client_id if utilisateur_demandeur.is_admin() else None
                }
            }
            
            return {
                'utilisateurs': liste_utilisateurs,
                'metadata': metadata
            }, None
            
        except Exception as e:
            return None, f"Erreur lors de la récupération: {str(e)}"
    
    def supprimer_batch_utilisateurs_en_attente(self, utilisateurs_ids: List[str], utilisateur_supprimeur: User) -> Dict[str, Any]:
        """Supprimer plusieurs utilisateurs en attente en une fois"""
        try:
            if not utilisateurs_ids:
                return {'success': False, 'message': 'Aucun utilisateur spécifié'}
            
            resultats = {
                'supprimes': [],
                'erreurs': [],
                'total_demande': len(utilisateurs_ids),
                'total_supprime': 0,
                'total_erreurs': 0
            }
            
            for user_id in utilisateurs_ids:
                try:
                    succes, message = self.supprimer_utilisateur_en_attente(user_id, utilisateur_supprimeur)
                    
                    if succes:
                        resultats['supprimes'].append({
                            'user_id': user_id,
                            'message': message
                        })
                        resultats['total_supprime'] += 1
                    else:
                        resultats['erreurs'].append({
                            'user_id': user_id,
                            'erreur': message
                        })
                        resultats['total_erreurs'] += 1
                        
                except Exception as e:
                    resultats['erreurs'].append({
                        'user_id': user_id,
                        'erreur': f'Erreur inattendue: {str(e)}'
                    })
                    resultats['total_erreurs'] += 1
            
            # Message de résumé
            if resultats['total_supprime'] > 0:
                resultats['success'] = True
                resultats['message'] = (f"{resultats['total_supprime']} utilisateurs supprimés avec succès"
                                       f"{f', {resultats["total_erreurs"]} erreurs' if resultats['total_erreurs'] > 0 else ''}")
            else:
                resultats['success'] = False
                resultats['message'] = f"Aucun utilisateur supprimé. {resultats['total_erreurs']} erreurs"
            
            return resultats
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de la suppression batch: {str(e)}',
                'total_demande': len(utilisateurs_ids),
                'total_supprime': 0,
                'total_erreurs': len(utilisateurs_ids)
            }
    
    # =================== MÉTHODES PRIVÉES POUR LES NOUVELLES FONCTIONNALITÉS ===================
    
    def _peut_supprimer_utilisateur_en_attente(self, utilisateur_supprimeur: User, utilisateur_cible: User) -> bool:
        """Vérifier si un utilisateur peut supprimer un utilisateur en attente"""
        # L'utilisateur doit être inactif
        if utilisateur_cible.actif:
            return False
        
        # Superadmin peut supprimer n'importe qui en attente
        if utilisateur_supprimeur.is_superadmin():
            return True
        
        # Admin peut supprimer seulement les users de son client en attente
        if utilisateur_supprimeur.is_admin():
            # Même client
            if utilisateur_cible.client_id != utilisateur_supprimeur.client_id:
                return False
            
            # Pas un autre admin ou superadmin
            if utilisateur_cible.is_admin() or utilisateur_cible.is_superadmin():
                return False
            
            return True
        
        return False
    
    def _count_user_activation_tokens(self, user_id: str) -> int:
        """Compter le nombre de tokens d'activation actifs pour un utilisateur"""
        try:
            if not self.redis:
                return 0
            
            pattern = "activation_token:*"
            keys = self.redis.keys(pattern)
            
            count = 0
            now = datetime.utcnow()
            
            for key in keys:
                try:
                    token_data_str = self.redis.get(key)
                    if token_data_str:
                        token_data = json.loads(token_data_str)
                        
                        if (token_data.get('user_id') == user_id and 
                            not token_data.get('used', False)):
                            
                            # Vérifier que le token n'est pas expiré
                            expires_at = datetime.fromisoformat(token_data['expires_at'])
                            if now <= expires_at:
                                count += 1
                except Exception:
                    continue
            
            return count
            
        except Exception as e:
            print(f"❌ Erreur comptage tokens utilisateur: {e}")
            return 0