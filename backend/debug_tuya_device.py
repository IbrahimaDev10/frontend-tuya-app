import os
import time
import hashlib
import hmac
import json
import requests
from dotenv import load_dotenv

# --- Fonctions de base pour l'API Tuya (inchangées) ---

def get_timestamp():
    return str(int(time.time() * 1000))

def generate_sign(access_id, access_secret, timestamp, method, path, query="", body="", access_token=""):
    content_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    headers_to_sign = ""
    url_path = path
    if query:
        url_path += f"?{query}"
    
    string_to_sign_parts = [method, content_hash, headers_to_sign, url_path]
    string_to_sign = "\n".join(string_to_sign_parts)
    
    final_string = f"{access_id}"
    if access_token:
        final_string += access_token
    final_string += f"{timestamp}{string_to_sign}"
    
    signature = hmac.new(
        access_secret.encode('utf-8'),
        final_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()
    
    return signature

def make_tuya_request(endpoint, access_id, access_secret, method, path, query="", body="", access_token=""):
    timestamp = get_timestamp()
    signature = generate_sign(access_id, access_secret, timestamp, method, path, query, body, access_token)
    
    headers = {
        'client_id': access_id,
        'sign': signature,
        't': timestamp,
        'sign_method': 'HMAC-SHA256',
        'Content-Type': 'application/json'
    }
    
    if access_token:
        headers['access_token'] = access_token
    
    url = f"{endpoint}{path}"
    if query:
        url += f"?{query}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=body)
        else:
            raise ValueError(f"Méthode HTTP non supportée: {method}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de requête vers {method} {path}: {e}")
        if e.response:
            print(f"   Réponse de l'API: {e.response.text}")
        return None

# --- Fonctions principales du script de débogage ---

def get_access_token(endpoint, access_id, access_secret):
    print("1. Récupération du token d'accès...")
    response = make_tuya_request(endpoint, access_id, access_secret, "GET", "/v1.0/token", "grant_type=1")
    if response and response.get('success'):
        print("   ✅ Token obtenu avec succès !")
        return response['result']['access_token']
    else:
        print("   ❌ Échec de la récupération du token.")
        if response:
            print(f"      Message d'erreur: {response.get('msg')}")
        return None

def get_all_devices(endpoint, access_id, access_secret, access_token):
    print("\n2. Récupération de la liste de vos appareils...")
    
    path = "/v2.0/cloud/thing/device"
    query = "page_size=20"
    
    response = make_tuya_request(endpoint, access_id, access_secret, "GET", path, query=query, access_token=access_token)
    
    if response and response.get('success'):
        # =========================================================================
        # === CORRECTION FINALE : La réponse est une liste directement dans 'result'
        # =========================================================================
        devices = response.get('result', [])
        
        # Vérification supplémentaire pour s'assurer que 'devices' est bien une liste
        if not isinstance(devices, list):
             print(f"   ❌ Erreur: la réponse attendue était une liste, mais nous avons reçu un {type(devices)}.")
             print(f"      Réponse complète: {response}")
             return []

        print(f"   ✅ {len(devices)} appareil(s) trouvé(s).")
        return devices
    else:
        print("   ❌ Échec de la récupération des appareils.")
        if response:
            print(f"      Message d'erreur: {response.get('msg')}")
        return []

def get_device_status(endpoint, access_id, access_secret, access_token, device_id):
    print(f"\n4. Récupération du statut détaillé pour l'appareil {device_id}...")
    path = f"/v1.0/devices/{device_id}/status"
    response = make_tuya_request(endpoint, access_id, access_secret, "GET", path, access_token=access_token)
    if response and response.get('success'):
        print("   ✅ Statut récupéré avec succès !")
        return response.get('result', [])
    else:
        print("   ❌ Échec de la récupération du statut.")
        if response:
            print(f"      Message d'erreur: {response.get('msg')}")
        return []

def main():
    print("=============================================")
    print("=   Script de Débogage des Appareils Tuya   =")
    print("=          (Version Finale v3)            =")
    print("=============================================\n")
    
    load_dotenv()
    access_id = os.getenv('ACCESS_ID')
    access_secret = os.getenv('ACCESS_KEY')
    endpoint = os.getenv('TUYA_ENDPOINT')

    if not all([access_id, access_secret, endpoint]):
        print("❌ Erreur: Assurez-vous que les variables ACCESS_ID et ACCESS_KEY sont à jour et que TUYA_ENDPOINT est défini dans .env")
        return

    token = get_access_token(endpoint, access_id, access_secret)
    if not token:
        return

    devices = get_all_devices(endpoint, access_id, access_secret, token)
    if not devices:
        return

    print("\n3. Veuillez choisir l'appareil à inspecter :\n")
    for i, device in enumerate(devices):
        # La structure de l'objet device est différente ici
        online_status = "🟢 En ligne" if device.get('isOnline', False) else "🔴 Hors ligne"
        print(f"   [{i}] - {device.get('name', 'Nom inconnu')} ({online_status}) - ID: {device.get('id')}")

    try:
        choice_index = int(input("\n   Entrez le numéro de l'appareil : "))
        if not 0 <= choice_index < len(devices):
            print("❌ Choix invalide.")
            return
        chosen_device = devices[choice_index]
    except (ValueError, IndexError):
        print("❌ Entrée invalide. Veuillez entrer un numéro de la liste.")
        return

    device_id = chosen_device.get('id')
    status_list = get_device_status(endpoint, access_id, access_secret, token, device_id)

    if status_list:
        print("\n================ RÉSULTAT DE L'INSPECTION ================")
        print(f"Appareil: {chosen_device.get('name')}")
        print(f"ID: {device_id}")
        print("----------------------------------------------------------")
        print("Voici tous les codes de statut et leurs valeurs actuelles :")
        
        for status in status_list:
            code = status.get('code')
            value = status.get('value')
            print(f"   - Code: {code:<20} | Valeur: {value}")
        
        print("----------------------------------------------------------")
        print("\n🔍 ACTION REQUISE :")
        print("Recherchez dans la liste ci-dessus le code qui semble contrôler l'état ON/OFF de votre appareil triphasé.")
        print("Une fois trouvé, ajoutez ce nom de code à la liste 'switch_candidates' dans votre fichier 'tuya_service.py'.")
        print("==========================================================")
    else:
        print("\nImpossible d'afficher les détails du statut pour cet appareil.")

if __name__ == "__main__":
    main()
