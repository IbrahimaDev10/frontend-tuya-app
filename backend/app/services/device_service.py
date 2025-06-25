# device_service.py - Service pour la gestion des appareils IoT avec Redis
# Compatible avec vos modèles Device, DeviceData, Alert, DeviceAccess
# ✅ NOUVEAU : Intégration Redis pour cache et performance

from app.services.tuya_service import TuyaClient
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.alert import Alert
from app.models.device_access import DeviceAccess
from app import db, get_redis  # ✅ NOUVEAU : Import get_redis
from datetime import datetime, timedelta
import json
import logging

class DeviceService:
    """Service pour la gestion des appareils IoT avec cache Redis"""
    
    def __init__(self):
        self.tuya_client = TuyaClient()
        # ✅ NOUVEAU : Redis d'abord, sinon fonctionnement normal
        self.redis = get_redis()
        
        # ✅ NOUVEAU : Configuration TTL depuis settings
        from config.settings import get_config
        config = get_config()
        self.ttl_config = config.REDIS_DEFAULT_TTL
        
        logging.info(f"DeviceService initialisé - Redis: {'✅' if self.redis else '❌'}")
    
    # =================== MÉTHODES REDIS POUR CACHE ===================
    
    def _cache_device_status(self, device_id, status_data, ttl=None):
        """Cache des statuts d'appareils dans Redis"""
        try:
            if not self.redis:
                return
            
            ttl = ttl or self.ttl_config.get('device_status', 30)
            key = f"device_status:{device_id}"
            
            cache_data = {
                'device_id': device_id,
                'is_online': status_data.get('is_online', False),
                'last_values': status_data.get('values', {}),
                'cached_at': datetime.utcnow().isoformat(),
                'tuya_response': status_data
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            logging.debug(f"Status cached for device {device_id}")
            
        except Exception as e:
            logging.error(f"Erreur cache statut device {device_id}: {e}")
    
    def _get_cached_device_status(self, device_id):
        """Récupérer statut depuis cache Redis"""
        try:
            if not self.redis:
                return None
            
            key = f"device_status:{device_id}"
            cached_data = self.redis.get(key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logging.error(f"Erreur récupération cache device {device_id}: {e}")
            return None
    
    def _cache_devices_list(self, devices_data, ttl=None):
        """Cache de la liste des appareils"""
        try:
            if not self.redis:
                return
            
            ttl = ttl or self.ttl_config.get('device_data', 300)
            key = "devices_list_tuya"
            
            cache_data = {
                'devices': devices_data,
                'cached_at': datetime.utcnow().isoformat(),
                'count': len(devices_data)
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            logging.info(f"Liste de {len(devices_data)} appareils mise en cache")
            
        except Exception as e:
            logging.error(f"Erreur cache liste appareils: {e}")
    
    def _get_cached_devices_list(self):
        """Récupérer liste depuis cache"""
        try:
            if not self.redis:
                return None
            
            key = "devices_list_tuya"
            cached_data = self.redis.get(key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logging.error(f"Erreur récupération cache liste: {e}")
            return None
    
    def _cache_device_data(self, device_id, data_values, ttl=None):
        """Cache des données IoT d'un appareil"""
        try:
            if not self.redis:
                return
            
            ttl = ttl or self.ttl_config.get('device_data', 300)
            key = f"device_data:{device_id}:{int(datetime.utcnow().timestamp())}"
            
            cache_data = {
                'device_id': device_id,
                'values': data_values,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            
            # Maintenir une liste des dernières données (sliding window)
            self._maintain_device_data_window(device_id, key)
            
        except Exception as e:
            logging.error(f"Erreur cache données device {device_id}: {e}")
    
    def _maintain_device_data_window(self, device_id, new_key):
        """Maintenir une fenêtre glissante des données en cache"""
        try:
            if not self.redis:
                return
            
            window_key = f"device_data_window:{device_id}"
            
            # Ajouter la nouvelle clé
            self.redis.lpush(window_key, new_key)
            
            # Garder seulement les 100 dernières entrées
            self.redis.ltrim(window_key, 0, 99)
            
            # TTL de la fenêtre = 1 heure
            self.redis.expire(window_key, 3600)
            
        except Exception as e:
            logging.error(f"Erreur maintenance fenêtre device {device_id}: {e}")
    
    def _cache_sync_result(self, sync_stats, ttl=None):
        """Cache du résultat de synchronisation"""
        try:
            if not self.redis:
                return
            
            ttl = ttl or self.ttl_config.get('api_cache', 60)
            key = "last_device_sync"
            
            cache_data = {
                'sync_stats': sync_stats,
                'synced_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            
        except Exception as e:
            logging.error(f"Erreur cache sync result: {e}")
    
    def _get_last_sync_info(self):
        """Récupérer info dernière synchronisation"""
        try:
            if not self.redis:
                return None
            
            key = "last_device_sync"
            cached_data = self.redis.get(key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logging.error(f"Erreur récupération info sync: {e}")
            return None
    
    def _invalidate_device_cache(self, device_id):
        """Invalider le cache d'un appareil spécifique"""
        try:
            if not self.redis:
                return
            
            # Invalider statut
            status_key = f"device_status:{device_id}"
            self.redis.delete(status_key)
            
            # Invalider fenêtre de données
            window_key = f"device_data_window:{device_id}"
            data_keys = self.redis.lrange(window_key, 0, -1)
            
            if data_keys:
                for key in data_keys:
                    if isinstance(key, bytes):
                        key = key.decode()
                    self.redis.delete(key)
                
                self.redis.delete(window_key)
            
            logging.debug(f"Cache invalidé pour device {device_id}")
            
        except Exception as e:
            logging.error(f"Erreur invalidation cache device {device_id}: {e}")
    
    def _invalidate_all_cache(self):
        """Invalider tout le cache des appareils"""
        try:
            if not self.redis:
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
                keys = self.redis.keys(pattern)
                if keys:
                    deleted = self.redis.delete(*keys)
                    total_deleted += deleted
            
            logging.info(f"Cache invalidé: {total_deleted} clés supprimées")
            return total_deleted
            
        except Exception as e:
            logging.error(f"Erreur invalidation cache complet: {e}")
            return 0
    
    # =================== MÉTHODES PRINCIPALES AVEC REDIS ===================
    
    def import_tuya_devices(self, use_cache=True, force_refresh=False):
        """Import avec cache Redis et PRIORITÉ à l'endpoint liste"""
        try:
            print("🔍 Début import appareils Tuya avec cache Redis...")
            
            # ✅ NOUVEAU : Vérifier cache d'abord (sauf si force_refresh)
            if use_cache and not force_refresh:
                cached_devices = self._get_cached_devices_list()
                if cached_devices:
                    cached_at = datetime.fromisoformat(cached_devices['cached_at'])
                    age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
                    
                    if age_minutes < 2:  # Cache valide 2 minutes
                        print(f"📦 Utilisation cache Tuya (âge: {age_minutes:.1f}min)")
                        devices = cached_devices['devices']
                        
                        # Traiter avec les données cachées
                        result = self._process_devices_data(devices, from_cache=True)
                        
                        # Mettre à jour cache sync
                        if result.get("success"):
                            self._cache_sync_result(result.get("statistiques", {}))
                        
                        return result
            
            if not self.tuya_client.auto_connect_from_env():
                return {"success": False, "error": "Impossible de se connecter à Tuya Cloud"}
            
            # Récupération depuis Tuya API
            devices_response = self.tuya_client.get_all_devices_with_details()
            
            if not devices_response.get("success"):
                return {"success": False, "error": devices_response.get("error", "Erreur récupération appareils")}
            
            devices = devices_response.get("result", [])
            print(f"📱 {len(devices)} appareils récupérés depuis Tuya")
            
            # ✅ NOUVEAU : Mettre en cache la liste Tuya
            if use_cache:
                self._cache_devices_list(devices)
            
            # Traiter les données
            result = self._process_devices_data(devices, from_cache=False)
            
            # ✅ NOUVEAU : Cache du résultat de sync
            if result.get("success") and use_cache:
                self._cache_sync_result(result.get("statistiques", {}))
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur import Tuya: {e}")
            db.session.rollback()
            return {"success": False, "error": f"Erreur lors de l'import: {str(e)}"}
    
    def _process_devices_data(self, devices, from_cache=False):
        """Traiter les données d'appareils (depuis API ou cache)"""
        try:
            appareils_importes = 0
            appareils_mis_a_jour = 0
            online_count = 0
            offline_count = 0
            
            source_text = "cache Redis" if from_cache else "API Tuya"
            print(f"🔄 Traitement de {len(devices)} appareils depuis {source_text}")
            
            # ✅ CRÉER UN MAPPING des statuts depuis l'endpoint liste
            device_status_map = {}
            for device_data in devices:
                device_id = device_data.get("id")
                if device_id:
                    is_online = device_data.get("isOnline", False)
                    device_status_map[device_id] = is_online
                    
                    # ✅ NOUVEAU : Cache individuel du statut
                    self._cache_device_status(device_id, {
                        'is_online': is_online,
                        'values': {},
                        'source': source_text
                    })
            
            print(f"📊 Mapping des statuts créé pour {len(device_status_map)} appareils")
            
            for device_data in devices:
                tuya_device_id = device_data.get("id") or device_data.get("device_id")
                if not tuya_device_id:
                    continue
                
                # ✅ UTILISER LE STATUT de l'ENDPOINT LISTE
                is_online = device_status_map.get(tuya_device_id, False)
                device_name = device_data.get("name", f"Appareil {tuya_device_id}")
                
                status_emoji = "🟢" if is_online else "🔴"
                status_text = "EN LIGNE" if is_online else "HORS LIGNE"
                print(f"📡 {device_name}: {status_emoji} {status_text} (depuis {source_text})")
                
                if is_online:
                    online_count += 1
                else:
                    offline_count += 1
                
                # Rechercher appareil existant
                existing_device = Device.get_by_tuya_id(tuya_device_id)
                
                if existing_device:
                    # ✅ MISE À JOUR DIRECTE des attributs
                    old_status = existing_device.en_ligne
                    
                    existing_device.en_ligne = is_online
                    existing_device.tuya_nom_original = device_data.get("name", existing_device.tuya_nom_original)
                    existing_device.tuya_modele = device_data.get("model", existing_device.tuya_modele)
                    existing_device.tuya_version_firmware = device_data.get("sw_ver", existing_device.tuya_version_firmware)
                    
                    if not existing_device.nom_appareil or existing_device.nom_appareil == existing_device.tuya_nom_original:
                        existing_device.nom_appareil = device_name
                    
                    db.session.add(existing_device)
                    appareils_mis_a_jour += 1
                    
                    # ✅ NOUVEAU : Invalider cache si statut changé
                    if old_status != is_online:
                        self._invalidate_device_cache(tuya_device_id)
                        change_text = f"{'🟢' if old_status else '🔴'} → {'🟢' if is_online else '🔴'}"
                        print(f"   🔄 Statut changé: {change_text}")
                
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
                    appareils_importes += 1
            
            # ✅ COMMIT avec gestion d'erreur
            try:
                db.session.flush()
                print("💾 Flush réussi - Préparation du commit...")
                
                db.session.commit()
                print("💾 Commit réussi - Changements sauvegardés")
                
            except Exception as commit_error:
                print(f"❌ Erreur lors du commit: {commit_error}")
                db.session.rollback()
                return {"success": False, "error": f"Erreur commit: {str(commit_error)}"}
            
            print(f"✅ Traitement terminé:")
            print(f"   📊 {appareils_importes} nouveaux, {appareils_mis_a_jour} mis à jour")
            print(f"   🟢 {online_count} en ligne")
            print(f"   🔴 {offline_count} hors ligne")
            print(f"   📦 Source: {source_text}")
            
            return {
                "success": True,
                "message": f"{len(devices)} appareils traités avec succès",
                "statistiques": {
                    "appareils_importes": appareils_importes,
                    "appareils_mis_a_jour": appareils_mis_a_jour,
                    "total": len(devices),
                    "online": online_count,
                    "offline": offline_count,
                    "source": source_text,
                    "cached": from_cache
                }
            }
            
        except Exception as e:
            print(f"❌ Erreur traitement données: {e}")
            db.session.rollback()
            return {"success": False, "error": f"Erreur traitement: {str(e)}"}
    
    def get_device_status(self, tuya_device_id, use_cache=True):
        """Récupérer le statut d'un appareil avec cache Redis"""
        try:
            # ✅ NOUVEAU : Vérifier cache d'abord
            if use_cache:
                cached_status = self._get_cached_device_status(tuya_device_id)
                if cached_status:
                    cached_at = datetime.fromisoformat(cached_status['cached_at'])
                    age_seconds = (datetime.utcnow() - cached_at).total_seconds()
                    
                    if age_seconds < 30:  # Cache valide 30 secondes
                        print(f"📦 Statut depuis cache pour {tuya_device_id} (âge: {age_seconds:.1f}s)")
                        return {
                            "success": True,
                            "values": cached_status['last_values'],
                            "is_online": cached_status['is_online'],
                            "from_cache": True,
                            "cached_at": cached_status['cached_at']
                        }
            
            # Connexion si nécessaire
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion Tuya impossible"}
            
            # Récupération depuis API
            status_response = self.tuya_client.get_device_current_values(tuya_device_id)
            
            if status_response.get("success"):
                # ✅ NOUVEAU : Mettre en cache
                if use_cache:
                    self._cache_device_status(tuya_device_id, status_response)
                
                # ✅ NOUVEAU : Cache des données IoT
                values = status_response.get("values", {})
                if values and use_cache:
                    self._cache_device_data(tuya_device_id, values)
                
                # Sauvegarder en DB si assigné
                device = Device.get_by_tuya_id(tuya_device_id)
                if device and device.is_assigne():
                    self._save_device_data(device, status_response)
                
                # Mettre à jour dernière donnée
                if device:
                    device.update_last_data_time()
                
                # Ajouter info cache
                status_response['from_cache'] = False
                status_response['cached_at'] = datetime.utcnow().isoformat()
            
            return status_response
            
        except Exception as e:
            print(f"❌ Erreur statut appareil {tuya_device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_all_devices(self, utilisateur=None, include_non_assignes=False, refresh_status=True, use_cache=True):
        """Récupérer tous les appareils avec cache intelligent"""
        try:
            # ✅ NOUVEAU : Vérifier cache de synchronisation
            if use_cache and not refresh_status:
                last_sync = self._get_last_sync_info()
                if last_sync:
                    synced_at = datetime.fromisoformat(last_sync['synced_at'])
                    age_minutes = (datetime.utcnow() - synced_at).total_seconds() / 60
                    
                    if age_minutes < 1:  # Cache sync valide 1 minute
                        print(f"📦 Utilisation cache sync (âge: {age_minutes:.1f}min)")
                        refresh_status = False
            
            # Synchronisation si nécessaire
            if refresh_status:
                print("🔄 Actualisation des statuts avant récupération...")
                sync_result = self.import_tuya_devices(use_cache=use_cache)
                if not sync_result.get("success"):
                    print(f"⚠️ Échec synchronisation: {sync_result.get('error')}")
                else:
                    db.session.expire_all()
            
            # Récupération selon permissions
            if utilisateur and utilisateur.is_superadmin():
                if include_non_assignes:
                    devices = Device.query.all()
                else:
                    devices = Device.query.filter_by(statut_assignation='assigne').all()
            elif utilisateur:
                devices = Device.get_assignes_client(utilisateur.client_id)
            else:
                devices = Device.get_non_assignes() if include_non_assignes else []
            
            # Préparer résultat
            result = {
                "success": True,
                "devices": [device.to_dict(include_stats=True, include_tuya_info=True) for device in devices],
                "count": len(devices),
                "last_sync": datetime.utcnow().isoformat() if refresh_status else None,
                "cache_used": use_cache
            }
            
            # Statistiques
            online_count = sum(1 for d in devices if d.en_ligne)
            offline_count = len(devices) - online_count
            
            result["stats"] = {
                "total": len(devices),
                "online": online_count,
                "offline": offline_count,
                "sync_method": "with_cache" if use_cache else "direct_api"
            }
            
            print(f"📊 Appareils récupérés: {len(devices)} ({online_count} 🟢, {offline_count} 🔴)")
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur récupération appareils: {e}")
            return {"success": False, "error": str(e)}
    
    def get_non_assigned_devices(self, refresh_status=True, use_cache=True):
        """Récupérer appareils non-assignés avec cache"""
        try:
            print("🔍 Récupération appareils non-assignés avec cache...")
            
            return self.get_all_devices(
                utilisateur=None,
                include_non_assignes=True,
                refresh_status=refresh_status,
                use_cache=use_cache
            )
            
        except Exception as e:
            print(f"❌ Erreur récupération non-assignés: {e}")
            return {"success": False, "error": str(e)}
    
    def get_device_real_time_data(self, tuya_device_id, use_cache=True):
        """Données temps réel avec cache intelligent"""
        try:
            print(f"📊 Données temps réel pour {tuya_device_id} (cache: {use_cache})")
            
            # 1. Vérifier statut (avec cache)
            status_result = self.get_device_status(tuya_device_id, use_cache=use_cache)
            
            if not status_result.get("success"):
                return status_result
            
            # 2. Enrichir avec données récentes depuis cache si disponibles
            if use_cache and self.redis:
                window_key = f"device_data_window:{tuya_device_id}"
                recent_keys = self.redis.lrange(window_key, 0, 4)  # 5 dernières
                
                recent_data = []
                for key in recent_keys:
                    if isinstance(key, bytes):
                        key = key.decode()
                    
                    data_str = self.redis.get(key)
                    if data_str:
                        try:
                            data = json.loads(data_str)
                            recent_data.append(data)
                        except:
                            continue
                
                if recent_data:
                    status_result['recent_history'] = recent_data
                    status_result['history_count'] = len(recent_data)
            
            return status_result
            
        except Exception as e:
            print(f"❌ Erreur données temps réel: {e}")
            return {"success": False, "error": str(e)}
    
    def batch_check_devices_status(self, device_ids_list, use_cache=True):
        """Vérification batch avec cache optimisé"""
        try:
            print(f"🔍 Vérification batch de {len(device_ids_list)} appareils (cache: {use_cache})")
            
            results = []
            api_needed_devices = []
            
            # ✅ NOUVEAU : Vérifier cache d'abord pour chaque appareil
            if use_cache:
                for device_id in device_ids_list:
                    cached_status = self._get_cached_device_status(device_id)
                    if cached_status:
                        cached_at = datetime.fromisoformat(cached_status['cached_at'])
                        age_seconds = (datetime.utcnow() - cached_at).total_seconds()
                        
                        if age_seconds < 60:  # Cache valide 1 minute pour batch
                            device = Device.get_by_tuya_id(device_id)
                            results.append({
                                "device_id": device_id,
                                "device_name": device.nom_appareil if device else "Inconnu",
                                "is_online": cached_status['is_online'],
                                "from_cache": True,
                                "cache_age": age_seconds,
                                "changed": False
                            })
                            continue
                    
                    api_needed_devices.append(device_id)
                
                print(f"📦 {len(results)} depuis cache, {len(api_needed_devices)} depuis API")
            else:
                api_needed_devices = device_ids_list
            
            # API pour les appareils non cachés
            if api_needed_devices:
                if not self.tuya_client.reconnect_if_needed():
                    return {"success": False, "error": "Connexion Tuya impossible"}
                
                # Récupérer tous les statuts Tuya
                devices_response = self.tuya_client.get_all_devices_with_details()
                if not devices_response.get("success"):
                    return {"success": False, "error": "Impossible de récupérer statuts Tuya"}
                
                tuya_devices = devices_response.get("result", [])
                tuya_status_map = {}
                for tuya_device in tuya_devices:
                    device_id = tuya_device.get("id")
                    if device_id:
                        tuya_status_map[device_id] = tuya_device.get("isOnline", False)
                
                # Traiter appareils depuis API
                updated_count = 0
                for device_id in api_needed_devices:
                    tuya_status = tuya_status_map.get(device_id)
                    device = Device.get_by_tuya_id(device_id)
                    
                    if device and tuya_status is not None:
                        old_status = device.en_ligne
                        device.en_ligne = tuya_status
                        
                        changed = old_status != tuya_status
                        if changed:
                            updated_count += 1
                            # Invalider cache
                            self._invalidate_device_cache(device_id)
                        
                        # ✅ NOUVEAU : Mettre en cache le nouveau statut
                        if use_cache:
                            self._cache_device_status(device_id, {
                                'is_online': tuya_status,
                                'values': {},
                                'source': 'batch_api'
                            })
                        
                        results.append({
                            "device_id": device_id,
                            "device_name": device.nom_appareil,
                            "is_online": tuya_status,
                            "from_cache": False,
                            "changed": changed,
                            "old_status": old_status
                        })
                    else:
                        results.append({
                            "device_id": device_id,
                            "device_name": "Inconnu",
                            "is_online": tuya_status,
                            "from_cache": False,
                            "changed": False,
                            "error": "Appareil non trouvé"
                        })
                
                # Sauvegarder changements
                if updated_count > 0:
                    db.session.commit()
                    print(f"✅ {updated_count} statuts mis à jour depuis API")
            
            return {
                "success": True,
                "checked_count": len(device_ids_list),
                "updated_count": sum(1 for r in results if r.get('changed', False)),
                "cached_count": sum(1 for r in results if r.get('from_cache', False)),
                "api_count": sum(1 for r in results if not r.get('from_cache', True)),
                "results": results,
                "timestamp": datetime.utcnow().isoformat(),
                "cache_efficiency": f"{(sum(1 for r in results if r.get('from_cache', False)) / len(results) * 100):.1f}%" if results else "0%"
            }
            
        except Exception as e:
            print(f"❌ Erreur vérification batch: {e}")
            return {"success": False, "error": str(e)}
    
    # =================== MÉTHODES AVEC CACHE POUR DONNÉES HISTORIQUES ===================
    
    def get_device_history(self, tuya_device_id, limit=100, hours_back=24, use_cache=True):
        """Historique avec cache des données récentes"""
        try:
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            # ✅ NOUVEAU : Enrichir avec données cache Redis si disponibles
            cached_recent_data = []
            if use_cache and self.redis:
                window_key = f"device_data_window:{tuya_device_id}"
                cached_keys = self.redis.lrange(window_key, 0, min(limit, 50))  # Max 50 depuis cache
                
                for key in cached_keys:
                    if isinstance(key, bytes):
                        key = key.decode()
                    
                    data_str = self.redis.get(key)
                    if data_str:
                        try:
                            cached_data = json.loads(data_str)
                            cached_recent_data.append({
                                'horodatage': cached_data['timestamp'],
                                'donnees_brutes': cached_data['values'],
                                'source': 'redis_cache'
                            })
                        except:
                            continue
            
            # Récupération depuis DB
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            db_limit = max(0, limit - len(cached_recent_data))
            
            db_data = []
            if db_limit > 0:
                db_query = DeviceData.query.filter_by(appareil_id=device.id)\
                                          .filter(DeviceData.horodatage >= start_time)\
                                          .order_by(DeviceData.horodatage.desc())\
                                          .limit(db_limit).all()
                
                db_data = [d.to_dict() for d in db_query]
                for item in db_data:
                    item['source'] = 'database'
            
            # Combiner et trier par timestamp
            all_data = cached_recent_data + db_data
            all_data.sort(key=lambda x: x['horodatage'], reverse=True)
            
            # Limiter au nombre demandé
            final_data = all_data[:limit]
            
            return {
                "success": True,
                "device_id": tuya_device_id,
                "hours_back": hours_back,
                "count": len(final_data),
                "cache_entries": len(cached_recent_data),
                "db_entries": len(db_data),
                "data": final_data,
                "cache_used": use_cache
            }
            
        except Exception as e:
            print(f"❌ Erreur historique appareil {tuya_device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_device_statistics(self, use_cache=True):
        """Statistiques avec cache"""
        try:
            # ✅ NOUVEAU : Cache des statistiques
            if use_cache and self.redis:
                cached_stats = self.redis.get("device_statistics")
                if cached_stats:
                    stats_data = json.loads(cached_stats)
                    cached_at = datetime.fromisoformat(stats_data['cached_at'])
                    age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
                    
                    if age_minutes < 5:  # Cache valide 5 minutes
                        print(f"📦 Statistiques depuis cache (âge: {age_minutes:.1f}min)")
                        return {
                            "success": True,
                            "statistiques": stats_data['stats'],
                            "cached_at": stats_data['cached_at'],
                            "from_cache": True
                        }
            
            # Calcul depuis DB
            stats = Device.count_by_status()
            
            # Statistiques supplémentaires
            stats.update({
                'en_ligne': Device.query.filter_by(en_ligne=True).count(),
                'hors_ligne': Device.query.filter_by(en_ligne=False).count(),
                'actifs': Device.query.filter_by(actif=True).count(),
                'inactifs': Device.query.filter_by(actif=False).count()
            })
            
            # ✅ NOUVEAU : Mettre en cache
            if use_cache and self.redis:
                cache_data = {
                    'stats': stats,
                    'cached_at': datetime.utcnow().isoformat()
                }
                self.redis.setex("device_statistics", 300, json.dumps(cache_data))  # 5 minutes
            
            return {
                "success": True,
                "statistiques": stats,
                "cached_at": datetime.utcnow().isoformat(),
                "from_cache": False
            }
            
        except Exception as e:
            print(f"❌ Erreur statistiques appareils: {e}")
            return {"success": False, "error": str(e)}
    
    # =================== MÉTHODES DE CONTRÔLE AVEC CACHE ===================
    
    def control_device(self, tuya_device_id, command, value=None, invalidate_cache=True):
        """Contrôler un appareil et gérer le cache"""
        try:
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion Tuya impossible"}
            
            # Exécuter la commande
            if command == "toggle" or command == "switch":
                result = self.tuya_client.toggle_device(tuya_device_id, value)
            else:
                commands = {
                    "commands": [
                        {
                            "code": command,
                            "value": value
                        }
                    ]
                }
                result = self.tuya_client.send_device_command(tuya_device_id, commands)
            
            if result.get("success"):
                # Mettre à jour DB
                device.update_last_data_time()
                
                # ✅ NOUVEAU : Invalider cache après contrôle
                if invalidate_cache:
                    self._invalidate_device_cache(tuya_device_id)
                    print(f"🗑️ Cache invalidé pour {tuya_device_id} après contrôle")
                
                # ✅ NOUVEAU : Récupérer nouveau statut après délai
                try:
                    import time
                    time.sleep(1)  # Attendre 1 seconde
                    new_status = self.get_device_status(tuya_device_id, use_cache=False)
                    if new_status.get("success"):
                        result['new_status'] = new_status
                except:
                    pass
            
            return result
                
        except Exception as e:
            print(f"❌ Erreur contrôle appareil {tuya_device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def assign_device_to_client(self, tuya_device_id, client_id, site_id, utilisateur_assigneur_id=None):
        """Assigner appareil avec invalidation cache"""
        try:
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            if device.is_assigne():
                return {"success": False, "error": "Appareil déjà assigné"}
            
            success, message = device.assigner_a_client(client_id, site_id, utilisateur_assigneur_id)
            
            if success:
                # ✅ NOUVEAU : Invalider caches après assignation
                self._invalidate_device_cache(tuya_device_id)
                
                # Invalider cache stats et sync
                if self.redis:
                    self.redis.delete("device_statistics")
                    self.redis.delete("last_device_sync")
            
            return {
                "success": success,
                "message": message,
                "device": device.to_dict() if success else None
            }
            
        except Exception as e:
            print(f"❌ Erreur assignation appareil: {e}")
            return {"success": False, "error": str(e)}
    
    def unassign_device(self, tuya_device_id):
        """Désassigner avec invalidation cache"""
        try:
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            if not device.is_assigne():
                return {"success": False, "error": "Appareil déjà non-assigné"}
            
            success, message = device.desassigner()
            
            if success:
                # ✅ NOUVEAU : Invalider caches après désassignation
                self._invalidate_device_cache(tuya_device_id)
                
                # Invalider cache stats et sync
                if self.redis:
                    self.redis.delete("device_statistics")
                    self.redis.delete("last_device_sync")
            
            return {
                "success": success,
                "message": message,
                "device": device.to_dict() if success else None
            }
            
        except Exception as e:
            print(f"❌ Erreur désassignation appareil: {e}")
            return {"success": False, "error": str(e)}
    
    # =================== MÉTHODES D'ADMINISTRATION DU CACHE ===================
    
    def get_cache_statistics(self):
        """Statistiques du cache Redis"""
        try:
            if not self.redis:
                return {
                    "success": False,
                    "error": "Redis non disponible",
                    "cache_enabled": False
                }
            
            # Compter les clés par type
            patterns = {
                "device_status": "device_status:*",
                "device_data": "device_data:*",
                "device_windows": "device_data_window:*",
                "devices_list": "devices_list_tuya",
                "sync_info": "last_device_sync",
                "statistics": "device_statistics"
            }
            
            cache_stats = {}
            total_keys = 0
            
            for cache_type, pattern in patterns.items():
                keys = self.redis.keys(pattern)
                count = len(keys)
                cache_stats[cache_type] = count
                total_keys += count
            
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
                    "used_memory_human": memory_info.get('used_memory_human'),
                    "keyspace": redis_info.get('keyspace', {})
                },
                "ttl_config": self.ttl_config,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erreur stats cache: {e}")
            return {"success": False, "error": str(e)}
    
    def cleanup_cache(self, cache_type=None):
        """Nettoyer le cache (tout ou par type)"""
        try:
            if not self.redis:
                return {"success": False, "error": "Redis non disponible"}
            
            if cache_type:
                # Nettoyage par type
                patterns = {
                    "device_status": ["device_status:*"],
                    "device_data": ["device_data:*", "device_data_window:*"],
                    "sync_info": ["last_device_sync", "devices_list_tuya"],
                    "statistics": ["device_statistics"]
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
                deleted_count = self._invalidate_all_cache()
                
                return {
                    "success": True,
                    "message": "Cache complet nettoyé",
                    "deleted_keys": deleted_count
                }
                
        except Exception as e:
            print(f"❌ Erreur nettoyage cache: {e}")
            return {"success": False, "error": str(e)}
    
    def warm_up_cache(self, device_ids=None):
        """Préchauffer le cache avec les données récentes"""
        try:
            if not self.redis:
                return {"success": False, "error": "Redis non disponible"}
            
            print("🔥 Préchauffage du cache...")
            
            # Récupérer la liste des appareils à préchauffer
            if device_ids:
                devices = [Device.get_by_tuya_id(did) for did in device_ids]
                devices = [d for d in devices if d]  # Filtrer les None
            else:
                # Tous les appareils actifs
                devices = Device.query.filter_by(actif=True).limit(50).all()  # Limite pour éviter la surcharge
            
            if not devices:
                return {"success": False, "error": "Aucun appareil à préchauffer"}
            
            # Préchauffer en batch
            device_ids_list = [d.tuya_device_id for d in devices]
            
            # 1. Statuts en batch
            print("🔥 Préchauffage des statuts...")
            batch_result = self.batch_check_devices_status(device_ids_list, use_cache=False)
            
            # 2. Données récentes pour les appareils assignés
            print("🔥 Préchauffage des données récentes...")
            data_cached = 0
            for device in devices:
                if device.is_assigne():
                    try:
                        status_result = self.get_device_status(device.tuya_device_id, use_cache=False)
                        if status_result.get("success") and status_result.get("values"):
                            data_cached += 1
                    except:
                        continue
            
            # 3. Statistiques
            print("🔥 Préchauffage des statistiques...")
            self.get_device_statistics(use_cache=False)
            
            return {
                "success": True,
                "message": "Cache préchauffé avec succès",
                "devices_processed": len(devices),
                "statuses_cached": len(device_ids_list),
                "data_cached": data_cached,
                "batch_result": batch_result.get("success", False),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erreur préchauffage cache: {e}")
            return {"success": False, "error": str(e)}
    
    def get_cached_device_timeline(self, tuya_device_id, hours_back=24):
        """Timeline des données cachées pour un appareil"""
        try:
            if not self.redis:
                return {"success": False, "error": "Redis non disponible"}
            
            window_key = f"device_data_window:{tuya_device_id}"
            cached_keys = self.redis.lrange(window_key, 0, -1)
            
            timeline_data = []
            now = datetime.utcnow()
            cutoff_time = now - timedelta(hours=hours_back)
            
            for key in cached_keys:
                if isinstance(key, bytes):
                    key = key.decode()
                
                data_str = self.redis.get(key)
                if data_str:
                    try:
                        cached_data = json.loads(data_str)
                        timestamp = datetime.fromisoformat(cached_data['timestamp'])
                        
                        if timestamp >= cutoff_time:
                            timeline_data.append({
                                'timestamp': cached_data['timestamp'],
                                'values': cached_data['values'],
                                'age_minutes': (now - timestamp).total_seconds() / 60,
                                'cache_key': key
                            })
                    except:
                        continue
            
            # Trier par timestamp
            timeline_data.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                "success": True,
                "device_id": tuya_device_id,
                "hours_back": hours_back,
                "cached_entries": len(timeline_data),
                "timeline": timeline_data,
                "window_key": window_key
            }
            
        except Exception as e:
            print(f"❌ Erreur timeline cache: {e}")
            return {"success": False, "error": str(e)}
    
    # =================== MÉTHODES EXISTANTES (sans modification) ===================
    
    def _determine_device_type(self, category, device_data):
        """Déterminer le type d'appareil basé sur les données Tuya"""
        category_mapping = {
            'cz': 'prise_connectee',
            'kg': 'interrupteur',
            'sp': 'camera',
            'wk': 'thermostat',
            'dlq': 'appareil_generique'
        }
        
        # Détection spéciale pour ATORCH (compteur d'énergie)
        device_name = device_data.get("name", "").lower()
        product_name = device_data.get("productName", "").lower()
        
        if "atorch" in device_name or "energy meter" in device_name:
            return 'atorch_compteur_energie'
        elif "gr2pws" in device_data.get("model", ""):
            return 'atorch_argp2ws'
        
        return category_mapping.get(category, 'appareil_generique')
    
    def _save_device_data(self, device, status_data):
        """Sauvegarder les données d'un appareil dans DeviceData"""
        try:
            if not status_data.get("success") or not device.is_assigne():
                return
            
            values = status_data.get("values", {})
            timestamp = datetime.utcnow()
            
            # Créer un enregistrement DeviceData avec toutes les valeurs
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
                donnees_brutes=values  # Sauvegarder toutes les données brutes
            )
            
            db.session.add(device_data)
            db.session.commit()
            
            # Vérifier les seuils et créer des alertes si nécessaire
            self._check_thresholds(device, values)
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde données {device.tuya_device_id}: {e}")
            db.session.rollback()
    
    def _check_thresholds(self, device, values):
        """Vérifier les seuils et créer des alertes"""
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
            
            # Créer les alertes
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
            
            db.session.commit()
            
        except Exception as e:
            print(f"❌ Erreur vérification seuils: {e}")
            db.session.rollback()
    
    # =================== MÉTHODES DE SYNCHRONISATION AMÉLIORÉES ===================
    
    def sync_all_devices(self, use_cache=True, force_refresh=False):
        """Synchronisation avec cache intelligent"""
        try:
            print("🔄 Synchronisation avec cache intelligent...")
            
            # 1. Import avec cache
            import_result = self.import_tuya_devices(use_cache=use_cache, force_refresh=force_refresh)
            
            if not import_result.get("success"):
                return import_result
            
            # 2. Statistiques finales
            stats_result = self.get_device_statistics(use_cache=False)  # Recalculer stats
            
            all_devices = Device.query.all()
            online_final = Device.query.filter_by(en_ligne=True).count()
            offline_final = Device.query.filter_by(en_ligne=False).count()
            
            sync_result = {
                "success": True,
                "message": f"Synchronisation terminée: {len(all_devices)} appareils",
                "import_stats": import_result.get("statistiques", {}),
                "sync_stats": {
                    "total": len(all_devices),
                    "final_online": online_final,
                    "final_offline": offline_final,
                    "source": "endpoint_liste_avec_cache" if use_cache else "endpoint_liste_direct",
                    "cache_used": use_cache,
                    "forced_refresh": force_refresh
                }
            }
            
            if stats_result.get("success"):
                sync_result["device_statistics"] = stats_result.get("statistiques")
            
            print(f"✅ Synchronisation terminée:")
            print(f"   📊 {len(all_devices)} appareils")
            print(f"   🟢 {online_final} en ligne")
            print(f"   🔴 {offline_final} hors ligne")
            print(f"   📦 Cache: {'✅' if use_cache else '❌'}")
            
            return sync_result
            
        except Exception as e:
            print(f"❌ Erreur synchronisation: {e}")
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    # =================== MÉTHODES DEBUG ET MONITORING ===================
    
    def debug_device_cache(self, tuya_device_id):
        """Debug complet du cache d'un appareil"""
        try:
            if not self.redis:
                return {"success": False, "error": "Redis non disponible"}
            
            debug_info = {
                "device_id": tuya_device_id,
                "cache_keys": {},
                "cache_data": {},
                "ttl_info": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Vérifier toutes les clés liées à cet appareil
            patterns = [
                f"device_status:{tuya_device_id}",
                f"device_data_window:{tuya_device_id}",
                f"device_data:{tuya_device_id}:*"
            ]
            
            for pattern in patterns:
                if "*" in pattern:
                    keys = self.redis.keys(pattern)
                else:
                    keys = [pattern] if self.redis.exists(pattern) else []
                
                debug_info["cache_keys"][pattern] = len(keys)
                
                for key in keys[:5]:  # Limiter à 5 clés par pattern
                    if isinstance(key, bytes):
                        key = key.decode()
                    
                    try:
                        data = self.redis.get(key)
                        ttl = self.redis.ttl(key)
                        
                        if data:
                            debug_info["cache_data"][key] = {
                                "data": json.loads(data) if data else None,
                                "ttl_seconds": ttl,
                                "expires_in": f"{ttl // 60}m {ttl % 60}s" if ttl > 0 else "No TTL"
                            }
                    except Exception as e:
                        debug_info["cache_data"][key] = {"error": str(e)}
            
            # Info depuis DB
            device = Device.get_by_tuya_id(tuya_device_id)
            if device:
                debug_info["database_info"] = {
                    "nom_appareil": device.nom_appareil,
                    "en_ligne": device.en_ligne,
                    "statut_assignation": device.statut_assignation,
                    "derniere_donnee": device.derniere_donnee.isoformat() if device.derniere_donnee else None
                }
            
            return {"success": True, "debug_info": debug_info}
            
        except Exception as e:
            print(f"❌ Erreur debug cache: {e}")
            return {"success": False, "error": str(e)}
    
    def health_check(self):
        """Vérification de santé du service"""
        try:
            health_status = {
                "service": "DeviceService",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {}
            }
            
            # Test Tuya connexion
            try:
                tuya_status = self.tuya_client.auto_connect_from_env()
                health_status["components"]["tuya"] = {
                    "status": "healthy" if tuya_status else "unhealthy",
                    "connected": tuya_status
                }
            except Exception as e:
                health_status["components"]["tuya"] = {
                    "status": "error",
                    "error": str(e)
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
                device_count = Device.query.count()
                health_status["components"]["database"] = {
                    "status": "healthy",
                    "device_count": device_count
                }
            except Exception as e:
                health_status["components"]["database"] = {
                    "status": "error",
                    "error": str(e)
                }
            
            # Statut global
            all_healthy = all(
                comp.get("status") in ["healthy", "disabled"] 
                for comp in health_status["components"].values()
            )
            
            health_status["overall_status"] = "healthy" if all_healthy else "degraded"
            
            return {"success": True, "health": health_status}
            
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
    
    # =================== MÉTHODES UTILITAIRES FINALES ===================
    
    def refresh_all_device_statuses(self, use_cache=True):
        """Forcer la synchronisation de tous les statuts avec cache"""
        try:
            print("🔄 Synchronisation forcée de tous les statuts...")
            
            # Invalider cache d'abord si demandé
            if not use_cache:
                self._invalidate_all_cache()
                print("🗑️ Cache invalidé avant synchronisation")
            
            # Utiliser sync_all_devices avec force_refresh
            result = self.sync_all_devices(use_cache=use_cache, force_refresh=True)
            
            if result.get("success"):
                stats = result.get("sync_stats", {})
                
                return {
                    "success": True,
                    "message": "Statuts synchronisés avec succès",
                    "stats": stats,
                    "cache_used": use_cache,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return result
                
        except Exception as e:
            print(f"❌ Erreur synchronisation statuts: {e}")
            return {"success": False, "error": str(e)}
    
    def get_assigned_devices(self, utilisateur, refresh_status=False, use_cache=True):
        """Récupérer les appareils assignés avec cache optimisé"""
        try:
            print(f"🔍 Récupération appareils assignés pour utilisateur {utilisateur.id} (cache: {use_cache})")
            
            # Utiliser get_all_devices avec paramètres optimisés
            result = self.get_all_devices(
                utilisateur=utilisateur,
                include_non_assignes=False,
                refresh_status=refresh_status,
                use_cache=use_cache
            )
            
            if result.get("success"):
                devices = result.get("devices", [])
                
                return {
                    "success": True,
                    "count": len(devices),
                    "devices": devices,
                    "last_refresh": result.get("last_sync"),
                    "stats": result.get("stats"),
                    "client_id": utilisateur.client_id if hasattr(utilisateur, 'client_id') else None,
                    "cache_used": use_cache,
                    "cache_efficiency": result.get("cache_efficiency", "N/A")
                }
            else:
                return result
                
        except Exception as e:
            print(f"❌ Erreur récupération appareils assignés: {e}")
            return {"success": False, "error": str(e)}
    
    def check_device_online_status(self, tuya_device_id, use_cache=True):
        """Vérifier rapidement si un appareil est en ligne avec cache"""
        try:
            # ✅ NOUVEAU : Vérifier cache d'abord
            if use_cache:
                cached_status = self._get_cached_device_status(tuya_device_id)
                if cached_status:
                    cached_at = datetime.fromisoformat(cached_status['cached_at'])
                    age_seconds = (datetime.utcnow() - cached_at).total_seconds()
                    
                    if age_seconds < 45:  # Cache valide 45 secondes
                        return {
                            "success": True,
                            "device_id": tuya_device_id,
                            "is_online": cached_status['is_online'],
                            "from_cache": True,
                            "cache_age": age_seconds,
                            "checked_at": cached_status['cached_at']
                        }
            
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion Tuya impossible"}
            
            # Récupérer depuis la liste Tuya (source fiable)
            devices_response = self.tuya_client.get_all_devices_with_details()
            if not devices_response.get("success"):
                return {"success": False, "error": "Impossible de récupérer la liste Tuya"}
            
            devices = devices_response.get("result", [])
            device_found = None
            
            for device_data in devices:
                if device_data.get("id") == tuya_device_id:
                    device_found = device_data
                    break
            
            if not device_found:
                return {"success": False, "error": "Appareil non trouvé dans Tuya"}
            
            is_online = device_found.get("isOnline", False)
            
            # ✅ NOUVEAU : Mettre en cache
            if use_cache:
                self._cache_device_status(tuya_device_id, {
                    'is_online': is_online,
                    'values': {},
                    'source': 'individual_check'
                })
            
            # Mettre à jour en DB
            device = Device.get_by_tuya_id(tuya_device_id)
            if device:
                old_status = device.en_ligne
                device.en_ligne = is_online
                db.session.commit()
                print(f"📡 {tuya_device_id}: {'🟢 EN LIGNE' if is_online else '🔴 HORS LIGNE'}")
                
                return {
                    "success": True,
                    "device_id": tuya_device_id,
                    "is_online": is_online,
                    "changed": old_status != is_online,
                    "from_cache": False,
                    "checked_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": True,
                    "device_id": tuya_device_id,
                    "is_online": is_online,
                    "device_in_db": False,
                    "from_cache": False,
                    "checked_at": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            print(f"❌ Erreur vérification {tuya_device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def diagnose_tuya_inconsistency(self, tuya_device_id):
        """Diagnostiquer les incohérences avec cache"""
        try:
            print(f"🔬 DIAGNOSTIC incohérences Tuya pour {tuya_device_id}")
            
            # ✅ NOUVEAU : Inclure info cache
            cache_info = {}
            if self.redis:
                cached_status = self._get_cached_device_status(tuya_device_id)
                if cached_status:
                    cache_info = {
                        "cached_status": cached_status['is_online'],
                        "cached_at": cached_status['cached_at'],
                        "cache_source": cached_status.get('source', 'unknown')
                    }
                else:
                    cache_info = {"cached_status": None, "message": "Pas de cache"}
            
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion impossible"}
            
            # 1. ENDPOINT LISTE
            devices_response = self.tuya_client.get_all_devices_with_details()
            list_status = None
            if devices_response.get("success"):
                devices = devices_response.get("result", [])
                for device_data in devices:
                    if device_data.get("id") == tuya_device_id:
                        list_status = device_data.get("isOnline")
                        break
            
            # 2. ENDPOINT INDIVIDUEL
            individual_response = self.tuya_client.get_device_status(tuya_device_id)
            individual_status = individual_response.get("success", False)
            
            # 3. DATABASE
            device = Device.get_by_tuya_id(tuya_device_id)
            db_status = device.en_ligne if device else None
            
            # 4. COMPARAISON
            statuses = [list_status, individual_status, db_status]
            if cache_info.get("cached_status") is not None:
                statuses.append(cache_info["cached_status"])
            
            all_consistent = len(set(s for s in statuses if s is not None)) <= 1
            
            result = {
                "success": True,
                "device_id": tuya_device_id,
                "endpoint_liste": {
                    "status": list_status,
                    "source": "/v2.0/cloud/thing/device"
                },
                "endpoint_individuel": {
                    "status": individual_status,
                    "source": "/v1.0/iot-03/devices/{id}/status",
                    "response": individual_response
                },
                "database": {
                    "status": db_status,
                    "device_exists": device is not None
                },
                "cache": cache_info,
                "consistent": all_consistent,
                "recommended_source": "endpoint_liste",
                "all_statuses": {
                    "list": list_status,
                    "individual": individual_status,
                    "database": db_status,
                    "cache": cache_info.get("cached_status")
                }
            }
            
            print(f"📊 RÉSULTATS:")
            print(f"   Endpoint liste: {'🟢' if list_status else '🔴'}")
            print(f"   Endpoint individuel: {'🟢' if individual_status else '🔴'}")
            print(f"   Database: {'🟢' if db_status else '🔴'}")
            print(f"   Cache: {'🟢' if cache_info.get('cached_status') else '🔴'}")
            print(f"   Cohérent: {'✅' if all_consistent else '❌'}")
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur diagnostic: {e}")
            return {"success": False, "error": str(e)}
    
    def force_status_from_list_endpoint(self, tuya_device_id):
        """Forcer le statut depuis l'endpoint liste avec invalidation cache"""
        try:
            print(f"🔧 Force statut depuis endpoint liste pour {tuya_device_id}")
            
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion impossible"}
            
            # Récupérer depuis la liste
            devices_response = self.tuya_client.get_all_devices_with_details()
            if not devices_response.get("success"):
                return {"success": False, "error": "Impossible de récupérer la liste"}
            
            devices = devices_response.get("result", [])
            target_device = None
            
            for device_data in devices:
                if device_data.get("id") == tuya_device_id:
                    target_device = device_data
                    break
            
            if not target_device:
                return {"success": False, "error": "Appareil non trouvé dans la liste"}
            
            # Mettre à jour en DB avec le statut de la liste
            db_device = Device.get_by_tuya_id(tuya_device_id)
            if not db_device:
                return {"success": False, "error": "Appareil non trouvé en DB"}
            
            list_status = target_device.get("isOnline", False)
            old_status = db_device.en_ligne
            cache_status = None
            
            # ✅ NOUVEAU : Vérifier cache avant modification
            if self.redis:
                cached_status = self._get_cached_device_status(tuya_device_id)
                if cached_status:
                    cache_status = cached_status['is_online']
            
            db_device.en_ligne = list_status
            db.session.commit()
            
            # ✅ NOUVEAU : Invalider cache et mettre à jour
            if self.redis:
                self._invalidate_device_cache(tuya_device_id)
                self._cache_device_status(tuya_device_id, {
                    'is_online': list_status,
                    'values': {},
                    'source': 'forced_from_list'
                })
            
            print(f"✅ Statut forcé depuis endpoint liste:")
            print(f"   Ancien DB: {'🟢' if old_status else '🔴'}")
            print(f"   Cache: {'🟢' if cache_status else '🔴'}")
            print(f"   Nouveau: {'🟢' if list_status else '🔴'}")
            
            return {
                "success": True,
                "device_id": tuya_device_id,
                "old_db_status": old_status,
                "old_cache_status": cache_status,
                "new_status": list_status,
                "source": "endpoint_liste",
                "db_changed": old_status != list_status,
                "cache_invalidated": True
            }
            
        except Exception as e:
            print(f"❌ Erreur force statut: {e}")
            return {"success": False, "error": str(e)}
    
    # =================== MÉTHODES DE CONFIGURATION ===================
    
    def configure_cache_ttl(self, cache_type, ttl_seconds):
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
                    "total_devices": Device.query.count(),
                    "online_devices": Device.query.filter_by(en_ligne=True).count(),
                    "assigned_devices": Device.query.filter_by(statut_assignation='assigne').count(),
                    "recent_data_count": DeviceData.query.filter(
                        DeviceData.horodatage >= datetime.utcnow() - timedelta(hours=1)
                    ).count()
                }
                metrics["database_stats"] = db_metrics
            except Exception as e:
                metrics["database_error"] = str(e)
            
            return {"success": True, "metrics": metrics}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def export_cache_data(self, device_id=None):
        """Exporter les données du cache pour analyse"""
        try:
            if not self.redis:
                return {"success": False, "error": "Redis non disponible"}
            
            export_data = {
                "exported_at": datetime.utcnow().isoformat(),
                "device_id": device_id,
                "cache_data": {}
            }
            
            if device_id:
                # Export pour un appareil spécifique
                patterns = [
                    f"device_status:{device_id}",
                    f"device_data_window:{device_id}",
                    f"device_data:{device_id}:*"
                ]
            else:
                # Export global (limité)
                patterns = [
                    "device_status:*",
                    "devices_list_tuya",
                    "last_device_sync",
                    "device_statistics"
                ]
            
            for pattern in patterns:
                if "*" in pattern:
                    keys = self.redis.keys(pattern)
                    # Limiter à 100 clés pour éviter la surcharge
                    keys = keys[:100] if len(keys) > 100 else keys
                else:
                    keys = [pattern] if self.redis.exists(pattern) else []
                
                pattern_data = {}
                for key in keys:
                    if isinstance(key, bytes):
                        key = key.decode()
                    
                    try:
                        data = self.redis.get(key)
                        ttl = self.redis.ttl(key)
                        
                        pattern_data[key] = {
                            "data": json.loads(data) if data else None,
                            "ttl": ttl
                        }
                    except Exception as e:
                        pattern_data[key] = {"error": str(e)}
                
                export_data["cache_data"][pattern] = pattern_data
            
            return {"success": True, "export": export_data}
            
        except Exception as e:
            return {"success": False, "error": str(e)}