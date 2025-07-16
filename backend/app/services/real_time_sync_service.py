# real_time_sync_service.py
# Service de synchronisation automatique toutes les 30 secondes
# Compatible avec votre DeviceService existant

import time
import threading
from datetime import datetime
from app.models.device import Device
from app import db
import logging

class RealTimeSyncService:
    """Service de synchronisation automatique des états d'appareils"""
    
    def __init__(self, tuya_client):
        self.tuya_client = tuya_client
        self.is_running = False
        self.sync_thread = None
        self.sync_interval = 30  # 30 secondes
        self.logger = logging.getLogger(__name__)
        
        # Statistiques
        self.stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'last_sync': None,
            'last_error': None,
            'devices_updated': 0
        }
        
        self.logger.info("RealTimeSyncService initialisé")
    
    def start_sync(self):
        """Démarrer la synchronisation automatique"""
        if self.is_running:
            self.logger.warning("Synchronisation déjà en cours")
            return False
        
        try:
            self.is_running = True
            self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.sync_thread.start()
            self.logger.info("✅ Synchronisation automatique démarrée (30s)")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erreur démarrage sync: {e}")
            self.is_running = False
            return False
    
    def stop_sync(self):
        """Arrêter la synchronisation automatique"""
        self.is_running = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
        self.logger.info("🛑 Synchronisation automatique arrêtée")
    
    def _sync_loop(self):
        """Boucle principale de synchronisation"""
        self.logger.info("🔄 Début de la boucle de synchronisation")
        
        while self.is_running:
            try:
                sync_start = datetime.utcnow()
                
                # Effectuer la synchronisation
                result = self._sync_all_devices()
                
                # Mettre à jour les statistiques
                self.stats['total_syncs'] += 1
                self.stats['last_sync'] = sync_start.isoformat()
                
                if result.get('success'):
                    self.stats['successful_syncs'] += 1
                    self.stats['devices_updated'] = result.get('updated_count', 0)
                    self.stats['last_error'] = None
                else:
                    self.stats['failed_syncs'] += 1
                    self.stats['last_error'] = result.get('error', 'Erreur inconnue')
                
                # Calculer temps d'attente
                sync_duration = (datetime.utcnow() - sync_start).total_seconds()
                wait_time = max(0, self.sync_interval - sync_duration)
                
                self.logger.debug(f"Sync terminée en {sync_duration:.1f}s, attente {wait_time:.1f}s")
                
                # Attendre avant la prochaine synchronisation
                if self.is_running and wait_time > 0:
                    time.sleep(wait_time)
                    
            except Exception as e:
                self.logger.error(f"❌ Erreur dans sync loop: {e}")
                self.stats['failed_syncs'] += 1
                self.stats['last_error'] = str(e)
                
                # Attendre avant de retenter
                if self.is_running:
                    time.sleep(5)
        
        self.logger.info("🏁 Fin de la boucle de synchronisation")
    
    def _sync_all_devices(self):
        """Synchroniser tous les appareils assignés"""
        try:
            # Récupérer tous les appareils assignés et actifs
            devices = Device.query.filter_by(
                statut_assignation='assigne',
                actif=True
            ).all()
            
            if not devices:
                return {
                    'success': True,
                    'message': 'Aucun appareil à synchroniser',
                    'updated_count': 0,
                    'total_devices': 0
                }
            
            self.logger.debug(f"🔄 Synchronisation de {len(devices)} appareils...")
            
            updated_count = 0
            errors = []
            
            for device in devices:
                try:
                    # Synchroniser cet appareil
                    was_updated = self._sync_single_device(device)
                    if was_updated:
                        updated_count += 1
                    
                    # Petite pause pour éviter surcharge API
                    time.sleep(0.1)
                    
                except Exception as e:
                    error_msg = f"Erreur {device.nom_appareil}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    continue
            
            # Sauvegarder les changements
            db.session.commit()
            
            success_rate = ((len(devices) - len(errors)) / len(devices)) * 100
            
            result = {
                'success': len(errors) < len(devices) / 2,  # Success si moins de 50% d'erreurs
                'updated_count': updated_count,
                'total_devices': len(devices),
                'error_count': len(errors),
                'success_rate': round(success_rate, 1),
                'errors': errors[:5]  # Limite les erreurs affichées
            }
            
            if updated_count > 0:
                self.logger.info(f"✅ {updated_count}/{len(devices)} appareils mis à jour")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur sync globale: {e}")
            db.session.rollback()
            return {
                'success': False,
                'error': str(e),
                'updated_count': 0,
                'total_devices': 0
            }
    
    def _sync_single_device(self, device):
        """Synchroniser un appareil individuel"""
        try:
            # Récupérer l'état actuel depuis Tuya
            current_values = self.tuya_client.get_device_current_values(device.tuya_device_id)
            
            if not current_values.get("success"):
                # Marquer comme hors ligne si erreur Tuya
                if device.en_ligne:
                    device.update_online_status(False)
                    self.logger.debug(f"📴 {device.nom_appareil} marqué hors ligne")
                    return True
                return False
            
            # Extraire les données importantes
            tuya_values = current_values.get("values", {})
            is_online = current_values.get("is_online", False)
            switch_state = tuya_values.get("etat_switch")
            
            # Vérifier si des mises à jour sont nécessaires
            needs_update = False
            changes = []
            
            # 1. Vérifier statut en ligne
            if device.en_ligne != is_online:
                device.update_online_status(is_online)
                changes.append(f"en_ligne: {device.en_ligne} → {is_online}")
                needs_update = True
            
            # 2. Vérifier état du switch
            if switch_state is not None and device.etat_actuel_tuya != switch_state:
                device.etat_actuel_tuya = switch_state
                device.derniere_maj_etat_tuya = datetime.utcnow()
                changes.append(f"switch: {device.etat_actuel_tuya} → {switch_state}")
                needs_update = True
            
            # 3. Mettre à jour timestamp dernière donnée
            if needs_update or is_online:
                device.update_last_data_time()
            
            # Log des changements
            if changes:
                self.logger.debug(f"🔄 {device.nom_appareil}: {', '.join(changes)}")
            
            return needs_update
            
        except Exception as e:
            self.logger.error(f"❌ Erreur sync {device.nom_appareil}: {e}")
            # En cas d'erreur, marquer comme hors ligne
            if device.en_ligne:
                device.update_online_status(False)
            return False
    
    def force_sync_device(self, device_id):
        """Forcer la synchronisation d'un appareil spécifique"""
        try:
            if isinstance(device_id, str):
                # Si c'est tuya_device_id
                device = Device.get_by_tuya_id(device_id)
            else:
                # Si c'est l'ID de la base
                device = Device.query.get(device_id)
            
            if not device:
                return {
                    'success': False,
                    'error': 'Appareil non trouvé',
                    'device_id': device_id
                }
            
            # Effectuer la synchronisation
            was_updated = self._sync_single_device(device)
            db.session.commit()
            
            return {
                'success': True,
                'device_id': device_id,
                'device_name': device.nom_appareil,
                'updated': was_updated,
                'current_state': {
                    'en_ligne': device.en_ligne,
                    'etat_switch': device.etat_actuel_tuya,
                    'derniere_maj': device.derniere_maj_etat_tuya.isoformat() if device.derniere_maj_etat_tuya else None
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur force sync {device_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'device_id': device_id
            }
    
    def get_sync_status(self):
        """Récupérer le statut du service de synchronisation"""
        return {
            'is_running': self.is_running,
            'sync_interval_seconds': self.sync_interval,
            'thread_alive': self.sync_thread.is_alive() if self.sync_thread else False,
            'stats': self.stats.copy(),
            'tuya_connected': self.tuya_client.is_connected if hasattr(self.tuya_client, 'is_connected') else None
        }
    
    def get_detailed_status(self):
        """Statut détaillé avec informations appareils"""
        try:
            # Statistiques des appareils
            total_devices = Device.query.filter_by(statut_assignation='assigne', actif=True).count()
            online_devices = Device.query.filter_by(statut_assignation='assigne', actif=True, en_ligne=True).count()
            offline_devices = total_devices - online_devices
            
            # Appareils avec état switch connu
            devices_with_switch = Device.query.filter(
                Device.statut_assignation == 'assigne',
                Device.actif == True,
                Device.etat_actuel_tuya.isnot(None)
            ).count()
            
            # Appareils allumés/éteints
            devices_on = Device.query.filter_by(
                statut_assignation='assigne',
                actif=True,
                etat_actuel_tuya=True
            ).count()
            
            devices_off = Device.query.filter_by(
                statut_assignation='assigne',
                actif=True,
                etat_actuel_tuya=False
            ).count()
            
            return {
                'service_status': self.get_sync_status(),
                'devices_stats': {
                    'total_assignes': total_devices,
                    'online': online_devices,
                    'offline': offline_devices,
                    'with_switch_state': devices_with_switch,
                    'switch_on': devices_on,
                    'switch_off': devices_off,
                    'switch_unknown': total_devices - devices_with_switch
                },
                'health': {
                    'service_healthy': self.is_running and (not self.sync_thread or self.sync_thread.is_alive()),
                    'sync_success_rate': round((self.stats['successful_syncs'] / max(1, self.stats['total_syncs'])) * 100, 1),
                    'last_sync_age_seconds': (datetime.utcnow() - datetime.fromisoformat(self.stats['last_sync'])).total_seconds() if self.stats['last_sync'] else None
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur statut détaillé: {e}")
            return {
                'service_status': self.get_sync_status(),
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def set_sync_interval(self, seconds):
        """Modifier l'intervalle de synchronisation"""
        if seconds < 10:
            return {
                'success': False,
                'error': 'Intervalle minimum: 10 secondes'
            }
        
        old_interval = self.sync_interval
        self.sync_interval = seconds
        
        self.logger.info(f"📝 Intervalle sync modifié: {old_interval}s → {seconds}s")
        
        return {
            'success': True,
            'old_interval': old_interval,
            'new_interval': seconds,
            'message': f'Intervalle mis à jour à {seconds}s'
        }
    
    def get_devices_states(self):
        """Récupérer l'état de tous les appareils"""
        try:
            devices = Device.query.filter_by(
                statut_assignation='assigne',
                actif=True
            ).all()
            
            devices_states = []
            for device in devices:
                devices_states.append({
                    'id': device.id,
                    'tuya_device_id': device.tuya_device_id,
                    'nom_appareil': device.nom_appareil,
                    'en_ligne': device.en_ligne,
                    'etat_actuel_tuya': device.etat_actuel_tuya,
                    'derniere_maj_etat_tuya': device.derniere_maj_etat_tuya.isoformat() if device.derniere_maj_etat_tuya else None,
                    'derniere_donnee': device.derniere_donnee.isoformat() if device.derniere_donnee else None,
                    'type_appareil': device.type_appareil,
                    'client_id': device.client_id,
                    'site_id': device.site_id
                })
            
            return {
                'success': True,
                'devices': devices_states,
                'count': len(devices_states),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération états: {e}")
            return {
                'success': False,
                'error': str(e),
                'devices': [],
                'count': 0
            }


# =================== INTÉGRATION AVEC VOTRE DEVICE SERVICE ===================

class DeviceServiceSyncExtension:
    """Extension pour intégrer RealTimeSyncService avec DeviceService"""
    
    def __init__(self, device_service):
        self.device_service = device_service
        self.sync_service = None
        self.logger = logging.getLogger(__name__)
    
    def start_real_time_sync(self):
        """Démarrer la synchronisation temps réel"""
        try:
            if self.sync_service and self.sync_service.is_running:
                return {
                    'success': False,
                    'error': 'Synchronisation déjà en cours'
                }
            
            # Créer le service de sync avec le client Tuya du DeviceService
            self.sync_service = RealTimeSyncService(self.device_service.tuya_client)
            
            # Démarrer la synchronisation
            success = self.sync_service.start_sync()
            
            if success:
                self.logger.info("✅ Synchronisation temps réel démarrée")
                return {
                    'success': True,
                    'message': 'Synchronisation automatique démarrée (30s)',
                    'status': self.sync_service.get_sync_status()
                }
            else:
                return {
                    'success': False,
                    'error': 'Impossible de démarrer la synchronisation'
                }
                
        except Exception as e:
            self.logger.error(f"❌ Erreur démarrage sync temps réel: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def stop_real_time_sync(self):
        """Arrêter la synchronisation temps réel"""
        try:
            if not self.sync_service:
                return {
                    'success': False,
                    'error': 'Aucune synchronisation en cours'
                }
            
            self.sync_service.stop_sync()
            self.logger.info("🛑 Synchronisation temps réel arrêtée")
            
            return {
                'success': True,
                'message': 'Synchronisation automatique arrêtée',
                'final_stats': self.sync_service.stats.copy()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur arrêt sync: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_sync_status(self):
        """Récupérer le statut de la synchronisation"""
        if not self.sync_service:
            return {
                'sync_active': False,
                'message': 'Service de synchronisation non initialisé'
            }
        
        return {
            'sync_active': True,
            **self.sync_service.get_detailed_status()
        }
    
    def force_sync_now(self):
        """Forcer une synchronisation immédiate"""
        try:
            if not self.sync_service:
                # Synchronisation ponctuelle via DeviceService
                return self.device_service.sync_all_devices(force_refresh=True)
            else:
                # Utiliser le service de sync
                result = self.sync_service._sync_all_devices()
                return {
                    'success': result.get('success', False),
                    'message': 'Synchronisation forcée terminée',
                    'stats': result
                }
                
        except Exception as e:
            self.logger.error(f"❌ Erreur sync forcée: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_single_device(self, device_id):
        """Synchroniser un appareil spécifique"""
        try:
            if not self.sync_service:
                # Utiliser DeviceService pour sync individuelle
                return self.device_service.get_device_status(device_id, use_cache=False)
            else:
                # Utiliser le service de sync
                return self.sync_service.force_sync_device(device_id)
                
        except Exception as e:
            self.logger.error(f"❌ Erreur sync device {device_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# =================== UTILISATION AVEC VOTRE DEVICE SERVICE ===================

def enhance_device_service_with_sync(device_service):
    """Améliorer votre DeviceService avec la synchronisation temps réel"""
    
    # Créer l'extension
    sync_extension = DeviceServiceSyncExtension(device_service)
    
    # Ajouter les méthodes au DeviceService
    device_service.sync_extension = sync_extension
    device_service.start_real_time_sync = sync_extension.start_real_time_sync
    device_service.stop_real_time_sync = sync_extension.stop_real_time_sync
    device_service.get_sync_status = sync_extension.get_sync_status
    device_service.force_sync_now = sync_extension.force_sync_now
    device_service.sync_single_device = sync_extension.sync_single_device
    
    return device_service


# =================== EXEMPLE D'UTILISATION ===================

def example_usage():
    """Exemple d'utilisation avec votre DeviceService"""
    
    # Importer votre DeviceService
    from app.services.device_service import DeviceService
    
    # Créer le service
    device_service = DeviceService()
    
    # Améliorer avec la synchronisation temps réel
    enhanced_service = enhance_device_service_with_sync(device_service)
    
    # Démarrer la synchronisation automatique
    start_result = enhanced_service.start_real_time_sync()
    print(f"Démarrage sync: {start_result}")
    
    # Vérifier le statut
    status = enhanced_service.get_sync_status()
    print(f"Statut: {status}")
    
    # Forcer une synchronisation immédiate
    force_result = enhanced_service.force_sync_now()
    print(f"Sync forcée: {force_result}")
    
    # Arrêter la synchronisation (optionnel)
    # stop_result = enhanced_service.stop_real_time_sync()
    # print(f"Arrêt sync: {stop_result}")


if __name__ == "__main__":
    example_usage()