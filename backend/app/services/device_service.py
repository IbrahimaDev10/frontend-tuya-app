# device_service.py - Service pour la gestion des appareils IoT
# Compatible avec vos modèles Device, DeviceData, Alert, DeviceAccess

from app.services.tuya_service import TuyaClient
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.alert import Alert
from app.models.device_access import DeviceAccess
from app import db
from datetime import datetime
import json

class DeviceService:
    """Service pour la gestion des appareils IoT"""
    
    def __init__(self):
        self.tuya_client = TuyaClient()
    
    def import_tuya_devices(self):
        """Importer les appareils depuis Tuya Cloud"""
        try:
            print("🔍 Début import appareils Tuya...")
            
            # Connexion au service Tuya
            if not self.tuya_client.auto_connect_from_env():
                return {
                    "success": False,
                    "error": "Impossible de se connecter à Tuya Cloud"
                }
            
            # Récupération des appareils
            devices_response = self.tuya_client.get_all_devices_with_details()
            
            if not devices_response.get("success"):
                return {
                    "success": False,
                    "error": devices_response.get("error", "Erreur récupération appareils")
                }
            
            devices = devices_response.get("result", [])
            print(f"📱 {len(devices)} appareils récupérés depuis Tuya")
            
            # Traitement des appareils
            appareils_importes = 0
            appareils_mis_a_jour = 0
            
            for device_data in devices:
                # Récupérer l'ID Tuya (différents formats possibles)
                tuya_device_id = device_data.get("id") or device_data.get("device_id")
                if not tuya_device_id:
                    continue
                
                # Rechercher si l'appareil existe déjà par tuya_device_id
                existing_device = Device.get_by_tuya_id(tuya_device_id)
                
                if existing_device:
                    # Mise à jour appareil existant
                    existing_device.tuya_nom_original = device_data.get("name", existing_device.tuya_nom_original)
                    existing_device.tuya_modele = device_data.get("model", existing_device.tuya_modele)
                    existing_device.en_ligne = device_data.get("isOnline", False)
                    
                    # Si pas de nom personnalisé, utiliser le nom Tuya
                    if not existing_device.nom_appareil or existing_device.nom_appareil == existing_device.tuya_nom_original:
                        existing_device.nom_appareil = device_data.get("name", tuya_device_id)
                    
                    existing_device.update_from_tuya_data(device_data)
                    appareils_mis_a_jour += 1
                else:
                    # Création nouvel appareil (NON-ASSIGNÉ par défaut)
                    device_name = device_data.get("name", f"Appareil {tuya_device_id}")
                    device_category = device_data.get("category", "unknown")
                    
                    # Déterminer le type d'appareil basé sur la catégorie Tuya
                    type_appareil = self._determine_device_type(device_category, device_data)
                    
                    new_device = Device(
                        tuya_device_id=tuya_device_id,
                        nom_appareil=device_name,
                        type_appareil=type_appareil,
                        tuya_nom_original=device_data.get("name", ""),
                        tuya_modele=device_data.get("model", ""),
                        tuya_version_firmware=device_data.get("sw_ver", ""),
                        en_ligne=device_data.get("isOnline", False),
                        statut_assignation='non_assigne',  # ✅ NON-ASSIGNÉ par défaut
                        date_installation=datetime.utcnow(),
                        actif=True
                    )
                    
                    db.session.add(new_device)
                    appareils_importes += 1
            
            # Sauvegarde
            db.session.commit()
            print(f"✅ Import terminé: {appareils_importes} nouveaux, {appareils_mis_a_jour} mis à jour")
            
            return {
                "success": True,
                "message": f"{len(devices)} appareils traités avec succès",
                "statistiques": {
                    "appareils_importes": appareils_importes,
                    "appareils_mis_a_jour": appareils_mis_a_jour,
                    "total": len(devices)
                }
            }
            
        except Exception as e:
            print(f"❌ Erreur import Tuya: {e}")
            db.session.rollback()
            return {
                "success": False,
                "error": f"Erreur lors de l'import: {str(e)}"
            }
    
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
    
    def get_device_status(self, tuya_device_id):
        """Récupérer le statut d'un appareil"""
        try:
            # Connexion si nécessaire
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion Tuya impossible"}
            
            # Récupération du statut depuis Tuya
            status_response = self.tuya_client.get_device_current_values(tuya_device_id)
            
            if status_response.get("success"):
                # Sauvegarder les données dans DeviceData
                device = Device.get_by_tuya_id(tuya_device_id)
                if device and device.is_assigne():
                    self._save_device_data(device, status_response)
                
                # Mettre à jour l'heure de dernière donnée
                if device:
                    device.update_last_data_time()
            
            return status_response
            
        except Exception as e:
            print(f"❌ Erreur statut appareil {tuya_device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def control_device(self, tuya_device_id, command, value=None):
        """Contrôler un appareil"""
        try:
            # Vérifier que l'appareil existe et peut être contrôlé
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            # Connexion si nécessaire
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion Tuya impossible"}
            
            # Commande switch (ON/OFF)
            if command == "toggle" or command == "switch":
                result = self.tuya_client.toggle_device(tuya_device_id, value)
                
                if result.get("success"):
                    # Mettre à jour la base de données
                    device.update_last_data_time()
                
                return result
            else:
                # Autres commandes
                commands = {
                    "commands": [
                        {
                            "code": command,
                            "value": value
                        }
                    ]
                }
                return self.tuya_client.send_device_command(tuya_device_id, commands)
                
        except Exception as e:
            print(f"❌ Erreur contrôle appareil {tuya_device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_all_devices(self, utilisateur=None, include_non_assignes=False):
        """Récupérer tous les appareils selon les permissions utilisateur"""
        try:
            if utilisateur and utilisateur.is_superadmin():
                # Superadmin voit tout
                if include_non_assignes:
                    devices = Device.query.all()
                else:
                    devices = Device.query.filter_by(statut_assignation='assigne').all()
            elif utilisateur:
                # Utilisateur normal ne voit que ses appareils assignés
                devices = Device.get_assignes_client(utilisateur.client_id)
            else:
                # Sans utilisateur, ne retourner que les non-assignés
                devices = Device.get_non_assignes() if include_non_assignes else []
            
            return {
                "success": True,
                "devices": [device.to_dict(include_stats=True, include_tuya_info=True) for device in devices]
            }
        except Exception as e:
            print(f"❌ Erreur récupération appareils DB: {e}")
            return {"success": False, "error": str(e)}
    
    def get_non_assigned_devices(self):
        """Récupérer tous les appareils non-assignés"""
        try:
            devices = Device.get_non_assignes()
            return {
                "success": True,
                "count": len(devices),
                "devices": [device.to_dict(include_tuya_info=True) for device in devices]
            }
        except Exception as e:
            print(f"❌ Erreur récupération appareils non-assignés: {e}")
            return {"success": False, "error": str(e)}
    
    def assign_device_to_client(self, tuya_device_id, client_id, site_id, utilisateur_assigneur_id=None):
        """Assigner un appareil à un client"""
        try:
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            if device.is_assigne():
                return {"success": False, "error": "Appareil déjà assigné"}
            
            success, message = device.assigner_a_client(client_id, site_id, utilisateur_assigneur_id)
            
            return {
                "success": success,
                "message": message,
                "device": device.to_dict() if success else None
            }
            
        except Exception as e:
            print(f"❌ Erreur assignation appareil: {e}")
            return {"success": False, "error": str(e)}
    
    def unassign_device(self, tuya_device_id):
        """Désassigner un appareil"""
        try:
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            if not device.is_assigne():
                return {"success": False, "error": "Appareil déjà non-assigné"}
            
            success, message = device.desassigner()
            
            return {
                "success": success,
                "message": message,
                "device": device.to_dict() if success else None
            }
            
        except Exception as e:
            print(f"❌ Erreur désassignation appareil: {e}")
            return {"success": False, "error": str(e)}
    
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
    
    def get_device_history(self, tuya_device_id, limit=100, hours_back=24):
        """Récupérer l'historique d'un appareil"""
        try:
            device = Device.get_by_tuya_id(tuya_device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            # Récupérer les données de la DB
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            data = DeviceData.query.filter_by(appareil_id=device.id)\
                                  .filter(DeviceData.horodatage >= start_time)\
                                  .order_by(DeviceData.horodatage.desc())\
                                  .limit(limit).all()
            
            return {
                "success": True,
                "device_id": tuya_device_id,
                "hours_back": hours_back,
                "count": len(data),
                "data": [d.to_dict() for d in data]
            }
        except Exception as e:
            print(f"❌ Erreur historique appareil {tuya_device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def sync_all_devices(self):
        """Synchroniser tous les appareils avec Tuya"""
        try:
            print("🔄 Synchronisation complète des appareils...")
            
            # Import depuis Tuya
            import_result = self.import_tuya_devices()
            
            if not import_result.get("success"):
                return import_result
            
            # Récupérer le statut de tous les appareils assignés
            devices = Device.query.filter_by(statut_assignation='assigne').all()
            sync_count = 0
            
            for device in devices:
                try:
                    status_result = self.get_device_status(device.tuya_device_id)
                    if status_result.get("success"):
                        sync_count += 1
                except Exception as e:
                    print(f"⚠️ Erreur sync {device.tuya_device_id}: {e}")
                    continue
            
            return {
                "success": True,
                "message": f"Synchronisation terminée: {sync_count} appareils",
                "import_stats": import_result.get("statistiques", {}),
                "sync_count": sync_count
            }
            
        except Exception as e:
            print(f"❌ Erreur synchronisation: {e}")
            return {"success": False, "error": str(e)}
    
    def get_device_statistics(self):
        """Obtenir les statistiques des appareils"""
        try:
            stats = Device.count_by_status()
            
            # Statistiques supplémentaires
            stats.update({
                'en_ligne': Device.query.filter_by(en_ligne=True).count(),
                'hors_ligne': Device.query.filter_by(en_ligne=False).count(),
                'actifs': Device.query.filter_by(actif=True).count(),
                'inactifs': Device.query.filter_by(actif=False).count()
            })
            
            return {"success": True, "statistiques": stats}
            
        except Exception as e:
            print(f"❌ Erreur statistiques appareils: {e}")
            return {"success": False, "error": str(e)}