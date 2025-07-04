# app/services/device_service_protection_extension.py - VERSION FINALE CORRIGÉE
# ✅ PROTECTION AUTOMATIQUE & PROGRAMMATION HORAIRES
# 🔧 Utilise EXCLUSIVEMENT vos vraies méthodes de ProtectionEvent et ScheduledAction

import asyncio
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any
import json
import logging
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.scheduled_action import ScheduledAction
from app.models.protection_event import ProtectionEvent
from app import db

class DeviceServiceProtectionExtension:
    """Extension pour Protection Automatique & Programmation Horaires - VERSION FINALE"""
    
    def __init__(self, device_service):
        self.device_service = device_service
        self.redis = device_service.redis
        self.logger = logging.getLogger(__name__)
        
        # Configuration cache protection
        self.protection_cache_config = {
            'protection_status_ttl': 300,      # 5 min - Statut protection
            'schedule_cache_ttl': 3600,        # 1h - Programmations horaires
            'pending_actions_ttl': 7200,       # 2h - Actions en attente
            'threshold_events_ttl': 1800,      # 30 min - Événements seuils
            'restart_queue_ttl': 3600,         # 1h - Queue des redémarrages
            'protection_history_ttl': 86400    # 24h - Historique protection
        }
        
        # Configuration protection par défaut
        self.default_protection_config = {
            'tension_protection': {
                'enabled': True,
                'min_threshold': 200.0,
                'max_threshold': 250.0,
                'auto_shutdown': True,
                'restart_delay_minutes': 1,
                'max_retries': 3
            },
            'courant_protection': {
                'enabled': True,
                'max_threshold': 20.0,
                'auto_shutdown': True,
                'restart_delay_minutes': 5,
                'max_retries': 2
            },
            'temperature_protection': {
                'enabled': True,
                'max_threshold': 60.0,
                'auto_shutdown': True,
                'restart_delay_minutes': 10,
                'max_retries': 1
            }
        }
        
        self.logger.info("✅ DeviceService Protection Extension initialisée (VERSION FINALE)")
    
    # =================== 🛡️ PROTECTION AUTOMATIQUE ===================
    
    def configure_device_protection(self, device_id: str, protection_config: Dict) -> Dict:
        """
        Configurer protection automatique pour un appareil
        """
        try:
            device = self._get_device_by_id(device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            self.logger.info(f"🛡️ Configuration protection pour device {device.id}")
            
            # Valider et enrichir la configuration
            validated_config = self._validate_protection_config(protection_config)
            
            # ✅ CORRECTION : Sauvegarder selon vos attributs réels
            try:
                if hasattr(device, 'protection_automatique_active'):
                    device.protection_automatique_active = validated_config.get('enabled', True)
                if hasattr(device, 'protection_config'):
                    device.protection_config = validated_config
                elif hasattr(device, 'config'):
                    if not device.config:
                        device.config = {}
                    device.config['protection'] = validated_config
                
                if hasattr(device, 'derniere_modification_protection'):
                    device.derniere_modification_protection = datetime.utcnow()
                
                db.session.add(device)
                db.session.commit()
                
            except Exception as attr_error:
                self.logger.warning(f"Attributs protection non trouvés sur Device: {attr_error}")
            
            # ✅ Mettre en cache
            if self.redis:
                self._cache_protection_config(device.id, validated_config)
            
            return {
                "success": True,
                "message": "Protection configurée avec succès",
                "device_id": device.id,
                "protection_config": validated_config,
                "monitoring_active": validated_config.get('enabled', True)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur configuration protection device {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def check_device_thresholds(self, device_data: DeviceData, device: Device) -> Dict:
        """
        Vérifier seuils et déclencher protection automatique
        """
        try:
            # ✅ CORRECTION : Vérifier protection active avec fallback
            protection_active = getattr(device, 'protection_automatique_active', False)
            if not protection_active:
                return {"success": True, "protection_triggered": False, "reason": "Protection désactivée"}
            
            protection_config = self._get_device_protection_config(device)
            protection_events = []
            shutdown_required = False
            
            self.logger.debug(f"🔍 Vérification seuils protection pour device {device.id}")
            
            # ✅ 1. Vérifier protection tension
            if protection_config.get('tension_protection', {}).get('enabled', True):
                tension_event = self._check_tension_protection(device_data, device, protection_config['tension_protection'])
                if tension_event:
                    protection_events.append(tension_event)
                    if tension_event.get('requires_shutdown'):
                        shutdown_required = True
            
            # ✅ 2. Vérifier protection courant
            if protection_config.get('courant_protection', {}).get('enabled', True):
                courant_event = self._check_courant_protection(device_data, device, protection_config['courant_protection'])
                if courant_event:
                    protection_events.append(courant_event)
                    if courant_event.get('requires_shutdown'):
                        shutdown_required = True
            
            # ✅ 3. Vérifier protection température
            if protection_config.get('temperature_protection', {}).get('enabled', True):
                temp_event = self._check_temperature_protection(device_data, device, protection_config['temperature_protection'])
                if temp_event:
                    protection_events.append(temp_event)
                    if temp_event.get('requires_shutdown'):
                        shutdown_required = True
            
            # ✅ 4. Déclencher extinction si nécessaire
            if shutdown_required:
                shutdown_result = self.auto_shutdown_device(
                    device.id, 
                    "Seuils de protection dépassés", 
                    protection_events
                )
                
                return {
                    "success": True,
                    "protection_triggered": True,
                    "shutdown_executed": shutdown_result.get('success', False),
                    "protection_events": protection_events,
                    "shutdown_details": shutdown_result
                }
            
            # ✅ 5. Enregistrer événements non-critiques
            for event in protection_events:
                self._log_protection_event(device, event)
            
            return {
                "success": True,
                "protection_triggered": len(protection_events) > 0,
                "shutdown_executed": False,
                "protection_events": protection_events
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur vérification seuils device {device.id}: {e}")
            return {"success": False, "error": str(e)}
    
    def auto_shutdown_device(self, device_id: str, reason: str, trigger_data: Any) -> Dict:
        """
        Extinction automatique sécurisée d'un appareil
        """
        try:
            device = self._get_device_by_id(device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            self.logger.warning(f"🚨 EXTINCTION AUTOMATIQUE - Device {device.id}: {reason}")
            
            # ✅ 1. Vérifier si extinction déjà en cours
            if self._is_shutdown_in_progress(device.id):
                return {
                    "success": False, 
                    "error": "Extinction déjà en cours",
                    "current_status": "shutdown_pending"
                }
            
            # ✅ 2. Marquer extinction en cours
            self._mark_shutdown_in_progress(device.id, reason)
            
            # ✅ 3. Exécuter extinction via Tuya
            shutdown_result = self.device_service.control_device(
                device.tuya_device_id, 
                "switch", 
                False,  # OFF
                invalidate_cache=True
            )
            
            if not shutdown_result.get("success"):
                self._clear_shutdown_in_progress(device.id)
                return {
                    "success": False,
                    "error": f"Échec extinction Tuya: {shutdown_result.get('error')}",
                    "tuya_result": shutdown_result
                }
            
            # ✅ 4. Créer événement protection critique - UTILISE VOS VRAIES MÉTHODES
            protection_event = self._create_protection_event_with_your_model(
                device=device,
                event_type="auto_shutdown",
                reason=reason,
                trigger_data=trigger_data
            )
            
            # ✅ 5. Programmer redémarrage automatique
            restart_delay = self._get_restart_delay_for_trigger(trigger_data)
            restart_scheduled = self.schedule_device_restart(
                device.id, 
                delay_minutes=restart_delay,
                reason=f"Auto-restart après: {reason}"
            )
            
            # ✅ 6. Mettre à jour cache et statut
            if self.redis:
                self._cache_protection_event(device.id, protection_event)
            
            self._clear_shutdown_in_progress(device.id)
            
            return {
                "success": True,
                "message": f"Appareil éteint automatiquement: {reason}",
                "device_id": device.id,
                "shutdown_timestamp": datetime.utcnow().isoformat(),
                "reason": reason,
                "protection_event_id": protection_event.id if protection_event else None,
                "restart_scheduled": restart_scheduled.get('success', False),
                "restart_eta": restart_scheduled.get('restart_eta'),
                "tuya_result": shutdown_result
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur extinction auto device {device_id}: {e}")
            # Nettoyer état si erreur
            if device_id:
                self._clear_shutdown_in_progress(device_id)
            return {"success": False, "error": str(e)}
    
    def schedule_device_restart(self, device_id: str, delay_minutes: int = 1, reason: str = "Auto-restart") -> Dict:
        """
        Programmer rallumage automatique d'un appareil - UTILISE VOS VRAIES MÉTHODES
        """
        try:
            device = self._get_device_by_id(device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            restart_time = datetime.utcnow() + timedelta(minutes=delay_minutes)
            
            self.logger.info(f"⏰ Programmation restart device {device.id} dans {delay_minutes}min")
            
            # ✅ CORRECTION COMPLÈTE : Utiliser VOS vraies méthodes ScheduledAction
            scheduled_action = ScheduledAction.creer_action_simple(
                client_id=device.client_id,
                appareil_id=device.id,
                action_type='turn_on',  # Selon votre enum
                heure=restart_time.strftime('%H:%M'),
                jours=[restart_time.weekday() + 1],  # Jour actuel
                nom_action=f"Auto-restart: {reason}",
                user_id=None  # Système
            )
            
            if not scheduled_action:
                return {"success": False, "error": "Échec création action programmée"}
            
            # Modifier pour être un restart unique
            scheduled_action.custom_command = {
                "command": "switch",
                "value": True,
                "reason": reason,
                "trigger_type": "protection_auto_restart"
            }
            scheduled_action.mode_execution = 'once'
            scheduled_action.date_debut = restart_time.date()
            scheduled_action.date_fin = restart_time.date()
            scheduled_action.retry_attempts = 3
            
            db.session.commit()
            
            # ✅ 2. Ajouter à la queue Redis
            if self.redis:
                self._add_to_restart_queue(device.id, scheduled_action.id, restart_time)
            
            return {
                "success": True,
                "message": f"Restart programmé dans {delay_minutes} minute(s)",
                "device_id": device.id,
                "scheduled_action_id": scheduled_action.id,
                "restart_eta": restart_time.isoformat(),
                "delay_minutes": delay_minutes,
                "reason": reason
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur programmation restart device {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_pending_restarts(self) -> Dict:
        """
        Exécuter les redémarrages programmés en attente - UTILISE VOS VRAIES MÉTHODES
        """
        try:
            now = datetime.utcnow()
            
            # ✅ CORRECTION : Utiliser VOS vraies méthodes
            # Chercher actions dues avec custom_command contenant protection_auto_restart
            pending_actions = ScheduledAction.get_actions_dues(tolerance_minutes=2)
            
            # Filtrer pour les restarts automatiques
            restart_actions = []
            for action in pending_actions:
                if (action.custom_command and 
                    action.custom_command.get('trigger_type') == 'protection_auto_restart'):
                    restart_actions.append(action)
            
            if not restart_actions:
                return {
                    "success": True,
                    "message": "Aucun restart en attente",
                    "executed_count": 0
                }
            
            self.logger.info(f"⚡ Exécution de {len(restart_actions)} restarts programmés")
            
            executed_count = 0
            failed_count = 0
            results = []
            
            for action in restart_actions:
                try:
                    # Vérifier conditions avant restart
                    restart_check = self.smart_restart_check(action.appareil_id)
                    
                    if not restart_check.get('safe_to_restart', False):
                        # ✅ UTILISER VOS MÉTHODES : Reporter avec retry
                        if action.should_retry():
                            # Reprogrammer dans 5 minutes
                            new_time = (now + timedelta(minutes=5)).time()
                            action.heure_execution = new_time
                            action.calculer_prochaine_execution()
                            action.executions_echouees += 1
                        else:
                            # Trop de tentatives
                            action.marquer_execution(
                                success=False, 
                                error_message=restart_check.get('reason', 'Conditions non sûres')
                            )
                            action.desactiver()
                        
                        results.append({
                            "action_id": action.id,
                            "device_id": action.appareil_id,
                            "status": "postponed" if action.should_retry() else "failed",
                            "reason": restart_check.get('reason')
                        })
                        continue
                    
                    # Exécuter restart
                    device = Device.query.get(action.appareil_id)
                    if device:
                        control_result = self.device_service.control_device(
                            device.tuya_device_id,
                            "switch",
                            True,  # ON
                            invalidate_cache=True
                        )
                        
                        if control_result.get("success"):
                            # ✅ UTILISER VOS MÉTHODES
                            action.marquer_execution(success=True)
                            action.desactiver()  # Restart ponctuel terminé
                            
                            executed_count += 1
                            
                            # Logger événement
                            self._log_restart_event(device, action)
                            
                            results.append({
                                "action_id": action.id,
                                "device_id": action.appareil_id,
                                "status": "success",
                                "executed_at": action.derniere_execution.isoformat() if action.derniere_execution else now.isoformat()
                            })
                        else:
                            # ✅ UTILISER VOS MÉTHODES
                            action.marquer_execution(
                                success=False, 
                                error_message=control_result.get('error', 'Erreur contrôle Tuya')
                            )
                            
                            failed_count += 1
                            
                            results.append({
                                "action_id": action.id,
                                "device_id": action.appareil_id,
                                "status": "failed",
                                "error": control_result.get('error')
                            })
                    
                except Exception as e:
                    self.logger.error(f"Erreur exécution restart action {action.id}: {e}")
                    
                    # ✅ UTILISER VOS MÉTHODES
                    action.marquer_execution(success=False, error_message=str(e))
                    
                    failed_count += 1
                    
                    results.append({
                        "action_id": action.id,
                        "device_id": getattr(action, 'appareil_id', 'unknown'),
                        "status": "failed",
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "message": f"Restarts exécutés: {executed_count} réussis, {failed_count} échoués",
                "total_processed": len(restart_actions),
                "executed_count": executed_count,
                "failed_count": failed_count,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur exécution restarts: {e}")
            return {"success": False, "error": str(e)}
    
    def smart_restart_check(self, device_id: str) -> Dict:
        """
        Vérifier conditions avant rallumage automatique
        """
        try:
            device = self._get_device_by_id(device_id)
            if not device:
                return {
                    "safe_to_restart": False,
                    "reason": "Appareil non trouvé"
                }
            
            # ✅ 1. Vérifier dernières données
            latest_data = DeviceData.query.filter_by(
                appareil_id=device.id
            ).order_by(DeviceData.horodatage.desc()).first()
            
            if not latest_data:
                return {
                    "safe_to_restart": True,
                    "reason": "Aucune donnée récente - redémarrage autorisé"
                }
            
            # ✅ 2. Vérifier que les conditions qui ont causé l'extinction sont résolues
            protection_config = self._get_device_protection_config(device)
            
            # Vérifier tension
            if latest_data.tension:
                tension_config = protection_config.get('tension_protection', {})
                min_threshold = tension_config.get('min_threshold', 200)
                max_threshold = tension_config.get('max_threshold', 250)
                
                if latest_data.tension < min_threshold or latest_data.tension > max_threshold:
                    return {
                        "safe_to_restart": False,
                        "reason": f"Tension toujours hors limites: {latest_data.tension}V (limites: {min_threshold}-{max_threshold}V)",
                        "current_tension": latest_data.tension,
                        "thresholds": {"min": min_threshold, "max": max_threshold}
                    }
            
            # Vérifier courant
            if latest_data.courant:
                courant_config = protection_config.get('courant_protection', {})
                max_threshold = courant_config.get('max_threshold', 20)
                
                if latest_data.courant > max_threshold:
                    return {
                        "safe_to_restart": False,
                        "reason": f"Courant toujours élevé: {latest_data.courant}A (max: {max_threshold}A)",
                        "current_courant": latest_data.courant,
                        "max_threshold": max_threshold
                    }
            
            # Vérifier température
            if latest_data.temperature:
                temp_config = protection_config.get('temperature_protection', {})
                max_threshold = temp_config.get('max_threshold', 60)
                
                if latest_data.temperature > max_threshold:
                    return {
                        "safe_to_restart": False,
                        "reason": f"Température toujours élevée: {latest_data.temperature}°C (max: {max_threshold}°C)",
                        "current_temperature": latest_data.temperature,
                        "max_threshold": max_threshold
                    }
            
            return {
                "safe_to_restart": True,
                "reason": "Conditions normales - redémarrage sûr",
                "last_data_timestamp": latest_data.horodatage.isoformat(),
                "current_values": {
                    "tension": latest_data.tension,
                    "courant": latest_data.courant,
                    "temperature": latest_data.temperature
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur vérification restart device {device_id}: {e}")
            return {
                "safe_to_restart": False,
                "reason": f"Erreur vérification: {str(e)}"
            }
    
    # =================== 🕐 PROGRAMMATION HORAIRES ===================
    
    def configure_device_schedule(self, device_id: str, schedule_config: Dict) -> Dict:
        """
        Configurer programmation horaires allumage/extinction - UTILISE VOS VRAIES MÉTHODES
        """
        try:
            device = self._get_device_by_id(device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            self.logger.info(f"⏰ Configuration horaires pour device {device.id}")
            
            # Valider configuration
            validated_config = self._validate_schedule_config(schedule_config)
            
            # ✅ CORRECTION : Sauvegarder avec vos attributs
            try:
                if hasattr(device, 'programmation_active'):
                    device.programmation_active = validated_config.get('enabled', True)
                if hasattr(device, 'horaires_config'):
                    device.horaires_config = validated_config
                elif hasattr(device, 'config'):
                    if not device.config:
                        device.config = {}
                    device.config['horaires'] = validated_config
                
                if hasattr(device, 'derniere_modification_horaires'):
                    device.derniere_modification_horaires = datetime.utcnow()
                
                db.session.add(device)
                db.session.commit()
                
            except Exception as attr_error:
                self.logger.warning(f"Attributs programmation non trouvés sur Device: {attr_error}")
            
            # ✅ Mettre en cache
            if self.redis:
                self._cache_schedule_config(device.id, validated_config)
            
            # ✅ Créer actions programmées avec VOS vraies méthodes
            if validated_config.get('enabled', True):
                self._create_scheduled_actions_with_your_model(device, validated_config)
            
            return {
                "success": True,
                "message": "Programmation configurée avec succès",
                "device_id": device.id,
                "schedule_config": validated_config,
                "active": validated_config.get('enabled', True)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur configuration horaires device {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_scheduled_actions(self, max_actions: int = 50) -> Dict:
        """
        Exécuter actions programmées en attente - UTILISE VOS VRAIES MÉTHODES
        """
        try:
            # ✅ UTILISER VOS VRAIES MÉTHODES
            pending_actions = ScheduledAction.get_actions_dues(tolerance_minutes=2)
            
            # Filtrer pour exclure les restarts automatiques (déjà gérés ailleurs)
            schedule_actions = []
            for action in pending_actions:
                if not (action.custom_command and 
                        action.custom_command.get('trigger_type') == 'protection_auto_restart'):
                    schedule_actions.append(action)
            
            if not schedule_actions:
                return {
                    "success": True,
                    "message": "Aucune action programmée en attente",
                    "executed_count": 0
                }
            
            # Limiter le nombre d'actions à traiter
            schedule_actions = schedule_actions[:max_actions]
            
            self.logger.info(f"📅 Exécution de {len(schedule_actions)} actions programmées")
            
            executed_count = 0
            failed_count = 0
            results = []
            
            for action in schedule_actions:
                try:
                    device = Device.query.get(action.appareil_id)
                    if not device:
                        action.marquer_execution(success=False, error_message="Appareil non trouvé")
                        failed_count += 1
                        continue
                    
                    # Vérifier si programmation toujours active
                    programmation_active = getattr(device, 'programmation_active', True)
                    if not programmation_active:
                        action.marquer_execution(success=False, error_message="Programmation désactivée")
                        continue
                    
                    # Vérifier mode manuel
                    if self.is_manual_mode_active(device.id):
                        action.marquer_execution(success=False, error_message="Mode manuel actif")
                        continue
                    
                    # Déterminer commande et valeur
                    if action.custom_command:
                        command = action.custom_command.get('command', 'switch')
                        value = action.custom_command.get('value', True if action.action_type == 'turn_on' else False)
                    else:
                        command = 'switch'
                        value = True if action.action_type == 'turn_on' else False
                    
                    # Exécuter action
                    control_result = self.device_service.control_device(
                        device.tuya_device_id,
                        command,
                        value,
                        invalidate_cache=True
                    )
                    
                    if control_result.get("success"):
                        action.marquer_execution(success=True)
                        executed_count += 1
                        
                        # Logger événement
                        self._log_scheduled_event(device, action, command, value)
                        
                        results.append({
                            "action_id": action.id,
                            "device_id": device.id,
                            "device_name": getattr(device, 'nom_appareil', device.id),
                            "action_type": action.action_type,
                            "status": "success",
                            "command": command,
                            "value": value
                        })
                    else:
                        error_msg = control_result.get('error', 'Erreur contrôle Tuya')
                        action.marquer_execution(success=False, error_message=error_msg)
                        failed_count += 1
                        
                        results.append({
                            "action_id": action.id,
                            "device_id": device.id,
                            "status": "failed",
                            "error": error_msg
                        })
                    
                except Exception as e:
                    self.logger.error(f"Erreur exécution action programmée {action.id}: {e}")
                    try:
                        action.marquer_execution(success=False, error_message=str(e))
                    except:
                        pass
                    failed_count += 1
                    
                    results.append({
                        "action_id": getattr(action, 'id', 'unknown'),
                        "device_id": getattr(action, 'appareil_id', 'unknown'),
                        "status": "failed",
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "message": f"Actions exécutées: {executed_count} réussies, {failed_count} échouées",
                "total_processed": len(schedule_actions),
                "executed_count": executed_count,
                "failed_count": failed_count,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur exécution actions programmées: {e}")
            return {"success": False, "error": str(e)}
    
    def get_device_schedule_status(self, device_id: str) -> Dict:
        """
        Récupérer statut programmation d'un appareil - UTILISE VOS VRAIES MÉTHODES
        """
        try:
            device = self._get_device_by_id(device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            schedule_config = self._get_device_schedule_config(device)
            
            # ✅ UTILISER VOS VRAIES MÉTHODES : Récupérer actions programmées pour cet appareil
            next_actions = ScheduledAction.get_actions_by_device(device.id)[:5]  
            # ✅ UTILISER VOS VRAIES MÉTHODES : Récupérer actions programmées pour cet appareil
            device_actions = ScheduledAction.get_actions_by_device(device.id)
            
            # Filtrer pour les prochaines actions actives
            next_actions = []
            now = datetime.utcnow()
            for action in device_actions:
                if action.actif and action.prochaine_execution and action.prochaine_execution > now:
                    next_actions.append({
                        'action_type': action.action_type,
                        'scheduled_time': action.prochaine_execution.isoformat(),
                        'nom_action': action.nom_action,
                        'jours_semaine_noms': action.get_jours_semaine_noms(),
                        'time_until': str(action.prochaine_execution - now)
                    })
            
            # Trier par prochaine exécution et limiter à 5
            next_actions.sort(key=lambda x: x['scheduled_time'])
            next_actions = next_actions[:5]
            
            # ✅ HISTORIQUE RÉCENT avec vos vraies méthodes
            recent_actions = []
            for action in device_actions:
                if action.derniere_execution:
                    recent_actions.append({
                        "action_type": action.action_type,
                        "scheduled_time": action.prochaine_execution.isoformat() if action.prochaine_execution else None,
                        "executed_at": action.derniere_execution.isoformat(),
                        "status": "completed" if action.derniere_execution_success else "failed",
                        "error": action.derniere_execution_error,
                        "nom_action": action.nom_action,
                        "taux_reussite": action.get_taux_reussite()
                    })
            
            # Trier par dernière exécution et limiter à 10
            recent_actions.sort(key=lambda x: x['executed_at'], reverse=True)
            recent_actions = recent_actions[:10]
            
            return {
                "success": True,
                "device_id": device.id,
                "device_name": getattr(device, 'nom_appareil', f'Device {device.id}'),
                "programmation_active": getattr(device, 'programmation_active', False),
                "schedule_config": schedule_config,
                "next_actions": next_actions,
                "recent_executions": recent_actions,
                "total_actions": len(device_actions),
                "active_actions": len([a for a in device_actions if a.actif]),
                "last_modification": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur statut programmation device {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def disable_device_schedule(self, device_id: str) -> Dict:
        """
        Désactiver programmation horaires d'un appareil - UTILISE VOS VRAIES MÉTHODES
        """
        try:
            device = self._get_device_by_id(device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            # ✅ CORRECTION : Désactiver avec vos attributs
            try:
                if hasattr(device, 'programmation_active'):
                    device.programmation_active = False
                if hasattr(device, 'derniere_modification_horaires'):
                    device.derniere_modification_horaires = datetime.utcnow()
                
                db.session.add(device)
                db.session.commit()
            except Exception as attr_error:
                self.logger.warning(f"Attributs programmation non trouvés: {attr_error}")
            
            # ✅ UTILISER VOS VRAIES MÉTHODES : Désactiver toutes les actions
            device_actions = ScheduledAction.get_actions_by_device(device.id)
            cancelled_count = 0
            
            for action in device_actions:
                if action.actif and action.action_type in ["turn_on", "turn_off"]:
                    action.desactiver()
                    cancelled_count += 1
            
            # Nettoyer cache
            if self.redis:
                self._clear_schedule_cache(device.id)
            
            return {
                "success": True,
                "message": "Programmation désactivée",
                "device_id": device.id,
                "cancelled_actions": cancelled_count
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur désactivation programmation device {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_next_scheduled_actions(self, limit: int = 10) -> Dict:
        """
        Récupérer prochaines actions programmées - UTILISE VOS VRAIES MÉTHODES
        """
        try:
            # ✅ UTILISER VOS VRAIES MÉTHODES
            upcoming_actions = ScheduledAction.get_prochaines_actions(limit=limit)
            
            actions_list = []
            for action in upcoming_actions:
                device = Device.query.get(action.appareil_id)
                actions_list.append({
                    "action_id": action.id,
                    "device_id": action.appareil_id,
                    "device_name": getattr(device, 'nom_appareil', 'Inconnu') if device else "Inconnu",
                    "action_type": action.action_type,
                    "scheduled_time": action.prochaine_execution.isoformat(),
                    "time_until": str(action.prochaine_execution - datetime.utcnow()),
                    "nom_action": action.nom_action,
                    "jours_semaine_noms": action.get_jours_semaine_noms(),
                    "custom_command": action.custom_command
                })
            
            return {
                "success": True,
                "upcoming_actions": actions_list,
                "count": len(actions_list),
                "query_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération actions programmées: {e}")
            return {"success": False, "error": str(e)}
    
    # =================== MÉTHODES UTILITAIRES CORRIGÉES ===================
    
    def _get_device_by_id(self, device_id: str) -> Optional[Device]:
        """Récupérer appareil par ID"""
        try:
            # Essayer UUID d'abord
            device = Device.query.get(device_id)
            
            if not device:
                # Essayer tuya_device_id si l'attribut existe
                try:
                    device = Device.query.filter_by(tuya_device_id=device_id).first()
                except:
                    pass
            
            return device
            
        except Exception as e:
            self.logger.error(f"Erreur récupération device {device_id}: {e}")
            return None
    
    def _get_device_protection_config(self, device: Device) -> Dict:
        """Récupérer configuration protection avec fallback"""
        try:
            # Essayer différentes méthodes selon votre modèle Device
            if hasattr(device, 'get_protection_config'):
                return device.get_protection_config() or self.default_protection_config
            elif hasattr(device, 'protection_config'):
                return device.protection_config or self.default_protection_config
            elif hasattr(device, 'config') and device.config:
                return device.config.get('protection', self.default_protection_config)
            else:
                return self.default_protection_config
        except:
            return self.default_protection_config
    
    def _get_device_schedule_config(self, device: Device) -> Dict:
        """Récupérer configuration horaires avec fallback"""
        try:
            # Essayer différentes méthodes selon votre modèle Device
            if hasattr(device, 'get_horaires_config'):
                return device.get_horaires_config() or {}
            elif hasattr(device, 'horaires_config'):
                return device.horaires_config or {}
            elif hasattr(device, 'config') and device.config:
                return device.config.get('horaires', {})
            else:
                return {}
        except:
            return {}
    
    def _create_protection_event_with_your_model(self, device: Device, event_type: str, reason: str, trigger_data: Any) -> Optional[ProtectionEvent]:
        """
        Créer événement protection - UTILISE VOS VRAIES MÉTHODES
        """
        try:
            # ✅ CORRECTION : Utiliser VOS vraies méthodes ProtectionEvent
            
            # Mapper les types d'événements vers vos enums
            type_protection_map = {
                'auto_shutdown': 'autre',
                'tension_high': 'tension_anormale',
                'tension_low': 'tension_anormale', 
                'courant_high': 'courant_depasse',
                'temperature_high': 'temperature_haute'
            }
            
            type_protection = type_protection_map.get(event_type, 'autre')
            action_effectuee = 'arret_appareil' if 'shutdown' in event_type else 'alerte_envoyee'
            
            # Extraire valeurs de déclenchement
            valeur_declenchement = None
            valeur_seuil = None
            unite_mesure = None
            
            if isinstance(trigger_data, list) and trigger_data:
                first_event = trigger_data[0]
                if isinstance(first_event, dict):
                    valeur_declenchement = first_event.get('measured_value')
                    valeur_seuil = first_event.get('threshold')
                    
                    # Déterminer l'unité
                    if 'tension' in event_type:
                        unite_mesure = 'V'
                    elif 'courant' in event_type:
                        unite_mesure = 'A'
                    elif 'temperature' in event_type:
                        unite_mesure = '°C'
            
            # ✅ UTILISER VOTRE VRAIE MÉTHODE
            protection_event = ProtectionEvent.creer_evenement_protection(
                client_id=device.client_id,
                appareil_id=device.id,
                type_protection=type_protection,
                action_effectuee=action_effectuee,
                valeur_declenchement=valeur_declenchement,
                valeur_seuil=valeur_seuil,
                unite_mesure=unite_mesure,
                type_systeme='monophase',
                etat_avant='on',
                etat_apres='off' if 'shutdown' in action_effectuee else 'on'
            )
            
            if protection_event and reason:
                protection_event.description = reason
                db.session.commit()
            
            return protection_event
            
        except Exception as e:
            self.logger.error(f"Erreur création protection event: {e}")
            return None
    
    def _create_scheduled_actions_with_your_model(self, device: Device, schedule_config: Dict):
        """Créer actions programmées - UTILISE VOS VRAIES MÉTHODES"""
        try:
            # ✅ SUPPRIMER anciennes actions avec vos méthodes
            old_actions = ScheduledAction.get_actions_by_device(device.id)
            for action in old_actions:
                if action.action_type in ["turn_on", "turn_off"]:
                    action.desactiver()
            
            # ✅ CRÉER action allumage avec votre vraie méthode
            allumage_config = schedule_config.get('allumage', {})
            if allumage_config.get('enabled', True):
                time_str = allumage_config.get('time', '07:00')
                days = allumage_config.get('days', [1, 2, 3, 4, 5])
                
                ScheduledAction.creer_action_simple(
                    client_id=device.client_id,
                    appareil_id=device.id,
                    action_type='turn_on',
                    heure=time_str,
                    jours=days,
                    nom_action=f"Allumage automatique - {getattr(device, 'nom_appareil', device.id)}"
                )
            
            # ✅ CRÉER action extinction avec votre vraie méthode
            extinction_config = schedule_config.get('extinction', {})
            if extinction_config.get('enabled', True):
                time_str = extinction_config.get('time', '22:00')
                days = extinction_config.get('days', [1, 2, 3, 4, 5, 6, 7])
                
                ScheduledAction.creer_action_simple(
                    client_id=device.client_id,
                    appareil_id=device.id,
                    action_type='turn_off',
                    heure=time_str,
                    jours=days,
                    nom_action=f"Extinction automatique - {getattr(device, 'nom_appareil', device.id)}"
                )
                
        except Exception as e:
            self.logger.error(f"Erreur création actions programmées: {e}")
    
    # =================== MÉTHODES DE VÉRIFICATION SEUILS ===================
    
    def _check_tension_protection(self, device_data: DeviceData, device: Device, config: Dict) -> Optional[Dict]:
        """Vérifier protection tension"""
        if not config.get('enabled', True):
            return None
        
        tension = device_data.tension
        if tension is None:
            return None
        
        min_threshold = config.get('min_threshold', 200.0)
        max_threshold = config.get('max_threshold', 250.0)
        auto_shutdown = config.get('auto_shutdown', True)
        
        if tension < min_threshold:
            return {
                'type': 'tension_low',
                'measured_value': tension,
                'threshold': min_threshold,
                'requires_shutdown': auto_shutdown,
                'severity': 'critical',
                'message': f'Tension trop basse: {tension}V < {min_threshold}V'
            }
        elif tension > max_threshold:
            return {
                'type': 'tension_high',
                'measured_value': tension,
                'threshold': max_threshold,
                'requires_shutdown': auto_shutdown,
                'severity': 'critical',
                'message': f'Tension trop élevée: {tension}V > {max_threshold}V'
            }
        
        return None
    
    def _check_courant_protection(self, device_data: DeviceData, device: Device, config: Dict) -> Optional[Dict]:
        """Vérifier protection courant"""
        if not config.get('enabled', True):
            return None
        
        courant = device_data.courant
        if courant is None:
            return None
        
        max_threshold = config.get('max_threshold', 20.0)
        auto_shutdown = config.get('auto_shutdown', True)
        
        if courant > max_threshold:
            return {
                'type': 'courant_high',
                'measured_value': courant,
                'threshold': max_threshold,
                'requires_shutdown': auto_shutdown,
                'severity': 'critical',
                'message': f'Courant trop élevé: {courant}A > {max_threshold}A'
            }
        
        return None
    
    def _check_temperature_protection(self, device_data: DeviceData, device: Device, config: Dict) -> Optional[Dict]:
        """Vérifier protection température"""
        if not config.get('enabled', True):
            return None
        
        temperature = device_data.temperature
        if temperature is None:
            return None
        
        max_threshold = config.get('max_threshold', 60.0)
        auto_shutdown = config.get('auto_shutdown', True)
        
        if temperature > max_threshold:
            return {
                'type': 'temperature_high',
                'measured_value': temperature,
                'threshold': max_threshold,
                'requires_shutdown': auto_shutdown,
                'severity': 'critical',
                'message': f'Température trop élevée: {temperature}°C > {max_threshold}°C'
            }
        
        return None
    
    def _get_restart_delay_for_trigger(self, trigger_data: Any) -> int:
        """Déterminer délai de redémarrage selon le déclencheur"""
        if not isinstance(trigger_data, list):
            return 1  # Défaut 1 minute
        
        # Analyser les événements pour déterminer le délai approprié
        max_delay = 1
        for event in trigger_data:
            if isinstance(event, dict):
                event_type = event.get('type', '')
                
                if 'temperature' in event_type:
                    max_delay = max(max_delay, 10)  # 10 min pour température
                elif 'courant' in event_type:
                    max_delay = max(max_delay, 5)   # 5 min pour courant
                elif 'tension' in event_type:
                    max_delay = max(max_delay, 1)   # 1 min pour tension
        
        return max_delay
    
    # =================== MÉTHODES DE VALIDATION ===================
    
    def _validate_protection_config(self, config: Dict) -> Dict:
        """Valider et enrichir configuration protection"""
        validated = self.default_protection_config.copy()
        
        if not isinstance(config, dict):
            return validated
        
        # Fusionner avec configuration fournie
        for protection_type, settings in config.items():
            if protection_type in validated and isinstance(settings, dict):
                validated[protection_type].update(settings)
        
        # Validation des seuils
        for protection_type in ['tension_protection', 'courant_protection', 'temperature_protection']:
            if protection_type in validated:
                settings = validated[protection_type]
                
                # S'assurer que les seuils sont numériques
                for threshold_key in ['min_threshold', 'max_threshold']:
                    if threshold_key in settings:
                        try:
                            settings[threshold_key] = float(settings[threshold_key])
                        except (ValueError, TypeError):
                            del settings[threshold_key]
                
                # Valider restart_delay_minutes
                if 'restart_delay_minutes' in settings:
                    try:
                        delay = int(settings['restart_delay_minutes'])
                        settings['restart_delay_minutes'] = max(1, min(delay, 60))  # Entre 1 et 60 minutes
                    except (ValueError, TypeError):
                        settings['restart_delay_minutes'] = 1
                
                # Valider max_retries
                if 'max_retries' in settings:
                    try:
                        retries = int(settings['max_retries'])
                        settings['max_retries'] = max(0, min(retries, 10))  # Entre 0 et 10
                    except (ValueError, TypeError):
                        settings['max_retries'] = 3
        
        return validated
    
    def _validate_schedule_config(self, config: Dict) -> Dict:
        """Valider configuration horaires"""
        default_schedule = {
            "enabled": True,
            "timezone": "Africa/Dakar",
            "override_protection": False,
            "allumage": {
                "enabled": True,
                "time": "07:00",
                "days": [1, 2, 3, 4, 5],  # Lundi-Vendredi
                "force_on": True
            },
            "extinction": {
                "enabled": True,
                "time": "22:00",
                "days": [1, 2, 3, 4, 5, 6, 7],  # Tous les jours
                "force_off": True
            }
        }
        
        if not isinstance(config, dict):
            return default_schedule
        
        validated = default_schedule.copy()
        validated.update(config)
        
        # Valider format des heures
        for action_type in ['allumage', 'extinction']:
            if action_type in validated and isinstance(validated[action_type], dict):
                action_config = validated[action_type]
                
                # Valider format heure (HH:MM)
                if 'time' in action_config:
                    try:
                        time_str = action_config['time']
                        datetime.strptime(time_str, '%H:%M')
                    except ValueError:
                        action_config['time'] = default_schedule[action_type]['time']
                
                # Valider jours (1-7)
                if 'days' in action_config:
                    if isinstance(action_config['days'], list):
                        valid_days = [d for d in action_config['days'] if isinstance(d, int) and 1 <= d <= 7]
                        action_config['days'] = valid_days if valid_days else default_schedule[action_type]['days']
                    else:
                        action_config['days'] = default_schedule[action_type]['days']
        
        return validated
    
    # =================== MÉTHODES DE CACHE REDIS ===================
    
    def _cache_protection_config(self, device_id: str, config: Dict):
        """Mettre en cache configuration protection"""
        if not self.redis:
            return
        
        try:
            key = f"protection_config:{device_id}"
            ttl = self.protection_cache_config['protection_status_ttl']
            
            cache_data = {
                'config': config,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            
        except Exception as e:
            self.logger.error(f"Erreur cache protection config: {e}")
    
    def _cache_schedule_config(self, device_id: str, config: Dict):
        """Mettre en cache configuration horaires"""
        if not self.redis:
            return
        
        try:
            key = f"schedule_config:{device_id}"
            ttl = self.protection_cache_config['schedule_cache_ttl']
            
            cache_data = {
                'config': config,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            
        except Exception as e:
            self.logger.error(f"Erreur cache schedule config: {e}")
    
    def _cache_protection_event(self, device_id: str, event: Any):
        """Mettre en cache événement protection"""
        if not self.redis:
            return
        
        try:
            key = f"protection_event:{device_id}:{int(datetime.utcnow().timestamp())}"
            ttl = self.protection_cache_config['threshold_events_ttl']
            
            event_data = {
                'event_id': event.id if event else None,
                'timestamp': datetime.utcnow().isoformat(),
                'device_id': device_id
            }
            
            self.redis.setex(key, ttl, json.dumps(event_data))
            
        except Exception as e:
            self.logger.error(f"Erreur cache protection event: {e}")
    
    def _add_to_restart_queue(self, device_id: str, action_id: str, restart_time: datetime):
        """Ajouter à la queue de redémarrage Redis"""
        if not self.redis:
            return
        
        try:
            queue_key = "restart_queue"
            restart_data = {
                'device_id': device_id,
                'action_id': action_id,
                'restart_time': restart_time.isoformat(),
                'queued_at': datetime.utcnow().isoformat()
            }
            
            # Score = timestamp pour tri chronologique
            score = restart_time.timestamp()
            self.redis.zadd(queue_key, {json.dumps(restart_data): score})
            
            # TTL sur la queue
            self.redis.expire(queue_key, self.protection_cache_config['restart_queue_ttl'])
            
        except Exception as e:
            self.logger.error(f"Erreur ajout restart queue: {e}")
    
    def _is_shutdown_in_progress(self, device_id: str) -> bool:
        """Vérifier si extinction en cours"""
        if not self.redis:
            return False
        
        try:
            key = f"shutdown_in_progress:{device_id}"
            return bool(self.redis.exists(key))
        except:
            return False
    
    def _mark_shutdown_in_progress(self, device_id: str, reason: str):
        """Marquer extinction en cours"""
        if not self.redis:
            return
        
        try:
            key = f"shutdown_in_progress:{device_id}"
            data = {
                'reason': reason,
                'started_at': datetime.utcnow().isoformat()
            }
            self.redis.setex(key, 300, json.dumps(data))  # 5 minutes max
        except Exception as e:
            self.logger.error(f"Erreur mark shutdown: {e}")
    
    def _clear_shutdown_in_progress(self, device_id: str):
        """Nettoyer marqueur extinction"""
        if not self.redis:
            return
        
        try:
            key = f"shutdown_in_progress:{device_id}"
            self.redis.delete(key)
        except Exception as e:
            self.logger.error(f"Erreur clear shutdown: {e}")
    
    def _clear_schedule_cache(self, device_id: str):
        """Nettoyer cache programmation"""
        if not self.redis:
            return
        
        try:
            patterns = [
                f"schedule_config:{device_id}",
                f"next_actions:{device_id}:*"
            ]
            
            for pattern in patterns:
                if "*" in pattern:
                    keys = self.redis.keys(pattern)
                    if keys:
                        self.redis.delete(*keys)
                else:
                    self.redis.delete(pattern)
            
        except Exception as e:
            self.logger.error(f"Erreur clear schedule cache: {e}")
    
    # =================== MÉTHODES DE LOGGING ===================
    
    def _log_protection_event(self, device: Device, event_data: Dict):
        """Logger événement protection"""
        try:
            event_type = event_data.get('type', 'unknown')
            severity = event_data.get('severity', 'info')
            message = event_data.get('message', 'Événement protection')
            
            self.logger.info(f"🛡️ Protection Event - Device {device.id}: {message} (Type: {event_type}, Severity: {severity})")
            
        except Exception as e:
            self.logger.error(f"Erreur log protection event: {e}")
    
    def _log_restart_event(self, device: Device, action: ScheduledAction):
        """Logger événement restart"""
        try:
            self.logger.info(f"⚡ Restart automatique exécuté - Device {device.id}: Action {action.id}")
            
        except Exception as e:
            self.logger.error(f"Erreur log restart event: {e}")
    
    def _log_scheduled_event(self, device: Device, action: ScheduledAction, command: str, value: Any):
        """Logger événement programmé"""
        try:
            action_type = action.action_type
            device_name = getattr(device, 'nom_appareil', device.id)
            
            self.logger.info(f"📅 Action programmée exécutée - {device_name} ({device.id}): {action_type} ({command}={value})")
            
        except Exception as e:
            self.logger.error(f"Erreur log scheduled event: {e}")
    
    # =================== INTÉGRATION AVEC DeviceService EXISTANT ===================
    
    def enhance_save_device_data_protection(self, device: Device, device_data: DeviceData) -> Dict:
        """
        ✅ Enhancement pour protection automatique
        Appelée APRÈS sauvegarde DeviceData pour vérifier seuils
        """
        try:
            protection_active = getattr(device, 'protection_automatique_active', False)
            if not protection_active:
                return {"success": True, "protection_checked": False, "reason": "Protection désactivée"}
            
            self.logger.debug(f"🛡️ Vérification protection pour device {device.id}")
            
            # Vérifier seuils de protection
            protection_result = self.check_device_thresholds(device_data, device)
            
            if protection_result.get('protection_triggered'):
                self.logger.warning(f"🚨 Protection déclenchée pour device {device.id}")
            
            return protection_result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur enhancement protection device {device.id}: {e}")
            return {"success": False, "error": str(e)}
    
    def enhance_control_device_with_schedule_check(self, device_id: str, command: str, value: Any) -> Dict:
        """
        ✅ Enhancement pour vérifier override programmation
        Vérifie si commande manuelle doit override la programmation
        """
        try:
            device = self._get_device_by_id(device_id)
            programmation_active = getattr(device, 'programmation_active', False)
            
            if not device or not programmation_active:
                return {"override_required": False, "reason": "Pas de programmation active"}
            
            # Vérifier si c'est une commande manuelle qui override la programmation
            if command == "switch" and isinstance(value, bool):
                # Marquer en mode manuel temporaire
                self._set_manual_mode(device.id, duration_minutes=60)
                
                return {
                    "override_required": True,
                    "manual_mode_set": True,
                    "duration_minutes": 60,
                    "message": "Mode manuel activé - programmation suspendue pendant 1h"
                }
            
            return {"override_required": False}
            
        except Exception as e:
            self.logger.error(f"❌ Erreur vérification override: {e}")
            return {"override_required": False, "error": str(e)}
    
    def _set_manual_mode(self, device_id: str, duration_minutes: int = 60):
        """Activer mode manuel temporaire"""
        if not self.redis:
            return