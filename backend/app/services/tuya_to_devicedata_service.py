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

class VerattiDecoder:
    """🧠 Décodeur intelligent pour appareils VERATTI triphasés"""
    
    def __init__(self, debug=True):
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        
        # ✅ FORMULES DÉCOUVERTES basées sur vos tests
        self.formulas = {
            'tension': [
                {'method': 'multiply', 'factor': 1.74, 'name': 'VERATTI_v1'},
                {'method': 'add', 'offset': 94, 'name': 'VERATTI_v2'},
                {'method': 'divide', 'divisor': 2.0, 'offset': 110, 'name': 'VERATTI_v3'}
            ],
            'courant': [
                {'method': 'divide', 'divisor': 875, 'name': 'VERATTI_primary'},
                {'method': 'divide', 'divisor': 900, 'name': 'VERATTI_alt1'},
                {'method': 'divide', 'divisor': 1000, 'name': 'VERATTI_alt2'},
                {'method': 'divide', 'divisor': 1200, 'name': 'VERATTI_alt3'}
            ],
            'puissance': [
                {'method': 'direct', 'name': 'VERATTI_direct'},
                {'method': 'calculate', 'name': 'VERATTI_calculated'}
            ]
        }
        
        # Plages de validation
        self.validation_ranges = {
            'tension': (180.0, 280.0),  # Volts
            'courant': (0.0, 100.0),    # Ampères
            'puissance': (0.0, 50000.0) # Watts
        }
        
        self._debug_log("🧠 Décodeur VERATTI initialisé avec formules adaptatives")
    
    def _debug_log(self, message: str):
        """Log de debug si activé"""
        if self.debug:
            print(f"[VERATTI] {message}")
    
    def decode_base64_to_bytes(self, base64_string: str) -> Optional[List[int]]:
        """Décoder une chaîne base64 en liste de bytes"""
        try:
            if not base64_string:
                return None
            decoded = base64.b64decode(base64_string)
            return list(decoded)
        except Exception as e:
            self._debug_log(f"❌ Erreur décodage base64: {e}")
            return None
    

    # def try_voltage_formulas(self, byte_value: int) -> Dict[str, float]:
   
    #     """
    #     ✅ Formule FINALE calibrée sur mesures Tuya Smart réelles
    #     """
    #     results = {}

    #     try:
    #         tension_brute = byte_value * 2 + 1
    #         tension_calibree = round(tension_brute * 0.582, 1)  # Facteur ajusté pour 224V
            
    #         self._debug_log(f"🔧 Tension byte {byte_value}: brute={tension_brute}V, calibrée={tension_calibree}V")

    #         if 200.0 <= tension_calibree <= 250.0:
    #             results['VERATTI_CALIBRATED_FINAL'] = tension_calibree
    #             self._debug_log(f"✅ Tension validée: {tension_calibree}V")

    #     except Exception as e:
    #         self._debug_log(f"❌ Erreur calcul tension: {e}")

    #     return results


    def try_voltage_formulas(self, byte_value: int) -> Dict[str, float]:
        """
        🎯 FACTEUR CORRIGÉ pour obtenir 220V avec bytes 138-139
        Nouveau calcul basé sur les dernières observations
        """
        results = {}

        try:
            tension_brute = byte_value * 2 + 1
            
            # 🔧 NOUVEAU FACTEUR CORRIGÉ
            # 220V ÷ (138×2+1) = 220 ÷ 277 = 0.794
            facteur = 0.794
            
            tension_finale = round(tension_brute * facteur, 1)
            
            # ✅ TOUJOURS ACCEPTER
            results['VERATTI_CORRECTED'] = tension_finale
            results['status'] = "✅ tension corrigée"
            
            self._debug_log(f"🎯 Tension CORRIGÉE: byte {byte_value} → {tension_finale}V (facteur {facteur})")
            
        except Exception as e:
            self._debug_log(f"❌ Erreur: {e}")

        return results

    def _debug_temperature_sources(self, tuya_values: Dict[str, Any]):
        """🧪 Debug pour identifier toutes les sources de température disponibles"""
        self._debug_log("🌡️ === DEBUG TEMPÉRATURE - SOURCES DISPONIBLES ===")
        
        temp_keys = ['temp_current', 'Temp Current', 'temperature']
        found_sources = {}
        
        for key in temp_keys:
            if key in tuya_values:
                value = tuya_values[key]
                found_sources[key] = value
                self._debug_log(f"   {key}: {value}")
                
                # Test des deux approches
                if isinstance(value, (int, float)):
                    direct = value
                    divided = value / 10
                    
                    self._debug_log(f"     → Direct: {direct}°C")
                    self._debug_log(f"     → Divisé par 10: {divided}°C")
        
        # Vérifier aussi raw_status si disponible
        if 'raw_status' in tuya_values:
            raw_status = tuya_values.get('raw_status', [])
            for item in raw_status:
                if isinstance(item, dict) and 'temp' in item.get('code', '').lower():
                    found_sources[f"raw_status.{item['code']}"] = item['value']
                    self._debug_log(f"   raw_status.{item['code']}: {item['value']}")
        
        # Recommandation
        if 'temp_current' in found_sources:
            recommended = found_sources['temp_current']
            self._debug_log(f"🎯 RECOMMANDATION: Utiliser temp_current = {recommended}°C (source la plus fiable)")
        
        self._debug_log("🌡️ === FIN DEBUG TEMPÉRATURE ===")
        return found_sources    





    
    def try_current_formulas(self, byte_value: int) -> Dict[str, float]:
        """Tester toutes les formules de courant - VERSION CALIBRÉE"""
        if byte_value == 0:
            return {'zero_current': 0.0}
        
        results = {}
        # Le diviseur correct est 1000
        divisor = 1000.0
        
        value = byte_value / divisor
        
        # Validation
        if 0.0 <= value <= 100.0:
            results['VERATTI_calibrated_primary'] = round(value, 3)
            
        return results
    
    def decode_veratti_phase(self, base64_data: str, phase_name: str = "Unknown") -> Dict[str, Any]:
        """
        🧠 Décodage intelligent d'une phase VERATTI - VERSION FINALE ET CORRIGÉE
        """
        try:
            self._debug_log(f"📊 Décodage phase {phase_name}: {base64_data[:20]}...")
            
            bytes_data = self.decode_base64_to_bytes(base64_data)
            
            if not bytes_data or len(bytes_data) < 5:
                return {
                    'success': False,
                    'error': f'Données insuffisantes: {len(bytes_data) if bytes_data else 0} bytes (minimum 5 requis)',
                    'phase': phase_name
                }
            
            result = {
                'success': True,
                'phase': phase_name,
                'timestamp': datetime.utcnow().isoformat(),
                'raw_bytes_hex': ' '.join([f'{b:02x}' for b in bytes_data]),
                'bytes_length': len(bytes_data)
            }
            
            # --- TENSION ---
            # (Cette partie fonctionnera maintenant car on suppose que try_voltage_formulas est corrigée)
            voltage_byte = bytes_data[1] if len(bytes_data) > 1 else 0
            voltage_candidates = self.try_voltage_formulas(voltage_byte)
            
            if voltage_candidates:
                # On prend la première formule valide, qui devrait être la "directe"
                best_voltage_key = list(voltage_candidates.keys())[0]
                result['tension'] = voltage_candidates[best_voltage_key]
                result['tension_formula'] = best_voltage_key
                self._debug_log(f"✅ Tension {phase_name}: {result['tension']}V ({best_voltage_key}) depuis byte {voltage_byte}")
            else:
                result['tension'] = None # Garder le None pour indiquer un échec
                result['tension_formula'] = 'failed'
                self._debug_log(f"⚠️ Tension {phase_name}: aucune formule valide pour byte {voltage_byte}")
            
            # --- COURANT --- (inchangé, c'est déjà parfait)
            current_byte = bytes_data[4] if len(bytes_data) > 4 else 0
            current_candidates = self.try_current_formulas(current_byte)
            
            if current_candidates:
                best_current_key = list(current_candidates.keys())[0]
                result['courant'] = current_candidates[best_current_key]
                result['courant_formula'] = best_current_key
            else:
                result['courant'] = 0.0
                result['courant_formula'] = 'zero_default'
            self._debug_log(f"✅ Courant {phase_name}: {result['courant']}A ({result['courant_formula']}) depuis byte {current_byte}")

            # --- PUISSANCE ---
            # ✅ AMÉLIORATION : Calcul plus robuste de la puissance
            if result.get('tension') is not None and result.get('courant') is not None:
                # Calcul de la puissance apparente (S = V * I)
                puissance_apparente = result['tension'] * result['courant']
                
                # Estimation de la puissance active (P = S * cos(phi))
                # On utilise un facteur de puissance (cos φ) de 0.9, ce qui est une bonne estimation pour des charges mixtes.
                facteur_puissance_estime = 0.9
                result['puissance'] = round(puissance_apparente * facteur_puissance_estime, 2)
                result['puissance_source'] = 'calculated'
                self._debug_log(f"✅ Puissance {phase_name}: {result['puissance']}W (calculée avec cos φ de {facteur_puissance_estime})")
            else:
                result['puissance'] = 0.0
                result['puissance_source'] = 'default'
                self._debug_log(f"⚠️ Puissance {phase_name}: 0W (tension ou courant manquant)")

            # --- DEBUG INFO --- (inchangé, c'est déjà parfait)
            if len(bytes_data) >= 8:
                result['debug_positions'] = {
                    'pos_0': bytes_data[0], 'pos_1_tension': bytes_data[1], 
                    'pos_2': bytes_data[2], 'pos_3': bytes_data[3],
                    'pos_4_courant': bytes_data[4], 'pos_5': bytes_data[5],
                    'pos_6': bytes_data[6], 'pos_7': bytes_data[7]
                }
            
            return result
            
        except Exception as e:
            self._debug_log(f"❌ Erreur décodage phase {phase_name}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False, 'error': str(e),
                'phase': phase_name, 'timestamp': datetime.utcnow().isoformat()
            }

    

    def decode_full_veratti_triphasé(self, tuya_values: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 DÉCODAGE COMPLET d'un appareil VERATTI triphasé - VERSION FINALE CALIBRÉE ET CORRIGÉE
        """
        try:
            self._debug_log("🔄 Décodage complet VERATTI triphasé (v3.1 CORRECTED)...")
            
            result = {
                'success': True,
                'timestamp': datetime.utcnow().isoformat(),
                'decoder_version': 'VERATTI_v3.1_CORRECTED',
                'type_systeme': 'triphase',
                'phases': {},
                'totaux': {},
                'quality': {},
                'tuya_direct': {}
            }
            
            # 🧪 DEBUG TEMPÉRATURE - Identifier toutes les sources disponibles
            self._debug_temperature_sources(tuya_values)
            
            # ✅ 1. VALEURS TUYA DIRECTES AVEC CORRECTION DES FACTEURS
            direct_mappings = {
                'Total Power': 'puissance_totale_tuya',
                'power factor': 'facteur_puissance_tuya',
                'Total forward energy': 'energie_totale_tuya',
                'total_forward_energy': 'energie_totale_tuya',
                'Temp Current': 'temperature',
                'temp_current': 'temperature',
                'energie_totale': 'energie_totale_tuya',
                'temperature': 'temperature'
            }
            
            for tuya_key, our_key in direct_mappings.items():
                if tuya_key in tuya_values:
                    value = tuya_values[tuya_key]
                    
                    # Nettoyage des unités (si c'est une chaîne)
                    if isinstance(value, str):
                        if 'kW' in value: value = float(value.replace('kW', '').replace('·h', '').strip())
                        elif 'pf' in value: value = float(value.replace('pf', '').strip())
                        elif '℃' in value: value = float(value.replace('℃', '').strip())
                    
                    # Application des facteurs de correction pour correspondre à l'application Tuya
                    if isinstance(value, (int, float)):
                        if our_key == 'energie_totale_tuya':
                            value = value / 100.0  # Ex: 94 -> 0.94 kWh
                            self._debug_log(f"🔋 Énergie corrigée: {value} kWh")
                        elif our_key == 'temperature':
                            # 🔧 CORRECTION TEMPÉRATURE - APPROCHE INTELLIGENTE
                            if tuya_key == 'temp_current':
                                # temp_current = 37 dans raw_status = 37°C réels (pas 3.7°C)
                                value = value  # Utiliser directement
                                self._debug_log(f"🌡️ Température temp_current: {value}°C (valeur réelle Tuya Smart)")
                            elif tuya_key in ['Temp Current', 'temperature']:
                                # Autres clés de température - vérifier la plage
                                if 0 <= value <= 10:  # Probablement en dixièmes (3.7 = 37°C)
                                    value = value * 10
                                    self._debug_log(f"🌡️ Température corrigée: {value}°C (×10 - était {value/10})")
                                elif 20 <= value <= 60:  # Déjà en degrés complets
                                    value = value
                                    self._debug_log(f"🌡️ Température directe: {value}°C (plage normale)")
                                else:
                                    self._debug_log(f"⚠️ Température hors plage normale: {value}°C - utilisation directe")
                    
                    result['tuya_direct'][our_key] = value
                    self._debug_log(f"✅ Valeur directe (corrigée) {tuya_key}: {value}")
            
            # ✅ 2. DÉCODAGE DES PHASES BASE64 (s'appuie sur les méthodes de phase corrigées)
            phase_mappings = [
                {'Phase A grid detailed data': 'L1', 'Phase B grid detailed data': 'L2', 'Phase C grid detailed data': 'L3'},
                {'phase_a': 'L1', 'phase_b': 'L2', 'phase_c': 'L3'}
            ]
            
            for mapping in phase_mappings:
                for tuya_phase_key, phase_name in mapping.items():
                    if tuya_phase_key in tuya_values and phase_name not in result['phases']:
                        base64_data = tuya_values[tuya_phase_key]
                        self._debug_log(f"🔍 Trouvé {tuya_phase_key} pour phase {phase_name}")
                        phase_result = self.decode_veratti_phase(base64_data, phase_name)
                        result['phases'][phase_name] = phase_result
            
            # ✅ 3. CALCULS TRIPHASÉS (le code est déjà correct et utilisera les nouvelles valeurs)
            phases_success = [p for p in result['phases'].values() if p.get('success')]
            
            if phases_success:
                tensions = [p.get('tension') for p in phases_success if p.get('tension') is not None]
                if tensions:
                    result['totaux']['tension_moyenne'] = round(sum(tensions) / len(tensions), 1)
                    result['totaux']['tension_min'] = min(tensions)
                    result['totaux']['tension_max'] = max(tensions)
                    self._debug_log(f"⚡ Tensions détectées: min={result['totaux']['tension_min']}V, max={result['totaux']['tension_max']}V, moy={result['totaux']['tension_moyenne']}V")
                else:
                    result['totaux']['tension_moyenne'] = 0.0
                    self._debug_log("⚠️ Aucune tension détectée")

                courants = [p.get('courant', 0.0) for p in phases_success]
                result['totaux']['courant_total'] = round(sum(courants), 3)
                self._debug_log(f"⚡ Courant total calculé: {result['totaux']['courant_total']}A")
                
                puissances = [p.get('puissance', 0.0) for p in phases_success]
                result['totaux']['puissance_totale_calculee'] = round(sum(puissances), 2)
                self._debug_log(f"⚡ Puissance totale calculée: {result['totaux']['puissance_totale_calculee']}W")

                result['totaux']['frequence'] = 50.0
                self._debug_log(f"✅ Fréquence définie à {result['totaux']['frequence']}Hz (défaut)")

                # ✅ 4. QUALITÉ ET DÉSÉQUILIBRES (le code est déjà correct)
                if len(tensions) >= 2:
                    tension_moy = result['totaux']['tension_moyenne']
                    if tension_moy > 0:
                        max_ecart_v = max([abs(t - tension_moy) for t in tensions])
                        result['quality']['desequilibre_tension_pct'] = round((max_ecart_v / tension_moy) * 100, 2)
                        self._debug_log(f"📊 Déséquilibre tension: {result['quality']['desequilibre_tension_pct']}%")
                
                if len(courants) >= 2 and result['totaux']['courant_total'] > 0.05: # Seuil ajusté
                    courant_moy = sum(courants) / len(courants) if len(courants) > 0 else 0
                    if courant_moy > 0:
                        max_ecart_c = max([abs(c - courant_moy) for c in courants])
                        result['quality']['desequilibre_courant_pct'] = round((max_ecart_c / courant_moy) * 100, 2)
                        self._debug_log(f"📊 Déséquilibre courant: {result['quality']['desequilibre_courant_pct']}%")
            
            phases_decoded = len(phases_success)
            self._debug_log(f"✅ Décodage complet terminé: {phases_decoded}/3 phases décodées")
            
            # ✅ 5. VALIDATION FINALE
            if phases_decoded == 0:
                self._debug_log("⚠️ Aucune phase décodée - vérification des clés disponibles")
                available_keys = [k for k in tuya_values.keys() if 'phase' in k.lower()]
                self._debug_log(f"Clés phase disponibles: {available_keys}")
                if available_keys:
                    result['debug_info'] = {
                        'available_phase_keys': available_keys,
                        'attempted_mappings': phase_mappings
                    }
            
            return result
            
        except Exception as e:
            self._debug_log(f"❌ Erreur décodage complet: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    

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

    def _fill_triphase_data_with_veratti(self, device_data, tuya_values, device):
        """✅ NOUVEAU: Remplissage triphasé avec décodeur VERATTI intégré"""
        try:
            print("⚡ Remplissage données triphasées avec décodeur VERATTI...")
            
            # ✅ 1. TENTATIVE DE DÉCODAGE VERATTI
            veratti_result = self.veratti_decoder.decode_full_veratti_triphasé(tuya_values)
            
            if veratti_result.get('success'):
                print("✅ Décodage VERATTI réussi - utilisation des données décodées")
                
                phases = veratti_result.get('phases', {})
                totaux = veratti_result.get('totaux', {})
                tuya_direct = veratti_result.get('tuya_direct', {})
                
                # Remplir les données par phase depuis VERATTI
                if 'L1' in phases and phases['L1'].get('success'):
                    device_data.tension_l1 = phases['L1'].get('tension')
                    device_data.courant_l1 = phases['L1'].get('courant')
                    device_data.puissance_l1 = phases['L1'].get('puissance')
                
                if 'L2' in phases and phases['L2'].get('success'):
                    device_data.tension_l2 = phases['L2'].get('tension')
                    device_data.courant_l2 = phases['L2'].get('courant')
                    device_data.puissance_l2 = phases['L2'].get('puissance')
                
                if 'L3' in phases and phases['L3'].get('success'):
                    device_data.tension_l3 = phases['L3'].get('tension')
                    device_data.courant_l3 = phases['L3'].get('courant')
                    device_data.puissance_l3 = phases['L3'].get('puissance')
                
                # Totaux depuis VERATTI
                device_data.puissance_totale = totaux.get('puissance_totale_calculee')
                
                # Données directes Tuya
                device_data.temperature = tuya_direct.get('temperature')
                device_data.energie_totale = tuya_direct.get('energie_totale_tuya')
                device_data.facteur_puissance_total = tuya_direct.get('facteur_puissance_tuya')
                
                # Stocker le résultat VERATTI complet pour debug
                device_data.donnees_brutes = {
                    'tuya_values': tuya_values,
                    'veratti_decode': veratti_result,
                    'decoder': 'VERATTI_v1.0',
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # ✅ BACKWARD COMPATIBILITY
                device_data.tension = device_data.get_tension_moyenne()
                device_data.courant = device_data.get_courant_total()
                device_data.puissance = device_data.get_puissance_totale_calculee()
                device_data.energie = device_data.energie_totale
                
                phases_decoded = len([p for p in phases.values() if p.get('success')])
                print(f"✅ VERATTI: {phases_decoded}/3 phases décodées avec succès")
                return True
                
            else:
                print(f"❌ Échec décodage VERATTI: {veratti_result.get('error')} - fallback classique")
                return self._fill_triphase_data_fallback(device_data, tuya_values)
                
        except Exception as e:
            print(f"❌ Erreur décodage VERATTI: {e} - fallback classique")
            return self._fill_triphase_data_fallback(device_data, tuya_values)
    
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