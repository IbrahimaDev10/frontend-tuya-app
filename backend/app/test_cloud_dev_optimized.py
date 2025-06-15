#!/usr/bin/env python3
# quick_test.py - Test rapide avec la bonne page_size

import os
import time
import hashlib
import hmac
import requests
from dotenv import load_dotenv

def get_timestamp():
    return str(int(time.time() * 1000))

def generate_sign(access_id, access_secret, timestamp, method, path, query="", body="", access_token=""):
    content_hash = hashlib.sha256(body.encode()).hexdigest()
    headers_to_sign = ""
    
    url_path = path
    if query:
        url_path += f"?{query}"
    
    string_to_sign = f"{method}\n{content_hash}\n{headers_to_sign}\n{url_path}"
    
    final_string = f"{access_id}"
    if access_token:
        final_string += access_token
    final_string += f"{timestamp}{string_to_sign}"
    
    signature = hmac.new(
        access_secret.encode(),
        final_string.encode(),
        hashlib.sha256
    ).hexdigest().upper()
    
    return signature

def main():
    print("🚀 TEST RAPIDE TUYA - PAGE_SIZE=10")
    print("=" * 40)
    
    load_dotenv()
    
    access_id = os.getenv('ACCESS_ID')
    access_secret = os.getenv('ACCESS_KEY')
    endpoint = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com')
    
    # ÉTAPE 1: Token
    print("🔧 Obtention token...")
    timestamp = get_timestamp()
    signature = generate_sign(access_id, access_secret, timestamp, "GET", "/v1.0/token", "grant_type=1")
    
    headers = {
        'client_id': access_id,
        'sign': signature,
        't': timestamp,
        'sign_method': 'HMAC-SHA256',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(f"{endpoint}/v1.0/token?grant_type=1", headers=headers)
    token_data = response.json()
    
    if not token_data.get('success'):
        print(f"❌ Erreur token: {token_data}")
        return
    
    access_token = token_data['result']['access_token']
    print(f"✅ Token: {access_token[:20]}...")
    
    # ÉTAPE 2: Appareils avec page_size=10
    print("🔧 Récupération appareils (page_size=10)...")
    timestamp2 = get_timestamp()
    signature2 = generate_sign(access_id, access_secret, timestamp2, "GET", "/v2.0/cloud/thing/device", "page_size=10", "", access_token)
    
    headers2 = {
        'client_id': access_id,
        'access_token': access_token,
        'sign': signature2,
        't': timestamp2,
        'sign_method': 'HMAC-SHA256',
        'Content-Type': 'application/json'
    }
    
    response2 = requests.get(f"{endpoint}/v2.0/cloud/thing/device?page_size=10", headers=headers2)
    devices_data = response2.json()
    
    print(f"📱 Response: {devices_data}")
    
    if devices_data.get('success') and devices_data.get('result'):
        devices = devices_data['result']
        print(f"\n🎉 SUCCÈS ! {len(devices)} appareils trouvés:")
        
        for i, device in enumerate(devices, 1):
            name = device.get('name', 'Sans nom')
            device_id = device.get('id', device.get('device_id', 'Sans ID'))
            online = "🟢" if device.get('isOnline') else "🔴"
            print(f"   {i:2d}. {online} {name} - {device_id}")
        
        print(f"\n✅ Votre TuyaClient devrait maintenant fonctionner parfaitement !")
    else:
        print(f"❌ Erreur: {devices_data}")

if __name__ == "__main__":
    main()