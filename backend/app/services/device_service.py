# app/services/device_service.py - PARTIE 1/3
# Service principal unifié pour la gestion des appareils IoT avec toutes les extensions

from app.services.tuya_service import TuyaClient
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.alert import Alert
from app import db, get_redis
from datetime import datetime, timedelta
from app.utils.fast_cache import fast_cache
import time
import json
import logging
import uuid

from app.models.device_action_log import DeviceActionLog

class DeviceService:
    """Service principal pour la gestion des appareils IoT avec Tuya"""
    
    def __init__(self):
        self.tuya_client = TuyaClient()
        
        # ✅ CORRECTION : Ajouter attribut redis pour compatibilité avec extensions
        self.redis = get_redis()
        
        logging.info(f"DeviceService initialisé - FastCache: {'✅' if fast_cache.is_connected() else '❌'}")
        
        # ✅ L'EXTENSION PROTECTION/PROGRAMMATION
        try:
            from app.services.device_service_protection_extension import DeviceServiceProtectionExtension
            self._protection_extension = DeviceServiceProtectionExtension(self)
            logging.info("✅ DeviceService Protection Extension initialisée")
        except ImportError as e:
            logging.warning(f"⚠️ Extension protection non disponible: {e}")
            self._protection_extension = None
        except Exception as e:
            logging.error(f"❌ Erreur initialisation extension protection: {e}")
            self._protection_extension = None

        # 🚀 NOUVEAU : AJOUTER AlertService - CORRIGÉ
        try:
            from app.services.alert_service import AlertService
            # ✅ CORRECTION : Passer self.redis au lieu de redis_client
            self._alert_service = AlertService()  # AlertService n'a plus besoin de redis en paramètre
            logging.info("✅ AlertService intégré dans DeviceService")
        except ImportError as e:
            logging.warning(f"⚠️ AlertService non disponible: {e}")
            self._alert_service = None
        except Exception as e:
            logging.error(f"❌ Erreur initialisation AlertService: {e}")
            self._alert_service = None

        # ✅ L'EXTENSION ANALYSIS
        try:
            from app.services.device_service_analysis_extension import DeviceServiceAnalysisExtension
            self._analysis_extension = DeviceServiceAnalysisExtension(self)
            logging.info("✅ DeviceService Analysis Extension initialisée")
        except ImportError as e:
            logging.warning(f"⚠️ Extension analysis non disponible: {e}")
            self._analysis_extension = None
        except Exception as e:
            logging.error(f"❌ Erreur initialisation extension analysis: {e}")
            self._analysis_extension = None


         
        # ✅ AJOUT : Intégration synchronisation temps réel AVEC DIAGNOSTIC
        self.sync_extension = None
        logging.info("✅ DeviceService initialisé (synchronisation extension désactivée)")
        logging.info("ℹ️ Utilisez sync_all_devices() et import_tuya_devices() pour synchroniser")

    # =================== GESTION CACHE REDIS OPTIMISÉE ===================
    
    def _cache_device_status(self, device_id, status_data, ttl=None):
        """Cache optimisé ultra-rapide"""
        try:
            ttl = ttl or 15  # TTL plus court pour plus de réactivité
            
            cache_data = {
                'device_id': device_id,
                'is_online': status_data.get('is_online', False),
                'last_values': status_data.get('values', {}),
                'cached_at': datetime.utcnow().isoformat()
            }
            
            key = f"device_status:{device_id}"
            return fast_cache.quick_set(key, cache_data, ttl)
        except Exception as e:
            logging.error(f"Erreur cache device status {device_id}: {e}")
            return False
    
    def _get_cached_device_status(self, device_id):
        """Get optimisé ultra-rapide"""
        try:
            key = f"device_status:{device_id}"
            return fast_cache.quick_get(key)
        except Exception as e:
            logging.error(f"Erreur get cache device status {device_id}: {e}")
            return None
    
    def _cache_devices_list(self, devices_data, ttl=None):
        """Cache liste optimisé"""
        try:
            ttl = ttl or 120  # 2 minutes au lieu de 5
            
            cache_data = {
                'devices': devices_data,
                'cached_at': datetime.utcnow().isoformat(),
                'count': len(devices_data)
            }
            
            return fast_cache.quick_set("devices_list_tuya", cache_data, ttl)
        except Exception as e:
            logging.error(f"Erreur cache devices list: {e}")
            return False
    
    def _get_cached_devices_list(self):
        """Get liste optimisé"""
        try:
            return fast_cache.quick_get("devices_list_tuya")
        except Exception as e:
            logging.error(f"Erreur get cache devices list: {e}")
            return None
    
    def _cache_sync_result(self, sync_stats, ttl=None):
        """Cache du résultat de synchronisation - VERSION OPTIMISÉE"""
        try:
            ttl = ttl or 60  # TTL direct au lieu de self.ttl_config
            
            cache_data = {
                'sync_stats': sync_stats,
                'synced_at': datetime.utcnow().isoformat()
            }
            
            return fast_cache.quick_set("last_device_sync", cache_data, ttl)
        except Exception as e:
            logging.error(f"Erreur cache sync result: {e}")
            return False
    
    def _get_last_sync_info(self):
        """Récupérer info dernière synchronisation - VERSION OPTIMISÉE"""
        try:
            return fast_cache.quick_get("last_device_sync")
        except Exception as e:
            logging.error(f"Erreur get last sync info: {e}")
            return None
    
    def _invalidate_device_cache(self, device_id):
        """Invalidation rapide optimisée"""
        try:
            patterns_to_delete = [
                f"device_status:{device_id}",
                f"device_data:{device_id}:*",
                f"device_data_window:{device_id}"
            ]
            
            total_deleted = 0
            for pattern in patterns_to_delete:
                deleted = fast_cache.delete_pattern(pattern)
                total_deleted += deleted
            
            logging.debug(f"Cache invalidé pour device {device_id}: {total_deleted} clés")
            
        except Exception as e:
            logging.error(f"Erreur invalidation cache device {device_id}: {e}")
        
    def _cache_device_data(self, device_id, data_values, ttl=None):
        """Cache des données IoT d'un appareil - VERSION OPTIMISÉE"""
        try:
            ttl = ttl or 120  # 2 minutes au lieu de 5
            key = f"device_data:{device_id}:{int(datetime.utcnow().timestamp())}"
            
            cache_data = {
                'device_id': device_id,
                'values': data_values,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Cache la donnée
            fast_cache.quick_set(key, cache_data, ttl)
            
            # Maintenir fenêtre glissante (optionnel, simplifiée)
            self._maintain_device_data_window_simple(device_id, key)
        except Exception as e:
            logging.error(f"Erreur cache device data {device_id}: {e}")
    
    def _maintain_device_data_window_simple(self, device_id, new_key):
        """Maintenir fenêtre glissante simplifiée"""
        try:
            window_key = f"device_data_window:{device_id}"
            
            # Récupérer fenêtre existante
            existing_window = fast_cache.quick_get(window_key)
            if not existing_window or not isinstance(existing_window, list):
                existing_window = []
            
            # Ajouter nouvelle clé
            existing_window.append(new_key)
            
            # Garder seulement les 50 dernières (au lieu de 100 pour performance)
            if len(existing_window) > 50:
                # Supprimer les anciennes clés
                old_keys = existing_window[:-50]
                for old_key in old_keys:
                    fast_cache.delete_pattern(old_key)
                
                existing_window = existing_window[-50:]
            
            # Sauvegarder fenêtre mise à jour
            fast_cache.quick_set(window_key, existing_window, 1800)  # 30 minutes
            
        except Exception as e:
            logging.error(f"Erreur maintenance fenêtre device {device_id}: {e}")
    
    def _invalidate_all_cache(self):
        """Invalider tout le cache des appareils - VERSION OPTIMISÉE"""
        try:
            if not fast_cache.is_connected():
                return 0
            
            patterns = [
                "device_status:*",
                "device_data:*", 
                "device_data_window:*",
                "devices_list_tuya",
                "last_device_sync"
            ]
            
            total_deleted = 0
            for pattern in patterns:
                deleted = fast_cache.delete_pattern(pattern)
                total_deleted += deleted
            
            logging.info(f"Cache invalidé: {total_deleted} clés supprimées")
            return total_deleted
            
        except Exception as e:
            logging.error(f"Erreur invalidation cache complet: {e}")
            return 0

    
    # =================== GESTION BASIQUE DES APPAREILS ===================
    
    def import_tuya_devices(self, use_cache=True, force_refresh=False):
        """Import avec cache Redis et gestion complète"""
        try:
            print("🔍 Début import appareils Tuya...")
            
            # Vérifier cache d'abord (sauf si force_refresh)
            if use_cache and not force_refresh:
                cached_devices = self._get_cached_devices_list()
                if cached_devices:
                    cached_at = datetime.fromisoformat(cached_devices['cached_at'])
                    age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
                    
                    if age_minutes < 2:  # Cache valide 2 minutes
                        print(f"📦 Utilisation cache Tuya (âge: {age_minutes:.1f}min)")
                        devices = cached_devices['devices']
                        return self._process_devices_data(devices, from_cache=True)
            
            if not self.tuya_client.auto_connect_from_env():
                return {"success": False, "error": "Impossible de se connecter à Tuya Cloud"}
            
            # Récupération depuis Tuya API
            devices_response = self.tuya_client.get_all_devices_with_details()
            
            if not devices_response.get("success"):
                return {"success": False, "error": devices_response.get("error", "Erreur récupération appareils")}
            
            devices = devices_response.get("result", [])
            print(f"📱 {len(devices)} appareils récupérés depuis Tuya")
            
            # Mettre en cache la liste Tuya
            if use_cache:
                self._cache_devices_list(devices)
            
            # Traiter les données
            result = self._process_devices_data(devices, from_cache=False)
            
            # Cache du résultat de sync
            if result.get("success") and use_cache:
                self._cache_sync_result(result.get("statistiques", {}))
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur import Tuya: {e}")
            db.session.rollback()
            return {"success": False, "error": f"Erreur lors de l'import: {str(e)}"}
    
    def _process_devices_data(self, devices, from_cache=False):
        """Traiter les données d'appareils avec mise à jour intelligente"""
        try:
            stats = {
                'appareils_importes': 0,
                'appareils_mis_a_jour': 0,
                'online_count': 0,
                'offline_count': 0,
                'protection_updates': 0,
                'programmation_updates': 0
            }
            
            source_text = "cache Redis" if from_cache else "API Tuya"
            print(f"🔄 Traitement de {len(devices)} appareils depuis {source_text}")
            
            # Créer mapping des statuts
            device_status_map = {}
            for device_data in devices:
                device_id = device_data.get("id")
                if device_id:
                    is_online = device_data.get("isOnline", False)
                    device_status_map[device_id] = is_online
                    
                    # Cache individuel du statut
                    self._cache_device_status(device_id, {
                        'is_online': is_online,
                        'values': {},
                        'source': source_text
                    })
            
            for device_data in devices:
                tuya_device_id = device_data.get("id") or device_data.get("device_id")
                if not tuya_device_id:
                    continue
                
                is_online = device_status_map.get(tuya_device_id, False)
                device_name = device_data.get("name", f"Appareil {tuya_device_id}")
                
                if is_online:
                    stats['online_count'] += 1
                else:
                    stats['offline_count'] += 1
                
                # Rechercher appareil existant
                existing_device = Device.get_by_tuya_id(tuya_device_id)
                
                if existing_device:
                    # Mise à jour
                    old_status = existing_device.en_ligne
                    
                    existing_device.en_ligne = is_online
                    existing_device.tuya_nom_original = device_data.get("name", existing_device.tuya_nom_original)
                    existing_device.tuya_modele = device_data.get("model", existing_device.tuya_modele)
                    existing_device.tuya_version_firmware = device_data.get("sw_ver", existing_device.tuya_version_firmware)
                    
                    if not existing_device.nom_appareil or existing_device.nom_appareil == existing_device.tuya_nom_original:
                        existing_device.nom_appareil = device_name
                    
                    # Vérifier si protection/programmation doivent être mises à jour
                    if existing_device.protection_automatique_active:
                        self._update_device_protection_status(existing_device, is_online)
                        stats['protection_updates'] += 1
                    
                    if existing_device.programmation_active:
                        self._update_device_schedule_status(existing_device, is_online)
                        stats['programmation_updates'] += 1
                    
                    db.session.add(existing_device)
                    stats['appareils_mis_a_jour'] += 1
                    
                    # Invalider cache si statut changé
                    if old_status != is_online:
                        self._invalidate_device_cache(tuya_device_id)
                
                else:
                    # Créer nouvel appareil
                    device_category = device_data.get("category", "unknown")
                    type_appareil = self._determine_device_type(device_category, device_data)
                    
                    new_device = Device(
                        tuya_device_id=tuya_device_id,
                        nom_appareil=device_name,
                        type_appareil=type_appareil,
                        tuya_nom_original=device_data.get("name", ""),
                        tuya_modele=device_data.get("model", ""),
                        tuya_version_firmware=device_data.get("sw_ver", ""),
                        en_ligne=is_online,
                        statut_assignation='non_assigne',
                        date_installation=datetime.utcnow(),
                        actif=True
                    )
                    
                    db.session.add(new_device)
                    stats['appareils_importes'] += 1
            
            # Commit avec gestion d'erreur
            try:
                db.session.flush()
                db.session.commit()
                print("💾 Changements sauvegardés avec succès")
                
            except Exception as commit_error:
                print(f"❌ Erreur lors du commit: {commit_error}")
                db.session.rollback()
                return {"success": False, "error": f"Erreur commit: {str(commit_error)}"}
            
            print(f"✅ Traitement terminé: {stats}")
            
            return {
                "success": True,
                "message": f"{len(devices)} appareils traités avec succès",
                "statistiques": stats
            }
            
        except Exception as e:
            print(f"❌ Erreur traitement données: {e}")
            db.session.rollback()
            return {"success": False, "error": f"Erreur traitement: {str(e)}"}




    def get_all_devices(self, utilisateur=None, include_non_assignes=False, refresh_status=True, use_cache=True):
        """Récupérer tous les appareils avec filtrage par site utilisateur - VERSION ENRICHIE CORRIGÉE"""
        try:
            # Cache key basé sur les paramètres ET le site utilisateur
            site_suffix = f"_site_{utilisateur.site_id}" if utilisateur and utilisateur.role == 'user' and utilisateur.site_id else ""
            cache_suffix = f"{utilisateur.id if utilisateur else 'none'}_{include_non_assignes}_{refresh_status}{site_suffix}"
            cache_key = f"devices_query:{cache_suffix}"
            
            # Vérifier cache
            if use_cache and not refresh_status:
                cached_result = self._get_generic_cache(cache_key)
                if cached_result:
                    print(f"📦 Liste appareils depuis cache (site: {utilisateur.site_id if utilisateur and utilisateur.role == 'user' else 'all'})")
                    return cached_result
            
            # Synchronisation si demandée
            if refresh_status:
                print("🔄 Actualisation des statuts avant récupération...")
                # MODIFICATION ICI : Appeler sync_all_devices au lieu de import_tuya_devices
                sync_result = self.sync_all_devices(force_refresh=True) # <-- Utilisez force_refresh=True pour s'assurer que Tuya est interrogé
                if not sync_result.get("success"):
                    print(f"⚠️ Échec synchronisation: {sync_result.get('error')}")
                else:
                    # db.session.expire_all() est important pour que les objets Device soient rafraîchis depuis la DB
                    db.session.expire_all() 
            
            # ✅ RÉCUPÉRATION SELON PERMISSIONS ET SITE
            if utilisateur and utilisateur.is_superadmin():
                if include_non_assignes:
                    devices = Device.query.all()
                else:
                    devices = Device.query.filter_by(statut_assignation='assigne').all()
                scope = "superadmin"
                
            elif utilisateur and utilisateur.is_admin():
                devices = Device.query.filter_by(
                    client_id=utilisateur.client_id,
                    statut_assignation='assigne'
                ).all()
                scope = "admin"
                
            elif utilisateur and utilisateur.role == 'user':
                # ✅ NOUVEAU : User simple - filtrage par site
                if not utilisateur.site_id:
                    devices = []
                    scope = "user_no_site"
                else:
                    devices = Device.query.filter_by(
                        client_id=utilisateur.client_id,
                        site_id=utilisateur.site_id,
                        statut_assignation='assigne'
                    ).all()
                    scope = f"user_site_{utilisateur.site_id}"
                    
            else:
                devices = Device.get_non_assignes() if include_non_assignes else []
                scope = "anonymous"
            
            # ✅ CORRECTION : Double vérification avec syntaxe correcte
            devices_accessibles = []
            for device in devices:
                try:
                    # Si pas d'utilisateur, inclure l'appareil
                    if utilisateur is None:
                        devices_accessibles.append(device)
                    # Si utilisateur présent, vérifier les permissions
                    elif device.peut_etre_vu_par_utilisateur(utilisateur):
                        devices_accessibles.append(device)
                    else:
                        print(f"🔒 Appareil {device.nom_appareil} filtré par permissions pour {utilisateur.nom_complet}")
                except Exception as e:
                    print(f"⚠️ Erreur vérification permissions appareil {getattr(device, 'nom_appareil', device.id)}: {e}")
                    # En cas d'erreur, ne pas inclure l'appareil (sécurité)
                    continue
            
            # Statistiques enrichies avec info site
            online_count = sum(1 for d in devices_accessibles if d.en_ligne)
            offline_count = len(devices_accessibles) - online_count
            
            # Compter appareils avec protection/programmation
            protection_active = sum(1 for d in devices_accessibles if getattr(d, 'protection_automatique_active', False))
            programmation_active = sum(1 for d in devices_accessibles if getattr(d, 'programmation_active', False))
            
            # Statistiques par type d'appareil
            types_count = {}
            for device in devices_accessibles:
                device_type = getattr(device, 'type_appareil', 'unknown')
                types_count[device_type] = types_count.get(device_type, 0) + 1
            
            result = {
                "success": True,
                "devices": [self._device_to_dict_enhanced(device) for device in devices_accessibles],
                "count": len(devices_accessibles),
                "last_sync": datetime.utcnow().isoformat() if refresh_status else None,
                "user_scope": scope,
                "user_info": {
                    "role": utilisateur.role if utilisateur else None,
                    "site_id": utilisateur.site_id if utilisateur and utilisateur.role == 'user' else None,
                    "site_nom": utilisateur.site.nom_site if utilisateur and utilisateur.role == 'user' and utilisateur.site else None
                } if utilisateur else None,
                "stats": {
                    "total": len(devices_accessibles),
                    "online": online_count,
                    "offline": offline_count,
                    "protection_active": protection_active,
                    "programmation_active": programmation_active,
                    "par_type": types_count,
                    "sync_method": "full_import" if refresh_status else "cache",
                    "filtering_applied": utilisateur is not None,
                    "original_count": len(devices),
                    "filtered_count": len(devices) - len(devices_accessibles)
                }
            }
            
            # Mettre en cache avec TTL adapté
            if use_cache:
                # TTL plus court pour users (changements plus fréquents)
                ttl = 60 if utilisateur and utilisateur.role == 'user' else 120
                self._set_generic_cache(cache_key, result, ttl=ttl)
            
            print(f"📊 Appareils récupérés pour {scope}: {len(devices_accessibles)} ({online_count} 🟢, {offline_count} 🔴)")
            
            # Log de filtrage si applicable
            filtered_count = len(devices) - len(devices_accessibles)
            if filtered_count > 0:
                print(f"🔒 {filtered_count} appareils filtrés par permissions")
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur récupération appareils: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}



    # ✅ NOUVELLE MÉTHODE : Spécifique aux appareils d'un site
    def get_devices_by_site(self, site_id, utilisateur=None, use_cache=True):
        """Récupérer les appareils d'un site spécifique"""
        try:
            cache_key = f"devices_site:{site_id}:{utilisateur.id if utilisateur else 'none'}"
            
            # Vérifier cache
            if use_cache:
                cached_result = self._get_generic_cache(cache_key)
                if cached_result:
                    print(f"📦 Appareils site {site_id} depuis cache")
                    return cached_result
            
            # Vérifier permissions d'accès au site
            if utilisateur:
                if utilisateur.is_superadmin():
                    # Superadmin peut voir tout
                    pass
                elif utilisateur.is_admin():
                    # Admin peut voir les sites de son client
                    from app.models.site import Site
                    site = Site.query.get(site_id)
                    if not site or site.client_id != utilisateur.client_id:
                        return {"success": False, "error": "Accès interdit à ce site"}
                elif utilisateur.role == 'user':
                    # User simple peut voir que son site
                    if utilisateur.site_id != site_id:
                        return {"success": False, "error": "Accès interdit - site non assigné"}
                else:
                    return {"success": False, "error": "Permissions insuffisantes"}
            
            # Récupération des appareils du site
            devices = Device.query.filter_by(
                site_id=site_id,
                statut_assignation='assigne'
            ).all()
            
            # Filtrer par permissions utilisateur
            if utilisateur:
                devices_accessibles = [
                    device for device in devices 
                    if device.peut_etre_vu_par_utilisateur(utilisateur)
                ]
            else:
                devices_accessibles = devices
            
            # Récupérer info du site
            from app.models.site import Site
            site = Site.query.get(site_id)
            
            # Statistiques
            online_count = sum(1 for d in devices_accessibles if d.en_ligne)
            offline_count = len(devices_accessibles) - online_count
            
            result = {
                "success": True,
                "site_id": site_id,
                "site_info": site.to_dict() if site else None,
                "devices": [self._device_to_dict_enhanced(device) for device in devices_accessibles],
                "count": len(devices_accessibles),
                "stats": {
                    "total": len(devices_accessibles),
                    "online": online_count,
                    "offline": offline_count
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache
            if use_cache:
                self._set_generic_cache(cache_key, result, ttl=180)  # 3 minutes
            
            print(f"📍 Site {site_id}: {len(devices_accessibles)} appareils")
            return result
            
        except Exception as e:
            print(f"❌ Erreur appareils site {site_id}: {e}")
            return {"success": False, "error": str(e)}


    # =================== CONTRÔLE ET STATUT DES APPAREILS ===================
    
    def get_device_status(self, tuya_device_id, use_cache=True):
        """Récupérer le statut d'un appareil avec enrichissement complet (corrigé & sécurisé)"""
        try:
            now = datetime.utcnow()

            # ✅ Throttle simple par device (anti-spam)
            last_check = getattr(self, '_last_status_check', {}).get(tuya_device_id)
            if last_check and (now - last_check).total_seconds() < 5:
                print(f"⚠️ Requête trop fréquente pour {tuya_device_id}, ignorée")
                return {"success": False, "error": "Requête trop fréquente. Attends quelques secondes."}
            
            self._last_status_check = getattr(self, '_last_status_check', {})
            self._last_status_check[tuya_device_id] = now

            # ✅ Vérifier cache Redis
            if use_cache:
                cached_status = self._get_cached_device_status(tuya_device_id)
                if cached_status:
                    cached_at = datetime.fromisoformat(cached_status['cached_at'])
                    age = (now - cached_at).total_seconds()
                    if age < 30:
                        print(f"📦 Statut depuis cache pour {tuya_device_id} (âge: {age:.1f}s)")
                        status_response = {
                            "success": True,
                            "values": cached_status['last_values'],
                            "is_online": cached_status['is_online'],
                            "from_cache": True,
                            "cached_at": cached_status['cached_at']
                        }
                        return self._enhance_device_status(status_response, tuya_device_id)
                    else:
                        print(f"⚠️ Cache expiré pour {tuya_device_id} (âge: {age:.1f}s)")
                else:
                    print(f"ℹ️ Aucun cache trouvé pour {tuya_device_id}")

            # ✅ Connexion Tuya
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion Tuya impossible"}

            # ✅ Appel direct sans récursion
            status_response = self.tuya_client.get_device_current_values(tuya_device_id)
            if not status_response.get("success"):
                return {"success": False, "error": status_response.get("error", "Erreur inconnue Tuya")}

            values = status_response.get("values", {})
            raw_values = status_response.get("raw_status", [])
            is_online = status_response.get("is_online", False)

            # ✅ Construction de l’état enrichi
            full_status = {
                "success": True,
                "values": values,
                "is_online": is_online,
                "from_cache": False,
                "raw_status": raw_values,
                "timestamp": status_response.get("timestamp", now.isoformat())
            }

            # ✅ Cache dans Redis
            if use_cache:
                self._cache_device_status(tuya_device_id, full_status)
                self._cache_device_data(tuya_device_id, values)

            # ✅ MAJ BDD si nécessaire
            device = Device.get_by_tuya_id(tuya_device_id)
            if device:
                if device.is_assigne():
                    self._save_device_data_with_processing(device, full_status)
                device.update_last_data_time()

            return self._enhance_device_status(full_status, tuya_device_id)

        except Exception as e:
            print(f"❌ Erreur statut appareil {tuya_device_id}: {e}")
            return {"success": False, "error": str(e)}


    

    def control_device(self, tuya_device_id, command, value=None, invalidate_cache=True):
        """
        Contrôler un appareil en utilisant la méthode de toggle intelligente du TuyaClient.
        """
        try:
            # --- Étape 1 : Vérifications initiales (inchangées) ---
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}

            # Vérifier protection avant contrôle
            protection_check = self._check_protection_before_control(device, command, value)
            if not protection_check.get('allowed', True):
                return {
                    "success": False,
                    "error": protection_check.get('reason', 'Contrôle bloqué par protection')
                }

            # Gérer mode manuel si programmation active
            if device.programmation_active and not device.mode_manuel_actif:
                device.enable_mode_manuel(duree_heures=2)
                print(f"🔧 Mode manuel activé pour {device.nom_appareil}")

            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion Tuya impossible"}

            # --- Étape 2 : Délégation de la commande (la partie corrigée) ---
            
            # On ne gère que les commandes de type switch/toggle ici.
            # Pour d'autres commandes (ex: 'mode', 'countdown'), il faudrait une autre logique.
            if command not in ["switch", "toggle"]:
                 return {"success": False, "error": f"La commande '{command}' n'est pas supportée par cette fonction."}

            print(f"🔧 Délégation de la commande '{command}' au toggle intelligent pour l'appareil {tuya_device_id}...")
            
            # On appelle directement la fonction toggle_device du client.
            # Elle se chargera de trouver le bon code ('switch', 'switch_1', etc.)
            # et de déterminer le nouvel état si 'value' est None.
            tuya_api_result = self.tuya_client.toggle_device(tuya_device_id, value)

            # --- Étape 3 : Traitement du résultat (simplifié) ---

            if tuya_api_result.get("success"):
                print(f"✅ Commande toggle intelligente réussie pour {tuya_device_id}")
                
                new_state = tuya_api_result.get("new_state")

                # Mettre à jour l'état dans la base de données locale
                if new_state is not None:
                    device.etat_actuel_tuya = new_state
                    device.derniere_maj_etat_tuya = datetime.utcnow()
                    db.session.commit()
                    print(f"✅ Appareil {device.nom_appareil} mis à jour en DB: etat_actuel_tuya={new_state}")

                # Enregistrer l'action dans l'historique
                try:
                    self._log_device_action(device, 'manual_control', {
                        'command': command,
                        'value': value,
                        'result': 'success',
                        'new_state_reported': new_state,
                        'switch_code_used': tuya_api_result.get('switch_code_used') # Log du code utilisé
                    })
                except Exception as log_err:
                    print(f"Erreur log action: {log_err}")

                # Invalider le cache
                if invalidate_cache:
                    self._invalidate_device_cache(tuya_device_id)

                # Retourner le résultat
                return {
                    "success": True,
                    "message": tuya_api_result.get('message', "Commande exécutée avec succès."),
                    "new_state": new_state,
                    "tuya_response": tuya_api_result
                }
            else:
                # L'appel à toggle_device a échoué
                print(f"❌ Échec de la commande toggle intelligente pour {tuya_device_id}.")
                return {
                    "success": False,
                    "error": tuya_api_result.get("error", "Échec de l'envoi de la commande à Tuya."),
                    "tuya_response": tuya_api_result
                }

        except Exception as e:
            print(f"❌ Erreur contrôle appareil {tuya_device_id}: {e}")
            db.session.rollback()
            return {"success": False, "error": str(e)}


    # =================== GESTION PROTECTION AUTOMATIQUE ===================
    
    def _check_protection_before_control(self, device, command, value):
        """Vérifier les protections avant d'autoriser un contrôle"""
        if not device.protection_automatique_active:
            return {'allowed': True}
        
        # Vérifier si l'appareil est en mode protection
        if device.protection_status == 'protected':
            # Vérifier le cooldown
            if device.derniere_protection_declenchee:
                # Récupérer config de protection pour cooldown
                protection_configs = [
                    device.protection_courant_config,
                    device.protection_puissance_config,
                    device.protection_temperature_config
                ]
                
                min_cooldown = 5  # Default 5 minutes
                for config in protection_configs:
                    if config and config.get('enabled'):
                        cooldown = config.get('cooldown_minutes', 5)
                        min_cooldown = min(min_cooldown, cooldown)
                
                time_since_protection = datetime.utcnow() - device.derniere_protection_declenchee
                if time_since_protection.total_seconds() < (min_cooldown * 60):
                    return {
                        'allowed': False,
                        'reason': f'Protection active - Cooldown de {min_cooldown}min'
                    }
        
        return {'allowed': True}
    
    def _update_device_protection_status(self, device, is_online):
        """Mettre à jour le statut de protection selon l'état de l'appareil"""
        if not device.protection_automatique_active:
            return
        
        # Si l'appareil vient de se reconnecter, réinitialiser le statut de protection
        if is_online and device.protection_status == 'protected':
            # Vérifier si le cooldown est écoulé
            if device.derniere_protection_declenchee:
                time_since = datetime.utcnow() - device.derniere_protection_declenchee
                if time_since.total_seconds() > 300:  # 5 minutes
                    device.reset_protection_status()
                    print(f"🔄 Protection status reset pour {device.nom_appareil}")
    
    def _process_protection_monitoring(self, device, values):
        """Analyser les valeurs et déclencher protections si nécessaire"""
        if not device.protection_automatique_active:
            return {'protection_triggered': False}
        
        triggered_protections = []
        
        # Vérifier protection courant
        if device.protection_courant_config and device.protection_courant_config.get('enabled'):
            courant = values.get('courant')
            if courant:
                threshold = device.protection_courant_config.get('threshold')
                if threshold and courant > threshold:
                    triggered_protections.append({
                        'type': 'courant_depasse',
                        'value': courant,
                        'threshold': threshold,
                        'unit': 'A',
                        'config': device.protection_courant_config
                    })
        
        # Vérifier protection puissance
        if device.protection_puissance_config and device.protection_puissance_config.get('enabled'):
            puissance = values.get('puissance')
            if puissance:
                threshold = device.protection_puissance_config.get('threshold')
                if threshold and puissance > threshold:
                    triggered_protections.append({
                        'type': 'puissance_depassee',
                        'value': puissance,
                        'threshold': threshold,
                        'unit': 'W',
                        'config': device.protection_puissance_config
                    })
        
        # Vérifier protection température
        if device.protection_temperature_config and device.protection_temperature_config.get('enabled'):
            temperature = values.get('temperature')
            if temperature:
                threshold = device.protection_temperature_config.get('threshold')
                if threshold and temperature > threshold:
                    triggered_protections.append({
                        'type': 'temperature_haute',
                        'value': temperature,
                        'threshold': threshold,
                        'unit': '°C',
                        'config': device.protection_temperature_config
                    })
        
        # Traiter les protections déclenchées
        if triggered_protections:
            return self._execute_protection_actions(device, triggered_protections)
        
        return {'protection_triggered': False}
    
    def _execute_protection_actions(self, device, triggered_protections):
        """Exécuter les actions de protection"""
        executed_actions = []
        
        for protection in triggered_protections:
            try:
                # Créer événement de protection si disponible
                try:
                    from app.models.protection_event import ProtectionEvent
                    
                    event = ProtectionEvent.creer_evenement_protection(
                        client_id=device.client_id,
                        appareil_id=device.id,
                        type_protection=protection['type'],
                        action_effectuee='arret_appareil',
                        valeur_declenchement=protection['value'],
                        valeur_seuil=protection['threshold'],
                        unite_mesure=protection['unit'],
                        type_systeme=device.type_systeme,
                        etat_avant='on',
                        config_protection=protection['config']
                    )
                except ImportError:
                    event = None
                
                # Exécuter l'action selon la config
                action = protection['config'].get('action', 'turn_off')
                
                if action == 'turn_off':
                    # Éteindre l'appareil
                    control_result = self.tuya_client.toggle_device(device.tuya_device_id, False)
                    
                    if control_result.get('success'):
                        # Marquer la protection comme déclenchée
                        device.log_protection_trigger(protection['type'], protection['value'])
                        
                        # Mettre à jour l'événement
                        if event:
                            event.etat_apres = 'off'
                            db.session.commit()
                        
                        executed_actions.append({
                            'type': protection['type'],
                            'action': 'device_turned_off',
                            'success': True
                        })
                        
                        print(f"🚨 Protection {protection['type']} déclenchée - Appareil {device.nom_appareil} éteint")
                    else:
                        executed_actions.append({
                            'type': protection['type'],
                            'action': 'shutdown_failed',
                            'success': False,
                            'error': control_result.get('error')
                        })
                
                # Programmer redémarrage automatique si configuré
                if protection['config'].get('auto_restart') and executed_actions[-1].get('success'):
                    restart_delay = protection['config'].get('restart_delay_minutes', 10)
                    self._schedule_auto_restart(device, restart_delay)
                
            except Exception as e:
                print(f"Erreur exécution protection {protection['type']}: {e}")
                executed_actions.append({
                    'type': protection['type'],
                    'action': 'execution_failed',
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'protection_triggered': True,
            'executed_actions': executed_actions,
            'shutdown_executed': any(a.get('success') and a.get('action') == 'device_turned_off' for a in executed_actions)
        }
    
            
    def _schedule_auto_restart(self, device, delay_minutes):
        """Programmer un redémarrage automatique"""
        try:
            restart_time = datetime.utcnow() + timedelta(minutes=delay_minutes)
            
            # Créer une action programmée temporaire pour le redémarrage
            try:
                from app.models.scheduled_action import ScheduledAction
                
                action = ScheduledAction(
                    client_id=device.client_id,
                    appareil_id=device.id,
                    action_type='turn_on',
                    heure_execution=restart_time.time(),
                    mode_execution='once',
                    nom_action=f'Redémarrage automatique après protection',
                    description=f'Redémarrage auto programmé après déclenchement protection',
                    date_debut=restart_time.date(),
                    date_fin=restart_time.date(),
                    priorite=10  # Priorité maximale
                )
                
                # Calculer la prochaine exécution
                action.prochaine_execution = restart_time
                action.set_jours_semaine([restart_time.weekday() + 1])
                
                db.session.add(action)
                db.session.commit()
                
                print(f"⏰ Redémarrage auto programmé pour {device.nom_appareil} dans {delay_minutes}min")
                
            except ImportError:
                print(f"⚠️ ScheduledAction non disponible - redémarrage auto ignoré")
            
        except Exception as e:
            print(f"Erreur programmation auto-restart: {e}")
    
    # =================== GESTION PROGRAMMATION HORAIRE ===================
    
    def _update_device_schedule_status(self, device, is_online):
        """Mettre à jour le statut de programmation selon l'état de l'appareil"""
        if not device.programmation_active:
            return
        
        # Vérifier si le mode manuel a expiré
        if device.is_mode_manuel_expire():
            print(f"🔧 Mode manuel expiré pour {device.nom_appareil}")
        
        # Recalculer la prochaine action si l'appareil vient de se reconnecter
        if is_online:
            try:
                device._calculate_next_scheduled_action()
            except Exception as e:
                print(f"Erreur recalcul prochaine action pour {device.nom_appareil}: {e}")
    
    def execute_scheduled_actions(self):
        """Exécuter les actions programmées dues"""
        try:
            # Récupérer toutes les actions dues
            try:
                from app.models.scheduled_action import ScheduledAction
                actions_dues = ScheduledAction.get_actions_dues(tolerance_minutes=2)
            except ImportError:
                return {'executed': 0, 'actions': [], 'error': 'ScheduledAction non disponible'}
            
            if not actions_dues:
                return {'executed': 0, 'actions': []}
            
            executed_actions = []
            
            for action in actions_dues:
                try:
                    device = Device.query.get(action.appareil_id)
                    if not device:
                        continue
                    
                    # Vérifier que l'appareil n'est pas en mode manuel
                    if device.mode_manuel_actif:
                        print(f"⏭️ Action programmée ignorée - Mode manuel actif pour {device.nom_appareil}")
                        continue
                    
                    # Vérifier que l'appareil n'est pas en protection
                    if device.protection_status == 'protected':
                        print(f"⏭️ Action programmée ignorée - Protection active pour {device.nom_appareil}")
                        continue
                    
                    # Exécuter l'action
                    success = self._execute_single_scheduled_action(device, action)
                    
                    # Enregistrer le résultat
                    action.marquer_execution(success=success)
                    
                    executed_actions.append({
                        'action_id': action.id,
                        'device_name': device.nom_appareil,
                        'action_type': action.action_type,
                        'success': success,
                        'executed_at': datetime.utcnow().isoformat()
                    })
                    
                except Exception as e:
                    print(f"Erreur exécution action programmée {action.id}: {e}")
                    action.marquer_execution(success=False, error_message=str(e))
                    
                    executed_actions.append({
                        'action_id': action.id,
                        'action_type': action.action_type,
                        'success': False,
                        'error': str(e)
                    })
            
            return {
                'executed': len(executed_actions),
                'actions': executed_actions
            }
            
        except Exception as e:
            print(f"Erreur exécution actions programmées: {e}")
            return {'executed': 0, 'actions': [], 'error': str(e)}
    
    def _execute_single_scheduled_action(self, device, action):
        """Exécuter une action programmée individuelle"""
        try:
            if not self.tuya_client.reconnect_if_needed():
                return False
            
            if action.action_type == 'turn_on':
                result = self.tuya_client.toggle_device(device.tuya_device_id, True)
            elif action.action_type == 'turn_off':
                result = self.tuya_client.toggle_device(device.tuya_device_id, False)
            elif action.action_type == 'toggle':
                result = self.tuya_client.toggle_device(device.tuya_device_id)
            elif action.action_type == 'custom_command' and action.custom_command:
                result = self.tuya_client.send_device_command(device.tuya_device_id, action.custom_command)
            else:
                print(f"Type d'action non supporté: {action.action_type}")
                return False
            
            if result.get('success'):
                # Enregistrer l'action dans l'historique
                self._log_device_action(device, 'scheduled_action', {
                    'action_type': action.action_type,
                    'action_id': action.id,
                    'result': 'success'
                })
                
                # Invalider cache
                self._invalidate_device_cache(device.tuya_device_id)
                
                print(f"✅ Action programmée exécutée: {action.action_type} sur {device.nom_appareil}")
                return True
            else:
                print(f"❌ Échec action programmée: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"Erreur exécution action {action.action_type}: {e}")
            return False
    
    # =================== ENRICHISSEMENT ET ANALYSE ===================
    
    def _enhance_device_status(self, status_response, tuya_device_id):
        """Enrichir les données de statut avec analyse et historique"""
        try:
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return status_response
            
            # Ajouter informations device
            status_response['device_info'] = {
                'id': device.id,
                'nom': device.nom_appareil,
                'type': device.type_appareil,
                'assigné': device.is_assigne()
            }
            
            # Ajouter statut protection si activé
            if device.protection_automatique_active:
                status_response['protection_status'] = device.get_protection_config()
            
            # Ajouter statut programmation si activé
            if device.programmation_active:
                status_response['programmation_status'] = device.get_horaires_config()
            
            # Ajouter analyse des seuils
            values = status_response.get('values', {})
            if values:
                status_response['threshold_analysis'] = self._analyze_thresholds(device, values)
            
            return status_response
            
        except Exception as e:
            print(f"Erreur enrichissement statut: {e}")
            return status_response
    
    def _analyze_thresholds(self, device, values):
        """Analyser les valeurs par rapport aux seuils"""
        analysis = {
            'warnings': [],
            'criticals': [],
            'all_ok': True
        }
        
        try:
            # Analyser tension
            tension = values.get('tension')
            if tension:
                if device.seuil_tension_min and tension < device.seuil_tension_min:
                    analysis['criticals'].append({
                        'metric': 'tension',
                        'value': tension,
                        'threshold': device.seuil_tension_min,
                        'type': 'below_minimum',
                        'unit': 'V'
                    })
                    analysis['all_ok'] = False
                elif device.seuil_tension_max and tension > device.seuil_tension_max:
                    analysis['criticals'].append({
                        'metric': 'tension',
                        'value': tension,
                        'threshold': device.seuil_tension_max,
                        'type': 'above_maximum',
                        'unit': 'V'
                    })
                    analysis['all_ok'] = False
            
            # Analyser courant
            courant = values.get('courant')
            if courant and device.seuil_courant_max:
                if courant > device.seuil_courant_max * 0.8:  # Warning à 80%
                    level = 'criticals' if courant > device.seuil_courant_max else 'warnings'
                    analysis[level].append({
                        'metric': 'courant',
                        'value': courant,
                        'threshold': device.seuil_courant_max,
                        'type': 'approaching_limit' if level == 'warnings' else 'above_maximum',
                        'unit': 'A'
                    })
                    if level == 'criticals':
                        analysis['all_ok'] = False
            
            # Analyser puissance
            puissance = values.get('puissance')
            if puissance and device.seuil_puissance_max:
                if puissance > device.seuil_puissance_max * 0.8:  # Warning à 80%
                    level = 'criticals' if puissance > device.seuil_puissance_max else 'warnings'
                    analysis[level].append({
                        'metric': 'puissance',
                        'value': puissance,
                        'threshold': device.seuil_puissance_max,
                        'type': 'approaching_limit' if level == 'warnings' else 'above_maximum',
                        'unit': 'W'
                    })
                    if level == 'criticals':
                        analysis['all_ok'] = False
            
            # Analyser température
            temperature = values.get('temperature')
            if temperature and device.seuil_temperature_max:
                if temperature > device.seuil_temperature_max * 0.8:  # Warning à 80%
                    level = 'criticals' if temperature > device.seuil_temperature_max else 'warnings'
                    analysis[level].append({
                        'metric': 'temperature',
                        'value': temperature,
                        'threshold': device.seuil_temperature_max,
                        'type': 'approaching_limit' if level == 'warnings' else 'above_maximum',
                        'unit': '°C'
                    })
                    if level == 'criticals':
                        analysis['all_ok'] = False
            
        except Exception as e:
            print(f"Erreur analyse seuils: {e}")
        
        return analysis
    


    def _save_device_data_with_processing(self, device, status_data):
        """Sauvegarder les données avec traitement OPTIMISÉ - Version corrigée ultra-rapide"""
        try:
            if not status_data.get("success") or not device.is_assigne():
                return
            
            values = status_data.get("values", {})
            timestamp = datetime.utcnow()
            
            # ✅ SUPPRESSION COMPLÈTE TuyaToDeviceDataService pour performance
            # Création directe classique (beaucoup plus rapide)
            device_data = DeviceData(
                appareil_id=device.id,
                client_id=device.client_id,
                horodatage=timestamp,
                tension=values.get("tension"),
                courant=values.get("courant"),
                puissance=values.get("puissance"),
                energie=values.get("energie"),
                temperature=values.get("temperature"),
                humidite=values.get("humidite"),
                etat_switch=values.get("etat_switch"),
                donnees_brutes=values
            )
            
            # Ajouter à la session DB
            db.session.add(device_data)
            
            # ✅ ANALYSE RAPIDE : AlertService en mode simplifié
            if hasattr(self, '_alert_service') and self._alert_service:
                try:
                    # Mode rapide sans cache complexe
                    alert_result = self._alert_service.analyser_et_creer_alertes(
                        device_data, device, {'use_cache': False, 'fast_mode': True}
                    )
                    
                    if alert_result.get('success', True):
                        nb_alertes = alert_result.get('nb_alertes', 0)
                        if nb_alertes > 0:
                            print(f"🔔 {nb_alertes} alertes pour {device.nom_appareil}")
                            
                except Exception as e:
                    # Skip alertes en cas d'erreur pour ne pas ralentir
                    logging.debug(f"Skip alertes pour {device.nom_appareil}: {e}")
            
            # ✅ PROTECTION : Seulement si activée
            if device.protection_automatique_active:
                try:
                    protection_result = self._process_protection_monitoring(device, values)
                    if protection_result.get('protection_triggered'):
                        print(f"🚨 Protection déclenchée pour {device.nom_appareil}")
                except Exception as e:
                    logging.debug(f"Skip protection pour {device.nom_appareil}: {e}")
            
            # Mettre à jour dernière donnée
            device.derniere_donnee = timestamp
            
            # ✅ COMMIT DIFFÉRÉ : Ne pas commit ici pour performance
            # Le commit sera fait en batch dans la méthode appelante
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde données {device.tuya_device_id}: {e}")
            


    def _check_thresholds_and_create_alerts_fallback(self, device, values):
        """Méthode fallback pour création d'alertes classiques (renommée)"""
        try:
            alerts_to_create = []
            
            # Vérifier tension
            tension = values.get("tension")
            if tension:
                if device.seuil_tension_min and tension < device.seuil_tension_min:
                    alerts_to_create.append({
                        "type": "seuil_depasse",
                        "gravite": "warning",
                        "titre": "Tension trop basse",
                        "message": f"Tension {tension}V inférieure au seuil minimum {device.seuil_tension_min}V",
                        "valeur_mesuree": tension,
                        "valeur_seuil": device.seuil_tension_min,
                        "unite": "V"
                    })
                elif device.seuil_tension_max and tension > device.seuil_tension_max:
                    alerts_to_create.append({
                        "type": "seuil_depasse",
                        "gravite": "critique",
                        "titre": "Tension trop élevée",
                        "message": f"Tension {tension}V supérieure au seuil maximum {device.seuil_tension_max}V",
                        "valeur_mesuree": tension,
                        "valeur_seuil": device.seuil_tension_max,
                        "unite": "V"
                    })
            
            # Vérifier courant
            courant = values.get("courant")
            if courant and device.seuil_courant_max and courant > device.seuil_courant_max:
                alerts_to_create.append({
                    "type": "seuil_depasse",
                    "gravite": "warning",
                    "titre": "Courant élevé",
                    "message": f"Courant {courant}A supérieur au seuil {device.seuil_courant_max}A",
                    "valeur_mesuree": courant,
                    "valeur_seuil": device.seuil_courant_max,
                    "unite": "A"
                })
            
            # Vérifier puissance
            puissance = values.get("puissance")
            if puissance and device.seuil_puissance_max and puissance > device.seuil_puissance_max:
                alerts_to_create.append({
                    "type": "seuil_depasse",
                    "gravite": "warning",
                    "titre": "Puissance élevée",
                    "message": f"Puissance {puissance}W supérieure au seuil {device.seuil_puissance_max}W",
                    "valeur_mesuree": puissance,
                    "valeur_seuil": device.seuil_puissance_max,
                    "unite": "W"
                })
            
            # Créer les alertes (méthode classique)
            for alert_data in alerts_to_create:
                # Vérifier qu'une alerte similaire n'existe pas déjà (dernières 5 minutes)
                recent_alert = Alert.query.filter_by(
                    appareil_id=device.id,
                    type_alerte=alert_data["type"],
                    statut='nouvelle'
                ).filter(
                    Alert.date_creation > datetime.utcnow() - timedelta(minutes=5)
                ).first()
                
                if not recent_alert:
                    alert = Alert(
                        client_id=device.client_id,
                        appareil_id=device.id,
                        type_alerte=alert_data["type"],
                        gravite=alert_data["gravite"],
                        titre=alert_data["titre"],
                        message=alert_data["message"],
                        valeur_mesuree=alert_data["valeur_mesuree"],
                        valeur_seuil=alert_data["valeur_seuil"],
                        unite=alert_data["unite"]
                    )
                    db.session.add(alert)
            
        except Exception as e:
            print(f"❌ Erreur vérification seuils fallback: {e}")
    
    def _log_device_action(self, device, action_type, details, result='success', user_id=None, ip_address=None, user_agent=None):
        """Méthode interne pour logger les actions sur les appareils."""
        try:
            # Utilisez la méthode statique log_action de la classe DeviceActionLog
            DeviceActionLog.log_action(
                device_id=device.id,
                client_id=device.client_id,
                action_type=action_type,
                result=result,
                details=details,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            print(f"✅ Action '{action_type}' loggée pour l'appareil {device.nom_appareil}.")
        except Exception as e:
            print(f"❌ Erreur lors du logging de l'action '{action_type}' pour {device.nom_appareil}: {e}") 


    # =================== MÉTHODES DE RÉCUPÉRATION AVANCÉES ===================
    
    def get_all_devices(self, utilisateur=None, include_non_assignes=False, refresh_status=False, use_cache=True):
        """Récupérer tous les appareils OPTIMISÉ - Version ultra-rapide sans doubles appels"""
        try:
            # Cache key basé sur les paramètres
            cache_suffix = f"{utilisateur.id if utilisateur else 'none'}_{include_non_assignes}_{refresh_status}"
            cache_key = f"devices_query:{cache_suffix}"

            # ✅ CACHE EN PRIORITÉ avec TTL plus long
            if use_cache:
                cached_result = self._get_generic_cache(cache_key)
                if cached_result:
                    print(f"📦 Liste appareils depuis cache")
                    return cached_result

            # ✅ SYNCHRONISATION CONDITIONNELLE seulement si nécessaire
            if refresh_status:
                print("🔄 Actualisation des statuts (sync globale)...")
                sync_result = self.import_tuya_devices(use_cache=use_cache, force_refresh=False)
                if not sync_result.get("success"):
                    print(f"⚠️ Échec synchronisation: {sync_result.get('error')}")
                else:
                    db.session.expire_all()

            # Récupération selon permissions (inchangé)
            if utilisateur and utilisateur.is_superadmin():
                devices = Device.query.all() if include_non_assignes else Device.query.filter_by(statut_assignation='assigne').all()
            elif utilisateur:
                devices = Device.get_assignes_client(utilisateur.client_id)
            else:
                devices = Device.get_non_assignes() if include_non_assignes else []

            # ✅ PRÉPARATION OPTIMISÉE : SANS appels API individuels
            enriched_devices = []
            for device in devices:
                # ✅ VERSION RAPIDE : Utiliser seulement les données en base
                device_dict = self._device_to_dict_enhanced(device)

                # ✅ SUPPRESSION COMPLÈTE des appels temps réel individuels
                # Cette section causait les doubles appels et la lenteur :
                # try:
                #     real_time = self.get_device_real_time_data(device.tuya_device_id, use_cache=use_cache)
                #     ...
                # except Exception as e:
                #     ...

                # ✅ UTILISER LES DONNÉES DE LA BASE (beaucoup plus rapide)
                device_dict["etat"] = device.etat_actuel_tuya
                device_dict["is_online"] = device.en_ligne
                device_dict["last_update"] = device.derniere_maj_etat_tuya.isoformat() if device.derniere_maj_etat_tuya else None

                enriched_devices.append(device_dict)

            # Statistiques enrichies (optimisées)
            online_count = sum(1 for d in enriched_devices if d.get("is_online"))
            offline_count = len(enriched_devices) - online_count
            protection_active = sum(1 for d in devices if getattr(d, 'protection_automatique_active', False))
            programmation_active = sum(1 for d in devices if getattr(d, 'programmation_active', False))

            result = {
                "success": True,
                "devices": enriched_devices,
                "count": len(enriched_devices),
                "last_sync": datetime.utcnow().isoformat() if refresh_status else None,
                "stats": {
                    "total": len(enriched_devices),
                    "online": online_count,
                    "offline": offline_count,
                    "protection_active": protection_active,
                    "programmation_active": programmation_active,
                    "sync_method": "optimized_db_only" if not refresh_status else "sync_with_db"
                },
                "performance": {
                    "method": "database_only",
                    "no_individual_api_calls": True,
                    "cache_enabled": use_cache
                }
            }

            # ✅ CACHE PLUS LONG pour éviter appels fréquents
            if use_cache:
                ttl = 300  # 5 minutes au lieu de 2 minutes
                self._set_generic_cache(cache_key, result, ttl=ttl)

            print(f"📊 Appareils récupérés (OPTIMISÉ): {len(enriched_devices)} ({online_count} 🟢, {offline_count} 🔴)")
            return result

        except Exception as e:
            print(f"❌ Erreur récupération appareils: {e}")
            return {"success": False, "error": str(e)}

    
    def get_non_assigned_devices(self, refresh_status=False, use_cache=True):
        """Récupérer appareils non-assignés OPTIMISÉ - Version ultra-rapide sans doubles appels"""
        try:
            cache_key = f"non_assigned_devices_{refresh_status}"

            # ✅ CACHE EN PRIORITÉ avec vérification étendue
            if use_cache:
                cached_result = self._get_generic_cache(cache_key)
                if cached_result:
                    print("📦 Appareils non-assignés depuis cache")
                    return cached_result

            # ✅ SYNCHRONISATION CONDITIONNELLE seulement si nécessaire
            if refresh_status:
                print("🔄 Sync globale pour appareils non-assignés...")
                sync_result = self.import_tuya_devices(use_cache=use_cache, force_refresh=False)
                if not sync_result.get("success"):
                    print(f"⚠️ Échec synchronisation: {sync_result.get('error')}")
                else:
                    db.session.expire_all()

            # Récupération des appareils non-assignés
            devices = Device.get_non_assignes()

            # ✅ TRAITEMENT OPTIMISÉ : SANS appels API individuels
            enriched_devices = []
            for device in devices:
                # ✅ VERSION RAPIDE : Pas d'enrichissement lourd
                device_dict = device.to_dict(include_stats=False, include_tuya_info=True)

                # ✅ SUPPRESSION COMPLÈTE des appels temps réel individuels
                # Cette section causait les doubles appels et la lenteur :
                # try:
                #     real_time = self.get_device_real_time_data(device.tuya_device_id, use_cache=use_cache)
                #     if real_time.get("success"):
                #         valeurs = real_time.get("data", {})
                #         switch_value = valeurs.get("switch") or valeurs.get("power")
                #         device_dict["etat"] = switch_value in [True, "true", "on", "ON", 1, "1"]
                #         device_dict["is_online"] = real_time.get("is_online", False)
                #     else:
                #         device_dict["etat"] = None
                #         device_dict["is_online"] = False
                # except Exception as e:
                #     print(f"⚠️ Erreur temps réel {device.id}: {e}")
                #     device_dict["etat"] = None
                #     device_dict["is_online"] = False

                # ✅ UTILISER LES DONNÉES DE LA BASE (beaucoup plus rapide)
                device_dict["etat"] = device.etat_actuel_tuya
                device_dict["is_online"] = device.en_ligne
                device_dict["last_update"] = device.derniere_maj_etat_tuya.isoformat() if device.derniere_maj_etat_tuya else None
                
                # Infos supplémentaires pour les non-assignés
                device_dict["status"] = "non_assigne"
                device_dict["available_for_assignment"] = True

                enriched_devices.append(device_dict)

            # Statistiques optimisées
            online_count = sum(1 for d in enriched_devices if d.get("is_online"))
            offline_count = len(enriched_devices) - online_count

            result = {
                "success": True,
                "count": len(enriched_devices),
                "devices": enriched_devices,
                "stats": {
                    "total": len(enriched_devices),
                    "online": online_count,
                    "offline": offline_count,
                    "all_non_assigned": True
                },
                "last_refresh": datetime.utcnow().isoformat() if refresh_status else None,
                "performance": {
                    "method": "database_only",
                    "no_individual_api_calls": True,
                    "optimized": True
                }
            }

            # ✅ CACHE PLUS LONG pour éviter appels fréquents
            if use_cache:
                ttl = 300  # 5 minutes au lieu de 90 secondes
                self._set_generic_cache(cache_key, result, ttl=ttl)

            print(f"📊 Appareils non-assignés (OPTIMISÉ): {len(enriched_devices)} ({online_count} 🟢, {offline_count} 🔴)")
            return result

        except Exception as e:
            print(f"❌ Erreur appareils non-assignés: {e}")
            return {"success": False, "error": str(e)}

    
    def get_assigned_devices(self, utilisateur, refresh_status=False, use_cache=True):
        """Récupérer appareils assignés à un utilisateur"""
        try:
            return self.get_all_devices(
                utilisateur=utilisateur,
                include_non_assignes=False,
                refresh_status=refresh_status,
                use_cache=use_cache
            )
        except Exception as e:
            print(f"❌ Erreur appareils assignés: {e}")
            return {"success": False, "error": str(e)}
    
    # =================== ASSIGNATION ET GESTION ===================
    
    def assign_device_to_client(self, tuya_device_id, client_id, site_id, utilisateur_assigneur_id=None):
        """Assigner un appareil à un client avec cache invalidation"""
        try:
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            if device.is_assigne():
                return {"success": False, "error": "Appareil déjà assigné"}
            
            success, message = device.assigner_a_client(client_id, site_id, utilisateur_assigneur_id)
            
            # Invalider caches liés
            if success:
                self._invalidate_device_cache(tuya_device_id)
                self._invalidate_assignment_caches()
            
            return {
                "success": success,
                "message": message,
                "device": self._device_to_dict_enhanced(device) if success else None
            }
            
        except Exception as e:
            print(f"❌ Erreur assignation: {e}")
            return {"success": False, "error": str(e)}
    
    def unassign_device(self, tuya_device_id):
        """Désassigner un appareil avec nettoyage"""
        try:
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            if not device.is_assigne():
                return {"success": False, "error": "Appareil déjà non-assigné"}
            
            # Désactiver protection et programmation avant désassignation
            if device.protection_automatique_active:
                device.disable_protection()
            
            if device.programmation_active:
                device.disable_programmation()
            
            success, message = device.desassigner()
            
            # Invalider caches
            if success:
                self._invalidate_device_cache(tuya_device_id)
                self._invalidate_assignment_caches()
            
            return {
                "success": success,
                "message": message,
                "device": self._device_to_dict_enhanced(device) if success else None
            }
            
        except Exception as e:
            print(f"❌ Erreur désassignation: {e}")
            return {"success": False, "error": str(e)}
    
    # =================== HISTORIQUE ET DONNÉES ===================
    
    def get_device_history(self, tuya_device_id, limit=100, hours_back=24, use_cache=True):
        """Récupérer historique avec cache"""
        try:
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            cache_key = f"device_history:{device.id}:{hours_back}h:{limit}"
            
            # Cache check
            if use_cache:
                cached_result = self._get_generic_cache(cache_key)
                if cached_result:
                    return cached_result
            
            # Récupération depuis DB
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            data = DeviceData.query.filter_by(appareil_id=device.id)\
                                  .filter(DeviceData.horodatage >= start_time)\
                                  .order_by(DeviceData.horodatage.desc())\
                                  .limit(limit).all()
            
            # Analyse des données
            analysis = self._analyze_device_data_trends(data) if data else {}
            
            result = {
                "success": True,
                "device_id": tuya_device_id,
                "device_name": device.nom_appareil,
                "hours_back": hours_back,
                "count": len(data),
                "data": [d.to_dict() for d in data],
                "analysis": analysis,
                "period": {
                    "start": start_time.isoformat(),
                    "end": datetime.utcnow().isoformat()
                }
            }
            
            # Cache
            if use_cache:
                self._set_generic_cache(cache_key, result, ttl=300)  # 5 minutes
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur historique: {e}")
            return {"success": False, "error": str(e)}
    
    # =================== ANALYSE ET DIAGNOSTICS ===================
    
    def get_device_real_time_data(self, tuya_device_id, use_cache=True):
        """Données temps réel enrichies"""
        try:
            status_result = self.get_device_status(tuya_device_id, use_cache=use_cache)
            
            if not status_result.get("success"):
                return status_result
            
            device = Device.get_by_tuya_id(tuya_device_id)
            is_online = status_result.get("is_online", False)
            real_time_data_values = status_result.get("values", {})
            
            # 🔍 Extraction explicite de l'état switch
            etat_switch = None
            for key in ['switch', 'switch_1', 'power']:
                if key in real_time_data_values:
                    etat_switch = real_time_data_values[key]
                    break
            
            result = {
                "success": True,
                "device_id": tuya_device_id,
                "device_name": device.nom_appareil if device else "Inconnu",
                "is_online": is_online,
                "etat": etat_switch,  # ✅ Ce champ est celui que tu veux dans le frontend
                "data": real_time_data_values,
                "timestamp": datetime.utcnow().isoformat(),
                "enhanced_status": status_result
            }
            
            if is_online and device:
                result["recommendations"] = self._generate_device_recommendations(device, real_time_data_values)
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur données temps réel: {e}")
            return {"success": False, "error": str(e)}

    
    def batch_check_devices_status(self, device_ids_list, use_cache=True):
        """Vérification batch optimisée"""
        try:
            if not device_ids_list:
                return {"success": False, "error": "Liste d'IDs requise"}
            
            cache_key = f"batch_status:{':'.join(sorted(device_ids_list))}"
            
            # Cache check
            if use_cache:
                cached_result = self._get_generic_cache(cache_key)
                if cached_result:
                    return cached_result
            
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion Tuya impossible"}
            
            # Récupération batch depuis Tuya
            devices_response = self.tuya_client.get_all_devices_with_details()
            if not devices_response.get("success"):
                return {"success": False, "error": "Erreur récupération Tuya"}
            
            tuya_devices = devices_response.get("result", [])
            tuya_status_map = {d.get("id"): d.get("isOnline", False) for d in tuya_devices if d.get("id")}
            
            # Traitement des appareils demandés
            results = []
            updated_count = 0
            
            for device_id in device_ids_list:
                tuya_status = tuya_status_map.get(device_id)
                device = Device.get_by_tuya_id(device_id)
                
                if device and tuya_status is not None:
                    old_status = device.en_ligne
                    device.en_ligne = tuya_status
                    
                    if old_status != tuya_status:
                        updated_count += 1
                        self._invalidate_device_cache(device_id)
                    
                    results.append({
                        "device_id": device_id,
                        "device_name": device.nom_appareil,
                        "is_online": tuya_status,
                        "changed": old_status != tuya_status,
                        "old_status": old_status,
                        "protection_active": device.protection_automatique_active,
                        "programmation_active": device.programmation_active
                    })
                else:
                    results.append({
                        "device_id": device_id,
                        "device_name": "Inconnu",
                        "is_online": tuya_status,
                        "changed": False,
                        "error": "Appareil non trouvé" if not device else "Statut Tuya manquant"
                    })
            
            # Commit si changements
            if updated_count > 0:
                db.session.commit()
            
            result = {
                "success": True,
                "checked_count": len(device_ids_list),
                "updated_count": updated_count,
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache
            if use_cache:
                self._set_generic_cache(cache_key, result, ttl=30)  # 30 secondes
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur batch check: {e}")
            return {"success": False, "error": str(e)}
    
    # =================== SYNCHRONISATION ET MAINTENANCE ===================
    
    def sync_all_devices(self, force_refresh=True):
        """Synchronisation complète optimisée"""
        try:
            print("🔄 Synchronisation complète des appareils...")
            
            # Import depuis Tuya (cela met déjà à jour les appareils existants et en crée de nouveaux)
            # Assurez-vous que import_tuya_devices met à jour l'état en ligne et l'état du switch
            import_result = self.import_tuya_devices(use_cache=not force_refresh, force_refresh=force_refresh)
            
            if not import_result.get("success"):
                return import_result
            
            # NOUVEAU : Mettre à jour l'état ON/OFF pour tous les appareils après l'import
            # C'est important car import_tuya_devices pourrait ne pas récupérer l'état du switch
            # ou vous voulez une mise à jour fraîche pour tous.
            
            # Récupérer tous les appareils de notre DB
            all_devices_in_db = Device.query.all()
            
            for device in all_devices_in_db:
                try:
                    # Récupérer le statut le plus récent de Tuya (sans cache)
                    status_result = self.get_device_status(device.tuya_device_id, use_cache=False)
                    
                    if status_result.get("success"):
                        # Mettre à jour le statut en ligne (en_ligne)
                        device.update_online_status(status_result.get("is_online", False))
                        
                        # Mettre à jour l'état ON/OFF (etat_actuel_tuya)
                        if "switch" in status_result.get("values", {}):
                            device.etat_actuel_tuya = status_result["values"]["switch"]
                            device.derniere_maj_etat_tuya = datetime.utcnow()
                            db.session.add(device) # Marquer l'objet comme modifié
                        
                    else:
                        # Si la récupération du statut échoue, marquer l'appareil comme hors ligne
                        device.update_online_status(False)
                        print(f"⚠️ Impossible de récupérer le statut de {device.nom_appareil} ({device.tuya_device_id}).")
                except Exception as e:
                    print(f"❌ Erreur lors de la mise à jour du statut de {device.nom_appareil}: {e}")
                    device.update_online_status(False) # Marquer comme hors ligne en cas d'erreur
            
            db.session.commit() # Commiter tous les changements après la boucle
            
            # Exécuter actions programmées en attente
            scheduled_result = self.execute_scheduled_actions()
            
            # Statistiques finales
            all_devices = Device.query.all() # Re-query pour les stats à jour
            online_final = Device.query.filter_by(en_ligne=True).count()
            offline_final = Device.query.filter_by(en_ligne=False).count()
            
            return {
                "success": True,
                "message": f"Synchronisation terminée: {len(all_devices)} appareils",
                "import_stats": import_result.get("statistiques", {}),
                "scheduled_actions": scheduled_result,
                "final_stats": {
                    "total": len(all_devices),
                    "online": online_final,
                    "offline": offline_final,
                    "protection_active": Device.query.filter_by(protection_automatique_active=True).count(),
                    "programmation_active": Device.query.filter_by(programmation_active=True).count()
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erreur synchronisation: {e}")
            db.session.rollback() # Rollback en cas d'erreur
            return {"success": False, "error": str(e)}

    
    def get_device_statistics(self, include_advanced=True):
        """Statistiques avancées des appareils"""
        try:
            base_stats = Device.count_by_status()
            
            # Statistiques de base
            advanced_stats = {
                'en_ligne': Device.query.filter_by(en_ligne=True).count(),
                'hors_ligne': Device.query.filter_by(en_ligne=False).count(),
                'actifs': Device.query.filter_by(actif=True).count(),
                'inactifs': Device.query.filter_by(actif=False).count()
            }
            
            if include_advanced:
                # Statistiques avancées
                advanced_stats.update({
                    'protection_active': Device.query.filter_by(protection_automatique_active=True).count(),
                    'programmation_active': Device.query.filter_by(programmation_active=True).count(),
                    'mode_manuel': Device.query.filter_by(mode_manuel_actif=True).count(),
                    'protection_declenchee': Device.query.filter_by(protection_status='protected').count(),
                    'par_type_systeme': {
                        'monophase': Device.query.filter_by(type_systeme='monophase').count(),
                        'triphase': Device.query.filter_by(type_systeme='triphase').count()
                    }
                })
                
                # Dernière synchronisation
                last_sync = self._get_last_sync_info()
                if last_sync:
                    advanced_stats['last_sync'] = last_sync
            
            return {
                "success": True, 
                "statistiques": {**base_stats, **advanced_stats},
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erreur statistiques: {e}")
            return {"success": False, "error": str(e)}
    
    # =================== MÉTHODES UTILITAIRES INTERNES ===================
    
    def _device_to_dict_enhanced(self, device):
        """Conversion enrichie d'un appareil en dictionnaire avec état switch"""
        try:
            base_dict = device.to_dict(include_stats=True, include_tuya_info=True)

            # Protection active
            if device.protection_automatique_active:
                base_dict['protection_config'] = device.get_protection_config()
            
            # Programmation active
            if device.programmation_active:
                base_dict['horaires_config'] = device.get_horaires_config()
            
            # Statut de santé
            base_dict['health_status'] = self._get_device_health_status(device)
            
            # Infos de cache
            cached_status = self._get_cached_device_status(device.tuya_device_id)
            if cached_status:
                base_dict['cache_info'] = {
                    'has_cached_status': True,
                    'cached_at': cached_status.get('cached_at')
                }

            # ✅ Nouvel ajout : État réel (allumé/éteint) → "etat_switch"
            try:
                if device.en_ligne and self.tuya_client:
                    status = self.tuya_client.get_device_current_values(device.tuya_device_id)
                    if status.get('success'):
                        base_dict['etat_switch'] = status.get('values', {}).get('etat_switch')
                    else:
                        base_dict['etat_switch'] = None
                else:
                    base_dict['etat_switch'] = None
            except Exception as e:
                print(f"⚠️ Erreur état switch pour {device.tuya_device_id}: {e}")
                base_dict['etat_switch'] = None
            
            return base_dict

        except Exception as e:
            print(f"❌ Erreur conversion device dict: {e}")
            return device.to_dict() if hasattr(device, 'to_dict') else {}

    
    def _get_device_health_status(self, device):
        """Évaluation rapide de la santé d'un appareil"""
        if not device.en_ligne:
            return 'offline'
        
        if device.protection_status == 'protected':
            return 'protected'
        
        if device.mode_manuel_actif:
            return 'manual_mode'
        
        # Vérifier dernière donnée
        if device.derniere_donnee:
            silence_hours = (datetime.utcnow() - device.derniere_donnee).total_seconds() / 3600
            if silence_hours > 2:
                return 'silent'
        
        return 'healthy'
    
    def _analyze_device_data_trends(self, data_points):
        """Analyse des tendances dans les données"""
        if len(data_points) < 5:
            return {"insufficient_data": True}
        
        analysis = {
            "data_count": len(data_points),
            "time_span_hours": None,
            "trends": {},
            "alerts_detected": 0
        }
        
        try:
            # Calculer span temporel
            if data_points:
                latest = data_points[0].horodatage
                oldest = data_points[-1].horodatage
                analysis["time_span_hours"] = (latest - oldest).total_seconds() / 3600
            
            # Analyser chaque métrique
            metrics = ['tension', 'courant', 'puissance', 'temperature']
            
            for metric in metrics:
                values = [getattr(dp, metric) for dp in data_points if getattr(dp, metric) is not None]
                
                if len(values) >= 3:
                    analysis["trends"][metric] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "variation": max(values) - min(values),
                        "trend": self._calculate_simple_trend(values)
                    }
            
            return analysis
            
        except Exception as e:
            print(f"Erreur analyse tendances: {e}")
            return {"error": str(e)}
    
    def _calculate_simple_trend(self, values):
        """Calcul de tendance simple"""
        if len(values) < 3:
            return "stable"
        
        mid = len(values) // 2
        first_half = sum(values[:mid]) / mid
        second_half = sum(values[mid:]) / (len(values) - mid)
        
        change_pct = ((second_half - first_half) / first_half) * 100 if first_half > 0 else 0
        
        if change_pct > 5:
            return "increasing"
        elif change_pct < -5:
            return "decreasing"
        else:
            return "stable"
    
    def _generate_device_recommendations(self, device, current_values):
        """Générer recommandations pour un appareil"""
        recommendations = []
        
        try:
            # Recommandations basées sur les seuils
            threshold_analysis = self._analyze_thresholds(device, current_values)
            
            if not threshold_analysis.get('all_ok'):
                if threshold_analysis.get('criticals'):
                    recommendations.append({
                        "type": "urgent",
                        "message": "Intervention urgente requise - Seuils critiques dépassés",
                        "action": "Vérifier immédiatement l'installation"
                    })
                
                if threshold_analysis.get('warnings'):
                    recommendations.append({
                        "type": "maintenance",
                        "message": "Maintenance préventive recommandée",
                        "action": "Planifier une inspection"
                    })
            
            # Recommandations protection
            if not device.protection_automatique_active and device.is_assigne():
                recommendations.append({
                    "type": "security",
                    "message": "Protection automatique non activée",
                    "action": "Configurer la protection automatique"
                })
            
            # Recommandations programmation
            if not device.programmation_active and device.is_assigne():
                recommendations.append({
                    "type": "optimization",
                    "message": "Programmation horaire non configurée",
                    "action": "Configurer les horaires d'allumage/extinction"
                })
            
            return recommendations
            
        except Exception as e:
            print(f"Erreur génération recommandations: {e}")
            return []
    
    def _invalidate_assignment_caches(self):
        """Invalider les caches liés aux assignations"""
        try:
            if not self.redis:
                return
            
            patterns = [
                "devices_query:*",
                "non_assigned_devices_*"
            ]
            
            for pattern in patterns:
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
            
        except Exception as e:
            print(f"Erreur invalidation cache assignation: {e}")
    
    def _set_generic_cache(self, key, data, ttl=300):
        """Helper pour cache générique"""
        try:
            if not self.redis:
                return
            
            cache_data = {
                'data': data,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            
        except Exception as e:
            print(f"Erreur set cache {key}: {e}")
    
    def _get_generic_cache(self, key):
        """Helper pour récupération cache générique"""
        try:
            if not self.redis:
                return None
            
            cached_data = self.redis.get(key)
            if cached_data:
                data = json.loads(cached_data)
                return data.get('data')
            
            return None
            
        except Exception as e:
            print(f"Erreur get cache {key}: {e}")
            return None
    
    def _determine_device_type(self, category, device_data):
        """Déterminer le type d'appareil (méthode existante maintenue)"""
        category_mapping = {
            'cz': 'prise_connectee',
            'kg': 'interrupteur',
            'sp': 'camera',
            'wk': 'thermostat',
            'dlq': 'appareil_generique'
        }
        
        # Détection spéciale pour ATORCH
        device_name = device_data.get("name", "").lower()
        
        if "atorch" in device_name or "energy meter" in device_name:
            return 'atorch_compteur_energie'
        elif "gr2pws" in device_data.get("model", ""):
            return 'atorch_argp2ws'
        
        return category_mapping.get(category, 'appareil_generique')
    
    # =================== MÉTHODES DE DIAGNOSTIC ===================
    
    def get_service_health(self):
        """Diagnostic complet du service"""
        try:
            health = {
                "service": "DeviceService",
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "unknown",
                "components": {}
            }
            
            # Test Redis
            if self.redis:
                try:
                    self.redis.ping()
                    health["components"]["redis"] = {
                        "status": "healthy",
                        "cache_enabled": True
                    }
                except Exception as e:
                    health["components"]["redis"] = {
                        "status": "error",
                        "error": str(e)
                    }
            else:
                health["components"]["redis"] = {
                    "status": "disabled",
                    "cache_enabled": False
                }
            
            # Test Tuya
            try:
                tuya_connected = self.tuya_client.reconnect_if_needed()
                health["components"]["tuya"] = {
                    "status": "healthy" if tuya_connected else "error",
                    "connected": tuya_connected
                }
            except Exception as e:
                health["components"]["tuya"] = {
                    "status": "error",
                    "error": str(e)
                }
            
            # Test Database
            try:
                device_count = Device.query.count()
                health["components"]["database"] = {
                    "status": "healthy",
                    "device_count": device_count
                }
            except Exception as e:
                health["components"]["database"] = {
                    "status": "error",
                    "error": str(e)
                }
            
            # Déterminer statut global
            error_components = [c for c in health["components"].values() if c.get("status") == "error"]
            
            if error_components:
                health["overall_status"] = "degraded"
            else:
                health["overall_status"] = "healthy"
            
            return {"success": True, "health": health}
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "health": {
                    "service": "DeviceService",
                    "overall_status": "error",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
    
    def cleanup_cache(self, cache_type=None):
        """Nettoyage du cache"""
        try:
            if not self.redis:
                return {"success": False, "error": "Redis non disponible"}
            
            if cache_type:
                # Nettoyage sélectif
                patterns = {
                    'device_status': 'device_status:*',
                    'device_data': 'device_data:*',
                    'devices_list': 'devices_list_*',
                    'queries': 'devices_query:*'
                }
                
                pattern = patterns.get(cache_type)
                if not pattern:
                    return {"success": False, "error": f"Type de cache inconnu: {cache_type}"}
                
                keys = self.redis.keys(pattern)
                deleted_count = self.redis.delete(*keys) if keys else 0
                
                message = f"Cache {cache_type} nettoyé: {deleted_count} clés supprimées"
            else:
                # Nettoyage complet
                deleted_count = self._invalidate_all_cache()
                message = f"Cache complet nettoyé: {deleted_count} clés supprimées"
            
            return {
                "success": True,
                "message": message,
                "deleted_keys": deleted_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_cache_statistics(self):
        """Statistiques détaillées du cache"""
        try:
            if not self.redis:
                return {
                    "success": False,
                    "error": "Redis non disponible",
                    "cache_enabled": False
                }
            
            cache_types = {
                'device_status': 'device_status:*',
                'device_data': 'device_data:*',
                'device_data_windows': 'device_data_window:*',
                'devices_lists': 'devices_list_*',
                'query_cache': 'devices_query:*',
                'generic_cache': 'non_assigned_devices_*',
                'sync_info': 'last_device_sync'
            }
            
            cache_stats = {}
            total_keys = 0
            
            for cache_type, pattern in cache_types.items():
                if pattern.endswith('*'):
                    keys = self.redis.keys(pattern)
                    count = len(keys)
                else:
                    count = 1 if self.redis.exists(pattern) else 0
                
                cache_stats[cache_type] = count
                total_keys += count
            
            # Informations détaillées Redis
            redis_info = self.redis.info('memory')
            
            return {
                "success": True,
                "cache_enabled": True,
                "total_keys": total_keys,
                "keys_by_type": cache_stats,
                "redis_info": {
                    "used_memory_human": redis_info.get('used_memory_human'),
                    "keyspace_hits": redis_info.get('keyspace_hits', 0),
                    "keyspace_misses": redis_info.get('keyspace_misses', 0)
                },
                "ttl_config": self.ttl_config,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =================== MÉTHODES LEGACY (COMPATIBILITÉ) ===================
    
    def check_device_online_status(self, tuya_device_id):
        """Méthode legacy - Utilise maintenant get_device_status"""
        try:
            status_result = self.get_device_status(tuya_device_id, use_cache=False)
            
            if not status_result.get("success"):
                return status_result
            
            device = Device.get_by_tuya_id(tuya_device_id)
            is_online = status_result.get("is_online", False)
            
            return {
                "success": True,
                "device_id": tuya_device_id,
                "is_online": is_online,
                "changed": True,  # Assume changed for legacy compatibility
                "checked_at": datetime.utcnow().isoformat(),
                "enhanced": True  # Flag pour indiquer utilisation nouvelle méthode
            }
            
        except Exception as e:
            print(f"❌ Erreur vérification legacy: {e}")
            return {"success": False, "error": str(e)}
    
    def force_status_from_list_endpoint(self, tuya_device_id):
        """Méthode legacy - Force refresh depuis endpoint liste"""
        try:
            # Invalider cache d'abord
            self._invalidate_device_cache(tuya_device_id)
            
            # Force refresh depuis Tuya
            status_result = self.get_device_status(tuya_device_id, use_cache=False)
            
            if status_result.get("success"):
                device = Device.get_by_tuya_id(tuya_device_id)
                is_online = status_result.get("is_online", False)
                
                return {
                    "success": True,
                    "device_id": tuya_device_id,
                    "new_status": is_online,
                    "source": "forced_refresh",
                    "changed": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return status_result
                
        except Exception as e:
            print(f"❌ Erreur force status: {e}")
            return {"success": False, "error": str(e)}
    
    def refresh_all_device_statuses(self):
        """Méthode legacy - Utilise sync_all_devices"""
        try:
            return self.sync_all_devices(force_refresh=True)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def diagnose_tuya_inconsistency(self, tuya_device_id):
        """Diagnostic des incohérences Tuya (maintenu pour compatibilité)"""
        try:
            print(f"🔬 DIAGNOSTIC incohérences Tuya pour {tuya_device_id}")
            
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion impossible"}
            
            # Test endpoint liste
            devices_response = self.tuya_client.get_all_devices_with_details()
            list_status = None
            if devices_response.get("success"):
                devices = devices_response.get("result", [])
                for device_data in devices:
                    if device_data.get("id") == tuya_device_id:
                        list_status = device_data.get("isOnline")
                        break
            
            # Test endpoint individuel
            individual_response = self.tuya_client.get_device_status(tuya_device_id)
            individual_status = individual_response.get("success", False)
            
            # Test notre cache
            cached_status = self._get_cached_device_status(tuya_device_id)
            
            result = {
                "success": True,
                "device_id": tuya_device_id,
                "endpoint_liste": {
                    "status": list_status,
                    "source": "/v2.0/cloud/thing/device"
                },
                "endpoint_individuel": {
                    "status": individual_status,
                    "source": "/v1.0/iot-03/devices/{id}/status"
                },
                "cache_status": {
                    "has_cache": cached_status is not None,
                    "cached_status": cached_status.get('is_online') if cached_status else None
                },
                "consistent": list_status == individual_status,
                "recommended_source": "endpoint_liste"
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur diagnostic: {e}")
            return {"success": False, "error": str(e)}

    # =================== MÉTHODES D'INTÉGRATION FUTURES ===================
    
    def initialize_extensions(self):
        """Initialiser les extensions d'analyse si disponibles"""
        try:
            extensions_loaded = {
                'alert_service': False,
                'analyseur_triphase': False,
                'protection_extension': False,
                'analysis_extension': False
            }
            
            # Tentative de chargement AlertService
            try:
                from app.services.alert_service import AlertService
                self._alert_service = AlertService(redis_client=self.redis)
                extensions_loaded['alert_service'] = True
                print("✅ AlertService initialisé")
            except ImportError:
                print("⚠️ AlertService non disponible")
            
            # Tentative de chargement AnalyseurTriphase
            try:
                from app.services.analyseur_triphase_service import AnalyseurTriphaseService
                self._analyseur_triphase = AnalyseurTriphaseService(redis_client=self.redis)
                extensions_loaded['analyseur_triphase'] = True
                print("✅ AnalyseurTriphaseService initialisé")
            except ImportError:
                print("⚠️ AnalyseurTriphaseService non disponible")
            
            # Tentative de chargement extensions Protection et Analysis
            try:
                from app.services.device_service_protection_extension import DeviceServiceProtectionExtension
                self._protection_extension = DeviceServiceProtectionExtension(self)
                extensions_loaded['protection_extension'] = True
                print("✅ Protection Extension initialisée")
            except ImportError:
                print("⚠️ Protection Extension non disponible")
            
            try:
                from app.services.device_service_analysis_extension import DeviceServiceAnalysisExtension
                self._analysis_extension = DeviceServiceAnalysisExtension(self)
                extensions_loaded['analysis_extension'] = True
                print("✅ Analysis Extension initialisée")
            except ImportError:
                print("⚠️ Analysis Extension non disponible")
            
            return {
                "success": True,
                "extensions_loaded": extensions_loaded,
                "total_loaded": sum(extensions_loaded.values())
            }
            
        except Exception as e:
            print(f"❌ Erreur initialisation extensions: {e}")
            return {"success": False, "error": str(e)}
    
    def get_extension_status(self):
        """Statut des extensions chargées"""
        try:
            status = {
                'alert_service': hasattr(self, '_alert_service') and self._alert_service is not None,
                'analyseur_triphase': hasattr(self, '_analyseur_triphase') and self._analyseur_triphase is not None,
                'protection_extension': hasattr(self, '_protection_extension') and self._protection_extension is not None,
                'analysis_extension': hasattr(self, '_analysis_extension') and self._analysis_extension is not None
            }
            
            return {
                "success": True,
                "extensions": status,
                "total_active": sum(status.values()),
                "enhancement_available": any(status.values())
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def enhance_with_analysis(self, device_data, device):
        """Point d'intégration pour analyse avancée (si extensions disponibles)"""
        try:
            results = {
                'base_analysis': True,
                'alert_analysis': False,
                'triphase_analysis': False,
                'protection_analysis': False,
                'enhanced_analysis': False
            }
            
            # AlertService si disponible
            if hasattr(self, '_alert_service') and self._alert_service:
                try:
                    alert_result = self._alert_service.analyser_et_creer_alertes(device_data, device)
                    results['alert_analysis'] = alert_result.get('success', False)
                    results['alertes_creees'] = alert_result.get('nb_alertes', 0)
                except Exception as e:
                    print(f"Erreur AlertService: {e}")
            
            # AnalyseurTriphase si disponible et appareil triphasé
            if (hasattr(self, '_analyseur_triphase') and self._analyseur_triphase and 
                device.is_triphase() and device_data.is_triphase()):
                try:
                    triphase_result = self._analyseur_triphase.analyser_donnees_sans_creation_alertes(device_data)
                    results['triphase_analysis'] = triphase_result.get('success', False)
                    results['anomalies_detectees'] = triphase_result.get('nb_anomalies', 0)
                except Exception as e:
                    print(f"Erreur AnalyseurTriphase: {e}")
            
            # Protection Extension si disponible
            if hasattr(self, '_protection_extension') and self._protection_extension:
                try:
                    protection_result = self._protection_extension.enhance_save_device_data_protection(device, device_data)
                    results['protection_analysis'] = protection_result.get('success', False)
                except Exception as e:
                    print(f"Erreur Protection Extension: {e}")
            
            # Analysis Extension si disponible
            if hasattr(self, '_analysis_extension') and self._analysis_extension:
                try:
                    analysis_result = self._analysis_extension.analyser_device_complete_auto(
                        device_data, device, use_cache=True
                    )
                    results['enhanced_analysis'] = analysis_result.get('success', False)
                    results['analysis_summary'] = analysis_result.get('analysis_summary', {})
                except Exception as e:
                    print(f"Erreur Analysis Extension: {e}")
            
            return results
            
        except Exception as e:
            print(f"Erreur enhance_with_analysis: {e}")
            return {'base_analysis': True, 'error': str(e)}

    # =================== MÉTHODES DE SYNCHRONISATION TEMPS RÉEL AMÉLIORÉES ===================

    
    def start_real_time_sync(self):
        """Synchronisation temps réel non disponible"""
        return {
            "success": False,
            "error": "Extension synchronisation temps réel désactivée",
            "alternative": "Utilisez sync_all_devices() pour synchroniser manuellement"
        }
    
    def stop_real_time_sync(self):
        """Arrêter la synchronisation temps réel"""
        return {
            "success": True,
            "message": "Aucune synchronisation automatique à arrêter"
        }
    
    def get_sync_status(self):
        """Statut de synchronisation"""
        return {
            "sync_active": False,
            "mode": "manual_only",
            "extension_available": False,
            "message": "Extension sync désactivée - utilisez sync_all_devices()"
        }
    
    def force_sync_now(self):
        """Forcer synchronisation via méthode existante"""
        try:
            return self.sync_all_devices(force_refresh=True)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sync_single_device_realtime(self, device_id):
        """Synchroniser un appareil via méthode existante"""
        try:
            return self.get_device_status(device_id, use_cache=False)
        except Exception as e:
            return {"success": False, "error": str(e)}



# =================== FIN DE LA CLASSE DeviceService ===================



@property
def protection_extension(self):
    """Accès à l'extension protection"""
    return getattr(self, '_protection_extension', None)

@property
def analysis_extension(self):
    """Accès à l'extension analysis"""
    return getattr(self, '_analysis_extension', None)

@property
def alert_service(self):
    """Accès au service d'alertes"""
    return getattr(self, '_alert_service', None)

def has_extension(self, extension_name):
    """Vérifier si une extension est disponible"""
    extension_map = {
        'protection': '_protection_extension',
        'analysis': '_analysis_extension',
        'alert': '_alert_service'
    }
    
    attr_name = extension_map.get(extension_name)
    if not attr_name:
        return False
    
    return hasattr(self, attr_name) and getattr(self, attr_name) is not None


