import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.models.scheduled_action import ScheduledAction
from app.models.device import Device
from app import db
import time

class ScheduleExecutorService:
    """Service d'exécution ultra-optimisé pour programmations horaires"""
    
    def __init__(self, tuya_client=None):
        self.logger = logging.getLogger(__name__)
        self.tuya_client = tuya_client
        
        # Configuration optimisée
        self.max_actions_per_batch = 20
        self.execution_timeout = 30
        
        self.logger.info("✅ ScheduleExecutorService initialisé")
        
    def execute_pending_actions_optimized(self) -> Dict:
        """Exécution optimisée de toutes les actions en attente"""
        start_time = time.time()
        
        try:
            now = datetime.utcnow()
            
            # Requête optimisée avec jointure
            pending_actions = db.session.query(ScheduledAction, Device)\
                .join(Device, ScheduledAction.appareil_id == Device.id)\
                .filter(
                    ScheduledAction.actif == True,
                    ScheduledAction.prochaine_execution.isnot(None),
                    ScheduledAction.prochaine_execution >= (now - timedelta(minutes=2)),
                    ScheduledAction.prochaine_execution <= (now + timedelta(minutes=2)),
                    Device.statut_assignation == 'assigne',
                    Device.actif == True,
                    Device.programmation_active == True
                )\
                .order_by(ScheduledAction.priorite.desc())\
                .limit(self.max_actions_per_batch)\
                .all()
            
            if not pending_actions:
                return {
                    "success": True,
                    "message": "Aucune action en attente",
                    "executed_count": 0,
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2)
                }
            
            self.logger.info(f"📅 {len(pending_actions)} actions à exécuter")
            
            # Assurer connexion Tuya
            if not self._ensure_tuya_connection():
                return {"success": False, "error": "Connexion Tuya impossible"}
            
            # Exécution en lot
            results = self._execute_actions_batch(pending_actions)
            
            # Commit unique
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                self.logger.error(f"Erreur commit: {e}")
            
            execution_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                "success": True,
                "message": f"Batch exécuté en {execution_time}ms",
                "executed_count": results["executed_count"],
                "failed_count": results["failed_count"],
                "execution_time_ms": execution_time,
                "details": results["details"]
            }
            
        except Exception as e:
            self.logger.error(f"Erreur exécution batch: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_device_pending_actions(self, device_id: str) -> Dict:
        """Exécuter les actions d'un appareil spécifique"""
        try:
            device = Device.query.get(device_id) or Device.query.filter_by(tuya_device_id=device_id).first()
            
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            now = datetime.utcnow()
            
            # Actions de cet appareil seulement
            device_actions = ScheduledAction.query.filter(
                ScheduledAction.appareil_id == device.id,
                ScheduledAction.actif == True,
                ScheduledAction.prochaine_execution.isnot(None),
                ScheduledAction.prochaine_execution >= (now - timedelta(minutes=2)),
                ScheduledAction.prochaine_execution <= (now + timedelta(minutes=2))
            ).all()
            
            if not device_actions:
                return {
                    "success": True,
                    "message": f"Aucune action en attente pour {device.nom_appareil}",
                    "executed_count": 0
                }
            
            # Assurer connexion Tuya
            if not self._ensure_tuya_connection():
                return {"success": False, "error": "Connexion Tuya impossible"}
            
            # Exécuter les actions de cet appareil
            results = self._execute_actions_batch([(action, device) for action in device_actions])
            
            db.session.commit()
            
            return {
                "success": True,
                "message": f"{results['executed_count']} actions exécutées pour {device.nom_appareil}",
                "device_id": device.id,
                "device_name": device.nom_appareil,
                "executed_count": results["executed_count"],
                "failed_count": results["failed_count"],
                "details": results["details"]
            }
            
        except Exception as e:
            self.logger.error(f"Erreur exécution device {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_next_actions_fast(self, limit: int = 10) -> Dict:
        """Récupération rapide des prochaines actions"""
        try:
            now = datetime.utcnow()
            max_time = now + timedelta(hours=24)
            
            # Requête optimisée avec jointure
            upcoming = db.session.query(ScheduledAction, Device)\
                .join(Device, ScheduledAction.appareil_id == Device.id)\
                .filter(
                    ScheduledAction.actif == True,
                    ScheduledAction.prochaine_execution.isnot(None),
                    ScheduledAction.prochaine_execution > now,
                    ScheduledAction.prochaine_execution <= max_time,
                    Device.statut_assignation == 'assigne'
                )\
                .order_by(ScheduledAction.prochaine_execution)\
                .limit(limit)\
                .all()
            
            actions_list = []
            for action, device in upcoming:
                time_until = action.prochaine_execution - now
                
                actions_list.append({
                    "action_id": action.id,
                    "device_id": device.id,
                    "device_name": device.nom_appareil,
                    "action_type": action.action_type,
                    "scheduled_time": action.prochaine_execution.isoformat(),
                    "minutes_until": int(time_until.total_seconds() / 60),
                    "priority": action.priorite,
                    "active": action.actif
                })
            
            return {
                "success": True,
                "upcoming_actions": actions_list,
                "count": len(actions_list)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_device_next_actions(self, device_id: str, limit: int = 5) -> Dict:
        """Actions d'un appareil spécifique"""
        try:
            device = Device.query.get(device_id) or Device.query.filter_by(tuya_device_id=device_id).first()
            
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            now = datetime.utcnow()
            
            device_actions = ScheduledAction.query.filter(
                ScheduledAction.appareil_id == device.id,
                ScheduledAction.actif == True,
                ScheduledAction.prochaine_execution.isnot(None),
                ScheduledAction.prochaine_execution > now
            ).order_by(ScheduledAction.prochaine_execution).limit(limit).all()
            
            actions_list = []
            for action in device_actions:
                time_until = action.prochaine_execution - now
                
                actions_list.append({
                    "action_id": action.id,
                    "action_type": action.action_type,
                    "scheduled_time": action.prochaine_execution.isoformat(),
                    "minutes_until": int(time_until.total_seconds() / 60),
                    "time_display": action.heure_execution.strftime('%H:%M'),
                    "days": action.get_jours_semaine_noms()
                })
            
            return {
                "success": True,
                "device_id": device.id,
                "device_name": device.nom_appareil,
                "upcoming_actions": actions_list,
                "count": len(actions_list)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_execution_health(self) -> Dict:
        """Vérifier la santé du système d'exécution"""
        try:
            now = datetime.utcnow()
            
            # Statistiques rapides
            total_active = ScheduledAction.query.filter_by(actif=True).count()
            pending_soon = ScheduledAction.query.filter(
                ScheduledAction.actif == True,
                ScheduledAction.prochaine_execution > now,
                ScheduledAction.prochaine_execution <= now + timedelta(hours=1)
            ).count()
            
            # Vérifier si des actions sont bloquées
            overdue = ScheduledAction.query.filter(
                ScheduledAction.actif == True,
                ScheduledAction.prochaine_execution < now - timedelta(minutes=10)
            ).count()
            
            health_status = "healthy" if overdue == 0 else "degraded"
            
            return {
                "healthy": health_status == "healthy",
                "status": health_status,
                "stats": {
                    "total_active_actions": total_active,
                    "pending_next_hour": pending_soon,
                    "overdue_actions": overdue
                },
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "status": "error",
                "error": str(e)
            }
    
    def _ensure_tuya_connection(self) -> bool:
        """Assurer connexion Tuya"""
        try:
            if not self.tuya_client:
                from app.services.tuya_service import TuyaClient
                self.tuya_client = TuyaClient()
            
            return self.tuya_client.reconnect_if_needed()
            
        except Exception as e:
            self.logger.error(f"Erreur connexion Tuya: {e}")
            return False
    
    def _execute_actions_batch(self, actions_with_devices: List) -> Dict:
        """Exécution en lot optimisée"""
        executed_count = 0
        failed_count = 0
        details = []
        
        for action, device in actions_with_devices:
            try:
                # Vérifications rapides
                if not self._is_action_executable(action, device):
                    continue
                
                # Exécuter via Tuya
                tuya_result = self._execute_tuya_action_fast(device, action)
                
                if tuya_result["success"]:
                    action.marquer_execution(success=True)
                    executed_count += 1
                    
                    # Mise à jour état device
                    if "new_state" in tuya_result:
                        device.etat_actuel_tuya = tuya_result["new_state"]
                        device.derniere_maj_etat_tuya = datetime.utcnow()
                    
                    details.append({
                        "device_name": device.nom_appareil,
                        "action_type": action.action_type,
                        "status": "success"
                    })
                    
                    self.logger.debug(f"✅ {action.action_type} → {device.nom_appareil}")
                    
                else:
                    error_msg = tuya_result.get("error", "Erreur Tuya")
                    action.marquer_execution(success=False, error_message=error_msg)
                    failed_count += 1
                    
                    details.append({
                        "device_name": device.nom_appareil,
                        "action_type": action.action_type,
                        "status": "failed",
                        "error": error_msg
                    })
                    
                    self.logger.warning(f"❌ {action.action_type} → {device.nom_appareil}: {error_msg}")
                    
            except Exception as e:
                self.logger.error(f"Erreur action {action.id}: {e}")
                
                try:
                    action.marquer_execution(success=False, error_message=str(e))
                except:
                    pass  # Éviter erreur en cascade
                
                failed_count += 1
                
                details.append({
                    "device_name": getattr(device, 'nom_appareil', 'Unknown'),
                    "action_type": getattr(action, 'action_type', 'unknown'),
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "executed_count": executed_count,
            "failed_count": failed_count,
            "details": details
        }
    
    def _is_action_executable(self, action: ScheduledAction, device: Device) -> bool:
        """Vérification rapide d'exécutabilité"""
        if not action.actif or not device.programmation_active:
            return False
        
        if device.mode_manuel_actif:
            if device.mode_manuel_jusqu and datetime.utcnow() > device.mode_manuel_jusqu:
                device.mode_manuel_actif = False
                device.mode_manuel_jusqu = None
            else:
                return False
        
        if getattr(device, 'protection_status', None) == 'protected':
            return False
        
        return True
    
    def _execute_tuya_action_fast(self, device: Device, action: ScheduledAction) -> Dict:
        """
        Exécution Tuya rapide et robuste
        ✅ VERSION COMPLÈTE avec gestion custom_command
        """
        try:
            if action.action_type == 'turn_on':
                return self.tuya_client.toggle_device(device.tuya_device_id, True)
                
            elif action.action_type == 'turn_off':
                return self.tuya_client.toggle_device(device.tuya_device_id, False)
                
            elif action.action_type == 'toggle':
                return self.tuya_client.toggle_device(device.tuya_device_id)
                
            elif action.action_type == 'custom_command' and action.custom_command:
                # Commande personnalisée
                command_data = action.custom_command
                if isinstance(command_data, dict):
                    if 'commands' in command_data:
                        # Format Tuya direct
                        return self.tuya_client.send_device_command(device.tuya_device_id, command_data)
                    else:
                        # Format simple : {"command": "switch", "value": true}
                        commands = {
                            "commands": [{
                                "code": command_data.get('command', 'switch'),
                                "value": command_data.get('value', True)
                            }]
                        }
                        return self.tuya_client.send_device_command(device.tuya_device_id, commands)
                else:
                    return {"success": False, "error": "Format custom_command invalide"}
            
            else:
                return {
                    "success": False,
                    "error": f"Type d'action non supporté: {action.action_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur Tuya: {str(e)}"
            }