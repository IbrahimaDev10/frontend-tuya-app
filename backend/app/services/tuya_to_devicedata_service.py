# tuya_to_devicedata_service.py
# Service pour sauvegarder automatiquement les données Tuya dans votre modèle DeviceData

from app.models.device_data import DeviceData
from app.models.device import Device
from app.models.alert import Alert
from app import db
from datetime import datetime
import json

class TuyaToDeviceDataService:
    """Service pour convertir les données Tuya vers DeviceData"""
    
    def __init__(self, tuya_client):
        self.tuya_client = tuya_client
    
    def save_tuya_data_to_database(self, device_id, force_type=None):
        """
        Récupérer les données Tuya et les sauvegarder dans DeviceData
        
        Args:
            device_id (str): ID Tuya de l'appareil
            force_type (str): Forcer 'monophase' ou 'triphase' (optionnel)
            
        Returns:
            dict: Résultat de l'opération
        """
        try:
            print(f"🔄 Synchronisation {device_id}...")
            
            # 1. Récupérer l'appareil de la base
            device = Device.get_by_tuya_id(device_id)
            if not device:
                return {
                    "success": False,
                    "error": f"Appareil {device_id} non trouvé en base. Assignez-le d'abord."
                }
            
            print(f"📊 Appareil trouvé: {device.nom_appareil} ({device.type_systeme})")
            
            # 2. Récupérer les données depuis Tuya (avec votre nouveau service)
            tuya_response = self.tuya_client.get_device_current_values(device_id)
            if not tuya_response.get("success"):
                return {
                    "success": False,
                    "error": f"Erreur Tuya: {tuya_response.get('error', 'Inconnue')}"
                }
            
            tuya_values = tuya_response.get("values", {})
            is_triphase_detected = tuya_response.get("is_triphase", False)
            
            # 3. Déterminer le type final
            if force_type:
                final_type = force_type
                print(f"🔧 Type forcé: {final_type}")
            else:
                # Utiliser le type de la base ou la détection Tuya
                if device.type_systeme == 'triphase' or is_triphase_detected:
                    final_type = 'triphase'
                else:
                    final_type = 'monophase'
                print(f"🔍 Type déterminé: {final_type} (base: {device.type_systeme}, détecté: {is_triphase_detected})")
            
            # 4. Créer le DeviceData
            device_data = DeviceData(
                appareil_id=device.id,
                client_id=device.client_id,
                type_systeme=final_type,
                horodatage=datetime.utcnow(),
                donnees_brutes=tuya_response.get("raw_status", {})
            )
            
            # 5. Remplir selon le type
            if final_type == 'triphase':
                success = self._fill_triphase_data(device_data, tuya_values)
            else:
                success = self._fill_monophase_data(device_data, tuya_values)
            
            if not success:
                return {"success": False, "error": "Erreur remplissage des données"}
            
            # 6. Sauvegarder
            db.session.add(device_data)
            db.session.commit()
            
            # 7. Mettre à jour l'appareil
            device.update_last_data_time()
            device.update_online_status(True)
            
            # 8. Vérifier les seuils et créer des alertes
            alertes_creees = self._check_seuils_and_create_alerts(device, device_data)
            
            result = {
                "success": True,
                "device_id": device_id,
                "device_name": device.nom_appareil,
                "device_data_id": device_data.id,
                "type_systeme": device_data.type_systeme,
                "timestamp": device_data.horodatage.isoformat(),
                "tuya_values_count": len(tuya_values),
                "alertes_creees": len(alertes_creees),
                "data_summary": self._get_data_summary(device_data)
            }
            
            print(f"✅ Sauvegarde réussie: {device_data.id} ({device_data.type_systeme})")
            if alertes_creees:
                print(f"⚠️  {len(alertes_creees)} alerte(s) créée(s)")
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde {device_id}: {e}")
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    def _fill_triphase_data(self, device_data, tuya_values):
        """Remplir les données triphasées"""
        try:
            # ===== MAPPING a,b,c → L1,L2,L3 (fait par votre service) =====
            # Courants par phase (déjà mappés par votre service)
            device_data.courant_l1 = tuya_values.get("courant_l1")
            device_data.courant_l2 = tuya_values.get("courant_l2") 
            device_data.courant_l3 = tuya_values.get("courant_l3")
            
            # Tensions par phase (si disponibles)
            device_data.tension_l1 = tuya_values.get("tension_l1")
            device_data.tension_l2 = tuya_values.get("tension_l2")
            device_data.tension_l3 = tuya_values.get("tension_l3")
            
            # Si pas de tensions par phase, utiliser la tension globale
            tension_globale = tuya_values.get("tension")
            if not any([device_data.tension_l1, device_data.tension_l2, device_data.tension_l3]) and tension_globale:
                print(f"⚠️  Utilisation tension globale {tension_globale}V pour les 3 phases")
                device_data.tension_l1 = tension_globale
                device_data.tension_l2 = tension_globale
                device_data.tension_l3 = tension_globale
            
            # Puissances par phase
            device_data.puissance_l1 = tuya_values.get("puissance_l1")
            device_data.puissance_l2 = tuya_values.get("puissance_l2")
            device_data.puissance_l3 = tuya_values.get("puissance_l3")
            device_data.puissance_totale = tuya_values.get("puissance_totale")
            
            # Fréquence
            device_data.frequence = tuya_values.get("frequence", 50.0)
            
            # État switch
            device_data.etat_switch = tuya_values.get("etat_switch")
            
            # ===== CALCULS AUTOMATIQUES =====
            # Calculs de votre modèle DeviceData existant
            if not device_data.puissance_totale:
                device_data.puissance_totale = device_data._calculer_puissance_totale()
            
            # ===== CHAMPS DE COMPATIBILITÉ (pour les anciens endpoints) =====
            device_data.tension = tuya_values.get("tension_moyenne") or device_data.get_tension_moyenne()
            device_data.courant = tuya_values.get("courant_total") or device_data.get_courant_total()
            device_data.puissance = device_data.puissance_totale
            
            print(f"✅ Données triphasées remplies:")
            print(f"   Courants: L1={device_data.courant_l1}A, L2={device_data.courant_l2}A, L3={device_data.courant_l3}A")
            print(f"   Tensions: L1={device_data.tension_l1}V, L2={device_data.tension_l2}V, L3={device_data.tension_l3}V")
            print(f"   Puissance totale: {device_data.puissance_totale}W")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur remplissage triphasé: {e}")
            return False
    
    def _fill_monophase_data(self, device_data, tuya_values):
        """Remplir les données monophasées"""
        try:
            # Données classiques monophasées
            device_data.tension = tuya_values.get("tension")
            device_data.courant = tuya_values.get("courant")
            device_data.puissance = tuya_values.get("puissance")
            device_data.energie = tuya_values.get("energie")
            device_data.frequence = tuya_values.get("frequence", 50.0)
            device_data.etat_switch = tuya_values.get("etat_switch")
            device_data.temperature = tuya_values.get("temperature")
            
            print(f"✅ Données monophasées remplies:")
            print(f"   Tension: {device_data.tension}V, Courant: {device_data.courant}A")
            print(f"   Puissance: {device_data.puissance}W, Énergie: {device_data.energie}kWh")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur remplissage monophasé: {e}")
            return False
    
    def _check_seuils_and_create_alerts(self, device, device_data):
        """Vérifier les seuils et créer des alertes si nécessaire"""
        alertes_creees = []
        
        try:
            # Récupérer les seuils de l'appareil
            seuils = device.get_seuils_actifs()
            
            # Utiliser la méthode existante de votre modèle DeviceData
            anomalies = device_data.detecter_anomalies(seuils)
            
            for anomalie in anomalies:
                # Créer une alerte selon le type de système
                if device_data.is_triphase():
                    alerte = Alert.create_alerte_triphase(
                        client_id=device.client_id,
                        appareil_id=device.id,
                        type_alerte=self._map_anomalie_to_alert_type(anomalie['type']),
                        gravite=self._map_gravite(anomalie['gravite']),
                        titre=f"Seuil dépassé - {device.nom_appareil}",
                        message=anomalie['message'],
                        phase_concernee=anomalie.get('phase'),
                        valeur_principale=anomalie['valeur'],
                        seuil_principal=anomalie['seuil'],
                        unite=anomalie['unite']
                    )
                else:
                    alerte = Alert.create_alerte_monophase(
                        client_id=device.client_id,
                        appareil_id=device.id,
                        type_alerte=self._map_anomalie_to_alert_type(anomalie['type']),
                        gravite=self._map_gravite(anomalie['gravite']),
                        titre=f"Seuil dépassé - {device.nom_appareil}",
                        message=anomalie['message'],
                        valeur=anomalie['valeur'],
                        seuil=anomalie['seuil'],
                        unite=anomalie['unite']
                    )
                
                if alerte:
                    alertes_creees.append(alerte)
            
        except Exception as e:
            print(f"⚠️  Erreur vérification seuils: {e}")
        
        return alertes_creees
    
    def _map_anomalie_to_alert_type(self, anomalie_type):
        """Mapper le type d'anomalie vers le type d'alerte"""
        mapping = {
            'seuil_depasse': 'seuil_depasse',
            'desequilibre': 'desequilibre_tension',
            'facteur_puissance': 'facteur_puissance_faible'
        }
        return mapping.get(anomalie_type, 'seuil_depasse')
    
    def _map_gravite(self, gravite):
        """Mapper la gravité d'anomalie vers la gravité d'alerte"""
        mapping = {
            'critique': 'critique',
            'warning': 'warning', 
            'info': 'info'
        }
        return mapping.get(gravite, 'info')
    
    def _get_data_summary(self, device_data):
        """Résumé des données pour le retour"""
        if device_data.is_triphase():
            return {
                "type": "triphase",
                "courants": {
                    "L1": device_data.courant_l1,
                    "L2": device_data.courant_l2,
                    "L3": device_data.courant_l3,
                    "total": device_data.get_courant_total()
                },
                "tensions": {
                    "L1": device_data.tension_l1,
                    "L2": device_data.tension_l2,
                    "L3": device_data.tension_l3,
                    "moyenne": device_data.get_tension_moyenne()
                },
                "puissance_totale": device_data.puissance_totale,
                "desequilibres": {
                    "courant": device_data.calculer_desequilibre_courant(),
                    "tension": device_data.calculer_desequilibre_tension()
                }
            }
        else:
            return {
                "type": "monophase",
                "tension": device_data.tension,
                "courant": device_data.courant,
                "puissance": device_data.puissance,
                "energie": device_data.energie
            }
    
    def sync_all_assigned_devices(self):
        """Synchroniser tous les appareils assignés"""
        try:
            print("🔄 Synchronisation globale des appareils assignés...")
            
            # Récupérer tous les appareils assignés et actifs
            devices = Device.query.filter_by(
                statut_assignation='assigne',
                actif=True
            ).all()
            
            results = []
            success_count = 0
            
            for device in devices:
                print(f"\n📊 Sync {device.nom_appareil} ({device.tuya_device_id})...")
                
                result = self.save_tuya_data_to_database(device.tuya_device_id)
                result["device_name"] = device.nom_appareil
                result["device_type"] = device.type_systeme
                
                results.append(result)
                
                if result.get("success"):
                    success_count += 1
                
                # Petite pause pour éviter de surcharger l'API Tuya
                import time
                time.sleep(0.5)
            
            print(f"\n✅ Synchronisation terminée: {success_count}/{len(results)} réussies")
            
            return {
                "success": True,
                "total_devices": len(results),
                "successful_syncs": success_count,
                "failed_syncs": len(results) - success_count,
                "results": results,
                "summary": {
                    "devices_synced": success_count,
                    "devices_failed": len(results) - success_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            print(f"❌ Erreur sync globale: {e}")
            return {"success": False, "error": str(e)}
    
    def sync_device_by_name(self, device_name):
        """Synchroniser un appareil par son nom"""
        try:
            device = Device.query.filter_by(nom_appareil=device_name).first()
            if not device:
                return {"success": False, "error": f"Appareil '{device_name}' non trouvé"}
            
            return self.save_tuya_data_to_database(device.tuya_device_id)
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# ===== FONCTIONS UTILITAIRES =====

def create_tuya_sync_service(tuya_client):
    """Factory pour créer le service de sync"""
    return TuyaToDeviceDataService(tuya_client)

def sync_single_device(tuya_device_id):
    """Synchroniser un seul appareil"""
    from tuya_service import TuyaClient
    
    # Connexion Tuya
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        return {"success": False, "error": "Connexion Tuya impossible"}
    
    # Service de sync
    sync_service = TuyaToDeviceDataService(tuya_client)
    
    # Synchronisation
    return sync_service.save_tuya_data_to_database(tuya_device_id)

def sync_all_devices():
    """Synchroniser tous les appareils"""
    from tuya_service import TuyaClient
    
    # Connexion Tuya
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        return {"success": False, "error": "Connexion Tuya impossible"}
    
    # Service de sync
    sync_service = TuyaToDeviceDataService(tuya_client)
    
    # Synchronisation globale
    return sync_service.sync_all_assigned_devices()


# ===== EXEMPLE D'UTILISATION =====

def test_sync_service():
    """Test du service de synchronisation"""
    from tuya_service import TuyaClient
    import json
    
    print("🧪 Test du service de synchronisation...")
    
    # 1. Créer le service
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        print("❌ Connexion Tuya impossible")
        return
    
    sync_service = TuyaToDeviceDataService(tuya_client)
    
    # 2. Lister les appareils assignés
    devices = Device.query.filter_by(statut_assignation='assigne').all()
    print(f"📊 {len(devices)} appareils assignés trouvés:")
    
    for device in devices:
        print(f"  - {device.nom_appareil} ({device.type_systeme}) - Tuya ID: {device.tuya_device_id}")
    
    # 3. Test sur le premier appareil
    if devices:
        test_device = devices[0]
        print(f"\n🔍 Test sur {test_device.nom_appareil}...")
        
        result = sync_service.save_tuya_data_to_database(test_device.tuya_device_id)
        print(f"📊 Résultat:")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    test_sync_service()