# device_service.py - Service pour la gestion des appareils IoT
# Compatible avec vos modèles Device, DeviceData, Alert, DeviceAccess

from app.services.tuya_service import TuyaClient
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.alert import Alert
from app.models.device_access import DeviceAccess
from app import db
from datetime import datetime, timedelta
import json

class DeviceService:
    """Service pour la gestion des appareils IoT"""
    
    def __init__(self):
        self.tuya_client = TuyaClient()
    
    def import_tuya_devices(self):
        """Import avec PRIORITÉ à l'endpoint liste ET correction du problème de commit"""
        try:
            print("🔍 Début import appareils Tuya avec priorité endpoint liste...")
            
            if not self.tuya_client.auto_connect_from_env():
                return {"success": False, "error": "Impossible de se connecter à Tuya Cloud"}
            
            # Récupération des appareils depuis Tuya (SOURCE FIABLE pour les statuts)
            devices_response = self.tuya_client.get_all_devices_with_details()
            
            if not devices_response.get("success"):
                return {"success": False, "error": devices_response.get("error", "Erreur récupération appareils")}
            
            devices = devices_response.get("result", [])
            print(f"📱 {len(devices)} appareils récupérés depuis Tuya")
            
            appareils_importes = 0
            appareils_mis_a_jour = 0
            online_count = 0
            offline_count = 0
            
            # ✅ CRÉER UN MAPPING des statuts depuis l'endpoint liste (SOURCE FIABLE)
            device_status_map = {}
            for device_data in devices:
                device_id = device_data.get("id")
                if device_id:
                    device_status_map[device_id] = device_data.get("isOnline", False)
            
            print(f"📊 Mapping des statuts créé pour {len(device_status_map)} appareils")
            
            for device_data in devices:
                tuya_device_id = device_data.get("id") or device_data.get("device_id")
                if not tuya_device_id:
                    continue
                
                # ✅ UTILISER LE STATUT de l'ENDPOINT LISTE (plus fiable)
                is_online = device_status_map.get(tuya_device_id, False)
                device_name = device_data.get("name", f"Appareil {tuya_device_id}")
                
                # ✅ LOGGING détaillé pour debug
                status_emoji = "🟢" if is_online else "🔴"
                status_text = "EN LIGNE" if is_online else "HORS LIGNE"
                print(f"📡 {device_name}: {status_emoji} {status_text} (depuis endpoint liste)")
                
                if is_online:
                    online_count += 1
                else:
                    offline_count += 1
                
                # Rechercher appareil existant
                existing_device = Device.get_by_tuya_id(tuya_device_id)
                
                if existing_device:
                    # ✅ MISE À JOUR DIRECTE des attributs (SANS update_from_tuya_data)
                    old_status = existing_device.en_ligne
                    
                    # ✅ CORRECTION: Mise à jour directe sans passer par une méthode qui pourrait poser problème
                    existing_device.en_ligne = is_online
                    existing_device.tuya_nom_original = device_data.get("name", existing_device.tuya_nom_original)
                    existing_device.tuya_modele = device_data.get("model", existing_device.tuya_modele)
                    existing_device.tuya_version_firmware = device_data.get("sw_ver", existing_device.tuya_version_firmware)
                    
                    if not existing_device.nom_appareil or existing_device.nom_appareil == existing_device.tuya_nom_original:
                        existing_device.nom_appareil = device_name
                    
                    # ✅ MARQUER l'objet comme modifié explicitement
                    db.session.add(existing_device)
                    appareils_mis_a_jour += 1
                    
                    # ✅ LOG du changement de statut
                    if old_status != is_online:
                        change_text = f"{'🟢' if old_status else '🔴'} → {'🟢' if is_online else '🔴'}"
                        print(f"   🔄 Statut changé: {change_text}")
                        print(f"   🔧 DEBUG: Objet en_ligne = {existing_device.en_ligne}")
                    
                else:
                    # Créer nouvel appareil avec le statut de l'endpoint liste
                    device_category = device_data.get("category", "unknown")
                    type_appareil = self._determine_device_type(device_category, device_data)
                    
                    new_device = Device(
                        tuya_device_id=tuya_device_id,
                        nom_appareil=device_name,
                        type_appareil=type_appareil,
                        tuya_nom_original=device_data.get("name", ""),
                        tuya_modele=device_data.get("model", ""),
                        tuya_version_firmware=device_data.get("sw_ver", ""),
                        en_ligne=is_online,  # ✅ STATUT de l'endpoint liste
                        statut_assignation='non_assigne',
                        date_installation=datetime.utcnow(),
                        actif=True
                    )
                    
                    db.session.add(new_device)
                    appareils_importes += 1
            
            # ✅ FLUSH avant commit pour détecter les erreurs
            try:
                db.session.flush()
                print("💾 Flush réussi - Préparation du commit...")
            except Exception as flush_error:
                print(f"❌ Erreur lors du flush: {flush_error}")
                db.session.rollback()
                return {"success": False, "error": f"Erreur flush: {str(flush_error)}"}
            
            # ✅ COMMIT avec gestion d'erreur
            try:
                db.session.commit()
                print("💾 Commit réussi - Changements sauvegardés en base de données")
            except Exception as commit_error:
                print(f"❌ Erreur lors du commit: {commit_error}")
                db.session.rollback()
                return {"success": False, "error": f"Erreur commit: {str(commit_error)}"}
            
            # ✅ VÉRIFICATION POST-COMMIT AMÉLIORÉE
            print("🔍 VÉRIFICATION POST-COMMIT DÉTAILLÉE:")
            
            # Nouvelle session pour être sûr
            db.session.expire_all()
            
            all_devices_check = Device.query.all()
            online_check = 0
            offline_check = 0
            
            print("🔍 ÉTAT RÉEL EN BASE:")
            for device_check in all_devices_check:
                if device_check.en_ligne:
                    online_check += 1
                    print(f"   🟢 {device_check.nom_appareil} - EN LIGNE (DB)")
                else:
                    offline_check += 1
                    print(f"   🔴 {device_check.nom_appareil} - HORS LIGNE (DB)")
            
            print(f"   📊 TOTAL DB: {online_check} 🟢, {offline_check} 🔴")
            
            # ✅ VÉRIFICATION DE COHÉRENCE
            if online_check != (online_count - (1 if offline_count > 0 else 0)):
                print(f"⚠️ INCOHÉRENCE DÉTECTÉE:")
                print(f"   Attendu: {online_count} en ligne")
                print(f"   DB: {online_check} en ligne")
                
                # ✅ CORRECTION FORCÉE si incohérence
                print("🔧 CORRECTION FORCÉE...")
                for device_data in devices:
                    tuya_device_id = device_data.get("id")
                    is_online = device_data.get("isOnline", False)
                    
                    if tuya_device_id:
                        db_device = Device.get_by_tuya_id(tuya_device_id)
                        if db_device and db_device.en_ligne != is_online:
                            print(f"   🔧 Correction {db_device.nom_appareil}: {db_device.en_ligne} → {is_online}")
                            db_device.en_ligne = is_online
                            db.session.add(db_device)
                
                # Nouveau commit pour les corrections
                try:
                    db.session.commit()
                    print("   ✅ Corrections appliquées")
                    
                    # Re-vérification
                    db.session.expire_all()
                    final_online = Device.query.filter_by(en_ligne=True).count()
                    final_offline = Device.query.filter_by(en_ligne=False).count()
                    print(f"   📊 APRÈS CORRECTION: {final_online} 🟢, {final_offline} 🔴")
                    
                except Exception as correction_error:
                    print(f"   ❌ Erreur correction: {correction_error}")
                    db.session.rollback()
            
            print(f"✅ Import terminé:")
            print(f"   📊 {appareils_importes} nouveaux, {appareils_mis_a_jour} mis à jour")
            print(f"   🟢 {online_count} en ligne (Tuya)")
            print(f"   🔴 {offline_count} hors ligne (Tuya)")
            
            return {
                "success": True,
                "message": f"{len(devices)} appareils traités avec succès",
                "statistiques": {
                    "appareils_importes": appareils_importes,
                    "appareils_mis_a_jour": appareils_mis_a_jour,
                    "total": len(devices),
                    "online": online_count,
                    "offline": offline_count
                }
            }
            
        except Exception as e:
            print(f"❌ Erreur import Tuya: {e}")
            db.session.rollback()
            return {"success": False, "error": f"Erreur lors de l'import: {str(e)}"}
    
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
    
    def get_all_devices(self, utilisateur=None, include_non_assignes=False, refresh_status=True):
        """Récupérer tous les appareils selon les permissions utilisateur avec statuts réels"""
        try:
            # ✅ OPTION 1: Synchronisation automatique des statuts avant récupération
            if refresh_status:
                print("🔄 Actualisation des statuts avant récupération...")
                sync_result = self.import_tuya_devices()
                if not sync_result.get("success"):
                    print(f"⚠️ Échec synchronisation statuts: {sync_result.get('error')}")
                    # Continue même si la sync échoue, avec les données DB existantes
                else:
                    db.session.expire_all()
            
            # Récupération selon les permissions utilisateur
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
            
            # ✅ OPTION 2: Vérification rapide des statuts individuels (si pas de sync complète)
            if not refresh_status and len(devices) <= 20:  # Limite pour éviter trop d'appels API
                print("⚡ Vérification rapide des statuts individuels...")
                self._quick_status_verification(devices)
                db.session.expire_all()
                # Re-récupérer après mise à jour
                if utilisateur and utilisateur.is_superadmin():
                    if include_non_assignes:
                        devices = Device.query.all()
                    else:
                        devices = Device.query.filter_by(statut_assignation='assigne').all()
                elif utilisateur:
                    devices = Device.get_assignes_client(utilisateur.client_id)
                else:
                    devices = Device.get_non_assignes() if include_non_assignes else []
            
            # Préparer le résultat avec infos de synchronisation
            result = {
                "success": True,
                "devices": [device.to_dict(include_stats=True, include_tuya_info=True) for device in devices],
                "count": len(devices),
                "last_sync": datetime.utcnow().isoformat() if refresh_status else None
            }
            
            # ✅ Statistiques en temps réel
            online_count = sum(1 for d in devices if d.en_ligne)
            offline_count = len(devices) - online_count
            
            result["stats"] = {
                "total": len(devices),
                "online": online_count,
                "offline": offline_count,
                "sync_method": "full_import" if refresh_status else "quick_check"
            }
            
            print(f"📊 Appareils récupérés: {len(devices)} ({online_count} 🟢, {offline_count} 🔴)")
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur récupération appareils DB: {e}")
            return {"success": False, "error": str(e)}
    
    def get_non_assigned_devices(self, refresh_status=True):
        """Récupérer tous les appareils non-assignés avec statuts réels"""
        try:
            print("🔍 Récupération appareils non-assignés...")
            
            # ✅ SYNCHRONISATION des statuts avant récupération
            if refresh_status:
                print("🔄 Actualisation des statuts avant récupération...")
                sync_result = self.import_tuya_devices()
                if not sync_result.get("success"):
                    print(f"⚠️ Échec synchronisation: {sync_result.get('error')}")
                    # Continue même si la sync échoue
                else:
                    # ✅ FORCER le commit et refresh de la session pour voir les changements
                    db.session.expire_all()
            
            # ✅ RÉCUPÉRER les appareils APRÈS le refresh de session
            devices = Device.get_non_assignes()
            
            # ✅ VÉRIFICATION RAPIDE des statuts si pas de sync complète
            if not refresh_status and len(devices) <= 20:
                print("⚡ Vérification rapide des statuts...")
                self._update_devices_status_from_tuya(devices)
                # Forcer le commit après la vérification rapide
                db.session.commit()
                db.session.expire_all()
                # Re-récupérer les appareils pour avoir les vrais statuts
                devices = Device.get_non_assignes()
            
            # ✅ CALCULER les statistiques avec DEBUG
            online_count = 0
            offline_count = 0
            
            print("🔍 DÉCOMPTE DES STATUTS:")
            for device in devices:
                if device.en_ligne:
                    online_count += 1
                    print(f"   🟢 {device.nom_appareil} - EN LIGNE")
                else:
                    offline_count += 1
                    print(f"   🔴 {device.nom_appareil} - HORS LIGNE")
            
            print(f"📊 RÉSULTAT FINAL: {len(devices)} appareils ({online_count} 🟢, {offline_count} 🔴)")
            
            return {
                "success": True,
                "count": len(devices),
                "devices": [device.to_dict(include_tuya_info=True) for device in devices],
                "stats": {
                    "total": len(devices),
                    "online": online_count,
                    "offline": offline_count
                },
                "last_refresh": datetime.utcnow().isoformat() if refresh_status else None,
                "message": f"{len(devices)} appareils non-assignés trouvés"
            }
            
        except Exception as e:
            print(f"❌ Erreur récupération appareils non-assignés: {e}")
            return {"success": False, "error": str(e)}
    
    def _update_devices_status_from_tuya(self, devices):
        """Mettre à jour les statuts d'une liste d'appareils depuis Tuya"""
        try:
            if not devices or not self.tuya_client.reconnect_if_needed():
                return
            
            # Récupérer tous les statuts depuis l'endpoint liste Tuya
            devices_response = self.tuya_client.get_all_devices_with_details()
            if not devices_response.get("success"):
                print("⚠️ Impossible de récupérer les statuts Tuya")
                return
            
            # Créer un mapping des statuts Tuya
            tuya_devices = devices_response.get("result", [])
            tuya_status_map = {}
            for tuya_device in tuya_devices:
                device_id = tuya_device.get("id")
                if device_id:
                    tuya_status_map[device_id] = tuya_device.get("isOnline", False)
            
            # Mettre à jour les statuts des appareils
            updated_count = 0
            for device in devices:
                tuya_status = tuya_status_map.get(device.tuya_device_id)
                if tuya_status is not None and device.en_ligne != tuya_status:
                    old_status = device.en_ligne
                    device.en_ligne = tuya_status
                    updated_count += 1
                    
                    status_change = f"{'🟢' if old_status else '🔴'} → {'🟢' if tuya_status else '🔴'}"
                    print(f"   🔄 {device.nom_appareil}: {status_change}")
            
            # Sauvegarder les changements
            if updated_count > 0:
                db.session.commit()
                print(f"✅ {updated_count} statuts mis à jour")
            else:
                print("ℹ️ Tous les statuts sont déjà à jour")
                
        except Exception as e:
            print(f"⚠️ Erreur mise à jour statuts: {e}")
            db.session.rollback()

    def _quick_status_verification(self, devices):
        """Vérification rapide des statuts pour un petit nombre d'appareils"""
        try:
            if not self.tuya_client.reconnect_if_needed():
                print("⚠️ Impossible de vérifier les statuts - connexion Tuya échouée")
                return
            
            # Récupérer la liste complète depuis Tuya pour avoir tous les statuts
            devices_response = self.tuya_client.get_all_devices_with_details()
            if not devices_response.get("success"):
                print("⚠️ Impossible de récupérer la liste Tuya pour vérification")
                return
            
            # Créer un mapping des statuts Tuya
            tuya_devices = devices_response.get("result", [])
            tuya_status_map = {}
            for tuya_device in tuya_devices:
                device_id = tuya_device.get("id")
                if device_id:
                    tuya_status_map[device_id] = tuya_device.get("isOnline", False)
            
            # Mettre à jour les statuts si différents
            updated_count = 0
            for device in devices:
                tuya_status = tuya_status_map.get(device.tuya_device_id)
                if tuya_status is not None and device.en_ligne != tuya_status:
                    old_status = device.en_ligne
                    device.en_ligne = tuya_status
                    updated_count += 1
                    
                    status_change = f"{'🟢' if old_status else '🔴'} → {'🟢' if tuya_status else '🔴'}"
                    print(f"   🔄 {device.nom_appareil}: {status_change}")
            
            if updated_count > 0:
                db.session.commit()
                print(f"✅ {updated_count} statuts mis à jour")
            else:
                print("ℹ️ Tous les statuts sont à jour")
                
        except Exception as e:
            print(f"⚠️ Erreur vérification rapide: {e}")
    
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
        """Synchronisation en PRIORISANT l'endpoint liste Tuya"""
        try:
            print("🔄 Synchronisation avec priorité endpoint liste Tuya...")
            
            # 1. ✅ Import depuis Tuya (qui utilise maintenant l'endpoint liste)
            import_result = self.import_tuya_devices()
            
            if not import_result.get("success"):
                return import_result
            
            # 2. ✅ PAS de double vérification par API individuelle 
            # (car elle donne des résultats incohérents)
            print("ℹ️ Utilisation exclusive de l'endpoint liste pour éviter les incohérences")
            
            # 3. ✅ Récupérer les statistiques finales depuis la DB
            all_devices = Device.query.all()
            online_final = Device.query.filter_by(en_ligne=True).count()
            offline_final = Device.query.filter_by(en_ligne=False).count()
            
            print(f"✅ Synchronisation terminée:")
            print(f"   📊 {len(all_devices)} appareils")
            print(f"   🟢 {online_final} en ligne")
            print(f"   🔴 {offline_final} hors ligne")
            
            return {
                "success": True,
                "message": f"Synchronisation terminée: {len(all_devices)} appareils",
                "import_stats": import_result.get("statistiques", {}),
                "sync_stats": {
                    "total": len(all_devices),
                    "final_online": online_final,
                    "final_offline": offline_final,
                    "source": "endpoint_liste_uniquement"
                }
            }
            
        except Exception as e:
            print(f"❌ Erreur synchronisation: {e}")
            db.session.rollback()
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

    # ✅ MÉTHODES SUPPLÉMENTAIRES pour diagnostiquer et forcer les statuts
    
    def diagnose_tuya_inconsistency(self, tuya_device_id):
        """Diagnostiquer les incohérences entre les endpoints Tuya"""
        try:
            print(f"🔬 DIAGNOSTIC incohérences Tuya pour {tuya_device_id}")
            
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion impossible"}
            
            # 1. ✅ ENDPOINT LISTE
            devices_response = self.tuya_client.get_all_devices_with_details()
            list_status = None
            if devices_response.get("success"):
                devices = devices_response.get("result", [])
                for device_data in devices:
                    if device_data.get("id") == tuya_device_id:
                        list_status = device_data.get("isOnline")
                        break
            
            # 2. ✅ ENDPOINT INDIVIDUEL
            individual_response = self.tuya_client.get_device_status(tuya_device_id)
            individual_status = individual_response.get("success", False)
            
            # 3. ✅ COMPARAISON
            consistent = (list_status == individual_status)
            
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
                "consistent": consistent,
                "recommended_source": "endpoint_liste"
            }
            
            print(f"📊 RÉSULTATS:")
            print(f"   Endpoint liste: {'🟢' if list_status else '🔴'}")
            print(f"   Endpoint individuel: {'🟢' if individual_status else '🔴'}")
            print(f"   Cohérent: {'✅' if consistent else '❌'}")
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur diagnostic: {e}")
            return {"success": False, "error": str(e)}

    def force_status_from_list_endpoint(self, tuya_device_id):
        """Forcer le statut depuis l'endpoint liste (plus fiable)"""
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
            
            db_device.en_ligne = list_status
            db.session.commit()
            
            print(f"✅ Statut forcé depuis endpoint liste:")
            print(f"   Ancien: {'🟢' if old_status else '🔴'}")
            print(f"   Nouveau: {'🟢' if list_status else '🔴'}")
            
            return {
                "success": True,
                "device_id": tuya_device_id,
                "old_status": old_status,
                "new_status": list_status,
                "source": "endpoint_liste",
                "changed": old_status != list_status
            }
            
        except Exception as e:
            print(f"❌ Erreur force statut: {e}")
            return {"success": False, "error": str(e)}

    def refresh_all_device_statuses(self):
        """Forcer la synchronisation de tous les statuts d'appareils"""
        try:
            print("🔄 Synchronisation forcée de tous les statuts...")
            
            # Utiliser import_tuya_devices qui gère maintenant les statuts correctement
            result = self.import_tuya_devices()
            
            if result.get("success"):
                stats = result.get("statistiques", {})
                
                return {
                    "success": True,
                    "message": "Statuts synchronisés avec succès",
                    "stats": stats,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return result
                
        except Exception as e:
            print(f"❌ Erreur synchronisation statuts: {e}")
            return {"success": False, "error": str(e)}

    def get_assigned_devices(self, utilisateur, refresh_status=False):
        """Récupérer les appareils assignés à un utilisateur avec statuts réels"""
        try:
            print(f"🔍 Récupération appareils assignés pour utilisateur {utilisateur.id}...")
            
            # Utiliser get_all_devices avec refresh optionnel (moins fréquent pour les assignés)
            result = self.get_all_devices(
                utilisateur=utilisateur,
                include_non_assignes=False,
                refresh_status=refresh_status
            )
            
            if result.get("success"):
                devices = result.get("devices", [])
                
                return {
                    "success": True,
                    "count": len(devices),
                    "devices": devices,
                    "last_refresh": result.get("last_sync"),
                    "stats": result.get("stats"),
                    "client_id": utilisateur.client_id if hasattr(utilisateur, 'client_id') else None
                }
            else:
                return result
                
        except Exception as e:
            print(f"❌ Erreur récupération appareils assignés: {e}")
            return {"success": False, "error": str(e)}

    def check_device_online_status(self, tuya_device_id):
        """Vérifier rapidement si un appareil est en ligne"""
        try:
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
                    "checked_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": True,
                    "device_id": tuya_device_id,
                    "is_online": is_online,
                    "device_in_db": False,
                    "checked_at": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            print(f"❌ Erreur vérification {tuya_device_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_device_real_time_data(self, tuya_device_id):
        """Récupérer les données en temps réel d'un appareil avec son statut"""
        try:
            print(f"📊 Récupération données temps réel pour {tuya_device_id}")
            
            # 1. Vérifier le statut en ligne d'abord
            status_check = self.check_device_online_status(tuya_device_id)
            if not status_check.get("success"):
                return status_check
            
            is_online = status_check.get("is_online", False)
            
            # 2. Si en ligne, récupérer les données détaillées
            if is_online:
                values_response = self.tuya_client.get_device_current_values(tuya_device_id)
                if values_response.get("success"):
                    return {
                        "success": True,
                        "device_id": tuya_device_id,
                        "is_online": True,
                        "data": values_response.get("values", {}),
                        "timestamp": datetime.utcnow().isoformat(),
                        "raw_response": values_response
                    }
                else:
                    return {
                        "success": True,
                        "device_id": tuya_device_id,
                        "is_online": True,
                        "data": {},
                        "timestamp": datetime.utcnow().isoformat(),
                        "error": "Impossible de récupérer les valeurs détaillées"
                    }
            else:
                return {
                    "success": True,
                    "device_id": tuya_device_id,
                    "is_online": False,
                    "data": {},
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": "Appareil hors ligne"
                }
                
        except Exception as e:
            print(f"❌ Erreur données temps réel {tuya_device_id}: {e}")
            return {"success": False, "error": str(e)}

    def batch_check_devices_status(self, device_ids_list):
        """Vérifier le statut de plusieurs appareils en une seule fois"""
        try:
            print(f"🔍 Vérification batch de {len(device_ids_list)} appareils...")
            
            if not self.tuya_client.reconnect_if_needed():
                return {"success": False, "error": "Connexion Tuya impossible"}
            
            # Récupérer tous les statuts depuis Tuya
            devices_response = self.tuya_client.get_all_devices_with_details()
            if not devices_response.get("success"):
                return {"success": False, "error": "Impossible de récupérer les statuts Tuya"}
            
            tuya_devices = devices_response.get("result", [])
            tuya_status_map = {}
            for tuya_device in tuya_devices:
                device_id = tuya_device.get("id")
                if device_id:
                    tuya_status_map[device_id] = tuya_device.get("isOnline", False)
            
            # Vérifier et mettre à jour chaque appareil demandé
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
                    
                    results.append({
                        "device_id": device_id,
                        "device_name": device.nom_appareil,
                        "is_online": tuya_status,
                        "changed": old_status != tuya_status,
                        "old_status": old_status
                    })
                else:
                    results.append({
                        "device_id": device_id,
                        "device_name": "Inconnu",
                        "is_online": tuya_status,
                        "changed": False,
                        "error": "Appareil non trouvé en DB" if not device else "Statut Tuya non trouvé"
                    })
            
            # Sauvegarder les changements
            if updated_count > 0:
                db.session.commit()
                print(f"✅ {updated_count} statuts mis à jour")
            
            return {
                "success": True,
                "checked_count": len(device_ids_list),
                "updated_count": updated_count,
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erreur vérification batch: {e}")
            return {"success": False, "error": str(e)}