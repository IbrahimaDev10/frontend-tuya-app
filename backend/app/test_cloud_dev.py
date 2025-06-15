#!/usr/bin/env python3
# test_cloud_dev.py - Test approche Cloud Development Tuya

import os
import time
import hashlib
import hmac
import json
import requests
from dotenv import load_dotenv

def get_timestamp():
    """Timestamp pour l'API Tuya"""
    return str(int(time.time() * 1000))

def generate_sign(access_id, access_secret, timestamp, method, path, query="", body="", access_token=""):
    """Générer la signature Tuya (corrigée)"""
    # Construction du string à signer
    content_hash = hashlib.sha256(body.encode()).hexdigest()
    
    # Headers à inclure dans la signature
    headers_to_sign = ""
    
    # Construction de l'URL complète
    url_path = path
    if query:
        url_path += f"?{query}"
    
    # String to sign format: method + "\n" + content-sha256 + "\n" + headers + "\n" + url
    string_to_sign = f"{method}\n{content_hash}\n{headers_to_sign}\n{url_path}"
    
    # Ajouter client_id, access_token (si présent) et timestamp
    final_string = f"{access_id}"
    if access_token:
        final_string += access_token
    final_string += f"{timestamp}{string_to_sign}"
    
    print(f"   🔍 String to sign: {final_string}")
    
    # Génération de la signature HMAC-SHA256
    signature = hmac.new(
        access_secret.encode(),
        final_string.encode(),
        hashlib.sha256
    ).hexdigest().upper()
    
    return signature

def test_tuya_cloud_api():
    """Test direct de l'API Cloud Tuya"""
    
    print("🚀 TEST API CLOUD TUYA DIRECTE")
    print("=" * 50)
    
    load_dotenv()
    
    access_id = os.getenv('ACCESS_ID')
    access_secret = os.getenv('ACCESS_KEY')
    endpoint = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com')
    
    print(f"📋 Configuration:")
    print(f"   Access ID: {access_id[:10]}...")
    print(f"   Endpoint: {endpoint}")
    print()
    
    # ÉTAPE 1: Obtenir un token direct via l'API Cloud
    print("🔧 ÉTAPE 1: Obtenir token Cloud")
    
    timestamp = get_timestamp()
    method = "GET"
    path = "/v1.0/token"
    query = f"grant_type=1"
    
    signature = generate_sign(access_id, access_secret, timestamp, method, path, query)
    
    headers = {
        'client_id': access_id,
        'sign': signature,
        't': timestamp,
        'sign_method': 'HMAC-SHA256',
        'Content-Type': 'application/json'
    }
    
    url = f"{endpoint}{path}?{query}"
    
    try:
        response = requests.get(url, headers=headers)
        token_data = response.json()
        print(f"   📊 Token response: {token_data}")
        
        if token_data.get('success') and token_data.get('result'):
            access_token = token_data['result']['access_token']
            print(f"   ✅ Token obtenu: {access_token[:20]}...")
            
            # ÉTAPE 2: Lister les appareils avec le token
            print(f"\n🔧 ÉTAPE 2: Lister appareils avec token")
            
            timestamp2 = get_timestamp()
            path2 = "/v1.0/devices"
            signature2 = generate_sign(access_id, access_secret, timestamp2, "GET", path2, access_token=access_token)
            
            headers2 = {
                'client_id': access_id,
                'access_token': access_token,
                'sign': signature2,
                't': timestamp2,
                'sign_method': 'HMAC-SHA256',
                'Content-Type': 'application/json'
            }
            
            url2 = f"{endpoint}{path2}"
            
            response2 = requests.get(url2, headers=headers2)
            devices_data = response2.json()
            print(f"   📱 Devices response: {devices_data}")
            
            if devices_data.get('success') and devices_data.get('result'):
                devices = devices_data['result']
                print(f"   🎯 APPAREILS TROUVÉS: {len(devices)}")
                for i, device in enumerate(devices[:5]):
                    print(f"      {i+1}. {device.get('name', 'Sans nom')} - {device.get('id', 'Sans ID')}")
            else:
                # ÉTAPE 3: Essayer avec l'UID récupéré
                uid = token_data['result']['uid']
                print(f"\n🔧 ÉTAPE 3: Homes pour UID {uid}")
                
                timestamp3 = get_timestamp()
                path3 = f"/v1.0/users/{uid}/homes"
                signature3 = generate_sign(access_id, access_secret, timestamp3, "GET", path3, access_token=access_token)
                
                headers3 = {
                    'client_id': access_id,
                    'access_token': access_token,
                    'sign': signature3,
                    't': timestamp3,
                    'sign_method': 'HMAC-SHA256',
                    'Content-Type': 'application/json'
                }
                
                url3 = f"{endpoint}{path3}"
                
                response3 = requests.get(url3, headers=headers3)
                homes_data = response3.json()
                print(f"   🏠 Homes response: {homes_data}")
                
                if homes_data.get('success') and homes_data.get('result'):
                    homes = homes_data['result']
                    print(f"   🏠 Homes trouvés: {len(homes)}")
                    
                    # Pour chaque home, récupérer les appareils
                    for home in homes:
                        home_id = home.get('home_id')
                        home_name = home.get('name', 'Sans nom')
                        print(f"   🏠 Home: {home_name} ({home_id})")
                        
                        # Devices pour ce home
                        timestamp4 = get_timestamp()
                        path4 = f"/v1.0/homes/{home_id}/devices"
                        signature4 = generate_sign(access_id, access_secret, timestamp4, "GET", path4, access_token=access_token)
                        
                        headers4 = {
                            'client_id': access_id,
                            'access_token': access_token,
                            'sign': signature4,
                            't': timestamp4,
                            'sign_method': 'HMAC-SHA256',
                            'Content-Type': 'application/json'
                        }
                        
                        url4 = f"{endpoint}{path4}"
                        
                        response4 = requests.get(url4, headers=headers4)
                        home_devices_data = response4.json()
                        print(f"      📱 Devices home response: {home_devices_data}")
                        
                        if home_devices_data.get('success') and home_devices_data.get('result'):
                            home_devices = home_devices_data['result']
                            print(f"      🎯 APPAREILS DANS {home_name}: {len(home_devices)}")
                            for i, device in enumerate(home_devices[:5]):
                                device_name = device.get('name', 'Sans nom')
                                device_id = device.get('id', 'Sans ID')
                                print(f"         {i+1}. {device_name} - {device_id}")
                else:
                    # ÉTAPE 4: Endpoint alternatif
                    print(f"\n🔧 ÉTAPE 4: Endpoint alternatif /v2.0/cloud/thing/device")
                    
                    timestamp5 = get_timestamp()
                    path5 = "/v2.0/cloud/thing/device"
                    query5 = "page_size=100"
                    signature5 = generate_sign(access_id, access_secret, timestamp5, "GET", path5, query5, access_token=access_token)
                    
                    headers5 = {
                        'client_id': access_id,
                        'access_token': access_token,
                        'sign': signature5,
                        't': timestamp5,
                        'sign_method': 'HMAC-SHA256',
                        'Content-Type': 'application/json'
                    }
                    
                    url5 = f"{endpoint}{path5}?{query5}"
                    
                    response5 = requests.get(url5, headers=headers5)
                    alt_devices_data = response5.json()
                    print(f"   📱 Alt devices response: {alt_devices_data}")
                    
                    if alt_devices_data.get('success') and alt_devices_data.get('result'):
                        alt_devices = alt_devices_data['result']
                        print(f"   🎯 APPAREILS (ALT): {len(alt_devices)}")
                        for i, device in enumerate(alt_devices[:5]):
                            print(f"      {i+1}. {device.get('name', 'Sans nom')} - {device.get('device_id', 'Sans ID')}")
        else:
            print(f"   ❌ Erreur token: {token_data}")
            
    except Exception as e:
        print(f"❌ Erreur API directe: {e}")
        import traceback
        traceback.print_exc()

def test_with_tuya_iot_alternative():
    """Test avec tuya-iot mais approche différente"""
    
    print(f"\n🔧 TEST AVEC TUYA-IOT ALTERNATIF")
    print("=" * 40)
    
    load_dotenv()
    
    access_id = os.getenv('ACCESS_ID')
    access_secret = os.getenv('ACCESS_KEY')
    endpoint = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com')
    
    try:
        from tuya_iot import TuyaOpenAPI
        
        # Test 1: API sans connexion utilisateur (mode Cloud)
        print("   🧪 Test 1: Mode Cloud pur")
        api = TuyaOpenAPI(endpoint, access_id, access_secret)
        
        # Essayer directement les endpoints sans connect()
        try:
            direct_devices = api.get('/v1.0/devices')
            print(f"   📱 Devices direct: {direct_devices}")
        except Exception as e:
            print(f"   ❌ Devices direct error: {e}")
        
        # Test 2: Forcer l'authentification
        print("\n   🧪 Test 2: Authentification forcée")
        try:
            # Certaines versions de tuya-iot ont une méthode auth()
            if hasattr(api, 'auth'):
                auth_result = api.auth()
                print(f"   🔐 Auth result: {auth_result}")
            
            # Ou une méthode get_access_token()
            if hasattr(api, 'get_access_token'):
                token_result = api.get_access_token()
                print(f"   🎫 Get token result: {token_result}")
                
        except Exception as e:
            print(f"   ❌ Auth error: {e}")
            
    except ImportError:
        print("   ❌ tuya-iot non disponible")

if __name__ == "__main__":
    test_tuya_cloud_api()
    test_with_tuya_iot_alternative()