from app import db
from app.models.site import Site
from app.models.client import Client
from app.models.user import User
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any


class SiteService:
    def __init__(self):
        pass
    
    # =================== GESTION DES SITES ===================
    
    def creer_site(self, donnees_site: Dict[str, Any], utilisateur_createur: User) -> Tuple[Optional[Site], Optional[str]]:
        """Créer un nouveau site - SEUL LE SUPERADMIN PEUT"""
        try:
            # Vérification : seul le superadmin peut créer des sites
            if not utilisateur_createur.is_superadmin():
                return None, "Seul le superadmin peut créer des sites"
            
            # Validation des données requises
            champs_requis = ['nom_site', 'adresse', 'client_id']
            champs_manquants = [champ for champ in champs_requis if not donnees_site.get(champ)]
            if champs_manquants:
                return None, f"Champs requis manquants: {', '.join(champs_manquants)}"
            
            # Vérifier que le client existe et est actif
            client = Client.query.get(donnees_site['client_id'])
            if not client:
                return None, "Client non trouvé"
            if not client.actif:
                return None, "Le client est désactivé"
            
            # Vérifier unicité du nom de site pour ce client
            site_existant = Site.query.filter_by(
                client_id=donnees_site['client_id'],
                nom_site=donnees_site['nom_site'].strip(),
                actif=True
            ).first()
            if site_existant:
                return None, f"Un site '{donnees_site['nom_site']}' existe déjà pour ce client"
            
            # Créer le site
            nouveau_site = Site(
                client_id=donnees_site['client_id'],
                nom_site=donnees_site['nom_site'].strip(),
                adresse=donnees_site['adresse'].strip(),
                ville=donnees_site.get('ville', '').strip() or None,
                quartier=donnees_site.get('quartier', '').strip() or None,
                code_postal=donnees_site.get('code_postal', '').strip() or None,
                pays=donnees_site.get('pays', 'Sénégal').strip(),
                contact_site=donnees_site.get('contact_site', '').strip() or None,
                telephone_site=donnees_site.get('telephone_site', '').strip() or None
            )
            
            # Gérer les coordonnées si fournies
            if donnees_site.get('latitude') and donnees_site.get('longitude'):
                if nouveau_site.set_coordinates(
                    donnees_site['latitude'], 
                    donnees_site['longitude'], 
                    donnees_site.get('precision_gps', 'exacte')
                ):
                    print(f"✅ Coordonnées manuelles définies pour {nouveau_site.nom_site}")
                else:
                    print(f"⚠️ Coordonnées invalides ignorées pour {nouveau_site.nom_site}")
            
            db.session.add(nouveau_site)
            db.session.flush()  # Pour obtenir l'ID
            
            # Tentative de géocodage automatique si pas de coordonnées
            if not nouveau_site.has_coordinates():
                print(f"🌍 Tentative géocodage automatique pour {nouveau_site.nom_site}...")
                if nouveau_site.try_geocode_address():
                    print(f"✅ Géocodage réussi pour {nouveau_site.nom_site}")
                else:
                    print(f"❌ Géocodage échoué pour {nouveau_site.nom_site}")
            
            db.session.commit()
            
            return nouveau_site, None
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de la création du site: {str(e)}"
    
    def modifier_site(self, site_id: str, nouvelles_donnees: Dict[str, Any], utilisateur_modificateur: User) -> Tuple[Optional[Site], Optional[str]]:
        """Modifier un site existant - SEUL LE SUPERADMIN PEUT"""
        try:
            # Vérification : seul le superadmin peut modifier des sites
            if not utilisateur_modificateur.is_superadmin():
                return None, "Seul le superadmin peut modifier des sites"
            
            site = Site.query.get(site_id)
            if not site:
                return None, "Site non trouvé"
            
            # Vérifier que le client du site est toujours actif
            if not site.client or not site.client.actif:
                return None, "Le client de ce site est désactivé"
            
            # Champs modifiables
            champs_modifiables = [
                'nom_site', 'adresse', 'ville', 'quartier', 'code_postal', 
                'pays', 'contact_site', 'telephone_site'
            ]
            
            # Appliquer les modifications
            site_modifie = False
            for champ in champs_modifiables:
                if champ in nouvelles_donnees:
                    valeur = nouvelles_donnees[champ]
                    if valeur is not None:
                        valeur = str(valeur).strip()
                        if champ in ['nom_site', 'adresse'] and not valeur:
                            return None, f"Le champ {champ} ne peut pas être vide"
                    
                    # Vérifier unicité du nom si modifié
                    if champ == 'nom_site' and valeur and valeur != site.nom_site:
                        site_existant = Site.query.filter_by(
                            client_id=site.client_id,
                            nom_site=valeur,
                            actif=True
                        ).filter(Site.id != site_id).first()
                        if site_existant:
                            return None, f"Un site '{valeur}' existe déjà pour ce client"
                    
                    if getattr(site, champ) != (valeur if valeur else None):
                        setattr(site, champ, valeur if valeur else None)
                        site_modifie = True
            
            # Gérer les coordonnées si fournies
            if ('latitude' in nouvelles_donnees and 'longitude' in nouvelles_donnees):
                lat = nouvelles_donnees['latitude']
                lon = nouvelles_donnees['longitude']
                precision = nouvelles_donnees.get('precision_gps', 'exacte')
                
                if lat is not None and lon is not None:
                    if site.set_coordinates(lat, lon, precision):
                        site_modifie = True
                        print(f"✅ Coordonnées mises à jour pour {site.nom_site}")
                    else:
                        return None, "Coordonnées invalides"
                elif lat is None and lon is None:
                    # Effacer les coordonnées
                    site.latitude = None
                    site.longitude = None
                    site.precision_gps = 'inconnue'
                    site.coordonnees_auto = False
                    site_modifie = True
                    print(f"📍 Coordonnées effacées pour {site.nom_site}")
            
            # Regéocodage si adresse modifiée et pas de coordonnées manuelles
            if site_modifie and ('adresse' in nouvelles_donnees or 'ville' in nouvelles_donnees):
                if not site.has_coordinates() or site.coordonnees_auto:
                    print(f"🌍 Regéocodage automatique pour {site.nom_site}...")
                    site.try_geocode_address()
            
            if site_modifie:
                db.session.commit()
                return site, None
            else:
                return site, "Aucune modification apportée"
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de la modification: {str(e)}"
    
    def lister_sites(self, utilisateur_demandeur: User, client_id: Optional[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Lister les sites selon les permissions"""
        try:
            query = Site.query.filter_by(actif=True)
            
            if utilisateur_demandeur.is_superadmin():
                # SUPERADMIN voit tout
                if client_id:
                    # Filtrer par client spécifique si demandé
                    query = query.filter_by(client_id=client_id)
                    
            elif utilisateur_demandeur.is_admin():
                # ADMIN voit seulement son client
                query = query.filter_by(client_id=utilisateur_demandeur.client_id)
                
            else:
                # USER voit seulement les sites avec des appareils autorisés
                # TODO: Implémenter la logique DeviceAccess plus tard
                query = query.filter_by(client_id=utilisateur_demandeur.client_id)
            
            # Ordonner par nom du site
            sites = query.order_by(Site.nom_site).all()
            
            # Convertir en dictionnaire avec informations enrichies
            liste_sites = []
            for site in sites:
                site_dict = site.to_dict(include_map_link=True, include_stats=True)
                liste_sites.append(site_dict)
            
            return liste_sites, None
            
        except Exception as e:
            return None, f"Erreur lors de la récupération des sites: {str(e)}"
    
    def obtenir_site(self, site_id: str, utilisateur_demandeur: User) -> Tuple[Optional[Dict], Optional[str]]:
        """Obtenir les détails d'un site"""
        try:
            site = Site.query.get(site_id)
            if not site:
                return None, "Site non trouvé"
            
            # Vérifier les permissions d'accès
            if not self._peut_voir_site(utilisateur_demandeur, site):
                return None, "Permission insuffisante pour voir ce site"
            
            # Retourner les informations complètes
            site_dict = site.to_dict(
                include_map_link=True, 
                include_stats=True, 
                include_devices=utilisateur_demandeur.is_superadmin()  # Devices seulement pour superadmin
            )
            
            # Ajouter des informations sur les permissions
            site_dict['permissions'] = {
                'peut_modifier': self._peut_modifier_site(utilisateur_demandeur, site),
                'peut_supprimer': self._peut_supprimer_site(utilisateur_demandeur, site),
                'peut_voir_appareils': True  # TODO: Affiner avec DeviceAccess
            }
            
            return site_dict, None
            
        except Exception as e:
            return None, f"Erreur lors de la récupération du site: {str(e)}"
    
    def desactiver_site(self, site_id: str, utilisateur_desactivateur: User) -> Tuple[bool, str]:
        """Désactiver un site - SUPERADMIN SEULEMENT"""
        try:
            if not utilisateur_desactivateur.is_superadmin():
                return False, "Seul le superadmin peut désactiver des sites"
            
            site = Site.query.get(site_id)
            if not site:
                return False, "Site non trouvé"
            
            if not site.actif:
                return False, "Site déjà désactivé"
            
            # Vérifier s'il y a des appareils actifs
            nb_appareils_actifs = site.appareils.filter_by(actif=True).count()
            if nb_appareils_actifs > 0:
                return False, f"Impossible de désactiver: {nb_appareils_actifs} appareils actifs sur ce site"
            
            site.actif = False
            db.session.commit()
            
            return True, f"Site '{site.nom_site}' désactivé avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la désactivation: {str(e)}"
    
    def reactiver_site(self, site_id: str, utilisateur_reactivateur: User) -> Tuple[bool, str]:
        """Réactiver un site désactivé - SUPERADMIN SEULEMENT"""
        try:
            if not utilisateur_reactivateur.is_superadmin():
                return False, "Seul le superadmin peut réactiver des sites"
            
            site = Site.query.filter_by(id=site_id, actif=False).first()
            if not site:
                return False, "Site non trouvé ou déjà actif"
            
            # Vérifier que le client est toujours actif
            if not site.client or not site.client.actif:
                return False, "Impossible de réactiver: le client est désactivé"
            
            site.actif = True
            db.session.commit()
            
            return True, f"Site '{site.nom_site}' réactivé avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la réactivation: {str(e)}"
    
    def supprimer_site(self, site_id: str, utilisateur_supprimeur: User, forcer: bool = False) -> Tuple[bool, str]:
        """Supprimer définitivement un site - SUPERADMIN SEULEMENT"""
        try:
            if not utilisateur_supprimeur.is_superadmin():
                return False, "Seul le superadmin peut supprimer des sites"
            
            site = Site.query.get(site_id)
            if not site:
                return False, "Site non trouvé"
            
            # Vérifier s'il y a des appareils liés
            nb_appareils = site.appareils.count()
            
            if nb_appareils > 0 and not forcer:
                return False, (f"Impossible de supprimer: {nb_appareils} appareils sont liés à ce site. "
                             f"Utilisez forcer=True pour supprimer définitivement.")
            
            nom_site = site.nom_site
            client_nom = site.client.nom_entreprise if site.client else "Client inconnu"
            
            if forcer and nb_appareils > 0:
                # Suppression forcée - SQLAlchemy gère les CASCADE
                db.session.delete(site)
                message = f"Site '{nom_site}' ({client_nom}) et ses {nb_appareils} appareils supprimés définitivement"
            else:
                # Suppression simple
                db.session.delete(site)
                message = f"Site '{nom_site}' ({client_nom}) supprimé avec succès"
            
            db.session.commit()
            return True, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la suppression: {str(e)}"
    
    # =================== FONCTIONNALITÉS GÉOGRAPHIQUES ===================
    
    def geocoder_site(self, site_id: str, utilisateur_demandeur: User) -> Tuple[bool, str]:
        """Forcer le géocodage d'un site - SUPERADMIN SEULEMENT"""
        try:
            if not utilisateur_demandeur.is_superadmin():
                return False, "Seul le superadmin peut forcer le géocodage"
            
            site = Site.query.get(site_id)
            if not site:
                return False, "Site non trouvé"
            
            if site.try_geocode_address():
                return True, f"Géocodage réussi pour '{site.nom_site}'"
            else:
                return False, f"Géocodage échoué pour '{site.nom_site}'"
            
        except Exception as e:
            return False, f"Erreur lors du géocodage: {str(e)}"
    
    def sites_proches(self, site_id: str, radius_km: int, utilisateur_demandeur: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Trouver les sites proches d'un site donné"""
        try:
            site_reference = Site.query.get(site_id)
            if not site_reference:
                return None, "Site de référence non trouvé"
            
            # Vérifier les permissions d'accès au site de référence
            if not self._peut_voir_site(utilisateur_demandeur, site_reference):
                return None, "Permission insuffisante pour ce site"
            
            if not site_reference.has_coordinates():
                return None, "Le site de référence n'a pas de coordonnées"
            
            # Limiter le rayon selon les permissions
            max_radius = 50 if utilisateur_demandeur.is_superadmin() else 20
            radius_km = min(radius_km, max_radius)
            
            # Trouver les sites proches
            client_filter = None if utilisateur_demandeur.is_superadmin() else utilisateur_demandeur.client_id
            
            sites_proches = Site.find_nearby_sites(
                latitude=float(site_reference.latitude),
                longitude=float(site_reference.longitude),
                radius_km=radius_km,
                client_id=client_filter
            )
            
            # Exclure le site de référence et calculer les distances
            resultats = []
            for site in sites_proches:
                if site.id != site_id and self._peut_voir_site(utilisateur_demandeur, site):
                    site_dict = site.to_dict(include_map_link=True)
                    site_dict['distance_km'] = site_reference.distance_to(site)
                    resultats.append(site_dict)
            
            # Trier par distance
            resultats.sort(key=lambda x: x['distance_km'] or float('inf'))
            
            return resultats, None
            
        except Exception as e:
            return None, f"Erreur lors de la recherche: {str(e)}"
    
    # =================== STATISTIQUES ===================
    
    def obtenir_statistiques_sites(self, utilisateur_demandeur: User, client_id: Optional[str] = None) -> Tuple[Optional[Dict], Optional[str]]:
        """Obtenir des statistiques sur les sites"""
        try:
            if not utilisateur_demandeur.is_admin():
                return None, "Permission insuffisante"
            
            query = Site.query.filter_by(actif=True)
            
            if utilisateur_demandeur.is_superadmin():
                if client_id:
                    query = query.filter_by(client_id=client_id)
                    scope = f"client {Client.query.get(client_id).nom_entreprise}" if Client.query.get(client_id) else "client inconnu"
                else:
                    scope = "global"
            else:
                query = query.filter_by(client_id=utilisateur_demandeur.client_id)
                scope = f"client {utilisateur_demandeur.client.nom_entreprise}" if utilisateur_demandeur.client else "votre client"
            
            sites = query.all()
            
            stats = {
                'scope': scope,
                'total_sites': len(sites),
                'sites_avec_coordonnees': len([s for s in sites if s.has_coordinates()]),
                'sites_coordonnees_auto': len([s for s in sites if s.coordonnees_auto]),
                'sites_coordonnees_manuelles': len([s for s in sites if s.has_coordinates() and not s.coordonnees_auto]),
                'repartition_villes': {},
                'repartition_pays': {},
                'total_appareils': 0,
                'appareils_actifs': 0,
                'taux_geocodage': 0
            }
            
            # Calculs détaillés
            for site in sites:
                # Répartition géographique
                ville = site.ville or 'Non renseignée'
                stats['repartition_villes'][ville] = stats['repartition_villes'].get(ville, 0) + 1
                
                pays = site.pays or 'Non renseigné'
                stats['repartition_pays'][pays] = stats['repartition_pays'].get(pays, 0) + 1
                
                # Comptage appareils
                stats['total_appareils'] += site.appareils.count()
                stats['appareils_actifs'] += site.appareils.filter_by(actif=True).count()
            
            # Taux de géocodage
            if stats['total_sites'] > 0:
                stats['taux_geocodage'] = round(
                    (stats['sites_avec_coordonnees'] / stats['total_sites']) * 100, 2
                )
            
            return stats, None
            
        except Exception as e:
            return None, f"Erreur lors du calcul des statistiques: {str(e)}"
    
    # =================== MÉTHODES PRIVÉES DE VALIDATION ===================
    
    def _peut_voir_site(self, utilisateur_demandeur: User, site: Site) -> bool:
        """Vérifier si un utilisateur peut voir un site"""
        # Superadmin voit tout
        if utilisateur_demandeur.is_superadmin():
            return True
        
        # Admin/User voit son client
        return site.client_id == utilisateur_demandeur.client_id
    
    def _peut_modifier_site(self, utilisateur_modificateur: User, site: Site) -> bool:
        """Vérifier si un utilisateur peut modifier un site"""
        # Seul le superadmin peut modifier des sites
        return utilisateur_modificateur.is_superadmin()
    
    def _peut_supprimer_site(self, utilisateur_supprimeur: User, site: Site) -> bool:
        """Vérifier si un utilisateur peut supprimer un site"""
        # Seul le superadmin peut supprimer des sites
        return utilisateur_supprimeur.is_superadmin()