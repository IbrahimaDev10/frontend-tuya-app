# app/services/triphase_detection_service.py
# Service pour détecter automatiquement les appareils triphasés et les configurer
# ✅ VERSION ADAPTÉE pour votre test_detection.py

import base64
import struct
import json
from datetime import datetime
from app.models.device import Device
from app.models.device_data import DeviceData
from app import db

class TriphaseDetectionService:
    """Service pour détecter et gérer les appareils triphasés - Compatible avec votre test"""
    
    def __init__(self, tuya_client):
        self.tuya_client = tuya_client
        print("🔍 Service de détection triphasé initialisé")
        
        # Indicateurs de détection triphasé
        self.triphase_indicators = {
            # Codes Tuya spécifiques triphasé
            'strong_indicators': [
                'phase_a', 'phase_b', 'phase_c',           # Données par phase
                'total_forward_energy',                     # Énergie totale
                'forward_energy_total',                     # Variante énergie
                'supply_frequency',                         # Fréquence réseau
                'leakage_current',                         # Courant de fuite
                'switch_prepayment',                       # Prépaiement
                'fault'                                    # Codes de défaut
            ],
            'medium_indicators': [
                'add_ele',                                 # Énergie si > seuil
                'cur_power'                               # Puissance si > seuil
            ],
            'weak_indicators': [
                'cur_voltage', 'cur_current'              # Basique électrique
            ]
        }
        
        # Mots-clés dans les noms d'appareils
        self.name_keywords = {
            'strong': ['triphase', 'triphasé', '3phase', 'three phase', 'analyseur', 
                      'compteur', 'meter', 'energy meter', 'power meter', 'atorch'],
            'medium': ['smart meter', 'electric', 'energy', 'power'],
            'weak': ['switch', 'socket', 'plug']
        }
        
        # Seuils de détection
        self.detection_thresholds = {
            'puissance_min_triphase': 3000,    # 3kW minimum pour suspecter triphasé
            'energie_min_triphase': 10,        # 10kWh minimum
            'confidence_minimum': 60           # 60% minimum pour classifier triphasé
        }
    
    def get_detection_report(self, save_to_db=False):
        """
        ✅ MÉTHODE PRINCIPALE pour votre test_detection.py
        Générer un rapport de détection complet SANS modification par défaut
        
        Args:
            save_to_db (bool): False par défaut pour sécurité
        """
        try:
            print("📋 === GÉNÉRATION RAPPORT DÉTECTION TRIPHASÉ ===")
            
            # Vérifier connexion Tuya
            if not self.tuya_client.ensure_token():
                return {
                    "success": False,
                    "error": "Token Tuya invalide - connexion impossible"
                }
            
            # 1. Récupérer tous les appareils Tuya avec votre TuyaClient intelligent
            print("📡 Récupération des appareils Tuya...")
            devices_response = self.tuya_client.get_all_devices_with_details()
            
            if not devices_response.get("success"):
                return {
                    "success": False,
                    "error": f"Impossible de récupérer les appareils: {devices_response.get('error', 'Erreur inconnue')}"
                }
            
            tuya_devices = devices_response.get("result", [])
            print(f"📊 {len(tuya_devices)} appareils Tuya trouvés")
            
            if not tuya_devices:
                return {
                    "success": True,
                    "summary": {
                        "total_devices": 0,
                        "triphase_detected": 0,
                        "monophase_detected": 0,
                        "unknown_detected": 0,
                        "detection_rate": 0.0
                    },
                    "triphase_devices": [],
                    "monophase_devices": [],
                    "recommendations": ["Aucun appareil trouvé à analyser"],
                    "detection_timestamp": datetime.utcnow().isoformat()
                }
            
            # 2. Analyser chaque appareil
            detection_results = []
            triphase_count = 0
            monophase_count = 0
            unknown_count = 0
            
            for i, tuya_device in enumerate(tuya_devices, 1):
                device_id = tuya_device.get("id") or tuya_device.get("device_id")
                device_name = tuya_device.get("name", "Appareil inconnu")
                
                print(f"🔍 [{i}/{len(tuya_devices)}] Analyse {device_name[:30]}...")
                
                # Analyser cet appareil
                analysis = self._analyze_single_device(device_id, device_name)
                
                if analysis["success"]:
                    detected_type = analysis["detected_type"]
                    confidence = analysis["confidence"]
                    
                    if detected_type == "triphase":
                        triphase_count += 1
                    elif detected_type == "monophase":
                        monophase_count += 1
                    else:
                        unknown_count += 1
                    
                    # Vérifier si l'appareil existe en base
                    existing_device = Device.get_by_tuya_id(device_id) if device_id else None
                    
                    detection_results.append({
                        "device_id": device_id,
                        "name": device_name,
                        "detected_type": detected_type,
                        "confidence": confidence,
                        "key_indicators": self._extract_key_indicators(analysis.get("indicators", {})),
                        "exists_in_db": existing_device is not None,
                        "current_db_type": existing_device.type_systeme if existing_device else None,
                        "needs_update": (existing_device and existing_device.type_systeme != detected_type) if existing_device else False,
                        "online_status": tuya_device.get("isOnline", False),
                        "recommendation": self._get_device_recommendation(analysis, existing_device)
                    })
                else:
                    unknown_count += 1
                    print(f"   ❌ Erreur: {analysis.get('error', 'Inconnue')}")
            
            # 3. Filtrer les appareils par type
            triphase_devices = [d for d in detection_results if d["detected_type"] == "triphase"]
            monophase_devices = [d for d in detection_results if d["detected_type"] == "monophase"]
            
            # 4. Calculer statistiques
            total_analyzed = len(detection_results)
            detection_rate = round(
                ((triphase_count + monophase_count) / total_analyzed * 100) if total_analyzed > 0 else 0, 1
            )
            
            # 5. Générer recommandations
            recommendations = self._generate_recommendations(triphase_devices, monophase_devices, unknown_count)
            
            # 6. ✅ SAUVEGARDE OPTIONNELLE (désactivée par défaut pour sécurité)
            if save_to_db:
                print("💾 Sauvegarde des mises à jour en base...")
                update_results = self._apply_detection_updates(detection_results)
                save_info = {
                    "devices_updated": update_results["updated_count"],
                    "update_errors": update_results["error_count"],
                    "update_details": update_results["details"]
                }
            else:
                save_info = {
                    "mode": "lecture_seule",
                    "note": "Aucune modification effectuée en base"
                }
            
            # 7. Construire le rapport final
            report = {
                "success": True,
                "detection_timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "total_devices": len(tuya_devices),
                    "devices_analyzed": total_analyzed,
                    "triphase_detected": triphase_count,
                    "monophase_detected": monophase_count,
                    "unknown_detected": unknown_count,
                    "detection_rate": detection_rate
                },
                "triphase_devices": sorted(triphase_devices, key=lambda x: x["confidence"], reverse=True),
                "monophase_devices": monophase_devices[:5],  # Limiter pour le rapport
                "recommendations": recommendations,
                "save_info": save_info,
                "tuya_client_stats": self._get_tuya_client_stats()
            }
            
            # 8. Affichage du résumé
            print(f"\n✅ === RAPPORT GÉNÉRÉ ===")
            print(f"   📊 Total analysé: {total_analyzed}/{len(tuya_devices)}")
            print(f"   ⚡ Triphasés détectés: {triphase_count}")
            print(f"   🔌 Monophasés détectés: {monophase_count}")
            print(f"   ❓ Indéterminés: {unknown_count}")
            print(f"   📈 Taux de détection: {detection_rate}%")
            
            if triphase_devices:
                print(f"\n🔌 TOP 3 TRIPHASÉS DÉTECTÉS:")
                for device in triphase_devices[:3]:
                    print(f"   📱 {device['name'][:40]} (confiance: {device['confidence']}%)")
            
            return report
            
        except Exception as e:
            print(f"❌ Erreur génération rapport: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "detection_timestamp": datetime.utcnow().isoformat()
            }
    
    def _analyze_single_device(self, device_id, device_name):
        """Analyser un appareil spécifique pour détecter s'il est triphasé"""
        try:
            if not device_id:
                return {
                    "success": False,
                    "error": "ID appareil manquant"
                }
            
            # 1. Récupérer le statut avec votre TuyaClient intelligent
            status_response = self.tuya_client.get_device_current_values(device_id)
            
            if not status_response.get("success"):
                return {
                    "success": False,
                    "error": f"Impossible de récupérer le statut: {status_response.get('error', 'Erreur Tuya')}"
                }
            
            raw_status = status_response.get("raw_status", [])
            mapped_values = status_response.get("values", {})
            is_online = status_response.get("is_online", False)
            
            # 2. Analyser les indicateurs triphasés
            indicators = self._check_triphase_indicators(raw_status, mapped_values, device_name)
            
            # 3. Calculer le score de confiance
            confidence_score = self._calculate_confidence_score(indicators)
            
            # 4. Déterminer le type basé sur la confiance
            if confidence_score >= 80:
                detected_type = "triphase"
            elif confidence_score >= 60:
                detected_type = "triphase"  # Probable triphasé
            elif any([indicators.get("has_basic_electrical"), indicators.get("has_power_data")]):
                detected_type = "monophase"
            else:
                detected_type = "unknown"
            
            return {
                "success": True,
                "detected_type": detected_type,
                "confidence": confidence_score,
                "indicators": indicators,
                "is_online": is_online,
                "raw_data": {
                    "raw_status": raw_status,
                    "mapped_values": mapped_values,
                    "values_count": len(mapped_values)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur analyse appareil: {str(e)}"
            }
    
    def _check_triphase_indicators(self, raw_status, mapped_values, device_name):
        """Vérifier les différents indicateurs de système triphasé"""
        indicators = {
            "has_phase_data": False,
            "has_phase_codes": False,
            "has_triphase_energy": False,
            "has_frequency": False,
            "has_basic_electrical": False,
            "has_power_data": False,
            "has_high_power": False,
            "phase_codes_found": [],
            "triphase_codes_found": [],
            "electrical_codes_found": [],
            "device_name_hints": False,
            "power_level": 0,
            "energy_level": 0
        }
        
        # 1. Vérifier le nom de l'appareil
        name_lower = device_name.lower()
        
        # Vérifier mots-clés forts
        for keyword in self.name_keywords['strong']:
            if keyword in name_lower:
                indicators["device_name_hints"] = True
                indicators["name_hint_strength"] = "strong"
                break
        
        # Vérifier mots-clés moyens si pas de fort
        if not indicators["device_name_hints"]:
            for keyword in self.name_keywords['medium']:
                if keyword in name_lower:
                    indicators["device_name_hints"] = True
                    indicators["name_hint_strength"] = "medium"
                    break
        
        # 2. Analyser les codes bruts
        for item in raw_status:
            if not isinstance(item, dict):
                continue
                
            code = item.get('code', '')
            value = item.get('value')
            
            # Indicateurs forts (codes spécifiques triphasé)
            if code in self.triphase_indicators['strong_indicators']:
                indicators["triphase_codes_found"].append(code)
                
                if code in ['phase_a', 'phase_b', 'phase_c']:
                    indicators["has_phase_codes"] = True
                    indicators["has_phase_data"] = True
                    
                    # Essayer de décoder les données de phase
                    if value and self._try_decode_phase_data(value):
                        indicators["has_decoded_phase_data"] = True
                
                elif code in ['total_forward_energy', 'forward_energy_total']:
                    indicators["has_triphase_energy"] = True
                    if value:
                        indicators["energy_level"] = value
                        
                elif code == 'supply_frequency':
                    indicators["has_frequency"] = True
            
            # Indicateurs moyens
            elif code in self.triphase_indicators['medium_indicators']:
                indicators["electrical_codes_found"].append(code)
                
                if code == 'cur_power' and value:
                    indicators["has_power_data"] = True
                    indicators["power_level"] = value / 10 if value else 0  # Tuya donne en dixièmes
                    
                    # Puissance élevée = suspect triphasé
                    if indicators["power_level"] > self.detection_thresholds['puissance_min_triphase']:
                        indicators["has_high_power"] = True
                        
                elif code == 'add_ele' and value:
                    indicators["energy_level"] = value / 1000 if value else 0  # Tuya donne en millièmes
            
            # Indicateurs faibles
            elif code in self.triphase_indicators['weak_indicators']:
                indicators["has_basic_electrical"] = True
                indicators["electrical_codes_found"].append(code)
        
        # 3. Vérifier données mappées par votre TuyaClient intelligent
        if any(key in mapped_values for key in ['phase_a', 'phase_b', 'phase_c']):
            indicators["has_phase_data"] = True
        
        if mapped_values.get('frequence'):
            indicators["has_frequency"] = True
        
        # Vérifier puissance et énergie dans les valeurs mappées
        puissance = mapped_values.get('puissance', 0)
        if puissance and puissance > self.detection_thresholds['puissance_min_triphase']:
            indicators["has_high_power"] = True
            indicators["power_level"] = max(indicators["power_level"], puissance)
        
        energie = mapped_values.get('energie', 0)
        if energie and energie > self.detection_thresholds['energie_min_triphase']:
            indicators["energy_level"] = max(indicators["energy_level"], energie)
        
        return indicators
    
    def _try_decode_phase_data(self, phase_data_b64):
        """Essayer de décoder les données de phase encodées en base64"""
        try:
            if not phase_data_b64:
                return False
            
            # Décoder base64
            decoded = base64.b64decode(phase_data_b64)
            
            # Les données triphasées sont généralement des structures binaires
            if len(decoded) >= 8:  # Au moins 8 bytes pour des données utiles
                # Essayer de lire comme des floats/ints
                try:
                    # Format courant ATORCH : floats de 4 bytes
                    if len(decoded) >= 12:  # 3 valeurs de 4 bytes
                        values = struct.unpack('>3f', decoded[:12])  # Big endian floats
                        # Vérifier si les valeurs sont réalistes pour électricité
                        if all(0 < v < 1000 for v in values):  # Entre 0 et 1000 (V, A, W...)
                            return True
                except:
                    pass
                
                # Autres formats possibles
                try:
                    # Format entiers
                    if len(decoded) >= 6:  # 3 valeurs de 2 bytes
                        values = struct.unpack('>3H', decoded[:6])  # Big endian unsigned shorts
                        if all(0 < v < 65000 for v in values):
                            return True
                except:
                    pass
            
            return len(decoded) > 0  # Au moins quelque chose de décodé
            
        except Exception as e:
            return False
    
    def _calculate_confidence_score(self, indicators):
        """Calculer un score de confiance pour la détection triphasé"""
        score = 0
        
        # Poids des différents indicateurs
        weights = {
            "has_phase_codes": 40,      # Fort indicateur (données phase_a/b/c)
            "has_phase_data": 25,       # Indicateur moyen
            "has_triphase_energy": 20,  # Énergie totale
            "has_frequency": 15,        # Fréquence réseau
            "has_high_power": 15,       # Puissance élevée
            "device_name_hints": 10,    # Nom suggère triphasé
            "has_power_data": 5,        # Données de puissance
            "has_basic_electrical": 2   # Données électriques basiques
        }
        
        # Calculer score de base
        for indicator, weight in weights.items():
            if indicators.get(indicator):
                score += weight
        
        # Bonus pour combinaisons spéciales
        if indicators.get("has_phase_codes") and indicators.get("has_frequency"):
            score += 15  # Combinaison très forte
        
        if indicators.get("has_triphase_energy") and indicators.get("has_high_power"):
            score += 10  # Énergie + puissance élevée
        
        # Bonus pour nom d'appareil
        name_hint_strength = indicators.get("name_hint_strength")
        if name_hint_strength == "strong":
            score += 20
        elif name_hint_strength == "medium":
            score += 10
        
        # Bonus pour codes multiples
        triphase_codes_count = len(indicators.get("triphase_codes_found", []))
        if triphase_codes_count >= 3:
            score += 15
        elif triphase_codes_count >= 2:
            score += 8
        
        # Bonus pour puissance/énergie élevée
        power_level = indicators.get("power_level", 0)
        if power_level > 10000:  # > 10kW
            score += 15
        elif power_level > 5000:  # > 5kW
            score += 10
        elif power_level > 3000:  # > 3kW
            score += 5
        
        energy_level = indicators.get("energy_level", 0)
        if energy_level > 100:  # > 100kWh
            score += 10
        elif energy_level > 50:  # > 50kWh
            score += 5
        
        # Malus pour indicateurs faibles seuls
        if (indicators.get("has_basic_electrical") and 
            not any([indicators.get("has_phase_data"), indicators.get("has_triphase_energy"), 
                    indicators.get("has_frequency"), indicators.get("has_high_power")])):
            score = max(0, score - 10)
        
        return min(100, score)  # Cap à 100%
    
    def _extract_key_indicators(self, indicators):
        """Extraire les indicateurs clés pour le rapport"""
        key_indicators = []
        
        if indicators.get("has_phase_codes"):
            key_indicators.append("Données phases A/B/C détectées")
        
        if indicators.get("has_triphase_energy"):
            key_indicators.append("Compteur d'énergie triphasé")
        
        if indicators.get("has_frequency"):
            key_indicators.append("Mesure fréquence réseau")
        
        if indicators.get("has_high_power"):
            power = indicators.get("power_level", 0)
            key_indicators.append(f"Puissance élevée ({power:.0f}W)")
        
        if indicators.get("device_name_hints"):
            key_indicators.append("Nom d'appareil suggestif")
        
        codes_found = indicators.get("triphase_codes_found", [])
        if codes_found:
            key_indicators.append(f"Codes Tuya triphasés: {', '.join(codes_found[:3])}")
        
        if not key_indicators:
            key_indicators.append("Données électriques basiques")
        
        return key_indicators
    
    def _get_device_recommendation(self, analysis, existing_device):
        """Obtenir une recommandation pour l'appareil"""
        if not analysis.get("success"):
            return "Erreur d'analyse - vérification manuelle requise"
        
        detected_type = analysis["detected_type"]
        confidence = analysis["confidence"]
        
        if detected_type == "triphase":
            if confidence >= 80:
                if existing_device and existing_device.type_systeme != "triphase":
                    return "🔄 Mise à jour vers triphasé recommandée (haute confiance)"
                else:
                    return "✅ Appareil triphasé confirmé"
            elif confidence >= 60:
                return "⚠️ Probablement triphasé - vérification recommandée"
        elif detected_type == "monophase":
            if existing_device and existing_device.type_systeme == "triphase":
                return "🔍 Vérifier configuration - détecté comme monophasé"
            else:
                return "✅ Appareil monophasé confirmé"
        else:
            return "❓ Type indéterminé - analyse manuelle requise"
        
        return "✅ Configuration actuelle appropriée"
    
    def _generate_recommendations(self, triphase_devices, monophase_devices, unknown_count):
        """Générer des recommandations globales"""
        recommendations = []
        
        if triphase_devices:
            high_confidence = [d for d in triphase_devices if d["confidence"] >= 80]
            medium_confidence = [d for d in triphase_devices if 60 <= d["confidence"] < 80]
            
            if high_confidence:
                recommendations.append(
                    f"🔧 {len(high_confidence)} appareils triphasés détectés avec haute confiance - Configuration recommandée"
                )
            
            if medium_confidence:
                recommendations.append(
                    f"⚠️ {len(medium_confidence)} appareils probablement triphasés - Vérification manuelle suggérée"
                )
            
            needs_update = [d for d in triphase_devices if d.get("needs_update")]
            if needs_update:
                recommendations.append(
                    f"🔄 {len(needs_update)} appareils nécessitent une mise à jour de type en base"
                )
        
        if unknown_count > 2:
            recommendations.append(
                f"❓ {unknown_count} appareils de type indéterminé - Investigation manuelle suggérée"
            )
        
        if not recommendations:
            recommendations.append("✅ Aucune action particulière requise")
        
        return recommendations
    
    def _apply_detection_updates(self, detection_results):
        """Appliquer les mises à jour détectées en base de données"""
        update_results = {
            "updated_count": 0,
            "error_count": 0,
            "details": []
        }
        
        try:
            for result in detection_results:
                if result.get("needs_update") and result.get("confidence", 0) >= 60:
                    device_id = result["device_id"]
                    detected_type = result["detected_type"]
                    
                    try:
                        device = Device.get_by_tuya_id(device_id)
                        if device:
                            old_type = device.type_systeme
                            device.type_systeme = detected_type
                            
                            # Configurer seuils triphasés si nécessaire
                            if detected_type == "triphase":
                                device.set_seuils_triphase(
                                    tensions_min={'L1': 200.0, 'L2': 200.0, 'L3': 200.0},
                                    tensions_max={'L1': 250.0, 'L2': 250.0, 'L3': 250.0},
                                    courants_max={'L1': 20.0, 'L2': 20.0, 'L3': 20.0},
                                    desequilibre_tension=2.0,
                                    desequilibre_courant=10.0,
                                    facteur_puissance_min=0.85
                                )
                            
                            db.session.commit()
                            
                            update_results["updated_count"] += 1
                            update_results["details"].append({
                                "device_id": device_id,
                                "name": result["name"],
                                "old_type": old_type,
                                "new_type": detected_type,
                                "confidence": result["confidence"]
                            })
                            
                            print(f"   ✅ {result['name']}: {old_type} → {detected_type}")
                        
                    except Exception as e:
                        db.session.rollback()
                        update_results["error_count"] += 1
                        print(f"   ❌ Erreur mise à jour {result['name']}: {e}")
            
        except Exception as e:
            print(f"❌ Erreur globale mise à jour: {e}")
        
        return update_results
    
    def _get_tuya_client_stats(self):
        """Récupérer les statistiques du TuyaClient"""
        try:
            if hasattr(self.tuya_client, 'get_connection_info'):
                return self.tuya_client.get_connection_info()
            else:
                return {
                    "connected": self.tuya_client.is_connected_method() if hasattr(self.tuya_client, 'is_connected_method') else True,
                    "client_type": "TuyaClient intelligent"
                }
        except:
            return {"status": "unknown"}
    
    # ✅ MÉTHODES SUPPLÉMENTAIRES POUR COMPATIBILITÉ
    
    def detect_all_triphase_devices(self, force_update=False, save_to_db=True):
        """Alias pour compatibilité - redirige vers get_detection_report"""
        return self.get_detection_report(save_to_db=save_to_db)
    
    def detect_single_device(self, device_id):
        """Détecter le type d'un appareil spécifique"""
        try:
            analysis = self._analyze_single_device(device_id, device_id)
            
            if analysis["success"]:
                return {
                    "success": True,
                    "device_id": device_id,
                    "detected_type": analysis["detected_type"],
                    "confidence": analysis["confidence"],
                    "indicators": analysis["indicators"],
                    "recommendation": self._get_device_recommendation(analysis, None)
                }
            else:
                return analysis
                
        except Exception as e:
            return {"success": False, "error": str(e)}


# =================== FONCTIONS UTILITAIRES POUR VOTRE TEST ===================

def create_detection_service(tuya_client):
    """✅ Factory pour créer le service de détection - Compatible avec votre test"""
    return TriphaseDetectionService(tuya_client)

def test_detection_simple_standalone():
    """✅ Test autonome si appelé directement"""
    try:
        from app import create_app
        from app.services.tuya_service import TuyaClient
        
        app = create_app()
        with app.app_context():
            tuya_client = TuyaClient()
            if not tuya_client.auto_connect_from_env():
                print("❌ Connexion Tuya impossible")
                return False
            
            detector = TriphaseDetectionService(tuya_client)
            report = detector.get_detection_report()
            
            if report.get("success"):
                print(f"✅ Test réussi:")
                print(f"   Total: {report['summary']['total_devices']}")
                print(f"   Triphasés: {report['summary']['triphase_detected']}")
                print(f"   Monophasés: {report['summary']['monophase_detected']}")
                return True
            else:
                print(f"❌ Test échoué: {report.get('error')}")
                return False
                
    except Exception as e:
        print(f"❌ Erreur test: {e}")
        return False






if __name__ == "__main__":
    # Test autonome
    test_detection_simple_standalone()