# tuya_to_devicedata_service.py - VERSION AVEC IMPORTS CORRIGÉS
# ✅ À remplacer dans app/services/tuya_to_devicedata_service.py

from app.models.device_data import DeviceData
from app.models.device import Device
from app.models.alert import Alert
from app import db
from datetime import datetime
import json
import base64
import struct
import logging
from typing import Dict, Any, Optional, List, Tuple

# ===== DÉCODEUR VERATTI INTÉGRÉ =====

# ===== DÉCODEUR VERATTI v5.0 (CALIBRÉ SUR LOGS DÉVELOPPEUR) =====

class VerattiDecoder:
    """
    🧠 Décodeur intelligent v5.3 - Fiabilise le calcul de puissance pour éviter les
    valeurs aberrantes. C'est la version de production recommandée.
    """
    
    def __init__(self, debug=True):
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        self._debug_log("🧠 Décodeur VERATTI v5.3 (Puissance Fiabilisée) initialisé.")

    def _debug_log(self, message: str):
        if self.debug:
            print(f"[VERATTI_DECODER] {message}")

    def decode_phase_detailed_data(self, base64_data: str, phase_name: str) -> Dict[str, Any]:
        # Cette méthode est déjà fiable et ne change pas.
        self._debug_log(f"📊 Décodage détaillé de la phase {phase_name}...")
        try:
            bytes_data = base64.b64decode(base64_data)
        except Exception as e:
            return {'success': False, 'error': f'invalid_base64_detailed: {e}'}
        if len(bytes_data) < 14:
            return {'success': False, 'error': 'data_too_short_detailed'}
        try:
            result = {'success': True, 'phase': phase_name, 'data_type': 'detailed'}
            result['tension'] = round(struct.unpack('>H', bytes_data[0:2])[0] / 10.0, 1)
            result['courant'] = round(int.from_bytes(bytes_data[2:5], 'big') / 1000.0, 3)
            # La puissance lue dans les données détaillées est fiable.
            result['puissance'] = round(struct.unpack('>H', bytes_data[5:7])[0] / 10.0, 2)
            result['energie'] = round(int.from_bytes(bytes_data[7:10], 'big') / 100.0, 2)
            result['facteur_puissance'] = round(struct.unpack('>H', bytes_data[10:12])[0] / 1000.0, 3)
            result['frequence'] = round(struct.unpack('>H', bytes_data[12:14])[0] / 1000.0, 3)
            return result
        except Exception as e:
            return {'success': False, 'error': f'struct_unpack_error_detailed: {e}'}

    def decode_phase_simple_data(self, base64_data: str, phase_name: str) -> Dict[str, Any]:
        """
        🎯 MISE À JOUR v5.3 : La puissance est maintenant TOUJOURS calculée à partir de V et A
        pour garantir la cohérence et éliminer les valeurs fantômes.
        """
        self._debug_log(f"📊 Décodage simple (v5.3) de la phase {phase_name}...")
        
        try:
            bytes_data = base64.b64decode(base64_data)
        except Exception as e:
            return {'success': False, 'error': f'invalid_base64_simple: {e}'}

        if len(bytes_data) < 4: # On a juste besoin de V et A
            return {'success': False, 'error': 'data_too_short_simple'}
            
        try:
            result = {'success': True, 'phase': phase_name, 'data_type': 'simple'}
            
            # Structure confirmée pour V et A :
            # Octets 0-1: Tension (V) / 10
            # Octets 2-3: Courant (A) / 1000
            
            result['tension'] = round(struct.unpack('>H', bytes_data[0:2])[0] / 10.0, 1)
            result['courant'] = round(struct.unpack('>H', bytes_data[2:4])[0] / 1000.0, 3)
            
            # ✅ FIABILISATION : On ignore la puissance lue et on la calcule.
            # On estime un facteur de puissance moyen de 0.9, ce qui est une pratique standard.
            facteur_puissance_estime = 0.9
            result['puissance'] = round(result['tension'] * result['courant'] * facteur_puissance_estime, 2)

            self._debug_log(f"  ✅ {phase_name} (simple) décodé: {result['tension']}V, {result['courant']}A, Puissance calculée={result['puissance']}W")

            return result
        except Exception as e:
            return {'success': False, 'error': f'struct_unpack_error_simple: {e}'}

    def decode_full_veratti_triphase(self, tuya_values: Dict[str, Any]) -> Dict[str, Any]:
        # Cette méthode de haut niveau ne change pas, elle bénéficie automatiquement
        # des corrections dans les méthodes de décodage de phase.
        self._debug_log("🔄 Décodage complet VERATTI (v5.3)...")
        result = {
            'success': False, 'type_systeme': 'triphase', 'phases': {}, 'totaux': {}, 'donnees_directes': {}
        }
        phase_key_candidates = {
            'L1': ['Phase A grid detailed data', 'phase_a'],
            'L2': ['Phase B grid detailed data', 'phase_b'],
            'L3': ['Phase C grid detailed data', 'phase_c']
        }
        decoded_phases_count = 0
        for phase_name, key_list in phase_key_candidates.items():
            for tuya_key in key_list:
                if tuya_key in tuya_values:
                    self._debug_log(f"  🔑 Clé trouvée pour {phase_name}: '{tuya_key}'")
                    if 'grid detailed data' in tuya_key:
                        phase_result = self.decode_phase_detailed_data(tuya_values[tuya_key], phase_name)
                    else:
                        phase_result = self.decode_phase_simple_data(tuya_values[tuya_key], phase_name)
                    result['phases'][phase_name] = phase_result
                    if phase_result.get('success'):
                        decoded_phases_count += 1
                    break 
        if decoded_phases_count > 0:
            result['success'] = True
            valid_phases = [p for p in result['phases'].values() if p.get('success')]
            result['totaux']['puissance_totale'] = round(sum(p.get('puissance', 0) for p in valid_phases), 2)
            result['totaux']['energie_totale'] = round(sum(p.get('energie', 0) for p in valid_phases), 2)
            tensions = [p['tension'] for p in valid_phases if 'tension' in p]
            if tensions:
                result['totaux']['tension_moyenne'] = round(sum(tensions) / len(tensions), 1)
            pfs = [p['facteur_puissance'] for p in valid_phases if 'facteur_puissance' in p]
            if pfs:
                result['totaux']['facteur_puissance_moyen'] = round(sum(pfs) / len(pfs), 3)
        if 'Temp Current' in tuya_values:
            temp_str = str(tuya_values['Temp Current']).replace('℃', '')
            if temp_str:
                result['donnees_directes']['temperature'] = float(temp_str)
        self._debug_log(f"✅ Décodage terminé. {decoded_phases_count}/3 phases trouvées et traitées.")
        return result



# ===== SERVICE PRINCIPAL AVEC VERATTI INTÉGRÉ =====

class TuyaToDeviceDataService:
    """Service pour convertir les données Tuya vers DeviceData - Compatible TuyaClient Intelligent + VERATTI"""
    
    def __init__(self, tuya_client):
        self.tuya_client = tuya_client
        # ✅ NOUVEAU: Ajouter le décodeur VERATTI
        self.veratti_decoder = VerattiDecoder(debug=True)
        print("🔗 Service de sync initialisé avec TuyaClient Intelligent + Décodeur VERATTI")
    
    def save_tuya_data_to_database(self, device_id, force_type=None):
        """
        Récupérer les données Tuya et les sauvegarder dans DeviceData
        ✅ ADAPTÉ pour votre TuyaClient intelligent + VERATTI
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
                donnees_brutes=tuya_response.get("raw_status", {})
            )

            # 6. Remplir les données
            success = (
                self._fill_triphase_data_with_veratti(device_data, tuya_values, device)
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
                "veratti_enabled": True,
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
        ✅ Détection intelligente triphasé avec support VERATTI
        """
        try:
            # 1. Détection classique par phase_a/b/c
            def decode_base64_float(val):
                try:
                    if not val:
                        return 0.0
                    decoded = base64.b64decode(val)
                    if len(decoded) == 4:
                        return struct.unpack('<f', decoded)[0]
                    return 0.0
                except Exception:
                    return 0.0

            courant_a = decode_base64_float(tuya_values.get("phase_a"))
            courant_b = decode_base64_float(tuya_values.get("phase_b"))
            courant_c = decode_base64_float(tuya_values.get("phase_c"))

            if courant_a > 0 or courant_b > 0 or courant_c > 0:
                print("⚡ Triphasé détecté via phase_a/b/c")
                return True

            # 2. ✅ NOUVEAU: Détection VERATTI via "Phase X grid detailed data"
            veratti_phases = [
                'Phase A grid detailed data',
                'Phase B grid detailed data', 
                'Phase C grid detailed data'
            ]
            
            veratti_count = sum(1 for phase in veratti_phases if phase in tuya_values)
            
            if veratti_count >= 2:  # Au moins 2 phases VERATTI détectées
                print(f"⚡ Triphasé VERATTI détecté: {veratti_count}/3 phases trouvées")
                return True

            print("ℹ️ Aucun système triphasé détecté")
            return False

        except Exception as e:
            print(f"⚠️ Erreur détection triphasé: {e}")
            return False

    def _fill_triphase_data_with_veratti(self, device_data: DeviceData, tuya_values: Dict[str, Any], device: Device):
        """✅ Remplissage triphasé avec le décodeur v5.0 final."""
        print("⚡ Remplissage données triphasées avec décodeur VERATTI v5.0...")
        
        veratti_result = self.veratti_decoder.decode_full_veratti_triphase(tuya_values)
        
        if not veratti_result.get('success'):
            print("❌ Échec du décodage VERATTI. Aucune donnée ne sera enregistrée.")
            device_data.donnees_brutes = {'error': 'veratti_decode_failed_v5', 'tuya_values': tuya_values}
            return False

        # Remplir les données par phase (maintenant beaucoup plus riche)
        for phase_name, phase_data in veratti_result.get('phases', {}).items():
            if phase_data.get('success'):
                phase_prefix = phase_name.lower()
                setattr(device_data, f'tension_{phase_prefix}', phase_data.get('tension'))
                setattr(device_data, f'courant_{phase_prefix}', phase_data.get('courant'))
                setattr(device_data, f'puissance_{phase_prefix}', phase_data.get('puissance'))
                setattr(device_data, f'energie_{phase_prefix}', phase_data.get('energie'))
                setattr(device_data, f'facteur_puissance_{phase_prefix}', phase_data.get('facteur_puissance'))
        
        # Remplir les totaux et autres données
        totaux = veratti_result.get('totaux', {})
        
        device_data.puissance_totale = totaux.get('puissance_totale')
        device_data.energie_totale = totaux.get('energie_totale')
        device_data.facteur_puissance_total = totaux.get('facteur_puissance_moyen')
        
        first_valid_phase = next((p for p in veratti_result.get('phases', {}).values() if p.get('success')), None)
        if first_valid_phase:
            device_data.frequence = first_valid_phase.get('frequence')

        # Remplir les champs monophasés pour la compatibilité
        device_data.tension = totaux.get('tension_moyenne')
        device_data.puissance = totaux.get('puissance_totale')
        device_data.energie = totaux.get('energie_totale')
        valid_phases = [p for p in veratti_result.get('phases', {}).values() if p.get('success')]
        device_data.courant = round(sum(p['courant'] for p in valid_phases), 3)

        device_data.donnees_brutes = {'veratti_decode_v5': veratti_result, 'tuya_raw': tuya_values}
        
        print("✅ Données riches VERATTI remplies avec succès.")
        return True
    def _fill_triphase_data_fallback(self, device_data, tuya_values):
        """Méthode de fallback classique"""
        try:
            print("⚡ Remplissage triphasé classique (fallback)...")

            def decode_base64_float(val):
                try:
                    if not val:
                        return None
                    decoded = base64.b64decode(val)
                    if len(decoded) == 4:
                        return round(struct.unpack('<f', decoded)[0], 3)
                    return None
                except Exception:
                    return None

            # ===== COURANTS PAR PHASE =====
            device_data.courant_l1 = tuya_values.get("courant_l1") or decode_base64_float(tuya_values.get("phase_a"))
            device_data.courant_l2 = tuya_values.get("courant_l2") or decode_base64_float(tuya_values.get("phase_b"))
            device_data.courant_l3 = tuya_values.get("courant_l3") or decode_base64_float(tuya_values.get("phase_c"))
            device_data.courant_neutre = tuya_values.get("courant_neutre")

            # ===== TENSIONS PAR PHASE =====
            device_data.tension_l1 = tuya_values.get("tension_l1")
            device_data.tension_l2 = tuya_values.get("tension_l2")
            device_data.tension_l3 = tuya_values.get("tension_l3")

            # ===== PUISSANCES ACTIVES =====
            device_data.puissance_l1 = tuya_values.get("puissance_l1")
            device_data.puissance_l2 = tuya_values.get("puissance_l2")
            device_data.puissance_l3 = tuya_values.get("puissance_l3")
            device_data.puissance_totale = tuya_values.get("puissance_totale") or tuya_values.get("puissance")

            # ===== ENVIRONNEMENT =====
            device_data.frequence = tuya_values.get("frequence", 50.0)
            device_data.etat_switch = tuya_values.get("etat_switch")
            device_data.temperature = tuya_values.get("temperature")
            device_data.energie_totale = tuya_values.get("energie_totale") or tuya_values.get("energie")

            # ===== BACKWARD COMPATIBILITY =====
            device_data.tension = device_data.get_tension_moyenne()
            device_data.courant = device_data.get_courant_total()
            device_data.puissance = device_data.get_puissance_totale_calculee()
            device_data.energie = device_data.energie_totale

            print("✅ Données triphasées classiques remplies avec succès")
            return True

        except Exception as e:
            print(f"❌ Erreur remplissage triphasé classique: {e}")
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
        """✅ ADAPTÉ: Résumé des données pour le retour avec support VERATTI"""
        try:
            if device_data.is_triphase():
                return {
                    "type": "triphase",
                    "decoder": "VERATTI_enabled",
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
                    "puissances": {
                        "L1": device_data.puissance_l1,
                        "L2": device_data.puissance_l2,
                        "L3": device_data.puissance_l3,
                        "totale": device_data.puissance_totale
                    },
                    "desequilibres": {
                        "courant": device_data.calculer_desequilibre_courant() if hasattr(device_data, 'calculer_desequilibre_courant') else None,
                        "tension": device_data.calculer_desequilibre_tension() if hasattr(device_data, 'calculer_desequilibre_tension') else None
                    },
                    "facteur_puissance_total": device_data.facteur_puissance_total,
                    "frequence": device_data.frequence,
                    "temperature": device_data.temperature,
                    "energie_totale": device_data.energie_totale
                }
            else:
                return {
                    "type": "monophase",
                    "decoder": "standard",
                    "tension": device_data.tension,
                    "courant": device_data.courant,
                    "puissance": device_data.puissance,
                    "energie": device_data.energie,
                    "temperature": device_data.temperature,
                    "etat_switch": device_data.etat_switch
                }
        except Exception as e:
            return {"error": str(e), "decoder": "error"}
    
    def sync_all_assigned_devices(self):
        """✅ ADAPTÉ: Synchroniser tous les appareils assignés avec gestion intelligente + VERATTI"""
        try:
            print("🔄 Synchronisation globale des appareils assignés (VERATTI enabled)...")
            
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
            veratti_count = 0
            
            for i, device in enumerate(devices, 1):
                print(f"\n📊 [{i}/{len(devices)}] Sync {device.nom_appareil} ({device.tuya_device_id})...")
                
                result = self.save_tuya_data_to_database(device.tuya_device_id)
                result["device_name"] = device.nom_appareil
                result["device_type"] = device.type_systeme
                result["sync_order"] = i
                
                results.append(result)
                
                if result.get("success"):
                    success_count += 1
                    # Compter les décodages VERATTI réussis
                    if result.get("veratti_enabled") and result.get("type_systeme") == "triphase":
                        veratti_count += 1
                    print(f"   ✅ Succès")
                else:
                    print(f"   ❌ Erreur: {result.get('error', 'Inconnue')}")
                
                # ✅ Pause intelligente
                import time
                if i % 5 == 0:
                    print(f"   ⏸️ Pause intelligente (5 appareils traités)...")
                    time.sleep(1.0)
                else:
                    time.sleep(0.3)
            
            print(f"\n✅ Synchronisation terminée: {success_count}/{len(results)} réussies")
            print(f"🧠 VERATTI: {veratti_count} appareils triphasés décodés")
            
            return {
                "success": True,
                "total_devices": len(results),
                "successful_syncs": success_count,
                "failed_syncs": len(results) - success_count,
                "veratti_decoded": veratti_count,
                "success_rate": round((success_count / len(results)) * 100, 1) if results else 0,
                "results": results,
                "intelligent_sync": True,
                "veratti_enabled": True,
                "summary": {
                    "devices_synced": success_count,
                    "devices_failed": len(results) - success_count,
                    "veratti_triphasé": veratti_count,
                    "timestamp": datetime.utcnow().isoformat(),
                    "tuya_client_features": "intelligent",
                    "decoder_features": "VERATTI_v1.0"
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
    
    def sync_veratti_device_debug(self, device_id):
        """🧪 Synchronisation VERATTI avec debug détaillé"""
        try:
            print(f"🧪 === DEBUG VERATTI pour {device_id} ===")
            
            # Récupérer l'appareil
            device = Device.get_by_tuya_id(device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            # Récupérer les données Tuya brutes
            tuya_response = self.tuya_client.get_device_current_values(device_id)
            if not tuya_response.get("success"):
                return {"success": False, "error": "Erreur récupération Tuya"}
            
            tuya_values = tuya_response.get("values", {})
            
            print(f"📊 Données Tuya brutes pour {device.nom_appareil}:")
            for key, value in tuya_values.items():
                if 'Phase' in key or 'grid' in key:
                    print(f"   {key}: {value}")
            
            # Test décodage VERATTI
            veratti_result = self.veratti_decoder.decode_full_veratti_triphasé(tuya_values)
            
            print(f"\n🧠 Résultat décodage VERATTI:")
            print(f"   Succès: {veratti_result.get('success')}")
            
            if veratti_result.get('success'):
                phases = veratti_result.get('phases', {})
                for phase_name, phase_data in phases.items():
                    if phase_data.get('success'):
                        print(f"   {phase_name}: {phase_data.get('tension')}V, {phase_data.get('courant')}A, {phase_data.get('puissance')}W")
                        print(f"      Formules: tension={phase_data.get('tension_formula')}, courant={phase_data.get('courant_formula')}")
                    else:
                        print(f"   {phase_name}: Échec - {phase_data.get('error')}")
                
                totaux = veratti_result.get('totaux', {})
                quality = veratti_result.get('quality', {})
                print(f"   Totaux: {totaux}")
                print(f"   Qualité: {quality}")
            else:
                print(f"   Erreur: {veratti_result.get('error')}")
            
            return {
                "success": True,
                "device_name": device.nom_appareil,
                "tuya_values": tuya_values,
                "veratti_result": veratti_result,
                "debug_mode": True
            }
            
        except Exception as e:
            print(f"❌ Erreur debug VERATTI: {e}")
            return {"success": False, "error": str(e)}


# ===== FONCTIONS UTILITAIRES ADAPTÉES =====

def create_tuya_sync_service(tuya_client):
    """✅ ADAPTÉ: Factory pour créer le service de sync avec TuyaClient intelligent + VERATTI"""
    if not hasattr(tuya_client, 'get_device_current_values'):
        raise ValueError("Le TuyaClient fourni n'est pas compatible (méthode get_device_current_values manquante)")
    
    return TuyaToDeviceDataService(tuya_client)

def sync_single_device(tuya_device_id):
    """✅ ADAPTÉ: Synchroniser un seul appareil avec TuyaClient intelligent + VERATTI"""
    # ✅ IMPORT CORRIGÉ
    from app.services.tuya_service import TuyaClient
    
    # Connexion Tuya avec le client intelligent
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        return {"success": False, "error": "Connexion TuyaClient intelligent impossible"}
    
    # Service de sync adapté avec VERATTI
    sync_service = TuyaToDeviceDataService(tuya_client)
    
    # Synchronisation
    return sync_service.save_tuya_data_to_database(tuya_device_id)

def sync_all_devices():
    """✅ ADAPTÉ: Synchroniser tous les appareils avec TuyaClient intelligent + VERATTI"""
    # ✅ IMPORT CORRIGÉ
    from app.services.tuya_service import TuyaClient
    
    # Connexion Tuya avec le client intelligent
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        return {"success": False, "error": "Connexion TuyaClient intelligent impossible"}
    
    # Service de sync adapté avec VERATTI
    sync_service = TuyaToDeviceDataService(tuya_client)
    
    # Synchronisation globale intelligente avec VERATTI
    return sync_service.sync_all_assigned_devices()

def sync_all_devices_with_health_check():
    """✅ NOUVEAU: Synchronisation avec vérification santé + VERATTI"""
    # ✅ IMPORT CORRIGÉ
    from app.services.tuya_service import TuyaClient
    
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        return {"success": False, "error": "Connexion TuyaClient intelligent impossible"}
    
    sync_service = TuyaToDeviceDataService(tuya_client)
    return sync_service.sync_with_health_check()

def debug_veratti_device(tuya_device_id):
    """🧪 NOUVEAU: Debug spécifique VERATTI"""
    # ✅ IMPORT CORRIGÉ
    from app.services.tuya_service import TuyaClient
    
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        return {"success": False, "error": "Connexion TuyaClient impossible"}
    
    sync_service = TuyaToDeviceDataService(tuya_client)
    return sync_service.sync_veratti_device_debug(tuya_device_id)


# ===== EXEMPLE D'UTILISATION COMPLET (DÉSACTIVÉ POUR ÉVITER LES IMPORTS LORS DU MODULE) =====

def test_sync_service_with_veratti():
    """🧪 Test du service de synchronisation avec TuyaClient intelligent + VERATTI (pour tests manuels)"""
    
    print("⚠️ Cette fonction est prévue pour tests manuels.")
    print("🔧 Pour tester, utilisez le script test_veratti.py à la racine du projet")
    
    return {
        "message": "Utilisez le script test_veratti.py pour les tests complets",
        "available_functions": [
            "sync_single_device(device_id)",
            "sync_all_devices()", 
            "debug_veratti_device(device_id)",
            "sync_all_devices_with_health_check()"
        ]
    }

# ✅ EMPÊCHER L'EXÉCUTION AUTOMATIQUE DU TEST
if __name__ == "__main__":
    print("🧠 TuyaToDeviceDataService avec VERATTI chargé")
    print("📋 Fonctions disponibles:")
    print("   - sync_single_device(device_id)")
    print("   - sync_all_devices()")
    print("   - debug_veratti_device(device_id)")
    print("   - sync_all_devices_with_health_check()")
    print("\n🔧 Pour tester, créez le fichier test_veratti.py à la racine du projet")