#!/usr/bin/env python3
# test_tuya_debug.py

import os
from dotenv import load_dotenv

# Importer votre nouveau TuyaClient
from app.services.tuya_service import TuyaClient, test_tuya_complete

def debug_tuya_step_by_step():
    """Debug étape par étape pour identifier le problème"""
    print("🔍 === DEBUG TUYA ÉTAPE PAR ÉTAPE ===")
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Vérifier les variables
    access_id = os.getenv('ACCESS_ID')
    access_key = os.getenv('ACCESS_KEY')
    endpoint = os.getenv('TUYA_ENDPOINT')
    
    print(f"🔧 Configuration détectée:")
    print(f"   ACCESS_ID: {access_id}")
    print(f"   ACCESS_KEY: {access_key[:20]}..." if access_key else "None")
    print(f"   ENDPOINT: {endpoint}")
    
    if not access_id or not access_key:
        print("❌ Configuration manquante dans .env")
        return False
    
    # Test du client
    print("\n🧪 Test du TuyaClient...")
    client = TuyaClient()
    
    # Test token
    print("\n1️⃣ Test récupération token...")
    token_success = client.get_access_token()
    
    if not token_success:
        print("❌ Échec récupération token")
        return False
    
    print(f"✅ Token récupéré: {client.access_token[:20]}...")
    
    # Test simple récupération appareils
    print("\n2️⃣ Test récupération appareils...")
    devices_result = client.get_devices()
    
    if devices_result.get("success"):
        devices = devices_result.get("result", [])
        print(f"✅ {len(devices)} appareils récupérés avec succès")
        
        # Afficher quelques infos sur les appareils
        for i, device in enumerate(devices[:3]):  # Premiers 3 appareils
            print(f"   📱 Appareil {i+1}: {device.get('name', 'Sans nom')} ({device.get('id', 'Sans ID')})")
        
        return True
    else:
        error = devices_result.get("error", "Erreur inconnue")
        print(f"❌ Erreur récupération appareils: {error}")
        return False

def test_manually():
    """Test manuel avec vos vraies credentials"""
    print("🧪 === TEST MANUEL AVEC VRAIES CREDENTIALS ===")
    
    # Test avec vos vraies valeurs
    from app.services.tuya_service import make_tuya_request_fixed
    
    access_id = "cqg5gcysw5xcvachq8tr"
    access_secret = "b69149fe97e94518b71b9f44a367b427"
    endpoint = "https://openapi.tuyaeu.com"
    
    print("1️⃣ Test récupération token...")
    
    token_response = make_tuya_request_fixed(
        endpoint, 
        access_id, 
        access_secret, 
        "GET", 
        "/v1.0/token", 
        "grant_type=1"
    )
    
    print(f"📊 Réponse token: {token_response}")
    
    if token_response.get('success'):
        access_token = token_response['result']['access_token']
        print(f"✅ Token obtenu: {access_token[:20]}...")
        
        print("\n2️⃣ Test récupération appareils...")
        
        devices_response = make_tuya_request_fixed(
            endpoint,
            access_id,
            access_secret,
            "GET",
            "/v2.0/cloud/thing/device",
            {"page_size": 5, "page_no": 1},  # ✅ Format dict
            "",
            access_token
        )

        
        print(f"📊 Réponse appareils: {devices_response}")
        
        if devices_response.get('success'):
            devices = devices_response.get('result', [])
            print(f"✅ {len(devices)} appareils récupérés")
            return True
        else:
            print(f"❌ Erreur appareils: {devices_response.get('msg', 'Inconnue')}")
            return False
    else:
        print(f"❌ Erreur token: {token_response.get('msg', 'Inconnue')}")
        return False

if __name__ == "__main__":
    print("🚀 Démarrage tests Tuya...")
    
    # Test 1: Debug étape par étape
    success1 = debug_tuya_step_by_step()
    
    print("\n" + "="*50)
    
    # Test 2: Test manuel
    success2 = test_manually()
    
    print("\n" + "="*50)
    
    # Test 3: Test complet
    print("🧪 === TEST COMPLET ===")
    success3 = test_tuya_complete()
    
    print(f"\n📊 Résultats finaux:")
    print(f"   Debug étape par étape: {'✅' if success1 else '❌'}")
    print(f"   Test manuel: {'✅' if success2 else '❌'}")
    print(f"   Test complet: {'✅' if success3 else '❌'}")
    
    if success1 and success2 and success3:
        print("\n🎉 Tous les tests réussis ! Le problème est résolu.")
    else:
        print("\n⚠️ Certains tests ont échoué. Vérifiez les logs ci-dessus.")