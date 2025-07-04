# app/models/device.py - MODÈLE DEVICE COMPLET
# Version complète avec Protection, Programmation et toutes les extensions

from app import db
from datetime import datetime, timedelta, time
import uuid
import json
import pytz
from typing import List, Dict, Optional, Any

class Device(db.Model):
    """Modèle pour les appareils IoT avec support monophasé/triphasé + Protection/Programmation"""
    
    __tablename__ = 'devices'
    
    # =================== CHAMPS PRIMAIRES ===================
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relations
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=True, index=True)
    site_id = db.Column(db.String(36), db.ForeignKey('sites.id'), nullable=True, index=True)
    
    # Lien avec Tuya
    tuya_device_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    
    # Informations appareil
    nom_appareil = db.Column(db.String(255), nullable=False)
    type_appareil = db.Column(db.String(100), nullable=False)
    emplacement = db.Column(db.String(255), nullable=True)
    
    # Type de système électrique
    type_systeme = db.Column(db.Enum('monophase', 'triphase', name='electrical_system_type'), 
                           nullable=False, default='monophase', index=True)
    
    # Statut d'assignation
    statut_assignation = db.Column(db.Enum('non_assigne', 'assigne', name='device_assignment_status'), 
                                  nullable=False, default='non_assigne', index=True)
    
    # Métadonnées Tuya
    tuya_nom_original = db.Column(db.String(255), nullable=True)
    tuya_modele = db.Column(db.String(100), nullable=True)
    tuya_version_firmware = db.Column(db.String(50), nullable=True)
    
    # =================== SEUILS MONOPHASÉ ===================
    seuil_tension_min = db.Column(db.Float, nullable=True, default=200.0)
    seuil_tension_max = db.Column(db.Float, nullable=True, default=250.0)
    seuil_courant_max = db.Column(db.Float, nullable=True, default=20.0)
    seuil_puissance_max = db.Column(db.Float, nullable=True, default=5000.0)
    
    # =================== SEUILS TRIPHASÉ ===================
    # Seuils par phase - Tensions
    seuil_tension_l1_min = db.Column(db.Float, nullable=True)
    seuil_tension_l1_max = db.Column(db.Float, nullable=True)
    seuil_tension_l2_min = db.Column(db.Float, nullable=True)
    seuil_tension_l2_max = db.Column(db.Float, nullable=True)
    seuil_tension_l3_min = db.Column(db.Float, nullable=True)
    seuil_tension_l3_max = db.Column(db.Float, nullable=True)
    
    # Seuils par phase - Courants
    seuil_courant_l1_max = db.Column(db.Float, nullable=True)
    seuil_courant_l2_max = db.Column(db.Float, nullable=True)
    seuil_courant_l3_max = db.Column(db.Float, nullable=True)
    
    # Seuils déséquilibres
    seuil_desequilibre_tension = db.Column(db.Float, nullable=True, default=2.0)
    seuil_desequilibre_courant = db.Column(db.Float, nullable=True, default=10.0)
    seuil_facteur_puissance_min = db.Column(db.Float, nullable=True, default=0.85)
    
    # Seuil température (pour tous types)
    seuil_temperature_max = db.Column(db.Float, nullable=True, default=60.0)
    
    # =================== PROTECTION AUTOMATIQUE ===================
    # Protection activée/désactivée globalement
    protection_automatique_active = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # Configuration protection (JSON pour flexibilité)
    protection_courant_config = db.Column(db.JSON, nullable=True)
    protection_puissance_config = db.Column(db.JSON, nullable=True)
    protection_temperature_config = db.Column(db.JSON, nullable=True)
    protection_tension_config = db.Column(db.JSON, nullable=True)
    protection_desequilibre_config = db.Column(db.JSON, nullable=True)
    
    # Statistiques de déclenchements de protection
    protection_triggers_count = db.Column(db.Integer, default=0, nullable=False)
    derniere_protection_declenchee = db.Column(db.DateTime, nullable=True)
    derniere_protection_type = db.Column(db.String(50), nullable=True)
    
    # État de protection (normal, protected, error)
    protection_status = db.Column(db.Enum('normal', 'protected', 'error', name='protection_status_type'),
                                default='normal', nullable=False, index=True)
    
    # =================== PROGRAMMATION HORAIRE ===================
    # Programmation activée/désactivée
    programmation_active = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # Configuration des horaires (JSON)
    horaires_config = db.Column(db.JSON, nullable=True)
    
    # Prochaine action programmée (pour optimisation)
    prochaine_action_programmee = db.Column(db.DateTime, nullable=True)
    prochaine_action_type = db.Column(db.Enum('turn_on', 'turn_off', 'custom', name='scheduled_action_type'),
                                    nullable=True)
    
    # Dernière exécution d'action programmée
    derniere_action_programmee = db.Column(db.DateTime, nullable=True)
    derniere_action_programmee_type = db.Column(db.String(20), nullable=True)
    derniere_action_programmee_status = db.Column(db.Boolean, nullable=True)
    
    # Mode manuel (désactive temporairement la programmation)
    mode_manuel_actif = db.Column(db.Boolean, default=False, nullable=False)
    mode_manuel_jusqu = db.Column(db.DateTime, nullable=True)
    
    # =================== MÉTADONNÉES ET STATUS ===================
    date_installation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_assignation = db.Column(db.DateTime, nullable=True)
    derniere_donnee = db.Column(db.DateTime, nullable=True)
    actif = db.Column(db.Boolean, default=True, nullable=False, index=True)
    en_ligne = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # =================== RELATIONS ===================
    donnees = db.relationship('DeviceData', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    alertes = db.relationship('Alert', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    acces = db.relationship('DeviceAccess', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    protection_events = db.relationship('ProtectionEvent', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    scheduled_actions = db.relationship('ScheduledAction', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    action_logs = db.relationship('DeviceActionLog', backref='device', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Device {self.nom_appareil} ({self.type_systeme})>'
    
    # =================== MÉTHODES DE BASE ===================
    
    def is_assigne(self) -> bool:
        """Vérifier si l'appareil est assigné à un client"""
        return self.statut_assignation == 'assigne' and self.client_id is not None
    
    def is_triphase(self) -> bool:
        """Vérifier si l'appareil est triphasé"""
        return self.type_systeme == 'triphase'
    
    def is_monophase(self) -> bool:
        """Vérifier si l'appareil est monophasé"""
        return self.type_systeme == 'monophase'
    
    def update_last_data_time(self):
        """Mettre à jour le timestamp de dernière donnée"""
        try:
            self.derniere_donnee = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Erreur mise à jour dernière donnée: {e}")
    
    def update_online_status(self, is_online: bool) -> bool:
        """Mettre à jour le statut en ligne"""
        try:
            old_status = self.en_ligne
            self.en_ligne = is_online
            
            # Mettre à jour la dernière donnée si l'appareil vient de se connecter
            if is_online and not old_status:
                self.derniere_donnee = datetime.utcnow()
            
            db.session.commit()
            return True
        except Exception as e:
            print(f"Erreur mise à jour statut online pour {self.id}: {e}")
            db.session.rollback()
            return False
    
    # =================== GESTION DES SEUILS ===================
    
    def get_seuils_actifs(self) -> Dict[str, Any]:
        """Récupérer les seuils actifs selon le type de système"""
        if self.type_systeme == 'triphase':
            return {
                'type_systeme': 'triphase',
                'tensions': {
                    'L1_min': float(self.seuil_tension_l1_min) if self.seuil_tension_l1_min else None,
                    'L1_max': float(self.seuil_tension_l1_max) if self.seuil_tension_l1_max else None,
                    'L2_min': float(self.seuil_tension_l2_min) if self.seuil_tension_l2_min else None,
                    'L2_max': float(self.seuil_tension_l2_max) if self.seuil_tension_l2_max else None,
                    'L3_min': float(self.seuil_tension_l3_min) if self.seuil_tension_l3_min else None,
                    'L3_max': float(self.seuil_tension_l3_max) if self.seuil_tension_l3_max else None,
                },
                'courants': {
                    'L1_max': float(self.seuil_courant_l1_max) if self.seuil_courant_l1_max else None,
                    'L2_max': float(self.seuil_courant_l2_max) if self.seuil_courant_l2_max else None,
                    'L3_max': float(self.seuil_courant_l3_max) if self.seuil_courant_l3_max else None,
                },
                'desequilibres': {
                    'tension_max': float(self.seuil_desequilibre_tension) if self.seuil_desequilibre_tension else None,
                    'courant_max': float(self.seuil_desequilibre_courant) if self.seuil_desequilibre_courant else None,
                },
                'facteur_puissance_min': float(self.seuil_facteur_puissance_min) if self.seuil_facteur_puissance_min else None,
                'temperature_max': float(self.seuil_temperature_max) if self.seuil_temperature_max else None
            }
        else:
            # Monophasé
            return {
                'type_systeme': 'monophase',
                'tension_min': float(self.seuil_tension_min) if self.seuil_tension_min else None,
                'tension_max': float(self.seuil_tension_max) if self.seuil_tension_max else None,
                'courant_max': float(self.seuil_courant_max) if self.seuil_courant_max else None,
                'puissance_max': float(self.seuil_puissance_max) if self.seuil_puissance_max else None,
                'temperature_max': float(self.seuil_temperature_max) if self.seuil_temperature_max else None
            }
    
    def set_seuils_triphase(self, tensions_min: Dict[str, float] = None, tensions_max: Dict[str, float] = None,
                           courants_max: Dict[str, float] = None, desequilibre_tension: float = None,
                           desequilibre_courant: float = None, facteur_puissance_min: float = None) -> bool:
        """Configurer les seuils triphasés"""
        try:
            if tensions_min:
                self.seuil_tension_l1_min = tensions_min.get('L1')
                self.seuil_tension_l2_min = tensions_min.get('L2')
                self.seuil_tension_l3_min = tensions_min.get('L3')
            
            if tensions_max:
                self.seuil_tension_l1_max = tensions_max.get('L1')
                self.seuil_tension_l2_max = tensions_max.get('L2')
                self.seuil_tension_l3_max = tensions_max.get('L3')
            
            if courants_max:
                self.seuil_courant_l1_max = courants_max.get('L1')
                self.seuil_courant_l2_max = courants_max.get('L2')
                self.seuil_courant_l3_max = courants_max.get('L3')
            
            if desequilibre_tension is not None:
                self.seuil_desequilibre_tension = desequilibre_tension
            
            if desequilibre_courant is not None:
                self.seuil_desequilibre_courant = desequilibre_courant
            
            if facteur_puissance_min is not None:
                self.seuil_facteur_puissance_min = facteur_puissance_min
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur configuration seuils triphasés: {e}")
            return False
    
    def set_seuils_monophase(self, tension_min: float = None, tension_max: float = None,
                            courant_max: float = None, puissance_max: float = None,
                            temperature_max: float = None) -> bool:
        """Configurer les seuils monophasés"""
        try:
            if tension_min is not None:
                self.seuil_tension_min = tension_min
            if tension_max is not None:
                self.seuil_tension_max = tension_max
            if courant_max is not None:
                self.seuil_courant_max = courant_max
            if puissance_max is not None:
                self.seuil_puissance_max = puissance_max
            if temperature_max is not None:
                self.seuil_temperature_max = temperature_max
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur configuration seuils monophasés: {e}")
            return False
    
    # =================== GESTION PROTECTION AUTOMATIQUE ===================
    
    def enable_protection(self, protection_type: str, config: Dict[str, Any]) -> bool:
        """Activer un type de protection avec configuration"""
        try:
            self.protection_automatique_active = True
            
            base_config = {
                "enabled": True,
                "threshold": config.get("threshold"),
                "action": config.get("action", "turn_off"),
                "cooldown_minutes": config.get("cooldown_minutes", 5),
                "auto_restart": config.get("auto_restart", False),
                "restart_delay_minutes": config.get("restart_delay_minutes", 10),
                "configured_at": datetime.utcnow().isoformat()
            }
            
            if protection_type == "courant":
                base_config["threshold"] = config.get("threshold", self.seuil_courant_max or 20.0)
                self.protection_courant_config = base_config
                if "threshold" in config:
                    self.seuil_courant_max = config["threshold"]
                    
            elif protection_type == "puissance":
                base_config["threshold"] = config.get("threshold", self.seuil_puissance_max or 5000.0)
                self.protection_puissance_config = base_config
                if "threshold" in config:
                    self.seuil_puissance_max = config["threshold"]
                    
            elif protection_type == "temperature":
                base_config["threshold"] = config.get("threshold", self.seuil_temperature_max or 60.0)
                base_config["cooldown_minutes"] = config.get("cooldown_minutes", 10)
                base_config["restart_delay_minutes"] = config.get("restart_delay_minutes", 30)
                self.protection_temperature_config = base_config
                if "threshold" in config:
                    self.seuil_temperature_max = config["threshold"]
                    
            elif protection_type == "tension":
                base_config["threshold_min"] = config.get("threshold_min", self.seuil_tension_min)
                base_config["threshold_max"] = config.get("threshold_max", self.seuil_tension_max)
                self.protection_tension_config = base_config
                
            elif protection_type == "desequilibre" and self.is_triphase():
                base_config["threshold_tension"] = config.get("threshold_tension", self.seuil_desequilibre_tension or 2.0)
                base_config["threshold_courant"] = config.get("threshold_courant", self.seuil_desequilibre_courant or 10.0)
                self.protection_desequilibre_config = base_config
            
            db.session.commit()
            print(f"✅ Protection {protection_type} activée pour {self.nom_appareil}")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur activation protection {protection_type}: {e}")
            return False
    
    def disable_protection(self, protection_type: str = None) -> bool:
        """Désactiver protection (type spécifique ou toutes)"""
        try:
            if protection_type is None:
                # Désactiver toutes les protections
                self.protection_automatique_active = False
                self.protection_courant_config = None
                self.protection_puissance_config = None
                self.protection_temperature_config = None
                self.protection_tension_config = None
                self.protection_desequilibre_config = None
                self.protection_status = 'normal'
                
            elif protection_type == "courant" and self.protection_courant_config:
                config = dict(self.protection_courant_config)
                config["enabled"] = False
                config["disabled_at"] = datetime.utcnow().isoformat()
                self.protection_courant_config = config
                
            elif protection_type == "puissance" and self.protection_puissance_config:
                config = dict(self.protection_puissance_config)
                config["enabled"] = False
                config["disabled_at"] = datetime.utcnow().isoformat()
                self.protection_puissance_config = config
                
            elif protection_type == "temperature" and self.protection_temperature_config:
                config = dict(self.protection_temperature_config)
                config["enabled"] = False
                config["disabled_at"] = datetime.utcnow().isoformat()
                self.protection_temperature_config = config
                
            elif protection_type == "tension" and self.protection_tension_config:
                config = dict(self.protection_tension_config)
                config["enabled"] = False
                config["disabled_at"] = datetime.utcnow().isoformat()
                self.protection_tension_config = config
                
            elif protection_type == "desequilibre" and self.protection_desequilibre_config:
                config = dict(self.protection_desequilibre_config)
                config["enabled"] = False
                config["disabled_at"] = datetime.utcnow().isoformat()
                self.protection_desequilibre_config = config
            
            db.session.commit()
            print(f"✅ Protection {protection_type or 'toutes'} désactivée pour {self.nom_appareil}")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur désactivation protection: {e}")
            return False
    
    def get_protection_config(self) -> Dict[str, Any]:
        """Récupérer la configuration complète de protection"""
        return {
            "active": self.protection_automatique_active,
            "status": self.protection_status,
            "triggers_count": self.protection_triggers_count,
            "last_triggered": self.derniere_protection_declenchee.isoformat() if self.derniere_protection_declenchee else None,
            "last_triggered_type": self.derniere_protection_type,
            "configurations": {
                "courant": self.protection_courant_config or {"enabled": False},
                "puissance": self.protection_puissance_config or {"enabled": False},
                "temperature": self.protection_temperature_config or {"enabled": False},
                "tension": self.protection_tension_config or {"enabled": False},
                "desequilibre": self.protection_desequilibre_config or {"enabled": False} if self.is_triphase() else None
            }
        }
    
    def log_protection_trigger(self, protection_type: str, trigger_value: float, additional_data: Dict[str, Any] = None) -> bool:
        """Enregistrer un déclenchement de protection"""
        try:
            self.protection_triggers_count += 1
            self.derniere_protection_declenchee = datetime.utcnow()
            self.derniere_protection_type = protection_type
            self.protection_status = 'protected'
            
            db.session.commit()
            
            # Créer événement de protection si modèle disponible
            try:
                from app.models.protection_event import ProtectionEvent
                
                # Déterminer type d'événement basé sur protection_type
                event_type_mapping = {
                    'courant': 'courant_depasse',
                    'puissance': 'puissance_depassee',
                    'temperature': 'temperature_haute',
                    'tension_min': 'tension_anormale',
                    'tension_max': 'tension_anormale',
                    'desequilibre_tension': 'desequilibre_tension',
                    'desequilibre_courant': 'desequilibre_courant'
                }
                
                event_type = event_type_mapping.get(protection_type, 'autre')
                
                ProtectionEvent.creer_evenement_protection(
                    client_id=self.client_id,
                    appareil_id=self.id,
                    type_protection=event_type,
                    action_effectuee='arret_appareil',
                    valeur_declenchement=trigger_value,
                    valeur_seuil=self._get_threshold_for_protection_type(protection_type),
                    type_systeme=self.type_systeme,
                    etat_avant='on',
                    etat_apres='off',
                    details_techniques=additional_data or {}
                )
                
            except ImportError:
                pass  # ProtectionEvent n'est pas disponible
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur log protection trigger: {e}")
            return False
    
    def reset_protection_status(self) -> bool:
        """Réinitialiser le statut de protection"""
        try:
            self.protection_status = 'normal'
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            return False
    
    def _get_threshold_for_protection_type(self, protection_type: str) -> Optional[float]:
        """Récupérer le seuil pour un type de protection"""
        if protection_type == 'courant':
            return self.seuil_courant_max
        elif protection_type == 'puissance':
            return self.seuil_puissance_max
        elif protection_type == 'temperature':
            return self.seuil_temperature_max
        elif protection_type == 'tension_min':
            return self.seuil_tension_min
        elif protection_type == 'tension_max':
            return self.seuil_tension_max
        elif protection_type == 'desequilibre_tension':
            return self.seuil_desequilibre_tension
        elif protection_type == 'desequilibre_courant':
            return self.seuil_desequilibre_courant
        return None
    
    # =================== GESTION PROGRAMMATION HORAIRE ===================
    
    def set_horaires(self, allumage_time: str = None, extinction_time: str = None, 
                    days: List[int] = None, timezone: str = "Africa/Dakar") -> bool:
        """Configurer les horaires d'allumage/extinction"""
        try:
            config = self.horaires_config or {}
            
            if allumage_time:
                config["allumage"] = {
                    "enabled": True,
                    "time": allumage_time,
                    "days": days or [1,2,3,4,5,6,7],
                    "force_on": True
                }
            
            if extinction_time:
                config["extinction"] = {
                    "enabled": True,
                    "time": extinction_time,
                    "days": days or [1,2,3,4,5,6,7],
                    "force_off": True
                }
            
            config["timezone"] = timezone
            config["configured_at"] = datetime.utcnow().isoformat()
            
            self.horaires_config = config
            self.programmation_active = True
            
            # Calculer la prochaine action
            self._calculate_next_scheduled_action()
            
            db.session.commit()
            print(f"✅ Horaires configurés pour {self.nom_appareil}")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur configuration horaires: {e}")
            return False
    
    def disable_programmation(self) -> bool:
        """Désactiver la programmation horaire"""
        try:
            self.programmation_active = False
            self.prochaine_action_programmee = None
            self.prochaine_action_type = None
            
            if self.horaires_config:
                config = dict(self.horaires_config)
                config["disabled_at"] = datetime.utcnow().isoformat()
                self.horaires_config = config
            
            db.session.commit()
            print(f"✅ Programmation désactivée pour {self.nom_appareil}")
            return True
            
        except Exception as e:
            db.session.rollback()
            return False
    
    def enable_mode_manuel(self, duree_heures: int = 24) -> bool:
        """Activer le mode manuel temporairement"""
        try:
            self.mode_manuel_actif = True
            self.mode_manuel_jusqu = datetime.utcnow() + timedelta(hours=duree_heures)
            
            db.session.commit()
            print(f"🔧 Mode manuel activé pour {self.nom_appareil} ({duree_heures}h)")
            return True
            
        except Exception as e:
            db.session.rollback()
            return False
    
    def disable_mode_manuel(self) -> bool:
        """Désactiver le mode manuel"""
        try:
            self.mode_manuel_actif = False
            self.mode_manuel_jusqu = None
            
            # Recalculer la prochaine action
            self._calculate_next_scheduled_action()
            
            db.session.commit()
            print(f"🔧 Mode manuel désactivé pour {self.nom_appareil}")
            return True
            
        except Exception as e:
            db.session.rollback()
            return False
    
    def is_mode_manuel_expire(self) -> bool:
        """Vérifier si le mode manuel a expiré"""
        if not self.mode_manuel_actif:
            return False
        
        if self.mode_manuel_jusqu and datetime.utcnow() > self.mode_manuel_jusqu:
            # Mode manuel expiré - le désactiver automatiquement
            self.disable_mode_manuel()
            return True
        
        return False
    
    def get_horaires_config(self) -> Dict[str, Any]:
        """Récupérer la configuration complète des horaires"""
        return {
            "active": self.programmation_active,
            "mode_manuel": self.mode_manuel_actif,
            "mode_manuel_jusqu": self.mode_manuel_jusqu.isoformat() if self.mode_manuel_jusqu else None,
            "prochaine_action": self.prochaine_action_programmee.isoformat() if self.prochaine_action_programmee else None,
            "prochaine_action_type": self.prochaine_action_type,
            "derniere_action": {
                "timestamp": self.derniere_action_programmee.isoformat() if self.derniere_action_programmee else None,
                "type": self.derniere_action_programmee_type,
                "success": self.derniere_action_programmee_status
            },
            "horaires": self.horaires_config or {}
        }
    
     # ✅ MÉTHODE MANQUANTE à ajouter
    @staticmethod
    def get_by_tuya_id(tuya_device_id):
        """Récupérer un appareil par son tuya_device_id"""
        return Device.query.filter_by(tuya_device_id=tuya_device_id).first()
    
    # ✅ AUTRES MÉTHODES UTILES à ajouter si elles n'existent pas
    @staticmethod
    def get_non_assignes():
        """Récupérer les appareils non assignés"""
        return Device.query.filter_by(statut_assignation='non_assigne').all()
    
    @staticmethod
    def get_assignes_client(client_id):
        """Récupérer les appareils assignés à un client"""
        return Device.query.filter_by(
            client_id=client_id,
            statut_assignation='assigne'
        ).all()
    
    @staticmethod
    def count_by_status():
        """Compter les appareils par statut"""
        return {
            'total': Device.query.count(),
            'assignes': Device.query.filter_by(statut_assignation='assigne').count(),
            'non_assignes': Device.query.filter_by(statut_assignation='non_assigne').count(),
        }
    
    def is_assigne(self):
        """Vérifier si l'appareil est assigné"""
        return self.statut_assignation == 'assigne'
    
    def peut_etre_vu_par_utilisateur(self, user):
        """Vérifier si un utilisateur peut voir cet appareil"""
        if user.is_superadmin():
            return True
        
        if self.client_id == user.client_id:
            return True
            
        return False
    
    def peut_etre_controle_par_utilisateur(self, user):
        """Vérifier si un utilisateur peut contrôler cet appareil"""
        if not self.peut_etre_vu_par_utilisateur(user):
            return False
        
        # Ajouter d'autres vérifications selon vos besoins
        return True
    
    def peut_etre_configure_par_utilisateur(self, user):
        """Vérifier si un utilisateur peut configurer cet appareil"""
        return self.peut_etre_controle_par_utilisateur(user)
    
    def update_last_data_time(self):
        """Mettre à jour la dernière fois qu'on a reçu des données"""
        try:
            self.derniere_donnee = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            print(f"Erreur update last data time: {e}")
            db.session.rollback()
    
    def get_seuils_actifs(self):
        """Récupérer les seuils actifs de l'appareil"""
        return {
            'seuil_tension_min': getattr(self, 'seuil_tension_min', None),
            'seuil_tension_max': getattr(self, 'seuil_tension_max', None),
            'seuil_courant_max': getattr(self, 'seuil_courant_max', None),
            'seuil_puissance_max': getattr(self, 'seuil_puissance_max', None),
            'seuil_temperature_max': getattr(self, 'seuil_temperature_max', None)
        }
    
    def get_protection_config(self):
        """Récupérer la configuration de protection"""
        if not hasattr(self, 'protection_automatique_active'):
            return {'active': False}
            
        return {
            'active': getattr(self, 'protection_automatique_active', False),
            'status': getattr(self, 'protection_status', 'inactive'),
            'courant_config': getattr(self, 'protection_courant_config', {}),
            'puissance_config': getattr(self, 'protection_puissance_config', {}),
            'temperature_config': getattr(self, 'protection_temperature_config', {})
        }
    
    def get_horaires_config(self):
        """Récupérer la configuration des horaires"""
        if not hasattr(self, 'programmation_active'):
            return {'active': False}
            
        return {
            'active': getattr(self, 'programmation_active', False),
            'mode_manuel': getattr(self, 'mode_manuel_actif', False),
            'prochaine_action': getattr(self, 'prochaine_action_programmee', None)
        }
    
    def to_dict(self, include_stats=False, include_tuya_info=False, 
               include_protection=False, include_programmation=False):
        """Convertir en dictionnaire avec options"""
        base_dict = {
            'id': self.id,
            'tuya_device_id': self.tuya_device_id,
            'nom_appareil': self.nom_appareil,
            'type_appareil': self.type_appareil,
            'en_ligne': self.en_ligne,
            'actif': self.actif,
            'statut_assignation': self.statut_assignation,
            'client_id': self.client_id,
            'site_id': getattr(self, 'site_id', None),
            'date_installation': self.date_installation.isoformat() if self.date_installation else None,
            'derniere_donnee': self.derniere_donnee.isoformat() if self.derniere_donnee else None
        }
        
        if include_tuya_info:
            base_dict.update({
                'tuya_nom_original': getattr(self, 'tuya_nom_original', None),
                'tuya_modele': getattr(self, 'tuya_modele', None),
                'tuya_version_firmware': getattr(self, 'tuya_version_firmware', None)
            })
        
        if include_protection:
            base_dict['protection'] = self.get_protection_config()
        
        if include_programmation:
            base_dict['programmation'] = self.get_horaires_config()
        
        if include_stats:
            base_dict.update({
                'type_systeme': getattr(self, 'type_systeme', 'monophase'),
                'emplacement': getattr(self, 'emplacement', None),
                'description': getattr(self, 'description', None)
            })
        
        return base_dict
    
    def assigner_a_client(self, client_id, site_id, utilisateur_assigneur_id=None):
        """Assigner l'appareil à un client"""
        try:
            self.client_id = client_id
            self.site_id = site_id
            self.statut_assignation = 'assigne'
            self.assignateur_id = utilisateur_assigneur_id
            self.date_assignation = datetime.utcnow()
            
            db.session.commit()
            return True, "Appareil assigné avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur assignation: {str(e)}"
    
    def desassigner(self):
        """Désassigner l'appareil"""
        try:
            self.client_id = None
            self.site_id = None
            self.statut_assignation = 'non_assigne'
            self.assignateur_id = None
            self.date_assignation = None
            
            # Désactiver protections et programmations
            if hasattr(self, 'protection_automatique_active'):
                self.protection_automatique_active = False
            if hasattr(self, 'programmation_active'):
                self.programmation_active = False
            
            db.session.commit()
            return True, "Appareil désassigné avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur désassignation: {str(e)}"



    def peut_etre_vu_par_utilisateur(self, user):
        """Vérifier si un utilisateur peut voir cet appareil - VERSION AVEC SITE"""
        if user.is_superadmin():
            return True
        
        # Vérifier que l'appareil appartient au même client
        if self.client_id != user.client_id:
            return False
        
        # Admin peut voir tous les appareils de son client
        if user.is_admin():
            return True
        
        # ✅ NOUVEAU : User simple - vérifier accès au site spécifique
        if user.role == 'user':
            # User simple doit avoir un site assigné ET l'appareil doit être sur ce site
            if not user.site_id:
                return False  # User sans site ne peut rien voir
            
            return self.site_id == user.site_id
        
        return False
    
    def peut_etre_controle_par_utilisateur(self, user):
        """Vérifier si un utilisateur peut contrôler cet appareil - VERSION AVEC SITE"""
        if not self.peut_etre_vu_par_utilisateur(user):
            return False
        
        if user.is_superadmin() or user.is_admin():
            return True
        
        # ✅ User simple : peut contrôler si c'est son site
        if user.role == 'user':
            return self.site_id == user.site_id and user.site_id is not None
        
        return False
    
    def peut_etre_configure_par_utilisateur(self, user):
        """Vérifier si un utilisateur peut configurer cet appareil - VERSION AVEC SITE"""
        if not self.peut_etre_vu_par_utilisateur(user):
            return False
        
        if user.is_superadmin() or user.is_admin():
            return True
        
        # ✅ User simple : peut configurer si c'est son site (selon vos règles business)
        if user.role == 'user':
            # Option A : User peut configurer son site
            return self.site_id == user.site_id and user.site_id is not None
            
            # Option B : User ne peut que voir/contrôler mais pas configurer
            # return False
        
        return False
    
    # ✅ NOUVELLE MÉTHODE : Récupérer appareils par site utilisateur
    @staticmethod
    def get_appareils_site_utilisateur(user):
        """Récupérer les appareils accessibles à un utilisateur selon son site"""
        if user.is_superadmin():
            # Superadmin voit tout
            return Device.query.filter_by(statut_assignation='assigne').all()
        
        elif user.is_admin():
            # Admin voit tous les appareils de son client
            return Device.query.filter_by(
                client_id=user.client_id,
                statut_assignation='assigne'
            ).all()
        
        elif user.role == 'user':
            # ✅ User simple : uniquement son site
            if not user.site_id:
                return []  # Pas de site = pas d'appareils
            
            return Device.query.filter_by(
                client_id=user.client_id,
                site_id=user.site_id,
                statut_assignation='assigne'
            ).all()
        
        return []
    
    # ✅ NOUVELLE MÉTHODE : Compter appareils par site utilisateur
    @staticmethod
    def count_appareils_site_utilisateur(user):
        """Compter les appareils accessibles à un utilisateur"""
        if user.is_superadmin():
            return {
                'total': Device.query.filter_by(statut_assignation='assigne').count(),
                'en_ligne': Device.query.filter_by(statut_assignation='assigne', en_ligne=True).count(),
                'hors_ligne': Device.query.filter_by(statut_assignation='assigne', en_ligne=False).count()
            }
        
        elif user.is_admin():
            total = Device.query.filter_by(client_id=user.client_id, statut_assignation='assigne').count()
            en_ligne = Device.query.filter_by(client_id=user.client_id, statut_assignation='assigne', en_ligne=True).count()
            return {
                'total': total,
                'en_ligne': en_ligne,
                'hors_ligne': total - en_ligne
            }
        
        elif user.role == 'user' and user.site_id:
            total = Device.query.filter_by(
                client_id=user.client_id,
                site_id=user.site_id,
                statut_assignation='assigne'
            ).count()
            en_ligne = Device.query.filter_by(
                client_id=user.client_id,
                site_id=user.site_id,
                statut_assignation='assigne',
                en_ligne=True
            ).count()
            return {
                'total': total,
                'en_ligne': en_ligne,
                'hors_ligne': total - en_ligne,
                'site_id': user.site_id
            }
        
        return {'total': 0, 'en_ligne': 0, 'hors_ligne': 0}