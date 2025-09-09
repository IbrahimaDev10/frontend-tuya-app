# Fichier: test_qui_marche.py
# Ce script est une fusion directe de vos trois fichiers qui fonctionnent,
# pour un test simple et fiable.

import pulsar
import json
import base64
import hashlib
from Crypto.Cipher import AES
import logging

# --- Configuration du Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [TEST_QUI_MARCHE] - %(message)s'
)

# ===================================================================
# DÉBUT : Contenu fusionné de mq_authentication.py
# ===================================================================
def get_authentication(access_id, access_key):
    """
    Génère l'objet d'authentification.
    NOTE : La version originale utilise 'accsess_key' avec une faute de frappe.
    Je la corrige en 'access_key' pour la cohérence.
    Le paramètre "auth1" est crucial.
    """
    logging.info("Génération des identifiants d'authentification (méthode originale)...")
    md5_access_key = hashlib.md5(access_key.encode('utf-8')).hexdigest()
    combined = access_id + md5_access_key
    md5_combined = hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    # Formatage non-standard qui simule un JSON
    password = '"' + md5_combined[8:24] + '"}'
    user_name = '{{"username": "{}","password"'.format(access_id)
    
    # Le "auth1" est probablement le nom du plugin d'authentification côté client.
    # C'est une différence majeure avec nos tentatives précédentes.
    logging.info("Utilisation de pulsar.AuthenticationBasic avec le paramètre 'auth1'.")
    return pulsar.AuthenticationBasic(user_name, password, "auth1")
# ===================================================================
# FIN : Contenu fusionné de mq_authentication.py
# ===================================================================


# ===================================================================
# DÉBUT : Contenu fusionné de message_util.py
# ===================================================================
def decrypt_by_gcm(raw_bytes: bytes, key_bytes: bytes) -> str:
    nonce = raw_bytes[:12]
    ciphertext = raw_bytes[12:-16]
    auth_tag = raw_bytes[-16:]
    aes_cipher = AES.new(key_bytes, AES.MODE_GCM, nonce)
    return aes_cipher.decrypt_and_verify(ciphertext, auth_tag).decode('utf-8')

def decrypt_by_ecb(raw_bytes: bytes, key_bytes: bytes) -> str:
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    decrypted_data = cipher.decrypt(raw_bytes)
    res_str = decrypted_data.decode('utf-8', errors='ignore')
    # Nettoyage du padding et des caractères de contrôle
    return res_str.replace('\r', '').replace('\n', '').replace('\f', '').strip()

def decrypt_by_aes(raw: str, key: str, decrypt_model: str) -> str:
    raw_bytes = base64.b64decode(raw)
    key_bytes = key[8:24].encode('utf-8')

    if decrypt_model == "aes_gcm":
        return decrypt_by_gcm(raw_bytes, key_bytes)
    else:
        return decrypt_by_ecb(raw_bytes, key_bytes)

def do_decrypt_message(payload: str, decrypt_model: str, access_key: str) -> str:
    data_json = json.loads(payload)
    encrypt_data = data_json['data']
    return decrypt_by_aes(encrypt_data, access_key, decrypt_model)

def decrypt_message(pulsar_message, access_key: str) -> str:
    payload = pulsar_message.data().decode('utf-8')
    decrypt_model = pulsar_message.properties().get("em")
    logging.info(f"Déchiffrement du message avec la méthode : {decrypt_model}")
    return do_decrypt_message(payload, decrypt_model, access_key)

def message_id(msg_id) -> str:
    return f"{msg_id.ledger_id()}:{msg_id.entry_id()}:{msg_id.partition()}:{msg_id.batch_index()}"
# ===================================================================
# FIN : Contenu fusionné de message_util.py
# ===================================================================


# ===================================================================
# DÉBUT : Contenu fusionné de consumer_example.py (script principal)
# ===================================================================
def main():
    logging.info("--- DÉMARRAGE DU SCRIPT DE TEST FUSIONNÉ ---")
    
    # --- Configuration ---
    ACCESS_ID = "jj8av7m9435s78dmcfct"
    ACCESS_KEY = "680f5b3b680341de94e57e7854021323"
    PULSAR_SERVER_URL = "pulsar+ssl://mqe.tuyaeu.com:7285"
    MQ_ENV = "event"
    
    client = None
    try:
        logging.info("Initialisation du client Pulsar...")
        client = pulsar.Client(
            PULSAR_SERVER_URL,
            authentication=get_authentication(ACCESS_ID, ACCESS_KEY),
            # Ce paramètre désactive la vérification du certificat, ce qui peut expliquer
            # pourquoi cela fonctionne en dehors d'un venv avec des problèmes SSL.
            tls_allow_insecure_connection=True,
        )

        topic = f"{ACCESS_ID}/out/{MQ_ENV}"
        subscription_name = f"{ACCESS_ID}-sub-fonctionnel"
        
        logging.info(f"Souscription au topic '{topic}'...")
        consumer = client.subscribe(
            topic,
            subscription_name,
            consumer_type=pulsar.ConsumerType.Failover
        )

        logging.info("======================================================")
        logging.info("✅✅✅ CONNEXION RÉUSSIE ! ✅✅✅")
        logging.info("En attente de messages... (Pressez CTRL+C pour arrêter)")
        logging.info("======================================================")

        while True:
            pulsar_message = consumer.receive()
            msg_id = message_id(pulsar_message.message_id())
            logging.info(f"\n--- MESSAGE REÇU (ID: {msg_id}) ---")
            logging.info(f"Données chiffrées (brut): {pulsar_message.data()}")

            decrypted_msg = decrypt_message(pulsar_message, ACCESS_KEY)
            logging.info(f"Données déchiffrées: {decrypted_msg}")
            
            # Acquitter le message pour ne pas le recevoir à nouveau
            consumer.acknowledge(pulsar_message)
            logging.info("Message acquitté.")

    except (pulsar.ConnectError, pulsar.AuthenticationError) as e:
        logging.error("======================================================")
        logging.error("❌❌❌ ÉCHEC DE LA CONNEXION ❌❌❌")
        logging.error(f"Erreur : {e}")
        logging.error("======================================================")

    except KeyboardInterrupt:
        logging.info("\nArrêt demandé par l'utilisateur.")
        
    except Exception as e:
        logging.critical(f"Une erreur critique est survenue : {e}", exc_info=True)
        
    finally:
        if client:
            client.close()
            logging.info("Client Pulsar fermé.")

if __name__ == "__main__":
    main()
