from app import db
from app.models.user import User
from app.models.client import Client
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
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
                client_id=nouveau_client.id
            )
            
            # 🔐 Générer un mot de passe temporaire pour l'admin
            mot_de_passe_temporaire = self._generer_mot_de_passe_temporaire()
            admin_client.set_password(mot_de_passe_temporaire)
            
            db.session.add(admin_client)
            db.session.commit()
            
            # 🎉 Préparer le résultat complet
            resultat = {
                'client': nouveau_client.to_dict(),
                'admin_client': admin_client.to_dict(),
                'mot_de_passe_temporaire': mot_de_passe_temporaire,
                'identifiants_connexion': {
                    'email': email_admin,
                    'mot_de_passe': mot_de_passe_temporaire
                },
                'message_instructions': f"Transférez ces identifiants à l'administrateur de {nouveau_client.nom_entreprise}"
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
            
            clients = Client.query.filter_by(actif=True).order_by(Client.nom_entreprise).all()
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
            
            utilisateurs = query.filter_by(actif=True).order_by(User.prenom, User.nom).all()
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
                    'utilisateurs_inactifs': User.query.filter_by(actif=False).count()
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