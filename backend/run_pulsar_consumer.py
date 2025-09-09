# Fichier: run_pulsar_consumer.py

import pulsar
import os
import logging
import json
import time
from dotenv import load_dotenv

# --- Copiez/collez les utilitaires directement ici pour la simplicité ---

# --- mq_authentication.py ---
def get_authentication(access_id: str, access_key: str):
    md5_access_key = hashlib.md5(access_key.encode('utf-8')).hexdigest()
    combined = access_id + md5_access_key
    md5_combined = hashlib.md5(combined.encode('utf-8')).hexdigest()
    password_part = md5_combined[8:24]
    username_str = f'{{"username":"{access_id}","password":'
    password_str = f'"{password_part}"}}'
    return pulsar.AuthenticationBasic(username_str, password_str)

# --- message_util.py ---
import base64
from Crypto.Cipher import AES

def decrypt_message(pulsar_message, access_key):
    payload = pulsar_message.data().decode('utf-8')
    decrypt_model = pulsar_message.properties().get("em")
    data_json = json.loads(payload)
    encrypt_data = data_json['data']
    key_bytes = access_key[8:24].encode('utf-8')
    raw_bytes = base64.b64decode(encrypt_data)

    if decrypt_model == "aes_gcm":
        nonce = raw_bytes[:12]
        ciphertext = raw_bytes[12:-16]
        auth_tag = raw_bytes[-16:]
        aes_cipher = AES.new(key_bytes, AES.MODE_GCM, nonce)
        return aes_cipher.decrypt_and_verify(ciphertext, auth_tag).decode('utf-8')
    else:
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        decrypted_data = cipher.decrypt(raw_bytes)
        res_str = decrypted_data.decode('utf-8', errors='ignore')
        return res_str.strip()

def message_id(msg_id) -> str:
    return f"{msg_id.ledger_id()}:{msg_id.entry_id()}:{msg_id.partition()}:{msg_id.batch_index()}"

# --- Logique principale du consommateur ---

def handle_message(decrypted_message, msg_id):
    """
    C'est ici que vous traitez le message.
    Pour l'instant, on se contente de l'afficher.
    """
    logging.info(f"--- Message traité (ID: {msg_id}) ---")
    logging.info(decrypted_message)
    # TODO: Plus tard, vous pourrez envoyer ces données à votre API Flask
    # via une requête POST, ou les écrire dans Redis pour que Flask les lise.

def main():
    """
    Fonction principale pour lancer le consommateur.
    """
    # Configuration du logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [PULSAR_CONSUMER] - %(message)s')

    # Chargement des variables d'environnement depuis le fichier .env
    load_dotenv()
    
    ACCESS_ID = os.getenv('ACCESS_ID')
    ACCESS_KEY = os.getenv('ACCESS_KEY')
    PULSAR_SERVER_URL = "pulsar+ssl://mqe.tuyaeu.com:7285"
    MQ_ENV = "event"

    if not all([ACCESS_ID, ACCESS_KEY]):
        logging.error("ACCESS_ID ou ACCESS_KEY manquant dans le fichier .env. Arrêt.")
        return

    client = None
    while True: # Boucle de reconnexion automatique
        try:
            logging.info("Tentative de connexion au broker Pulsar...")
            client = pulsar.Client(
                PULSAR_SERVER_URL,
                authentication=get_authentication(ACCESS_ID, ACCESS_KEY),
                tls_allow_insecure_connection=True,
                operation_timeout_seconds=30
            )

            topic = f"{ACCESS_ID}/out/{MQ_ENV}"
            subscription_name = f"{ACCESS_ID}-subscription-standalone"

            consumer = client.subscribe(
                topic,
                subscription_name,
                consumer_type=pulsar.ConsumerType.Failover
            )
            logging.info(f"✅ Connecté et à l'écoute sur le topic '{topic}'")

            while True:
                pulsar_message = consumer.receive()
                msg_id = message_id(pulsar_message.message_id())
                logging.info(f"Message reçu (ID: {msg_id})")
                
                try:
                    decrypted_msg = decrypt_message(pulsar_message, ACCESS_KEY)
                    handle_message(decrypted_msg, msg_id)
                    consumer.acknowledge(pulsar_message)
                except Exception as e:
                    logging.error(f"Erreur lors du traitement du message {msg_id}: {e}")
                    # Ne pas acquitter pour que le message soit redélivré plus tard
                    consumer.negative_acknowledge(pulsar_message)

        except (pulsar.ConnectError, pulsar.AuthenticationError) as e:
            logging.error(f"Erreur de connexion ou d'authentification: {e}. Nouvelle tentative dans 30 secondes...")
        except Exception as e:
            logging.critical(f"Erreur critique inattendue: {e}. Nouvelle tentative dans 30 secondes...")
        finally:
            if client:
                client.close()
            time.sleep(30) # Attendre avant de retenter la connexion

if __name__ == "__main__":
    # Il manque la dépendance 'hashlib' qui est une bibliothèque standard en Python.
    # Je vais l'ajouter.
    import hashlib
    main()
