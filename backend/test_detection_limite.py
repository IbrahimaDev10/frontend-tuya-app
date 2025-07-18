# test_detection_limite.py - VERSION LIMITÉE
from app.services.tuya_service import TuyaClient
from app.services.triphase_detection_service import TriphaseDetectionService

def test_detection_limitee():
    """Test de détection sur 50 premiers appareils seulement"""
    
    # 1. Connexion Tuya
    tuya_client = TuyaClient()
    if not tuya_client.auto_connect_from_env():
        print("❌ Connexion Tuya impossible")
        return
    
    # 2. Service de détection
    detector = TriphaseDetectionService(tuya_client)
    
    # 3. MODIFICATION : Limiter à 50 appareils
    print("📋 Test sur les 50 premiers appareils seulement...")
    
    # Récupérer tous les appareils
    devices_result = tuya_client.get_all_devices_with_details()
    if not devices_result.get("success"):
        print(f"❌ Erreur: {devices_result.get('error')}")
        return
    
    all_devices = devices_result.get("result", [])
    
    # ✅ LIMITER À 50 pour le test
    limited_devices = all_devices[:50]
    print(f"🔍 Analyse de {len(limited_devices)} appareils (au lieu de {len(all_devices)})")
    
    # Analyser chaque appareil
    triphase_found = []
    monophase_found = []
    
    for i, device in enumerate(limited_devices):
        device_id = device.get("id")
        device_name = device.get("name", "Inconnu")
        
        print(f"\n📱 {i+1}/{len(limited_devices)} - {device_name}")
        
        # Analyse
        result = detector._analyze_device_for_triphase(device_id, device_name)
        
        if result.get("success"):
            detected_type = result["detected_type"]
            confidence = result["confidence"]
            
            print(f"   ✅ Type: {detected_type} (confiance: {confidence}%)")
            
            if detected_type == "triphase":
                indicators = result.get("indicators", {})
                triphase_codes = indicators.get("triphase_codes_found", [])
                
                triphase_found.append({
                    'name': device_name,
                    'id': device_id,
                    'confidence': confidence,
                    'codes': triphase_codes
                })
                print(f"   🔌 Codes triphasés: {', '.join(triphase_codes)}")
            elif detected_type == "monophase":
                monophase_found.append(device_name)
        else:
            print(f"   ❌ Erreur: {result.get('error')}")
    
    # Résumé final
    print(f"\n🎯 === RÉSUMÉ SUR {len(limited_devices)} APPAREILS ===")
    print(f"✅ Triphasés détectés: {len(triphase_found)}")
    print(f"📱 Monophasés détectés: {len(monophase_found)}")
    
    if triphase_found:
        print(f"\n🔌 DÉTAIL DES TRIPHASÉS:")
        for device in triphase_found:
            print(f"   📊 {device['name']} (confiance: {device['confidence']}%)")
            print(f"      Codes: {', '.join(device['codes'])}")
    
    print(f"\n📊 PROJECTION SUR {len(all_devices)} APPAREILS:")
    projection_triphase = int((len(triphase_found) / len(limited_devices)) * len(all_devices))
    print(f"   Estimation triphasés total: ~{projection_triphase}")
    
    return triphase_found

if __name__ == "__main__":
    test_detection_limitee()