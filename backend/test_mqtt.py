# Fichier: test_final.py
# Un script de test complet et autonome pour diagnostiquer la connexion Pulsar.

import pulsar
import os
import logging
import json
import time
import hashlib
import base64
from Crypto.Cipher import AES

# --- Dépendances requises ---
# pip install pulsar-client pycryptodome python-dotenv certifi

# --- Configuration du Logging ---
# Met en place un logger clair pour voir ce qui se passe.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [TEST_FINAL] - %(message)s'
)

# --- Fonctions Utilitaires (regroupées ici pour la simplicité) ---

def get_authentication(access_id: str, access_key: str):
    """
    Génère l'objet d'authentification Basic pour Pulsar, en utilisant
    le formatage très spécifique requis par Tuya.
    """
    logging.info("Génération des identifiants d'authentification...")
    md5_access_key = hashlib.md5(access_key.encode('utf-8')).hexdigest()
    combined = access_id + md5_access_key
    md5_combined = hashlib.md5(combined.encode('utf-8')).hexdigest()
    password_part = md5_combined[8:24]
    
    username_str = f'{{"username":"{access_id}","password":'
    password_str = f'"{password_part}"}}'
    
    logging.info("Identifiants formatés prêts pour l'envoi.")
    return pulsar.AuthenticationBasic(username_str, password_str)

def decrypt_message(pulsar_message, access_key: str) -> str:
    """
    Déchiffre un message Pulsar reçu de Tuya.
    """
    payload = pulsar_message.data().decode('utf-8')
    decrypt_model = pulsar_message.properties().get("em", "aes_ecb") # "aes_ecb" par défaut

    data_json = json.loads(payload)
    encrypt_data = data_json['data']
    key_bytes = access_key[8:24].encode('utf-8')
    raw_bytes = base64.b64decode(encrypt_data)

    logging.info(f"Déchiffrement du message avec la méthode : {decrypt_model}")

    if decrypt_model == "aes_gcm":
        nonce = raw_bytes[:12]
        ciphertext = raw_bytes[12:-16]
        auth_tag = raw_bytes[-16:]
        aes_cipher = AES.new(key_bytes, AES.MODE_GCM, nonce)
        return aes_cipher.decrypt_and_verify(ciphertext, auth_tag).decode('utf-8')
    else: # AES/ECB
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        decrypted_data = cipher.decrypt(raw_bytes)
        # Nettoyage du padding et des caractères invalides
        res_str = decrypted_data.decode('utf-8', errors='ignore')
        return res_str.strip()

def message_id(msg_id) -> str:
    """
    Formate l'ID du message Pulsar pour un affichage lisible.
    """
    return f"{msg_id.ledger_id()}:{msg_id.entry_id()}:{msg_id.partition()}:{msg_id.batch_index()}"

# --- Point d'entrée principal du script ---

def main():
    """
    Fonction principale qui se connecte à Pulsar et écoute les messages.
    """
    logging.info("--- DÉBUT DU TEST FINAL DE CONNEXION PULSAR ---")

    # --- 1. Chargement de la configuration ---
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logging.info("Fichier .env chargé.")
    except ImportError:
        logging.warning("python-dotenv non trouvé. Lecture des variables système uniquement.")

    ACCESS_ID = os.getenv('ACCESS_ID')
    ACCESS_KEY = os.getenv('ACCESS_KEY')
    PULSAR_SERVER_URL = "pulsar+ssl://mqe.tuyaeu.com:7285"
    MQ_ENV = "event"

    if not all([ACCESS_ID, ACCESS_KEY]):
        logging.error("ERREUR: ACCESS_ID ou ACCESS_KEY non trouvé dans les variables d'environnement.")
        logging.error("Veuillez créer un fichier .env ou exporter ces variables.")
        return

    logging.info(f"Configuration chargée pour ACCESS_ID: {ACCESS_ID[:10]}...")

    # --- 2. Configuration SSL avec certifi ---
    try:
        import certifi
        tls_trust_certs_file_path = certifi.where()
        logging.info(f"Utilisation du fichier de certificats SSL : {tls_trust_certs_file_path}")
    except ImportError:
        tls_trust_certs_file_path = None
        logging.warning("certifi non trouvé. Utilisation des certificats SSL du système.")

    # --- 3. Boucle de connexion et de réception ---
    client = None
    try:
        logging.info("Tentative de connexion au broker Pulsar...")
        client = pulsar.Client(
            PULSAR_SERVER_URL,
            authentication=get_authentication(ACCESS_ID, ACCESS_KEY),
            tls_trust_certs_file_path=tls_trust_certs_file_path,
            operation_timeout_seconds=30 # Délai d'attente de 30 secondes
        )

        topic = f"persistent://{ACCESS_ID}/out/{MQ_ENV}"
        subscription_name = f"{ACCESS_ID}-final-test-sub"

        consumer = client.subscribe(
            topic,
            subscription_name,
            consumer_type=pulsar.ConsumerType.Failover
        )
        
        logging.info("======================================================")
        logging.info("✅✅✅  CONNEXION RÉUSSIE ! ✅✅✅")
        logging.info(f"À l'écoute sur le topic : {topic}")
        logging.info("En attente de messages... (Pressez CTRL+C pour arrêter)")
        logging.info("======================================================")

        while True:
            pulsar_message = consumer.receive()
            msg_id = message_id(pulsar_message.message_id())
            logging.info(f"\n--- MESSAGE REÇU (ID: {msg_id}) ---")
            
            try:
                decrypted_msg = decrypt_message(pulsar_message, ACCESS_KEY)
                logging.info("CONTENU DÉCHIFFRÉ :")
                # Essayer de formater le JSON pour une meilleure lisibilité
                try:
                    parsed_json = json.loads(decrypted_msg)
                    logging.info(json.dumps(parsed_json, indent=2))
                except json.JSONDecodeError:
                    logging.info(decrypted_msg)

                consumer.acknowledge(pulsar_message)
                logging.info("Message acquitté avec succès.")

            except Exception as e:
                logging.error(f"Erreur lors du traitement du message {msg_id}: {e}")
                consumer.negative_acknowledge(pulsar_message)

    except (pulsar.ConnectError, pulsar.AuthenticationError) as e:
        logging.error("======================================================")
        logging.error("❌❌❌ ÉCHEC DE LA CONNEXION ❌❌❌")
        logging.error(f"Erreur : {e}")
        logging.error("Causes possibles : Pare-feu, Antivirus, Problème réseau, ou Identifiants incorrects.")
        logging.error("======================================================")
        
    except KeyboardInterrupt:
        logging.info("\nArrêt demandé par l'utilisateur.")
        
    except Exception as e:
        logging.critical(f"Une erreur critique et inattendue est survenue : {e}", exc_info=True)
        
    finally:
        if client:
            client.close()
            logging.info("Client Pulsar fermé proprement.")
        logging.info("--- FIN DU TEST ---")

if __name__ == "__main__":
    main()
