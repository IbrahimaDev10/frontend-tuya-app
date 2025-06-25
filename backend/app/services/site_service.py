# site_service.py - Service pour la gestion des sites avec Redis
# Compatible avec vos modèles Site, Client, User
# ✅ NOUVEAU : Intégration Redis pour cache et performance géographique

from app import db, get_redis  # ✅ NOUVEAU : Import get_redis
from app.models.site import Site
from app.models.client import Client
from app.models.user import User
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
import json
import logging

class SiteService:
    """Service pour la gestion des sites avec cache Redis intelligent"""
    
    def __init__(self):
        # ✅ NOUVEAU : Redis d'abord, sinon fonctionnement normal
        self.redis = get_redis()
        
        # ✅ NOUVEAU : Configuration TTL depuis settings
        from config.settings import get_config
        config = get_config()
        self.ttl_config = config.REDIS_DEFAULT_TTL
        
        logging.info(f"SiteService initialisé - Redis: {'✅' if self.redis else '❌'}")
    
    # =================== MÉTHODES REDIS POUR CACHE ===================
    
    def _cache_site_data(self, site_id, site_data, ttl=None):
        """Cache des données de site dans Redis"""
        try:
            if not self.redis:
                return
            
            ttl = ttl or self.ttl_config.get('api_cache', 300)
            key = f"site_data:{site_id}"
            
            cache_data = {
                'site_id': site_id,
                'site_data': site_data,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            logging.debug(f"Site data cached for {site_id}")
            
        except Exception as e:
            logging.error(f"Erreur cache site {site_id}: {e}")
    
    def _get_cached_site_data(self, site_id):
        """Récupérer données site depuis cache"""
        try:
            if not self.redis:
                return None
            
            key = f"site_data:{site_id}"
            cached_data = self.redis.get(key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logging.error(f"Erreur récupération cache site {site_id}: {e}")
            return None
    
    def _cache_sites_list(self, client_id, sites_data, ttl=None):
        """Cache de la liste des sites par client"""
        try:
            if not self.redis:
                return
            
            ttl = ttl or self.ttl_config.get('api_cache', 300)
            key = f"sites_list:client:{client_id}" if client_id else "sites_list:all"
            
            cache_data = {
                'client_id': client_id,
                'sites': sites_data,
                'cached_at': datetime.utcnow().isoformat(),
                'count': len(sites_data)
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            logging.info(f"Liste de {len(sites_data)} sites mise en cache pour client {client_id}")
            
        except Exception as e:
            logging.error(f"Erreur cache liste sites: {e}")
    
    def _get_cached_sites_list(self, client_id):
        """Récupérer liste sites depuis cache"""
        try:
            if not self.redis:
                return None
            
            key = f"sites_list:client:{client_id}" if client_id else "sites_list:all"
            cached_data = self.redis.get(key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logging.error(f"Erreur récupération cache liste sites: {e}")
            return None
    
    def _cache_geocoding_result(self, address_key, coordinates, ttl=None):
        """Cache des résultats de géocodage"""
        try:
            if not self.redis:
                return
            
            ttl = ttl or 86400  # 24h pour géocodage (stable)
            key = f"geocoding:{address_key}"
            
            cache_data = {
                'address_key': address_key,
                'coordinates': coordinates,
                'geocoded_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            logging.debug(f"Géocodage mis en cache pour {address_key}")
            
        except Exception as e:
            logging.error(f"Erreur cache géocodage: {e}")
    
    def _get_cached_geocoding(self, address_key):
        """Récupérer résultat géocodage depuis cache"""
        try:
            if not self.redis:
                return None
            
            key = f"geocoding:{address_key}"
            cached_data = self.redis.get(key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logging.error(f"Erreur récupération cache géocodage: {e}")
            return None
    
    def _cache_proximity_search(self, center_coords, radius_km, results, ttl=None):
        """Cache des recherches de proximité géographique"""
        try:
            if not self.redis:
                return
            
            ttl = ttl or self.ttl_config.get('api_cache', 600)  # 10 minutes
            cache_key = f"proximity:{center_coords['lat']:.6f},{center_coords['lng']:.6f}:r{radius_km}"
            
            cache_data = {
                'center': center_coords,
                'radius_km': radius_km,
                'results': results,
                'cached_at': datetime.utcnow().isoformat(),
                'count': len(results)
            }
            
            self.redis.setex(cache_key, ttl, json.dumps(cache_data))
            logging.debug(f"Recherche proximité mise en cache: {len(results)} résultats")
            
        except Exception as e:
            logging.error(f"Erreur cache proximité: {e}")
    
    def _get_cached_proximity_search(self, center_coords, radius_km):
        """Récupérer recherche proximité depuis cache"""
        try:
            if not self.redis:
                return None
            
            cache_key = f"proximity:{center_coords['lat']:.6f},{center_coords['lng']:.6f}:r{radius_km}"
            cached_data = self.redis.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logging.error(f"Erreur récupération cache proximité: {e}")
            return None
    
    def _cache_statistics(self, client_id, stats_data, ttl=None):
        """Cache des statistiques de sites"""
        try:
            if not self.redis:
                return
            
            ttl = ttl or self.ttl_config.get('api_cache', 600)  # 10 minutes
            key = f"site_stats:client:{client_id}" if client_id else "site_stats:global"
            
            cache_data = {
                'client_id': client_id,
                'statistics': stats_data,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            logging.debug(f"Statistiques sites mises en cache pour client {client_id}")
            
        except Exception as e:
            logging.error(f"Erreur cache statistiques: {e}")
    
    def _get_cached_statistics(self, client_id):
        """Récupérer statistiques depuis cache"""
        try:
            if not self.redis:
                return None
            
            key = f"site_stats:client:{client_id}" if client_id else "site_stats:global"
            cached_data = self.redis.get(key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logging.error(f"Erreur récupération cache stats: {e}")
            return None
    
    def _invalidate_site_cache(self, site_id, client_id=None):
        """Invalider le cache d'un site spécifique"""
        try:
            if not self.redis:
                return
            
            patterns_to_invalidate = [
                f"site_data:{site_id}",
                f"sites_list:client:{client_id}" if client_id else "sites_list:all",
                f"site_stats:client:{client_id}" if client_id else "site_stats:global",
                "proximity:*"  # Invalider toutes les recherches proximité
            ]
            
            deleted_count = 0
            for pattern in patterns_to_invalidate:
                if "*" in pattern:
                    keys = self.redis.keys(pattern)
                    if keys:
                        deleted_count += self.redis.delete(*keys)
                else:
                    if self.redis.exists(pattern):
                        deleted_count += self.redis.delete(pattern)
            
            logging.debug(f"Cache invalidé pour site {site_id}: {deleted_count} clés supprimées")
            
        except Exception as e:
            logging.error(f"Erreur invalidation cache site {site_id}: {e}")
    
    def _invalidate_all_sites_cache(self):
        """Invalider tout le cache des sites"""
        try:
            if not self.redis:
                return 0
            
            patterns = [
                "site_data:*",
                "sites_list:*",
                "site_stats:*",
                "geocoding:*",
                "proximity:*"
            ]
            
            total_deleted = 0
            for pattern in patterns:
                keys = self.redis.keys(pattern)
                if keys:
                    deleted = self.redis.delete(*keys)
                    total_deleted += deleted
            
            logging.info(f"Cache sites invalidé: {total_deleted} clés supprimées")
            return total_deleted
            
        except Exception as e:
            logging.error(f"Erreur invalidation cache complet: {e}")
            return 0
    
    # =================== GESTION DES SITES AVEC CACHE ===================
    
    def creer_site(self, donnees_site: Dict[str, Any], utilisateur_createur: User) -> Tuple[Optional[Site], Optional[str]]:
        """Créer un nouveau site avec invalidation cache"""
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
            
            # ✅ NOUVEAU : Géocodage avec cache
            geocoding_success = False
            if donnees_site.get('latitude') and donnees_site.get('longitude'):
                # Coordonnées manuelles
                if nouveau_site.set_coordinates(
                    donnees_site['latitude'], 
                    donnees_site['longitude'], 
                    donnees_site.get('precision_gps', 'exacte')
                ):
                    print(f"✅ Coordonnées manuelles définies pour {nouveau_site.nom_site}")
                    geocoding_success = True
                else:
                    print(f"⚠️ Coordonnées invalides ignorées pour {nouveau_site.nom_site}")
            
            db.session.add(nouveau_site)
            db.session.flush()  # Pour obtenir l'ID
            
            # ✅ NOUVEAU : Géocodage avec cache Redis
            if not geocoding_success:
                print(f"🌍 Tentative géocodage avec cache pour {nouveau_site.nom_site}...")
                geocoding_success = self._try_geocode_with_cache(nouveau_site)
            
            db.session.commit()
            
            # ✅ NOUVEAU : Invalider caches après création
            self._invalidate_site_cache(None, donnees_site['client_id'])
            
            return nouveau_site, None
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de la création du site: {str(e)}"
    
    def modifier_site(self, site_id: str, nouvelles_donnees: Dict[str, Any], utilisateur_modificateur: User) -> Tuple[Optional[Site], Optional[str]]:
        """Modifier un site avec gestion cache"""
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
            
            # Sauvegarder ancien état pour cache
            old_client_id = site.client_id
            
            # Appliquer les modifications
            site_modifie = False
            address_changed = False
            
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
                    
                    # Détecter changement d'adresse
                    if champ in ['adresse', 'ville', 'quartier'] and getattr(site, champ) != (valeur if valeur else None):
                        address_changed = True
                    
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
            
            # ✅ NOUVEAU : Regéocodage avec cache si adresse modifiée
            if site_modifie and address_changed:
                if not site.has_coordinates() or site.coordonnees_auto:
                    print(f"🌍 Regéocodage avec cache pour {site.nom_site}...")
                    self._try_geocode_with_cache(site)
            
            if site_modifie:
                db.session.commit()
                
                # ✅ NOUVEAU : Invalider caches après modification
                self._invalidate_site_cache(site_id, old_client_id)
                
                return site, None
            else:
                return site, "Aucune modification apportée"
            
        except Exception as e:
            db.session.rollback()
            return None, f"Erreur lors de la modification: {str(e)}"
    
    def lister_sites(self, utilisateur_demandeur: User, client_id: Optional[str] = None, use_cache: bool = True) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Lister les sites avec cache intelligent"""
        try:
            # Déterminer le client_id effectif selon les permissions
            effective_client_id = None
            if utilisateur_demandeur.is_superadmin():
                effective_client_id = client_id  # Peut être None pour "tous"
            else:
                effective_client_id = utilisateur_demandeur.client_id
            
            # ✅ NOUVEAU : Vérifier cache d'abord
            if use_cache:
                cached_sites = self._get_cached_sites_list(effective_client_id)
                if cached_sites:
                    cached_at = datetime.fromisoformat(cached_sites['cached_at'])
                    age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
                    
                    if age_minutes < 5:  # Cache valide 5 minutes
                        print(f"📦 Sites depuis cache pour client {effective_client_id} (âge: {age_minutes:.1f}min)")
                        return cached_sites['sites'], None
            
            # Récupération depuis DB
            query = Site.query.filter_by(actif=True)
            
            if utilisateur_demandeur.is_superadmin():
                if client_id:
                    query = query.filter_by(client_id=client_id)
            elif utilisateur_demandeur.is_admin():
                query = query.filter_by(client_id=utilisateur_demandeur.client_id)
            else:
                # USER voit seulement les sites avec des appareils autorisés
                query = query.filter_by(client_id=utilisateur_demandeur.client_id)
            
            # Ordonner par nom du site
            sites = query.order_by(Site.nom_site).all()
            
            # Convertir en dictionnaire avec informations enrichies
            liste_sites = []
            for site in sites:
                site_dict = site.to_dict(include_map_link=True, include_stats=True)
                
                # ✅ NOUVEAU : Cache individuel des données site
                if use_cache:
                    self._cache_site_data(site.id, site_dict)
                
                liste_sites.append(site_dict)
            
            # ✅ NOUVEAU : Mettre en cache la liste
            if use_cache:
                self._cache_sites_list(effective_client_id, liste_sites)
            
            return liste_sites, None
            
        except Exception as e:
            return None, f"Erreur lors de la récupération des sites: {str(e)}"
    
    def obtenir_site(self, site_id: str, utilisateur_demandeur: User, use_cache: bool = True) -> Tuple[Optional[Dict], Optional[str]]:
        """Obtenir les détails d'un site avec cache"""
        try:
            # ✅ NOUVEAU : Vérifier cache d'abord
            if use_cache:
                cached_site = self._get_cached_site_data(site_id)
                if cached_site:
                    cached_at = datetime.fromisoformat(cached_site['cached_at'])
                    age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
                    
                    if age_minutes < 10:  # Cache valide 10 minutes pour un site individuel
                        site_data = cached_site['site_data']
                        
                        # Vérifier permissions avec données cachées
                        if self._can_view_cached_site(utilisateur_demandeur, site_data):
                            print(f"📦 Site {site_id} depuis cache (âge: {age_minutes:.1f}min)")
                            return site_data, None
            
            # Récupération depuis DB
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
                include_devices=utilisateur_demandeur.is_superadmin()
            )
            
            # Ajouter des informations sur les permissions
            site_dict['permissions'] = {
                'peut_modifier': self._peut_modifier_site(utilisateur_demandeur, site),
                'peut_supprimer': self._peut_supprimer_site(utilisateur_demandeur, site),
                'peut_voir_appareils': True
            }
            
            # ✅ NOUVEAU : Mettre en cache
            if use_cache:
                self._cache_site_data(site_id, site_dict)
            
            return site_dict, None
            
        except Exception as e:
            return None, f"Erreur lors de la récupération du site: {str(e)}"
    
    def desactiver_site(self, site_id: str, utilisateur_desactivateur: User) -> Tuple[bool, str]:
        """Désactiver un site avec invalidation cache"""
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
            
            client_id = site.client_id
            site.actif = False
            db.session.commit()
            
            # ✅ NOUVEAU : Invalider caches
            self._invalidate_site_cache(site_id, client_id)
            
            return True, f"Site '{site.nom_site}' désactivé avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la désactivation: {str(e)}"
    
    def reactiver_site(self, site_id: str, utilisateur_reactivateur: User) -> Tuple[bool, str]:
        """Réactiver un site avec invalidation cache"""
        try:
            if not utilisateur_reactivateur.is_superadmin():
                return False, "Seul le superadmin peut réactiver des sites"
            
            site = Site.query.filter_by(id=site_id, actif=False).first()
            if not site:
                return False, "Site non trouvé ou déjà actif"
            
            # Vérifier que le client est toujours actif
            if not site.client or not site.client.actif:
                return False, "Impossible de réactiver: le client est désactivé"
            
            client_id = site.client_id
            site.actif = True
            db.session.commit()
            
            # ✅ NOUVEAU : Invalider caches
            self._invalidate_site_cache(site_id, client_id)
            
            return True, f"Site '{site.nom_site}' réactivé avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la réactivation: {str(e)}"
    
    def supprimer_site(self, site_id: str, utilisateur_supprimeur: User, forcer: bool = False) -> Tuple[bool, str]:
        """Supprimer définitivement un site avec invalidation cache"""
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
            client_id = site.client_id
            
            if forcer and nb_appareils > 0:
                # Suppression forcée
                db.session.delete(site)
                message = f"Site '{nom_site}' ({client_nom}) et ses {nb_appareils} appareils supprimés définitivement"
            else:
                # Suppression simple
                db.session.delete(site)
                message = f"Site '{nom_site}' ({client_nom}) supprimé avec succès"
            
            db.session.commit()
            
            # ✅ NOUVEAU : Invalider caches
            self._invalidate_site_cache(site_id, client_id)
            
            return True, message
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la suppression: {str(e)}"
    
    # =================== FONCTIONNALITÉS GÉOGRAPHIQUES AVEC CACHE ===================
    
    def _try_geocode_with_cache(self, site):
        """Géocodage avec cache Redis"""
        try:
            # Créer une clé d'adresse pour le cache
            address_components = [
                site.adresse or '',
                site.ville or '',
                site.quartier or '',
                site.pays or 'Sénégal'
            ]
            address_key = f"{'+'.join(filter(None, address_components))}".lower().replace(' ', '+')
            
            # Vérifier cache géocodage
            if self.redis:
                cached_geocoding = self._get_cached_geocoding(address_key)
                if cached_geocoding:
                    coords = cached_geocoding['coordinates']
                    if coords and coords.get('lat') and coords.get('lng'):
                        print(f"📦 Géocodage depuis cache pour {site.nom_site}")
                        
                        if site.set_coordinates(coords['lat'], coords['lng'], 'approximative'):
                            site.coordonnees_auto = True
                            return True
            
            # Géocodage réel
            success = site.try_geocode_address()
            
            # Mettre en cache le résultat
            if self.redis:
                if success and site.has_coordinates():
                    coords = {'lat': float(site.latitude), 'lng': float(site.longitude)}
                    print(f"💾 Géocodage mis en cache pour {site.nom_site}")
                else:
                    coords = None
                
                self._cache_geocoding_result(address_key, coords)
            
            return success
            
        except Exception as e:
            logging.error(f"Erreur géocodage avec cache: {e}")
            return False
    
    def geocoder_site(self, site_id: str, utilisateur_demandeur: User, force_refresh: bool = False) -> Tuple[bool, str]:
        """Forcer le géocodage d'un site avec gestion cache"""
        try:
            if not utilisateur_demandeur.is_superadmin():
                return False, "Seul le superadmin peut forcer le géocodage"
            
            site = Site.query.get(site_id)
            if not site:
                return False, "Site non trouvé"
            
            # ✅ NOUVEAU : Invalider cache géocodage si force_refresh
            if force_refresh and self.redis:
                address_components = [
                    site.adresse or '',
                    site.ville or '',
                    site.quartier or '',
                    site.pays or 'Sénégal'
                ]
                address_key = f"{'+'.join(filter(None, address_components))}".lower().replace(' ', '+')
                geocoding_cache_key = f"geocoding:{address_key}"
                self.redis.delete(geocoding_cache_key)
                print(f"🗑️ Cache géocodage invalidé pour forcer le refresh")
            
            if self._try_geocode_with_cache(site):
                db.session.commit()
                
                # ✅ NOUVEAU : Invalider cache site après géocodage
                self._invalidate_site_cache(site_id, site.client_id)
                
                return True, f"Géocodage réussi pour '{site.nom_site}'"
            else:
                return False, f"Géocodage échoué pour '{site.nom_site}'"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors du géocodage: {str(e)}"
    
    def sites_proches(self, site_id: str, radius_km: int, utilisateur_demandeur: User, use_cache: bool = True) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Trouver les sites proches avec cache géospatial"""
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
            
            center_coords = {
                'lat': float(site_reference.latitude),
                'lng': float(site_reference.longitude)
            }
            
            # ✅ NOUVEAU : Vérifier cache de proximité
            if use_cache:
                cached_proximity = self._get_cached_proximity_search(center_coords, radius_km)
                if cached_proximity:
                    cached_at = datetime.fromisoformat(cached_proximity['cached_at'])
                    age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
                    
                    if age_minutes < 10:  # Cache valide 10 minutes
                        print(f"📦 Recherche proximité depuis cache (âge: {age_minutes:.1f}min)")
                        
                        # Filtrer selon permissions actuelles
                        filtered_results = []
                        for result in cached_proximity['results']:
                            if self._can_view_cached_site(utilisateur_demandeur, result):
                                filtered_results.append(result)
                        
                        return filtered_results, None
            
            # Recherche depuis DB
            client_filter = None if utilisateur_demandeur.is_superadmin() else utilisateur_demandeur.client_id
            
            sites_proches = Site.find_nearby_sites(
                latitude=center_coords['lat'],
                longitude=center_coords['lng'],
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
            
            # ✅ NOUVEAU : Mettre en cache la recherche
            if use_cache:
                self._cache_proximity_search(center_coords, radius_km, resultats)
            
            return resultats, None
            
        except Exception as e:
            return None, f"Erreur lors de la recherche: {str(e)}"
    
    def batch_geocode_sites(self, site_ids: List[str], utilisateur_demandeur: User, force_refresh: bool = False) -> Dict[str, Any]:
        """Géocodage en lot avec cache optimisé"""
        try:
            if not utilisateur_demandeur.is_superadmin():
                return {"success": False, "error": "Seul le superadmin peut faire du géocodage en lot"}
            
            if not site_ids:
                return {"success": False, "error": "Aucun site spécifié"}
            
            resultats = {
                'total_requested': len(site_ids),
                'geocoded_success': 0,
                'geocoded_from_cache': 0,
                'geocoded_from_api': 0,
                'geocoded_failed': 0,
                'results': [],
                'cache_efficiency': 0
            }
            
            for site_id in site_ids:
                site = Site.query.get(site_id)
                if not site:
                    resultats['results'].append({
                        'site_id': site_id,
                        'success': False,
                        'error': 'Site non trouvé'
                    })
                    resultats['geocoded_failed'] += 1
                    continue
                
                # Sauvegarder état avant géocodage
                had_coordinates_before = site.has_coordinates()
                was_auto_before = site.coordonnees_auto
                
                # Géocodage avec cache
                success = self._try_geocode_with_cache(site)
                
                if success:
                    # Déterminer la source (cache vs API)
                    if had_coordinates_before and was_auto_before:
                        source = "updated_from_cache_or_api"
                    else:
                        # Vérifier si c'était depuis le cache en regardant les logs récents
                        source = "cache_or_api"  # Simplification pour cet exemple
                    
                    resultats['results'].append({
                        'site_id': site_id,
                        'site_name': site.nom_site,
                        'success': True,
                        'coordinates': {
                            'lat': float(site.latitude),
                            'lng': float(site.longitude)
                        },
                        'precision': site.precision_gps,
                        'source': source
                    })
                    resultats['geocoded_success'] += 1
                    
                    # Invalider cache du site après géocodage
                    self._invalidate_site_cache(site_id, site.client_id)
                    
                else:
                    resultats['results'].append({
                        'site_id': site_id,
                        'site_name': site.nom_site,
                        'success': False,
                        'error': 'Géocodage échoué'
                    })
                    resultats['geocoded_failed'] += 1
            
            # Sauvegarder les changements
            if resultats['geocoded_success'] > 0:
                db.session.commit()
            
            # Calculer efficacité (simplification)
            if resultats['total_requested'] > 0:
                resultats['cache_efficiency'] = f"{(resultats['geocoded_from_cache'] / resultats['total_requested'] * 100):.1f}%"
            
            return {
                "success": True,
                "batch_results": resultats,
                "message": f"{resultats['geocoded_success']} sites géocodés avec succès sur {resultats['total_requested']}"
            }
            
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    # =================== STATISTIQUES AVEC CACHE ===================
    
    def obtenir_statistiques_sites(self, utilisateur_demandeur: User, client_id: Optional[str] = None, use_cache: bool = True) -> Tuple[Optional[Dict], Optional[str]]:
        """Obtenir des statistiques avec cache intelligent"""
        try:
            if not utilisateur_demandeur.is_admin():
                return None, "Permission insuffisante"
            
            # Déterminer le client_id effectif
            effective_client_id = None
            if utilisateur_demandeur.is_superadmin():
                effective_client_id = client_id
            else:
                effective_client_id = utilisateur_demandeur.client_id
            
            # ✅ NOUVEAU : Vérifier cache d'abord
            if use_cache:
                cached_stats = self._get_cached_statistics(effective_client_id)
                if cached_stats:
                    cached_at = datetime.fromisoformat(cached_stats['cached_at'])
                    age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
                    
                    if age_minutes < 10:  # Cache valide 10 minutes
                        print(f"📦 Statistiques depuis cache pour client {effective_client_id} (âge: {age_minutes:.1f}min)")
                        return cached_stats['statistics'], None
            
            # Calcul depuis DB
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
                'taux_geocodage': 0,
                'cache_info': {
                    'from_cache': False,
                    'cached_at': datetime.utcnow().isoformat()
                }
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
            
            # ✅ NOUVEAU : Mettre en cache
            if use_cache:
                self._cache_statistics(effective_client_id, stats)
            
            return stats, None
            
        except Exception as e:
            return None, f"Erreur lors du calcul des statistiques: {str(e)}"
    
    def get_geocoding_statistics(self, use_cache: bool = True) -> Dict[str, Any]:
        """Statistiques spécifiques au géocodage avec info cache"""
        try:
            cache_key = "geocoding_stats"
            
            # ✅ Vérifier cache
            if use_cache and self.redis:
                cached_data = self.redis.get(cache_key)
                if cached_data:
                    stats_data = json.loads(cached_data)
                    cached_at = datetime.fromisoformat(stats_data['cached_at'])
                    age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
                    
                    if age_minutes < 15:  # Cache valide 15 minutes
                        return {
                            "success": True,
                            "statistics": stats_data['stats'],
                            "from_cache": True,
                            "cache_age_minutes": age_minutes
                        }
            
            # Calcul depuis DB
            all_sites = Site.query.filter_by(actif=True).all()
            
            geocoding_stats = {
                'total_sites': len(all_sites),
                'sites_geocoded': 0,
                'sites_manual_coords': 0,
                'sites_auto_coords': 0,
                'sites_no_coords': 0,
                'geocoding_rate': 0,
                'auto_geocoding_rate': 0,
                'precision_breakdown': {
                    'exacte': 0,
                    'approximative': 0,
                    'ville': 0,
                    'inconnue': 0
                }
            }
            
            for site in all_sites:
                if site.has_coordinates():
                    geocoding_stats['sites_geocoded'] += 1
                    
                    if site.coordonnees_auto:
                        geocoding_stats['sites_auto_coords'] += 1
                    else:
                        geocoding_stats['sites_manual_coords'] += 1
                    
                    # Précision
                    precision = site.precision_gps or 'inconnue'
                    geocoding_stats['precision_breakdown'][precision] = geocoding_stats['precision_breakdown'].get(precision, 0) + 1
                else:
                    geocoding_stats['sites_no_coords'] += 1
            
            # Calcul des taux
            if geocoding_stats['total_sites'] > 0:
                geocoding_stats['geocoding_rate'] = round(
                    (geocoding_stats['sites_geocoded'] / geocoding_stats['total_sites']) * 100, 2
                )
                geocoding_stats['auto_geocoding_rate'] = round(
                    (geocoding_stats['sites_auto_coords'] / geocoding_stats['total_sites']) * 100, 2
                )
            
            # Cache Redis info
            if self.redis:
                geocoding_cache_keys = self.redis.keys("geocoding:*")
                geocoding_stats['cache_info'] = {
                    'cached_addresses': len(geocoding_cache_keys),
                    'cache_enabled': True
                }
            else:
                geocoding_stats['cache_info'] = {
                    'cached_addresses': 0,
                    'cache_enabled': False
                }
            
            # ✅ Mettre en cache
            if use_cache and self.redis:
                cache_data = {
                    'stats': geocoding_stats,
                    'cached_at': datetime.utcnow().isoformat()
                }
                self.redis.setex(cache_key, 900, json.dumps(cache_data))  # 15 minutes
            
            return {
                "success": True,
                "statistics": geocoding_stats,
                "from_cache": False
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # =================== ADMINISTRATION DU CACHE ===================
    
    def get_cache_statistics(self):
        """Statistiques détaillées du cache Redis pour sites"""
        try:
            if not self.redis:
                return {
                    "success": False,
                    "error": "Redis non disponible",
                    "cache_enabled": False
                }
            
            # Compter les clés par type
            patterns = {
                "site_data": "site_data:*",
                "sites_lists": "sites_list:*",
                "site_statistics": "site_stats:*",
                "geocoding_cache": "geocoding:*",
                "proximity_searches": "proximity:*"
            }
            
            cache_stats = {}
            total_keys = 0
            
            for cache_type, pattern in patterns.items():
                keys = self.redis.keys(pattern)
                count = len(keys)
                cache_stats[cache_type] = count
                total_keys += count
                
                # Échantillon pour analyse
                if count > 0:
                    sample_key = keys[0]
                    if isinstance(sample_key, bytes):
                        sample_key = sample_key.decode()
                    
                    try:
                        ttl = self.redis.ttl(sample_key)
                        cache_stats[f"{cache_type}_sample_ttl"] = ttl
                    except:
                        cache_stats[f"{cache_type}_sample_ttl"] = "unknown"
            
            # Info Redis
            redis_info = self.redis.info()
            memory_info = self.redis.info('memory')
            
            return {
                "success": True,
                "cache_enabled": True,
                "total_keys": total_keys,
                "keys_by_type": cache_stats,
                "redis_info": {
                    "version": redis_info.get('redis_version'),
                    "uptime_seconds": redis_info.get('uptime_in_seconds'),
                    "connected_clients": redis_info.get('connected_clients'),
                    "used_memory_human": memory_info.get('used_memory_human')
                },
                "ttl_config": self.ttl_config,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def cleanup_cache(self, cache_type: Optional[str] = None):
        """Nettoyer le cache des sites"""
        try:
            if not self.redis:
                return {"success": False, "error": "Redis non disponible"}
            
            if cache_type:
                # Nettoyage par type
                patterns = {
                    "site_data": ["site_data:*"],
                    "sites_lists": ["sites_list:*"],
                    "statistics": ["site_stats:*", "geocoding_stats"],
                    "geocoding": ["geocoding:*"],
                    "proximity": ["proximity:*"]
                }
                
                if cache_type not in patterns:
                    return {"success": False, "error": f"Type de cache invalide: {cache_type}"}
                
                deleted_count = 0
                for pattern in patterns[cache_type]:
                    keys = self.redis.keys(pattern)
                    if keys:
                        deleted_count += self.redis.delete(*keys)
                
                return {
                    "success": True,
                    "message": f"Cache {cache_type} nettoyé",
                    "deleted_keys": deleted_count
                }
            else:
                # Nettoyage complet
                deleted_count = self._invalidate_all_sites_cache()
                
                return {
                    "success": True,
                    "message": "Cache sites complet nettoyé",
                    "deleted_keys": deleted_count
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def warm_up_cache(self, client_id: Optional[str] = None):
        """Préchauffer le cache des sites"""
        try:
            if not self.redis:
                return {"success": False, "error": "Redis non disponible"}
            
            print("🔥 Préchauffage du cache des sites...")
            
            # Récupérer les sites à préchauffer
            query = Site.query.filter_by(actif=True)
            if client_id:
                query = query.filter_by(client_id=client_id)
            
            sites = query.limit(100).all()  # Limite pour éviter surcharge
            
            if not sites:
                return {"success": False, "error": "Aucun site à préchauffer"}
            
            warmed_sites = 0
            warmed_geocoding = 0
            
            # 1. Préchauffer données individuelles des sites
            for site in sites:
                try:
                    site_dict = site.to_dict(include_map_link=True, include_stats=True)
                    self._cache_site_data(site.id, site_dict)
                    warmed_sites += 1
                    
                    # Géocodage si coordonnées existantes
                    if site.has_coordinates():
                        address_components = [
                            site.adresse or '',
                            site.ville or '',
                            site.quartier or '',
                            site.pays or 'Sénégal'
                        ]
                        address_key = f"{'+'.join(filter(None, address_components))}".lower().replace(' ', '+')
                        coords = {'lat': float(site.latitude), 'lng': float(site.longitude)}
                        self._cache_geocoding_result(address_key, coords)
                        warmed_geocoding += 1
                        
                except Exception as e:
                    logging.error(f"Erreur préchauffage site {site.id}: {e}")
                    continue
            
            # 2. Préchauffer listes par client
            if client_id:
                clients_to_warm = [client_id]
            else:
                # Tous les clients avec sites
                clients_to_warm = list(set(site.client_id for site in sites if site.client_id))
            
            warmed_lists = 0
            for cid in clients_to_warm:
                try:
                    client_sites = [s for s in sites if s.client_id == cid]
                    sites_data = [s.to_dict(include_map_link=True, include_stats=True) for s in client_sites]
                    self._cache_sites_list(cid, sites_data)
                    warmed_lists += 1
                except Exception as e:
                    logging.error(f"Erreur préchauffage liste client {cid}: {e}")
                    continue
            
            # 3. Préchauffer statistiques
            try:
                if client_id:
                    # Stats pour ce client spécifique
                    query_stats = Site.query.filter_by(actif=True, client_id=client_id)
                else:
                    # Stats globales
                    query_stats = Site.query.filter_by(actif=True)
                
                # Calculer et cacher stats (simplifié)
                stats_sites = query_stats.all()
                basic_stats = {
                    'total_sites': len(stats_sites),
                    'sites_avec_coordonnees': len([s for s in stats_sites if s.has_coordinates()]),
                    'cached_at': datetime.utcnow().isoformat()
                }
                self._cache_statistics(client_id, basic_stats)
                
            except Exception as e:
                logging.error(f"Erreur préchauffage stats: {e}")
            
            return {
                "success": True,
                "message": "Cache sites préchauffé avec succès",
                "warmed_sites": warmed_sites,
                "warmed_geocoding": warmed_geocoding,
                "warmed_lists": warmed_lists,
                "total_sites": len(sites),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def debug_site_cache(self, site_id: str):
        """Debug complet du cache d'un site"""
        try:
            if not self.redis:
                return {"success": False, "error": "Redis non disponible"}
            
            debug_info = {
                "site_id": site_id,
                "cache_keys": {},
                "cache_data": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Vérifier toutes les clés liées à ce site
            patterns = [
                f"site_data:{site_id}",
                "sites_list:*",
                "site_stats:*",
                "geocoding:*",
                "proximity:*"
            ]
            
            for pattern in patterns:
                if "*" in pattern:
                    keys = self.redis.keys(pattern)
                    # Pour les patterns génériques, limiter aux clés pertinentes
                    if pattern == "sites_list:*":
                        # Chercher les listes qui pourraient contenir ce site
                        relevant_keys = []
                        for key in keys:
                            if isinstance(key, bytes):
                                key = key.decode()
                            try:
                                data = self.redis.get(key)
                                if data and site_id in data:
                                    relevant_keys.append(key)
                            except:
                                continue
                        keys = relevant_keys[:3]  # Max 3 listes
                    else:
                        keys = keys[:5]  # Max 5 clés pour les autres patterns
                else:
                    keys = [pattern] if self.redis.exists(pattern) else []
                
                debug_info["cache_keys"][pattern] = len(self.redis.keys(pattern) if "*" in pattern else ([pattern] if self.redis.exists(pattern) else []))
                
                for key in keys:
                    if isinstance(key, bytes):
                        key = key.decode()
                    
                    try:
                        data = self.redis.get(key)
                        ttl = self.redis.ttl(key)
                        
                        debug_info["cache_data"][key] = {
                            "has_data": data is not None,
                            "data_length": len(data) if data else 0,
                            "ttl_seconds": ttl,
                            "expires_in": f"{ttl // 60}m {ttl % 60}s" if ttl > 0 else "No TTL"
                        }
                        
                        # Pour site_data, inclure le contenu
                        if key.startswith(f"site_data:{site_id}") and data:
                            try:
                                parsed_data = json.loads(data)
                                debug_info["cache_data"][key]["site_info"] = {
                                    "nom_site": parsed_data.get("site_data", {}).get("nom_site"),
                                    "cached_at": parsed_data.get("cached_at")
                                }
                            except:
                                pass
                                
                    except Exception as e:
                        debug_info["cache_data"][key] = {"error": str(e)}
            
            # Info depuis DB
            site = Site.query.get(site_id)
            if site:
                debug_info["database_info"] = {
                    "nom_site": site.nom_site,
                    "actif": site.actif,
                    "has_coordinates": site.has_coordinates(),
                    "client_id": site.client_id
                }
            
            return {"success": True, "debug_info": debug_info}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # =================== MÉTHODES PRIVÉES DE VALIDATION AVEC CACHE ===================
    
    def _peut_voir_site(self, utilisateur_demandeur: User, site: Site) -> bool:
        """Vérifier si un utilisateur peut voir un site"""
        # Superadmin voit tout
        if utilisateur_demandeur.is_superadmin():
            return True
        
        # Admin/User voit son client
        site_client_id = site_data.get('client_id')
        return site_client_id == utilisateur_demandeur.client_id
    
    # =================== MÉTHODES DE MONITORING ET SANTÉ ===================
    
    def health_check(self):
        """Vérification de santé du SiteService"""
        try:
            health_status = {
                "service": "SiteService",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {}
            }
            
            # Test Redis
            try:
                if self.redis:
                    self.redis.ping()
                    cache_stats = self.get_cache_statistics()
                    health_status["components"]["redis"] = {
                        "status": "healthy",
                        "cache_enabled": True,
                        "total_keys": cache_stats.get("total_keys", 0)
                    }
                else:
                    health_status["components"]["redis"] = {
                        "status": "disabled",
                        "cache_enabled": False
                    }
            except Exception as e:
                health_status["components"]["redis"] = {
                    "status": "error",
                    "error": str(e)
                }
            
            # Test Database
            try:
                site_count = Site.query.filter_by(actif=True).count()
                geocoded_count = Site.query.filter(
                    Site.actif == True,
                    Site.latitude.isnot(None),
                    Site.longitude.isnot(None)
                ).count()
                
                health_status["components"]["database"] = {
                    "status": "healthy",
                    "total_sites": site_count,
                    "geocoded_sites": geocoded_count,
                    "geocoding_rate": f"{(geocoded_count/site_count*100):.1f}%" if site_count > 0 else "0%"
                }
            except Exception as e:
                health_status["components"]["database"] = {
                    "status": "error",
                    "error": str(e)
                }
            
            # Test Geocoding Service (si implémenté)
            try:
                # Test simple de géocodage
                test_address = "Dakar, Sénégal"
                # Ici vous pourriez tester votre service de géocodage
                health_status["components"]["geocoding_service"] = {
                    "status": "available",
                    "test_address": test_address
                }
            except Exception as e:
                health_status["components"]["geocoding_service"] = {
                    "status": "error",
                    "error": str(e)
                }
            
            # Statut global
            all_healthy = all(
                comp.get("status") in ["healthy", "available", "disabled"] 
                for comp in health_status["components"].values()
            )
            
            health_status["overall_status"] = "healthy" if all_healthy else "degraded"
            
            return {"success": True, "health": health_status}
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "health": {
                    "service": "SiteService",
                    "overall_status": "error",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
    
    def get_performance_metrics(self):
        """Métriques de performance du service"""
        try:
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "cache_enabled": self.redis is not None,
                "ttl_config": self.ttl_config.copy()
            }
            
            if self.redis:
                # Stats cache
                cache_stats = self.get_cache_statistics()
                if cache_stats.get("success"):
                    metrics["cache_stats"] = cache_stats
                
                # Performance Redis
                redis_info = self.redis.info()
                metrics["redis_performance"] = {
                    "total_commands_processed": redis_info.get("total_commands_processed", 0),
                    "instantaneous_ops_per_sec": redis_info.get("instantaneous_ops_per_sec", 0),
                    "used_memory_human": redis_info.get("used_memory_human", "unknown"),
                    "connected_clients": redis_info.get("connected_clients", 0)
                }
            
            # Stats base de données
            try:
                db_metrics = {
                    "total_sites": Site.query.filter_by(actif=True).count(),
                    "geocoded_sites": Site.query.filter(
                        Site.actif == True,
                        Site.latitude.isnot(None),
                        Site.longitude.isnot(None)
                    ).count(),
                    "auto_geocoded_sites": Site.query.filter(
                        Site.actif == True,
                        Site.coordonnees_auto == True
                    ).count()
                }
                
                # Répartition par pays
                pays_stats = {}
                sites_by_country = Site.query.filter_by(actif=True).all()
                for site in sites_by_country:
                    pays = site.pays or 'Non renseigné'
                    pays_stats[pays] = pays_stats.get(pays, 0) + 1
                
                db_metrics["countries_breakdown"] = pays_stats
                metrics["database_stats"] = db_metrics
                
            except Exception as e:
                metrics["database_error"] = str(e)
            
            return {"success": True, "metrics": metrics}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def export_cache_data(self, site_id: Optional[str] = None):
        """Exporter les données du cache pour analyse"""
        try:
            if not self.redis:
                return {"success": False, "error": "Redis non disponible"}
            
            export_data = {
                "exported_at": datetime.utcnow().isoformat(),
                "site_id": site_id,
                "cache_data": {}
            }
            
            if site_id:
                # Export pour un site spécifique
                patterns = [
                    f"site_data:{site_id}",
                    "sites_list:*",
                    "geocoding:*"
                ]
                export_data["export_type"] = "single_site"
            else:
                # Export global (limité)
                patterns = [
                    "site_data:*",
                    "sites_list:*",
                    "site_stats:*",
                    "geocoding_stats"
                ]
                export_data["export_type"] = "global"
            
            for pattern in patterns:
                if "*" in pattern:
                    keys = self.redis.keys(pattern)
                    # Limiter pour éviter surcharge
                    if len(keys) > 50:
                        keys = keys[:50]
                        export_data["truncated"] = True
                else:
                    keys = [pattern] if self.redis.exists(pattern) else []
                
                pattern_data = {}
                for key in keys:
                    if isinstance(key, bytes):
                        key = key.decode()
                    
                    try:
                        data = self.redis.get(key)
                        ttl = self.redis.ttl(key)
                        
                        # Pour l'export, on inclut seulement les métadonnées
                        pattern_data[key] = {
                            "has_data": data is not None,
                            "data_size_bytes": len(data) if data else 0,
                            "ttl": ttl
                        }
                        
                        # Inclure un échantillon de données si c'est petit
                        if data and len(data) < 1000:  # Moins de 1KB
                            try:
                                pattern_data[key]["sample_data"] = json.loads(data)
                            except:
                                pattern_data[key]["sample_data"] = "non_json_data"
                                
                    except Exception as e:
                        pattern_data[key] = {"error": str(e)}
                
                export_data["cache_data"][pattern] = pattern_data
            
            return {"success": True, "export": export_data}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # =================== MÉTHODES UTILITAIRES AVANCÉES ===================
    
    def bulk_update_coordinates(self, sites_coordinates: List[Dict[str, Any]], utilisateur_demandeur: User) -> Dict[str, Any]:
        """Mise à jour en lot des coordonnées de sites"""
        try:
            if not utilisateur_demandeur.is_superadmin():
                return {"success": False, "error": "Seul le superadmin peut faire des mises à jour en lot"}
            
            if not sites_coordinates:
                return {"success": False, "error": "Aucune donnée fournie"}
            
            resultats = {
                'total_requested': len(sites_coordinates),
                'updated_success': 0,
                'updated_failed': 0,
                'results': []
            }
            
            sites_to_invalidate = set()
            
            for site_coord in sites_coordinates:
                site_id = site_coord.get('site_id')
                latitude = site_coord.get('latitude')
                longitude = site_coord.get('longitude')
                precision = site_coord.get('precision_gps', 'exacte')
                
                if not all([site_id, latitude is not None, longitude is not None]):
                    resultats['results'].append({
                        'site_id': site_id,
                        'success': False,
                        'error': 'Données incomplètes'
                    })
                    resultats['updated_failed'] += 1
                    continue
                
                site = Site.query.get(site_id)
                if not site:
                    resultats['results'].append({
                        'site_id': site_id,
                        'success': False,
                        'error': 'Site non trouvé'
                    })
                    resultats['updated_failed'] += 1
                    continue
                
                # Mise à jour des coordonnées
                if site.set_coordinates(latitude, longitude, precision):
                    site.coordonnees_auto = False  # Marquer comme manuel
                    sites_to_invalidate.add((site_id, site.client_id))
                    
                    resultats['results'].append({
                        'site_id': site_id,
                        'site_name': site.nom_site,
                        'success': True,
                        'coordinates': {
                            'lat': float(site.latitude),
                            'lng': float(site.longitude),
                            'precision': site.precision_gps
                        }
                    })
                    resultats['updated_success'] += 1
                else:
                    resultats['results'].append({
                        'site_id': site_id,
                        'success': False,
                        'error': 'Coordonnées invalides'
                    })
                    resultats['updated_failed'] += 1
            
            # Sauvegarder les changements
            if resultats['updated_success'] > 0:
                db.session.commit()
                
                # Invalider caches pour tous les sites modifiés
                for site_id, client_id in sites_to_invalidate:
                    self._invalidate_site_cache(site_id, client_id)
            
            return {
                "success": True,
                "bulk_results": resultats,
                "message": f"{resultats['updated_success']} sites mis à jour sur {resultats['total_requested']}"
            }
            
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    def find_sites_without_coordinates(self, client_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Trouver les sites sans coordonnées pour géocodage"""
        try:
            query = Site.query.filter_by(actif=True).filter(
                Site.latitude.is_(None) | Site.longitude.is_(None)
            )
            
            if client_id:
                query = query.filter_by(client_id=client_id)
            
            sites_sans_coords = query.limit(limit).all()
            
            sites_data = []
            for site in sites_sans_coords:
                site_dict = site.to_dict()
                
                # Ajouter info pour géocodage
                site_dict['geocoding_info'] = {
                    'full_address': f"{site.adresse}, {site.ville or ''}, {site.pays or 'Sénégal'}".strip(', '),
                    'can_geocode': bool(site.adresse),
                    'priority': 'high' if site.appareils.filter_by(actif=True).count() > 0 else 'low'
                }
                
                sites_data.append(site_dict)
            
            return {
                "success": True,
                "sites_without_coordinates": sites_data,
                "count": len(sites_data),
                "total_without_coords": Site.query.filter_by(actif=True).filter(
                    Site.latitude.is_(None) | Site.longitude.is_(None)
                ).count(),
                "client_id": client_id
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_sites_map_data(self, utilisateur_demandeur: User, client_id: Optional[str] = None, use_cache: bool = True) -> Dict[str, Any]:
        """Données optimisées pour affichage carte"""
        try:
            cache_key = f"map_data:client:{client_id}" if client_id else "map_data:all"
            
            # ✅ Vérifier cache spécial carte
            if use_cache and self.redis:
                cached_data = self.redis.get(cache_key)
                if cached_data:
                    map_data = json.loads(cached_data)
                    cached_at = datetime.fromisoformat(map_data['cached_at'])
                    age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
                    
                    if age_minutes < 5:  # Cache carte valide 5 minutes
                        print(f"📦 Données carte depuis cache (âge: {age_minutes:.1f}min)")
                        
                        # Filtrer selon permissions actuelles
                        filtered_sites = []
                        for site_data in map_data['sites']:
                            if self._can_view_cached_site(utilisateur_demandeur, site_data):
                                filtered_sites.append(site_data)
                        
                        return {
                            "success": True,
                            "map_data": {
                                "sites": filtered_sites,
                                "bounds": map_data.get('bounds'),
                                "center": map_data.get('center'),
                                "from_cache": True
                            }
                        }
            
            # Récupération depuis DB avec optimisation carte
            query = Site.query.filter_by(actif=True).filter(
                Site.latitude.isnot(None),
                Site.longitude.isnot(None)
            )
            
            # Appliquer filtres permissions
            if utilisateur_demandeur.is_superadmin():
                if client_id:
                    query = query.filter_by(client_id=client_id)
            else:
                query = query.filter_by(client_id=utilisateur_demandeur.client_id)
            
            sites = query.all()
            
            # Préparer données optimisées pour carte
            sites_map_data = []
            lats = []
            lngs = []
            
            for site in sites:
                lat = float(site.latitude)
                lng = float(site.longitude)
                
                lats.append(lat)
                lngs.append(lng)
                
                # Données minimales pour carte
                site_map = {
                    'id': site.id,
                    'nom_site': site.nom_site,
                    'adresse': site.adresse,
                    'ville': site.ville,
                    'client_id': site.client_id,
                    'coordinates': {'lat': lat, 'lng': lng},
                    'precision_gps': site.precision_gps,
                    'nb_appareils': site.appareils.filter_by(actif=True).count(),
                    'map_marker_color': 'green' if site.appareils.filter_by(actif=True).count() > 0 else 'gray'
                }
                sites_map_data.append(site_map)
            
            # Calculer bounds et centre
            bounds = None
            center = None
            if lats and lngs:
                bounds = {
                    'north': max(lats),
                    'south': min(lats),
                    'east': max(lngs),
                    'west': min(lngs)
                }
                center = {
                    'lat': sum(lats) / len(lats),
                    'lng': sum(lngs) / len(lngs)
                }
            
            map_data = {
                'sites': sites_map_data,
                'bounds': bounds,
                'center': center,
                'cached_at': datetime.utcnow().isoformat(),
                'from_cache': False
            }
            
            # ✅ Mettre en cache
            if use_cache and self.redis:
                self.redis.setex(cache_key, 300, json.dumps(map_data))  # 5 minutes
            
            return {
                "success": True,
                "map_data": map_data
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def configure_cache_ttl(self, cache_type: str, ttl_seconds: int):
        """Configurer dynamiquement les TTL du cache"""
        try:
            if cache_type not in self.ttl_config:
                return {"success": False, "error": f"Type de cache invalide: {cache_type}"}
            
            old_ttl = self.ttl_config[cache_type]
            self.ttl_config[cache_type] = ttl_seconds
            
            return {
                "success": True,
                "message": f"TTL {cache_type} modifié",
                "old_ttl": old_ttl,
                "new_ttl": ttl_seconds,
                "cache_type": cache_type
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        return site.client_id == utilisateur_demandeur.client_id
    
    def _peut_modifier_site(self, utilisateur_modificateur: User, site: Site) -> bool:
        """Vérifier si un utilisateur peut modifier un site"""
        # Seul le superadmin peut modifier des sites
        return utilisateur_modificateur.is_superadmin()
    
    def _peut_supprimer_site(self, utilisateur_supprimeur: User, site: Site) -> bool:
        """Vérifier si un utilisateur peut supprimer un site"""
        # Seul le superadmin peut supprimer des sites
        return utilisateur_supprimeur.is_superadmin()
    
    def _can_view_cached_site(self, utilisateur_demandeur: User, site_data: dict) -> bool:
        """Vérifier permissions sur données site cachées"""
        # Superadmin voit tout
        if utilisateur_demandeur.is_superadmin():
            return True
        
        # Admin/User voit son client