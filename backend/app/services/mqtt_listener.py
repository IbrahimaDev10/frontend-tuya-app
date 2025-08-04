# app/services/mqtt_listener.py - Notre "Coursier" qui écoute les messages de Tuya
import paho.mqtt.client as mqtt
import ssl
import json
import logging
from threading import Thread
from Crypto.Cipher import AES

# Utiliser le logger de l'application
log = logging.getLogger(__name__)

# Fonction pour "ouvrir l'enveloppe" : déchiffrer le message de Tuya
def decrypt_message(encrypted_data, secret_key):
    try:
        key = secret_key[:16].encode('utf-8')
        # On confirme ici qu'on utilise bien le bon mode
        cipher = AES.new(key, AES.MODE_ECB) # <--- C'est bien ECB, c'est parfait.
        
        import base64
        decoded_data = base64.b64decode(encrypted_data)
        decrypted_padded = cipher.decrypt(decoded_data)
        
        # Le "unpadding" est crucial pour ECB
        unpad = lambda s: s[ : -ord(s[len(s)-1:])]
        decrypted_data = unpad(decrypted_padded).decode('utf-8')
        
        return json.loads(decrypted_data)
    except Exception as e:
        log.error(f"[MQTT] Erreur de déchiffrement (probablement AES-ECB vs AES-GCM): {e}")
        return None

# La classe qui définit notre Coursier
class TuyaMQTTListener(Thread):
    def __init__(self, config, secret_key):
        super().__init__()
        self.daemon = True # Le thread s'arrêtera avec l'application principale
        self.config = config
        self.secret_key = secret_key
        self.client = None

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            topic = self.config['source_topic']['device']
            client.subscribe(topic)
            log.info(f"✅ [MQTT] Connecté et à l'écoute sur le canal: {topic}")
        else:
            log.error(f"❌ [MQTT] Échec de la connexion, code d'erreur: {rc}")

    def on_message(self, client, userdata, msg):
        log.info("--- 📩 [MQTT] Nouveau message reçu ! ---")
        try:
            payload_json = json.loads(msg.payload.decode('utf-8'))
            encrypted_data = payload_json.get('data')
            
            if encrypted_data:
                decrypted_message = decrypt_message(encrypted_data, self.secret_key)
                if decrypted_message:
                    log.info(f"[MQTT] Message déchiffré: {json.dumps(decrypted_message, indent=2)}")
                    #
                    # C'EST ICI QUE LA MAGIE OPÈRE !
                    # Prochaine étape : appeler un service pour traiter ces données
                    # (ex: from app.services.device_service import DeviceService; DeviceService.update_from_mqtt(decrypted_message))
                    #
        except Exception as e:
            log.error(f"[MQTT] Erreur lors du traitement du message: {e}")

    def run(self):
        self.client = mqtt.Client(client_id=self.config['client_id'])
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.username_pw_set(self.config['username'], self.config['password'])
        self.client.tls_set(cert_reqs=ssl.CERT_NONE)
        self.client.tls_insecure_set(True)
        
        try:
            url_parts = self.config['url'].split(':')
            host = url_parts[1].replace('//', '')
            port = int(url_parts[2])
            
            log.info(f"🔌 [MQTT] Tentative de connexion au broker: {host}:{port}")
            self.client.connect(host, port, 60)
            self.client.loop_forever() # Boucle d'écoute
        except Exception as e:
            log.critical(f"❌ [MQTT] Erreur critique du listener, le thread va s'arrêter: {e}")

