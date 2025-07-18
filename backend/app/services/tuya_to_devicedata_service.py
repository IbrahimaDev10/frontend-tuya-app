# tuya_to_devicedata_service.py - VERSION ADAPTÉE AU TUYA_SERVICE INTELLIGENT
# ✅ Parfaitement compatible avec votre TuyaClient intelligent

from app.models.device_data import DeviceData
from app.models.device import Device
from app.models.alert import Alert
from app import db
from datetime import datetime
import json
import base64
import struct

class TuyaToDeviceDataService:
    """Service pour convertir les données Tuya vers DeviceData - Compatible TuyaClient Intelligent"""
    
    def __init__(self, tuya_client):
        self.tuya_client = tuya_client
        print("🔗 Service de sync initialisé avec TuyaClient Intelligent")
    
    def save_tuya_data_to_database(self, device_id, force_type=None):
        """
        Récupérer les données Tuya et les sauvegarder dans DeviceData
        ✅ ADAPTÉ pour votre TuyaClient intelligent
        """
        try:
            print(f"🔄 Synchronisation {device_id}...")

            # ✅ Vérification du token Tuya
            if not self.tuya_client.ensure_token():
                return {
                    "success": False,
                    "error": "Client Tuya non connecté - token invalide"
                }

            # 1. Récupérer l'appareil
            device = Device.get_by_tuya_id(device_id)
            if not device:
                return {
                    "success": False,
                    "error": f"Appareil {device_id} non trouvé en base. Assignez-le d'abord."
                }

            print(f"📊 Appareil trouvé: {device.nom_appareil} ({device.type_systeme})")

            # 2. Récupérer les données Tuya
            tuya_response = self.tuya_client.get_device_current_values(device_id)
            if not tuya_response.get("success"):
                error_msg = tuya_response.get('error', 'Erreur inconnue')
                print(f"❌ Erreur Tuya: {error_msg}")
                return {"success": False, "error": f"Erreur Tuya: {error_msg}"}

            tuya_values = tuya_response.get("values", {})
            is_online = tuya_response.get("is_online", False)

            # ✅ Réactivation automatique si appareil désactivé mais online
            if not device.actif and is_online:
                print(f"🔄 Réactivation de l'appareil {device.nom_appareil} car il est détecté en ligne")
                device.actif = True
                db.session.commit()

            # 3. Détection automatique du triphasé
            is_triphase_detected = self._detect_triphase_from_values(tuya_values)
            print(f"🌐 Statut en ligne: {is_online}")
            print(f"⚡ Triphasé détecté: {is_triphase_detected}")

            # 4. Déterminer le type final
            if force_type:
                final_type = force_type
                print(f"🔧 Type forcé: {final_type}")
            else:
                final_type = 'triphase' if is_triphase_detected else 'monophase'
                print(f"🔍 Type déterminé: {final_type} (base: {device.type_systeme}, détecté: {is_triphase_detected})")

            # ✅ Mettre à jour le type_systeme si besoin
            if device.type_systeme != final_type:
                print(f"🛠️ Mise à jour type_systeme: {device.type_systeme} ➜ {final_type}")
                device.type_systeme = final_type
                db.session.commit()

            # 5. Créer une nouvelle entrée DeviceData
            device_data = DeviceData(
                appareil_id=device.id,
                client_id=device.client_id,
                type_systeme=final_type,
                horodatage=datetime.utcnow(),
                donnees_brutes=tuya_response.get("raw_status", {}),
                tuya_timestamp=tuya_response.get("timestamp"),
                intelligent_mapping=tuya_response.get("intelligent_mapping", True)
            )

            # 6. Remplir les données
            success = (
                self._fill_triphase_data(device_data, tuya_values)
                if final_type == 'triphase'
                else self._fill_monophase_data(device_data, tuya_values)
            )
            if not success:
                return {"success": False, "error": "Erreur remplissage des données"}

            # 7. Sauvegarder les données
            db.session.add(device_data)
            db.session.commit()

            # 8. Mettre à jour l'appareil
            device.update_last_data_time()
            device.update_online_status(is_online)

            # 9. Créer des alertes si besoin
            alertes_creees = self._check_seuils_and_create_alerts(device, device_data)

            # 10. Résultat
            result = {
                "success": True,
                "device_id": device_id,
                "device_name": device.nom_appareil,
                "device_data_id": device_data.id,
                "type_systeme": device_data.type_systeme,
                "timestamp": device_data.horodatage.isoformat(),
                "tuya_values_count": len(tuya_values),
                "alertes_creees": len(alertes_creees),
                "is_online": is_online,
                "intelligent_features": True,
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


    
    
    

    def _detect_triphase_from_values(self, tuya_values):
        """
        ✅ Détection intelligente : vérifie que phase_a, b, c sont présents
        ✅ Décode les valeurs base64 pour détecter si les courants sont non nuls
        """
        try:
            def decode_base64_float(val):
                try:
                    if not val:
                        return 0.0
                    decoded = base64.b64decode(val)
                    # Tuya encode souvent les float sous format IEEE 754 (float32, 4 bytes)
                    if len(decoded) == 4:
                        return struct.unpack('<f', decoded)[0]
                    return 0.0
                except Exception:
                    return 0.0

            courant_a = decode_base64_float(tuya_values.get("phase_a"))
            courant_b = decode_base64_float(tuya_values.get("phase_b"))
            courant_c = decode_base64_float(tuya_values.get("phase_c"))

            print(f"🔎 Courants décodés: A={courant_a} A, B={courant_b} A, C={courant_c} A")
            print(f"🔎 [DEBUG] BASE64: A={tuya_values.get('phase_a')} B={tuya_values.get('phase_b')} C={tuya_values.get('phase_c')}")
            print(f"🔎 Courants décodés: A={courant_a} A, B={courant_b} A, C={courant_c} A")

            if courant_a > 0 or courant_b > 0 or courant_c > 0:
                print("⚡ Triphasé détecté via décodage des courants phase_a/b/c")
                return True
            else:
                print("ℹ️ Aucune intensité significative détectée sur les 3 phases")
                return False

        except Exception as e:
            print(f"⚠️ Erreur dans la détection triphasé: {e}")
            return False


    
    def _fill_triphase_data(self, device_data, tuya_values):
        """✅ ADAPTÉ: Remplir les données triphasées avec le mapping intelligent"""
        try:
            print("⚡ Remplissage données triphasées avec mapping intelligent...")
            
            # ===== COURANTS PAR PHASE =====
            # Votre TuyaClient fait déjà le mapping intelligent des codes Tuya
            device_data.courant_l1 = tuya_values.get("courant_l1") or tuya_values.get("phase_a")
            device_data.courant_l2 = tuya_values.get("courant_l2") or tuya_values.get("phase_b") 
            device_data.courant_l3 = tuya_values.get("courant_l3") or tuya_values.get("phase_c")
            
            # ===== TENSIONS PAR PHASE =====
            device_data.tension_l1 = tuya_values.get("tension_l1")
            device_data.tension_l2 = tuya_values.get("tension_l2")
            device_data.tension_l3 = tuya_values.get("tension_l3")
            
            # Si pas de tensions par phase, utiliser la tension globale
            tension_globale = tuya_values.get("tension")
            if not any([device_data.tension_l1, device_data.tension_l2, device_data.tension_l3]) and tension_globale:
                print(f"⚠️ Utilisation tension globale {tension_globale}V pour les 3 phases")
                device_data.tension_l1 = tension_globale
                device_data.tension_l2 = tension_globale
                device_data.tension_l3 = tension_globale
            
            # ===== PUISSANCES PAR PHASE =====
            device_data.puissance_l1 = tuya_values.get("puissance_l1")
            device_data.puissance_l2 = tuya_values.get("puissance_l2")
            device_data.puissance_l3 = tuya_values.get("puissance_l3")
            
            # Puissance totale (déjà mappée par votre service intelligent)
            device_data.puissance_totale = (
                tuya_values.get("puissance_totale") or 
                tuya_values.get("energie_totale") or 
                tuya_values.get("puissance")  # Fallback sur puissance globale
            )
            
            # ===== AUTRES DONNÉES =====
            device_data.frequence = tuya_values.get("frequence", 50.0)
            device_data.etat_switch = tuya_values.get("etat_switch")
            
            # ✅ NOUVEAU: Support des données spécifiques triphasées
            device_data.courant_fuite = tuya_values.get("courant_fuite")
            device_data.defaut = tuya_values.get("defaut")
            
            # ===== CALCULS AUTOMATIQUES =====
            # Si pas de puissance totale, calculer
            if not device_data.puissance_totale:
                device_data.puissance_totale = device_data._calculer_puissance_totale()
            
            # ===== CHAMPS DE COMPATIBILITÉ =====
            # Pour les anciens endpoints qui attendent ces champs
            device_data.tension = device_data.get_tension_moyenne() if hasattr(device_data, 'get_tension_moyenne') else tension_globale
            device_data.courant = device_data.get_courant_total() if hasattr(device_data, 'get_courant_total') else tuya_values.get("courant")
            device_data.puissance = device_data.puissance_totale
            
            print(f"✅ Données triphasées remplies:")
            print(f"   Courants: L1={device_data.courant_l1}A, L2={device_data.courant_l2}A, L3={device_data.courant_l3}A")
            print(f"   Tensions: L1={device_data.tension_l1}V, L2={device_data.tension_l2}V, L3={device_data.tension_l3}V")
            print(f"   Puissance totale: {device_data.puissance_totale}W")
            print(f"   Fréquence: {device_data.frequence}Hz")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur remplissage triphasé: {e}")
            return False
    
    def _fill_monophase_data(self, device_data, tuya_values):
        """✅ ADAPTÉ: Remplir les données monophasées avec le mapping intelligent"""
        try:
            print("🔌 Remplissage données monophasées avec mapping intelligent...")
            
            # Données directement mappées par votre TuyaClient intelligent
            device_data.tension = tuya_values.get("tension")
            device_data.courant = tuya_values.get("courant") 
            device_data.puissance = tuya_values.get("puissance")
            device_data.energie = tuya_values.get("energie")
            device_data.frequence = tuya_values.get("frequence", 50.0)
            device_data.etat_switch = tuya_values.get("etat_switch")
            device_data.temperature = tuya_values.get("temperature")
            
            # ✅ NOUVEAU: Support données étendues si disponibles
            device_data.humidite = tuya_values.get("humidite")
            device_data.minuterie = tuya_values.get("minuterie")
            device_data.mode_eclairage = tuya_values.get("mode_eclairage")
            
            # Support thermostats
            device_data.temperature_consigne = tuya_values.get("temperature_consigne")
            device_data.mode = tuya_values.get("mode")
            device_data.mode_eco = tuya_values.get("mode_eco")
            device_data.verrouillage_enfant = tuya_values.get("verrouillage_enfant")
            
            print(f"✅ Données monophasées remplies:")
            print(f"   Tension: {device_data.tension}V, Courant: {device_data.courant}A")
            print(f"   Puissance: {device_data.puissance}W, Énergie: {device_data.energie}kWh")
            print(f"   Switch: {device_data.etat_switch}, Température: {device_data.temperature}°C")
            
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
            print(f"⚠️ Erreur vérification seuils: {e}")
        
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
        """✅ ADAPTÉ: Résumé des données pour le retour"""
        try:
            if device_data.is_triphase():
                return {
                    "type": "triphase",
                    "courants": {
                        "L1": device_data.courant_l1,
                        "L2": device_data.courant_l2,
                        "L3": device_data.courant_l3,
                        "total": device_data.get_courant_total() if hasattr(device_data, 'get_courant_total') else None
                    },
                    "tensions": {
                        "L1": device_data.tension_l1,
                        "L2": device_data.tension_l2,
                        "L3": device_data.tension_l3,
                        "moyenne": device_data.get_tension_moyenne() if hasattr(device_data, 'get_tension_moyenne') else None
                    },
                    "puissance_totale": device_data.puissance_totale,
                    "frequence": device_data.frequence,
                    "desequilibres": {
                        "courant": device_data.calculer_desequilibre_courant() if hasattr(device_data, 'calculer_desequilibre_courant') else None,
                        "tension": device_data.calculer_desequilibre_tension() if hasattr(device_data, 'calculer_desequilibre_tension') else None
                    }
                }
            else:
                return {
                    "type": "monophase",
                    "tension": device_data.tension,
                    "courant": device_data.courant,
                    "puissance": device_data.puissance,
                    "energie": device_data.energie,
                    "temperature": device_data.temperature,
                    "etat_switch": device_data.etat_switch
                }
        except Exception as e:
            return {"error": str(e)}
    
    def sync_all_assigned_devices(self):
        """✅ ADAPTÉ: Synchroniser tous les appareils assignés avec gestion intelligente"""
        try:
            print("🔄 Synchronisation globale des appareils assignés...")
            
            # ✅ VÉRIFICATION: S'assurer que le client Tuya est connecté
            if not self.tuya_client.ensure_token():
                return {"success": False, "error": "Client Tuya non connecté"}
            
            # Récupérer tous les appareils assignés et actifs
            devices = Device.query.filter_by(
                statut_assignation='assigne',
                actif=True
            ).all()
            
            print(f"📊 {len(devices)} appareils assignés trouvés")
            
            results = []
            success_count = 0
            
            for i, device in enumerate(devices, 1):
                print(f"\n📊 [{i}/{len(devices)}] Sync {device.nom_appareil} ({device.tuya_device_id})...")
                
                result = self.save_tuya_data_to_database(device.tuya_device_id)
                result["device_name"] = device.nom_appareil
                result["device_type"] = device.type_systeme
                result["sync_order"] = i
                
                results.append(result)
                
                if result.get("success"):
                    success_count += 1
                    print(f"   ✅ Succès")
                else:
                    print(f"   ❌ Erreur: {result.get('error', 'Inconnue')}")
                
                # ✅ ADAPTATION: Pause intelligente pour votre TuyaClient
                # Votre TuyaClient a déjà une gestion des pauses, mais on ajoute une pause ici pour la sécurité
                import time
                if i % 5 == 0:  # Pause plus longue tous les 5 appareils
                    print(f"   ⏸️ Pause intelligente (5 appareils traités)...")
                    time.sleep(1.0)
                else:
                    time.sleep(0.3)  # Pause courte entre chaque appareil
            
            print(f"\n✅ Synchronisation terminée: {success_count}/{len(results)} réussies")
            
            return {
                "success": True,
                "total_devices": len(results),
                "successful_syncs": success_count,
                "failed_syncs": len(results) - success_count,
                "success_rate": round((success_count / len(results)) * 100, 1) if results else 0,
                "results": results,
                "intelligent_sync": True,  # ✅ Indicateur de sync intelligente
                "summary": {
                    "devices_synced": success_count,
                    "devices_failed": len(results) - success_count,
                    "timestamp": datetime.utcnow().isoformat(),
                    "tuya_client_features": "intelligent"
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
    
    # ✅ NOUVELLES MÉTHODES ADAPTÉES AU TUYA_SERVICE INTELLIGENT
    
    def sync_with_health_check(self):
        """Synchronisation avec vérification santé du TuyaClient"""
        try:
            print("🏥 Vérification santé du TuyaClient...")
            
            # Utiliser la méthode health_check de votre TuyaClient intelligent
            health = self.tuya_client.health_check()
            
            if not health.get("success") or health.get("health", {}).get("overall_status") != "healthy":
                return {
                    "success": False,
                    "error": "TuyaClient en mauvaise santé",
                    "health_report": health
                }
            
            print("✅ TuyaClient en bonne santé, démarrage sync...")
            return self.sync_all_assigned_devices()
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_sync_recommendations(self):
        """Obtenir des recommandations pour la synchronisation"""
        try:
            # Utiliser les stats de pagination de votre TuyaClient
            pagination_stats = self.tuya_client.get_pagination_stats()
            
            # Comptage rapide
            quick_count = self.tuya_client.quick_device_count()
            
            recommendations = []
            
            if quick_count.get("success"):
                device_count = quick_count.get("first_page_count", 0)
                
                if device_count > 20:
                    recommendations.append("Utilisez la synchronisation par lots pour éviter la surcharge")
                
                if device_count > 50:
                    recommendations.append("Activez le mode performance dans la pagination")
                
                recommendations.append(f"Configuration optimale détectée pour {device_count} appareils")
            
            return {
                "success": True,
                "recommendations": recommendations,
                "pagination_config": pagination_stats,
                "device_count_estimate": quick_count
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# ===== FONCTIONS UTILITAIRES ADAPTÉES =====

def create_tuya_sync_service(tuya_client):
    """✅ ADAPTÉ: Factory pour créer le service de sync avec TuyaClient intelligent"""
    if not hasattr(tuya_client, 'get_device_current_values'):
        raise ValueError("Le TuyaClient fourni n'est pas compatible (méthode get_device_current_values manquante)")
    
    return TuyaToDeviceDataService(tuya_client)

def sync_single_device(tuya_device_id):
    """✅ ADAPTÉ: Synchroniser un seul appareil avec TuyaClient intelligent"""
    from tuya_service import TuyaClient
    
    # Connexion Tuya avec le client intelligent
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        return {"success": False, "error": "Connexion TuyaClient intelligent impossible"}
    
    # Service de sync adapté
    sync_service = TuyaToDeviceDataService(tuya_client)
    
    # Synchronisation
    return sync_service.save_tuya_data_to_database(tuya_device_id)

def sync_all_devices():
    """✅ ADAPTÉ: Synchroniser tous les appareils avec TuyaClient intelligent"""
    from tuya_service import TuyaClient
    
    # Connexion Tuya avec le client intelligent
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        return {"success": False, "error": "Connexion TuyaClient intelligent impossible"}
    
    # Service de sync adapté
    sync_service = TuyaToDeviceDataService(tuya_client)
    
    # Synchronisation globale intelligente
    return sync_service.sync_all_assigned_devices()

def sync_all_devices_with_health_check():
    """✅ NOUVEAU: Synchronisation avec vérification santé"""
    from tuya_service import TuyaClient
    
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        return {"success": False, "error": "Connexion TuyaClient intelligent impossible"}
    
    sync_service = TuyaToDeviceDataService(tuya_client)
    return sync_service.sync_with_health_check()


# ===== EXEMPLE D'UTILISATION ADAPTÉ =====

def test_sync_service_intelligent():
    """✅ ADAPTÉ: Test du service de synchronisation avec TuyaClient intelligent"""
    from tuya_service import TuyaClient
    import json
    
    print("🧪 Test du service de synchronisation avec TuyaClient Intelligent...")
    
    # 1. Créer le service avec TuyaClient intelligent
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        print("❌ Connexion TuyaClient intelligent impossible")
        return
    
    # Vérification santé
    health = tuya_client.health_check()
    print(f"🏥 Santé TuyaClient: {health.get('health', {}).get('overall_status', 'inconnue')}")
    
    sync_service = TuyaToDeviceDataService(tuya_client)
    
    # 2. Obtenir des recommandations
    recommendations = sync_service.get_sync_recommendations()
    if recommendations.get("success"):
        print(f"💡 Recommandations:")
        for rec in recommendations.get("recommendations", []):
            print(f"  - {rec}")
    
    # 3. Lister les appareils assignés
    devices = Device.query.filter_by(statut_assignation='assigne').all()
    print(f"📊 {len(devices)} appareils assignés trouvés:")
    
    for device in devices:
        print(f"  - {device.nom_appareil} ({device.type_systeme}) - Tuya ID: {device.tuya_device_id}")
    
    # 4. Test sur le premier appareil
    if devices:
        test_device = devices[0]
        print(f"\n🔍 Test intelligent sur {test_device.nom_appareil}...")
        
        result = sync_service.save_tuya_data_to_database(test_device.tuya_device_id)
        print(f"📊 Résultat de la synchronisation intelligente:")
        print(json.dumps(result, indent=2, default=str))
        
        if result.get("success"):
            print(f"\n✅ Synchronisation réussie!")
            print(f"   📊 Type détecté: {result.get('type_systeme')}")
            print(f"   🌐 En ligne: {result.get('is_online')}")
            print(f"   📈 Valeurs: {result.get('tuya_values_count')}")
            print(f"   ⚠️  Alertes: {result.get('alertes_creees')}")
            
            # Afficher le résumé des données
            summary = result.get("data_summary", {})
            if summary.get("type") == "triphase":
                print(f"   ⚡ Triphasé:")
                courants = summary.get("courants", {})
                print(f"     Courants: L1={courants.get('L1')}A, L2={courants.get('L2')}A, L3={courants.get('L3')}A")
                tensions = summary.get("tensions", {})
                print(f"     Tensions: L1={tensions.get('L1')}V, L2={tensions.get('L2')}V, L3={tensions.get('L3')}V")
                print(f"     Puissance totale: {summary.get('puissance_totale')}W")
            else:
                print(f"   🔌 Monophasé:")
                print(f"     Tension: {summary.get('tension')}V, Courant: {summary.get('courant')}A")
                print(f"     Puissance: {summary.get('puissance')}W, Énergie: {summary.get('energie')}kWh")
    
    # 5. Test de synchronisation globale (optionnel)
    print(f"\n🔄 Test synchronisation globale intelligente...")
    global_result = sync_service.sync_with_health_check()
    
    if global_result.get("success"):
        print(f"✅ Synchronisation globale réussie!")
        print(f"   📊 Total: {global_result.get('total_devices')} appareils")
        print(f"   ✅ Succès: {global_result.get('successful_syncs')}")
        print(f"   ❌ Échecs: {global_result.get('failed_syncs')}")
        print(f"   📈 Taux de réussite: {global_result.get('success_rate')}%")
    else:
        print(f"❌ Erreur synchronisation globale: {global_result.get('error')}")


if __name__ == "__main__":
    test_sync_service_intelligent()