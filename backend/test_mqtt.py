# test_mqtt_v4.py

import os
import time
import hashlib
import hmac
import json
import requests
import ssl
import base64
import struct
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from Crypto.Cipher import AES

# ==============================================================================
#  PARTIE 1 : CLIENT TUYA AVEC APPEL API CORRIGÉ
# ==============================================================================

class RobustTuyaClient:
    def __init__(self):
        load_dotenv()
        self.access_id = os.getenv('ACCESS_ID')
        self.access_secret = os.getenv('ACCESS_KEY')
        self.endpoint = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com' )
        self.access_token = None
        self.uid = None
        print(f"🔧 Client Tuya Robuste v4 initialisé avec Access ID: {self.access_id[:10]}...")

    def _calculate_sign(self, method, path, query=None, body=None, access_token=""):
        timestamp = str(int(time.time() * 1000))
        # Pour la signature, le body doit être une chaîne JSON vide si None, ou le dump du dict
        body_str = json.dumps(body, separators=(',', ':')) if body else ""
        
        content_hash = hashlib.sha256(body_str.encode('utf-8')).hexdigest()
        
        string_to_sign = f"{method}\n{content_hash}\n\n{path}"
        if query:
            query_str = "&".join(sorted([f"{k}={v}" for k, v in query.items()]))
            string_to_sign += f"?{query_str}"
            
        sign_str = self.access_id + access_token + timestamp + string_to_sign
        signature = hmac.new(self.access_secret.encode('utf-8'), sign_str.encode('utf-8'), hashlib.sha256).hexdigest().upper()
        
        return timestamp, signature

    def _make_request(self, method, path, query=None, body=None):
        access_token = self.access_token or ""
        timestamp, signature = self._calculate_sign(method, path, query, body, access_token)
        
        headers = {
            'client_id': self.access_id,
            'sign': signature,
            't': timestamp,
            'sign_method': 'HMAC-SHA256',
        }
        if access_token:
            headers['access_token'] = access_token
            
        url = f"{self.endpoint}{path}"
        if query:
            url += "?" + "&".join([f"{k}={v}" for k, v in query.items()])
            
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                # --- CORRECTION CLÉ ---
                # On utilise le paramètre 'json' qui gère tout pour nous.
                # On ne met plus 'Content-Type' dans les headers, 'requests' le fait.
                headers['Content-Type'] = 'application/json'
                response = requests.post(url, headers=headers, json=body, timeout=10)
            return response.json()
        except Exception as e:
            print(f"❌ Erreur critique de requête: {e}")
            return {"success": False, "msg": str(e)}

    # Le reste de la classe est inchangé
    def connect(self):
        print("🔑 Tentative de connexion à l'API Tuya...")
        response = self._make_request('GET', '/v1.0/token', query={'grant_type': 1})
        if response and response.get('success'):
            self.access_token = response['result']['access_token']
            self.uid = response['result']['uid']
            print("✅ Connexion API Tuya réussie.")
            return True
        else:
            print(f"❌ Erreur de connexion API Tuya: {response.get('msg')}")
            return False

    def get_mqtt_config(self, target_uid):
        print("🔄 [MQTT] Obtention de la configuration...")
        body = {
            "uid": target_uid,
            "link_id": f"sertec-test-script-{int(time.time())}",
            "topics": "device",
            "msg_encrypted_version": "2.0"
        }
        return self._make_request('POST', '/v1.0/iot-03/open-hub/access-config', body=body)

# ... (Copiez les classes VerattiDecoder et MqttTester du script v3 ici, elles n'ont pas besoin de changer) ...
# ... Pour être sûr, voici le code complet :

# ==============================================================================
#  PARTIE 2 : DÉCODEUR VERATTI (INCHANGÉ)
# ==============================================================================
class VerattiDecoder:
    def __init__(self, debug=True): self.debug = debug
    def _debug_log(self, message: str):
        if self.debug: print(f"[DECODEUR] {message}")
    def decode_phase_simple_data(self, base64_data: str, phase_name: str):
        try:
            bytes_data = base64.b64decode(base64_data)
            if len(bytes_data) < 4: return {'success': False, 'error': 'data_too_short'}
            result = {'success': True, 'tension': round(struct.unpack('>H', bytes_data[0:2])[0] / 10.0, 1), 'courant': round(struct.unpack('>H', bytes_data[2:4])[0] / 1000.0, 3)}
            result['puissance'] = round(result['tension'] * result['courant'] * 0.9, 2)
            return result
        except Exception as e: return {'success': False, 'error': str(e)}
    def decode_phase_detailed_data(self, base64_data: str, phase_name: str):
        try:
            bytes_data = base64.b64decode(base64_data)
            if len(bytes_data) < 14: return {'success': False, 'error': 'data_too_short'}
            result = {'success': True, 'tension': round(struct.unpack('>H', bytes_data[0:2])[0] / 10.0, 1), 'courant': round(int.from_bytes(bytes_data[2:5], 'big') / 1000.0, 3), 'puissance': round(struct.unpack('>H', bytes_data[5:7])[0] / 10.0, 2)}
            return result
        except Exception as e: return {'success': False, 'error': str(e)}

# ==============================================================================
#  PARTIE 3 : LE CLIENT MQTT (INCHANGÉ)
# ==============================================================================
class MqttTester:
    def __init__(self):
        self.tuya_client = RobustTuyaClient()
        self.decoder = VerattiDecoder()
        self.access_secret_bytes = self.tuya_client.access_secret.encode('utf-8')
        self.mqtt_client = None
        self.config = {}
    def _decrypt_message(self, encrypted_data: str):
        try:
            decoded_data = base64.b64decode(encrypted_data)
            cipher = AES.new(self.access_secret_bytes[:16], AES.MODE_ECB)
            decrypted_data = cipher.decrypt(decoded_data)
            unpad = lambda s: s[:-ord(s[len(s)-1:])]
            unpadded_data = unpad(decrypted_data)
            return json.loads(unpadded_data.decode('utf-8'))
        except Exception as e:
            print(f"❌ Erreur de décryptage: {e}")
            return None
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ [MQTT] Connecté avec succès au broker Tuya !")
            topic = self.config["source_topic"]["device"]
            client.subscribe(topic)
            print(f"👂 [MQTT] En écoute sur le topic: {topic}")
            print("\n" + "="*50 + "\n🚀 LE TEST EST ACTIF ! 🚀\n" + "="*50 + "\n")
        else:
            print(f"❌ [MQTT] Échec de la connexion, code de retour: {rc}")
    def on_message(self, client, userdata, msg):
        print("\n--- 📩 Message en Temps Réel Reçu ! ---")
        try:
            payload = json.loads(msg.payload.decode())
            encrypted_data = payload.get("data")
            if not encrypted_data: return
            decrypted_payload = self._decrypt_message(encrypted_data)
            if decrypted_payload:
                print("📦 Données décryptées :\n" + json.dumps(decrypted_payload, indent=2))
                for item in decrypted_payload.get("status", []):
                    code, value = item.get("code"), item.get("value")
                    if code in ['phase_a', 'phase_b', 'phase_c']:
                        print(f"🔎 Décodage {code}: {self.decoder.decode_phase_simple_data(value, code)}")
                    elif 'grid detailed data' in code:
                        print(f"🔎 Décodage {code}: {self.decoder.decode_phase_detailed_data(value, code)}")
        except Exception as e: print(f"❌ Erreur lors du traitement du message: {e}")
        finally: print("--- Fin du Message ---")
    def run_test(self):
        if not self.tuya_client.connect(): return
        target_uid = "bay1754056739178QqkC" 
        print(f"✅ [INFO] Utilisation de l'UID forcé : {target_uid}")
        response = self.tuya_client.get_mqtt_config(target_uid)
        if not response or not response.get("success"):
            print("❌ Impossible d'obtenir la configuration MQTT.")
            print(f"   Réponse de l'API: {response}")
            return
        self.config = response["result"]
        print("✅ [MQTT] Configuration obtenue.")
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=self.config["client_id"])
        self.mqtt_client.username_pw_set(self.config["username"], self.config["password"])
        self.mqtt_client.tls_set(cert_reqs=ssl.CERT_NONE)
        self.mqtt_client.tls_insecure_set(True)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        url = self.config["url"]
        host, port = (url.split("://")[1].split(":")[0], int(url.split(":")[-1])) if "://" in url else (url.split(":")[0], int(url.split(":")[1]))
        print(f"🔗 [MQTT] Connexion à {host} sur le port {port}...")
        try:
            self.mqtt_client.connect(host, port, 60)
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt: print("\n🛑 Script arrêté.")
        except Exception as e: print(f"❌ Erreur critique MQTT: {e}")
        finally:
            if self.mqtt_client.is_connected():
                self.mqtt_client.disconnect()
                print("🔌 [MQTT] Déconnecté.")

# ==============================================================================
#  PARTIE 4 : LANCEMENT DU TEST
# ==============================================================================
if __name__ == "__main__":
    print("="*50 + "\n     SCRIPT DE TEST MQTT v4 (Appel API Corrigé)\n" + "="*50)
    tester = MqttTester()
    tester.run_test()
