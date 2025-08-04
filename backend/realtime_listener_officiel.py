# realtime_listener_officiel.py
# CORRIGÉ v10 - Correction de l'AttributeError en transformant le dict en objet

import logging
import json
import os
import time
import hashlib
import hmac
import requests
from dotenv import load_dotenv
from types import SimpleNamespace  # <-- On importe SimpleNamespace
from tuya_iot import (
    TuyaOpenAPI,
    TuyaOpenMQ,
    TUYA_LOGGER,
)

# --- Fonctions de requête locales (inchangées) ---
def get_timestamp():
    return str(int(time.time() * 1000))

def generate_sign_fixed(access_id, access_secret, timestamp, method, path, query="", body="", access_token=""):
    # ... (code de la fonction inchangé)
    content_hash = hashlib.sha256(body.encode()).hexdigest()
    headers_to_sign = ""
    string_to_sign = f"{method}\n{content_hash}\n{headers_to_sign}\n{path}"
    if query:
        string_to_sign += f"?{query}"
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

def make_tuya_request_fixed(endpoint, access_id, access_secret, method, path, query="", body="", access_token=""):
    # ... (code de la fonction inchangé)
    timestamp = get_timestamp()
    signature = generate_sign_fixed(access_id, access_secret, timestamp, method, path, query, body, access_token)
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
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, data=body)
    else:
        raise ValueError(f"Méthode HTTP non supportée: {method}")
    return response.json()

# --- Configuration ---
load_dotenv()
ACCESS_ID = os.getenv('ACCESS_ID')
ACCESS_KEY = os.getenv('ACCESS_KEY')
API_ENDPOINT = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com' )

TUYA_LOGGER.setLevel(logging.INFO)

# --- Programme principal ---

openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)

try:
    print("🔧 Utilisation de la fonction de requête locale pour obtenir le token...")
    response = make_tuya_request_fixed(
        API_ENDPOINT,
        ACCESS_ID,
        ACCESS_KEY,
        "GET",
        "/v1.0/token",
        "grant_type=1"
    )
    
    if not response.get("success"):
        raise Exception(f"Échec de l'obtention du token : {response}")
    
    # --- CORRECTION FINALE ---
    # On transforme le dictionnaire 'result' en un objet SimpleNamespace.
    # Cela permet d'accéder aux clés comme des attributs (result.uid au lieu de result['uid'])
    openapi.token_info = json.loads(json.dumps(response["result"]), object_hook=lambda d: SimpleNamespace(**d))
    
    print("✅ Token obtenu et informations chargées avec succès.")
    print(f"   UID récupéré : {openapi.token_info.uid}") # On peut maintenant utiliser la notation .uid

except Exception as e:
    print(f"❌ Erreur lors de l'initialisation de l'API : {e}.")
    exit()

# 2. Initialisation du client Message Queue (MQ)
open_mq = TuyaOpenMQ(openapi)

# 3. Définir la fonction de rappel
def on_message(msg):
    print("-" * 60)
    print(f"📩 MESSAGE EN TEMPS RÉEL REÇU !")
    try:
        message_data = json.loads(msg)
        print(json.dumps(message_data, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"Erreur lors du formatage du message : {e}")
        print(f"Message brut reçu : {msg}")
    print("-" * 60)

# 4. Attacher la fonction de rappel
open_mq.add_message_listener(on_message)

# 5. Démarrer l'écoute
print("\n🚀 Démarrage de l'écoute des messages en temps réel...")
print("   Le système est prêt. Modifiez l'état d'un appareil pour voir les messages.")
print("   (Utilisez Ctrl+C pour arrêter le script)")
open_mq.start()
