# app/tasks/simple_scheduler.py
# Scheduler simple pour exécuter les actions programmées

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List

class SimpleScheduler:
    """Scheduler simple pour exécuter les actions programmées automatiquement"""
    
    def __init__(self, interval_seconds: int = 60, app=None):
        self.interval_seconds = interval_seconds
        self.app = app  # ✅ Stocker l'app Flask pour le contexte
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.logger = logging.getLogger(__name__)
        
        # Statistiques
        self.start_time = None
        self.last_execution = None
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        
        self.logger.info(f"✅ SimpleScheduler initialisé (intervalle: {interval_seconds}s)")
    
    def set_app(self, app):
        """Définir l'app Flask pour le contexte"""
        self.app = app
    
    def start(self):
        """Démarrer le scheduler"""
        if self.is_running:
            self.logger.warning("⚠️ Scheduler déjà en cours d'exécution")
            return False
        
        try:
            self.stop_event.clear()
            self.is_running = True
            self.start_time = datetime.utcnow()
            
            # Créer et démarrer le thread
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            
            self.logger.info("🚀 SimpleScheduler démarré avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur démarrage scheduler: {e}")
            self.is_running = False
            return False
    
    def stop(self):
        """Arrêter le scheduler"""
        if not self.is_running:
            self.logger.warning("⚠️ Scheduler déjà arrêté")
            return False
        
        try:
            self.stop_event.set()
            self.is_running = False
            
            # Attendre que le thread se termine
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)
                
            self.logger.info("🛑 SimpleScheduler arrêté")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur arrêt scheduler: {e}")
            return False
    
    def restart(self):
        """Redémarrer le scheduler"""
        self.stop()
        time.sleep(1)  # Petite pause
        return self.start()
    
    def _run_scheduler(self):
        """Boucle principale du scheduler"""
        self.logger.info("🔄 Boucle scheduler démarrée")
        
        while not self.stop_event.is_set():
            try:
                # Exécuter les actions programmées
                self._execute_scheduled_actions()
                
                # Attendre l'intervalle suivant
                if not self.stop_event.wait(timeout=self.interval_seconds):
                    continue  # Timeout normal, continuer
                else:
                    break  # Event set, arrêter
                    
            except Exception as e:
                self.logger.error(f"❌ Erreur dans boucle scheduler: {e}")
                self.failed_executions += 1
                
                # Attendre avant de réessayer
                if not self.stop_event.wait(timeout=10):
                    continue
                else:
                    break
        
        self.logger.info("🔄 Boucle scheduler terminée")
    
    def _execute_scheduled_actions(self):
        """Exécuter les actions programmées dues"""
        try:
            execution_start = time.time()
            
            from app.services.schedule_executor_service import ScheduleExecutorService
            
            # ✅ CORRECTION : Utiliser l'app stockée pour le contexte
            if self.app:
                with self.app.app_context():
                    # Créer une instance du service
                    executor = ScheduleExecutorService()
                    
                    # Exécuter les actions en attente
                    result = executor.execute_pending_actions_optimized()
            else:
                # Fallback si pas d'app - essayer current_app
                try:
                    from flask import current_app
                    with current_app.app_context():
                        executor = ScheduleExecutorService()
                        result = executor.execute_pending_actions_optimized()
                except RuntimeError:
                    # Si pas de contexte disponible, on skip cette exécution
                    self.logger.warning("⚠️ Pas de contexte Flask disponible - exécution ignorée")
                    return
            
            # Mettre à jour les statistiques
            self.last_execution = datetime.utcnow()
            self.total_executions += 1
            
            execution_time = round((time.time() - execution_start) * 1000, 1)
            
            if result.get("success"):
                self.successful_executions += 1
                executed_count = result.get("executed_count", 0)
                
                if executed_count > 0:
                    self.logger.info(f"✅ Scheduler: {executed_count} actions exécutées en {execution_time}ms")
                else:
                    self.logger.debug(f"📋 Scheduler: Aucune action en attente ({execution_time}ms)")
            else:
                self.failed_executions += 1
                error = result.get("error", "Erreur inconnue")
                self.logger.error(f"❌ Scheduler: Erreur exécution - {error}")
            
        except ImportError:
            self.logger.warning("⚠️ ScheduleExecutorService non disponible")
        except Exception as e:
            self.logger.error(f"❌ Erreur exécution actions: {e}")
            self.failed_executions += 1
    
    def get_status(self) -> Dict:
        """Récupérer le statut du scheduler"""
        uptime = None
        if self.start_time:
            uptime_delta = datetime.utcnow() - self.start_time
            uptime = {
                "total_seconds": uptime_delta.total_seconds(),
                "formatted": str(uptime_delta).split('.')[0]  # Enlever les microsecondes
            }
        
        return {
            "running": self.is_running,
            "interval_seconds": self.interval_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "uptime": uptime,
            "thread_alive": self.thread.is_alive() if self.thread else False,
            "statistics": {
                "total_executions": self.total_executions,
                "successful_executions": self.successful_executions,
                "failed_executions": self.failed_executions,
                "success_rate": round(
                    (self.successful_executions / max(self.total_executions, 1)) * 100, 1
                )
            }
        }
    
    def get_next_execution_time(self) -> Optional[datetime]:
        """Calculer l'heure de la prochaine exécution"""
        if not self.is_running or not self.last_execution:
            return None
        
        return self.last_execution + timedelta(seconds=self.interval_seconds)
    
    def is_running_status(self) -> bool:
        """Vérifier si le scheduler est en cours d'exécution (méthode)"""
        return self.is_running
    
    def is_healthy(self) -> bool:
        """Vérifier si le scheduler est en bonne santé"""
        if not self.is_running:
            return False
        
        if not self.thread or not self.thread.is_alive():
            return False
        
        # Vérifier si la dernière exécution n'est pas trop ancienne
        if self.last_execution:
            time_since_last = datetime.utcnow() - self.last_execution
            if time_since_last.total_seconds() > (self.interval_seconds * 2):
                return False
        
        return True
    
    def get_health_report(self) -> Dict:
        """Rapport de santé détaillé"""
        status = self.get_status()
        
        health_checks = {
            "scheduler_running": self.is_running,
            "thread_alive": self.thread.is_alive() if self.thread else False,
            "recent_execution": False,
            "success_rate_ok": False
        }
        
        # Vérifier exécution récente
        if self.last_execution:
            time_since_last = datetime.utcnow() - self.last_execution
            health_checks["recent_execution"] = time_since_last.total_seconds() < (self.interval_seconds * 2)
        
        # Vérifier taux de succès
        if self.total_executions > 0:
            success_rate = (self.successful_executions / self.total_executions) * 100
            health_checks["success_rate_ok"] = success_rate >= 80
        
        overall_health = all(health_checks.values())
        
        return {
            "healthy": overall_health,
            "status": status,
            "health_checks": health_checks,
            "recommendations": self._get_health_recommendations(health_checks)
        }
    
    def _get_health_recommendations(self, health_checks: Dict) -> List[str]:
        """Générer des recommandations basées sur la santé"""
        recommendations = []
        
        if not health_checks["scheduler_running"]:
            recommendations.append("Redémarrer le scheduler")
        
        if not health_checks["thread_alive"]:
            recommendations.append("Thread du scheduler mort - redémarrage nécessaire")
        
        if not health_checks["recent_execution"]:
            recommendations.append("Aucune exécution récente - vérifier les actions programmées")
        
        if not health_checks["success_rate_ok"]:
            recommendations.append("Taux de succès faible - vérifier la connectivité Tuya")
        
        if not recommendations:
            recommendations.append("Système en bonne santé")
        
        return recommendations

# =================== INSTANCE GLOBALE ===================

# Instance globale du scheduler
simple_scheduler = SimpleScheduler(interval_seconds=60)  # Exécution toutes les minutes

# =================== FONCTIONS UTILITAIRES ===================

def get_scheduler_instance() -> SimpleScheduler:
    """Récupérer l'instance du scheduler"""
    return simple_scheduler

def start_scheduler() -> bool:
    """Fonction utilitaire pour démarrer le scheduler"""
    return simple_scheduler.start()

def stop_scheduler() -> bool:
    """Fonction utilitaire pour arrêter le scheduler"""
    return simple_scheduler.stop()

def restart_scheduler() -> bool:
    """Fonction utilitaire pour redémarrer le scheduler"""
    return simple_scheduler.restart()

def get_scheduler_status() -> Dict:
    """Fonction utilitaire pour récupérer le statut"""
    return simple_scheduler.get_status()

def is_scheduler_running() -> bool:
    """Fonction utilitaire pour vérifier si le scheduler tourne"""
    return simple_scheduler.is_running

def get_scheduler_health() -> Dict:
    """Fonction utilitaire pour récupérer la santé"""
    return simple_scheduler.get_health_report()

# =================== INFORMATIONS ===================

if __name__ == "__main__":
    print("🔧 SimpleScheduler - Service de programmation horaire")
    print("   Utilisez les fonctions :")
    print("   - start_scheduler() : Démarrer")
    print("   - stop_scheduler() : Arrêter")
    print("   - get_scheduler_status() : Statut")
    print("   - get_scheduler_health() : Santé")
    print("")
    print("   Ou utilisez l'instance globale :")
    print("   - simple_scheduler.start()")
    print("   - simple_scheduler.stop()")
    print("   - simple_scheduler.get_status()")
    print("")
    print("   Intégration Flask :")
    print("   from app.tasks.simple_scheduler import simple_scheduler")
    print("   simple_scheduler.start()")