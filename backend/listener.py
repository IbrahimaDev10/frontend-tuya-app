# listener.py - Version pour l'ancienne bibliothèque "tuya-connector-python"

import logging
import json
from tuya_connector import TuyaOpenAPI, TuyaOpenPulsar, TuyaPulsarTopic

# =================================================================
# --- CONFIGURATION AVEC CLÉS UNIFIÉES ---
# =================================================================

# Mettez ici les clés de votre projet "Sertec_App"
# (Depuis la page "Cloud" > "Projects" > Votre Projet)
ACCESS_ID = "cqg5gcysw5xcvachq8tr"
ACCESS_KEY = "b69149fe97e94518b71b9f44a367b427" # Le secret de votre projet
API_ENDPOINT = "https://openapi.tuyaeu.com"

# Avec cette bibliothèque, on utilise les mêmes clés pour les deux services.
MQ_ACCESS_ID = ACCESS_ID
MQ_ACCESS_KEY = ACCESS_KEY

# =================================================================
# --- FIN DE LA CONFIGURATION ---
# =================================================================


# Configuration des logs pour voir les détails
logging.basicConfig(level=logging.INFO )

# --- Initialisation des services Tuya ---

# 1. Connexion à l'API standard
openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
try:
    # La méthode de connexion est légèrement différente
    response = openapi.connect()
    if response.get("success", False):
        print("✅ Connexion à l'API Tuya réussie.")
    else:
        print(f"❌ Erreur de connexion à l'API Tuya : {response.get('msg')}")
        exit()
except Exception as e:
    print(f"❌ Erreur critique de connexion à l'API Tuya : {e}")
    exit()


# 2. Initialisation du client Pulsar (le listener temps réel)
# La syntaxe pour s'abonner au topic de test est différente
open_pulsar = TuyaOpenPulsar(
    MQ_ACCESS_ID,
    MQ_ACCESS_KEY,
    openapi.endpoint,
    TuyaPulsarTopic.TEST # On utilise TuyaPulsarTopic.TEST
)


# --- Logique de traitement des messages ---

def on_message(msg):
    """
    Cette fonction est appelée automatiquement chaque fois qu'un message
    arrive depuis la file d'attente de Tuya.
    """
    try:
        print("\n" + "="*40)
        print("--- ✅ Nouveau Message Temps Réel Reçu ---")
        print("="*40)
        
        # Avec cette ancienne bibliothèque, le déchiffrement n'est pas automatique.
        # Il faut appeler une méthode spécifique pour le faire.
        decrypted_message = openapi.pulsar_listener_on_message(msg)
        
        print(f"Données complètes décodées :\n{json.dumps(decrypted_message, indent=2)}")

        # Extraction des informations utiles
        device_id = decrypted_message.get("devId")
        product_id = decrypted_message.get("productId")
        status_list = decrypted_message.get("status", [])

        print("\n--- Analyse du message ---")
        print(f"Appareil concerné (Device ID) : {device_id}")
        print(f"Produit (Product ID) : {product_id}")

        if not status_list:
            print("Message de statut vide (peut être un événement de connexion/déconnexion).")
        else:
            for status in status_list:
                code = status.get("code")
                value = status.get("value")
                print(f"  -> Le statut '{code}' a changé à : {value}")
        
        print("="*40 + "\n")

    except Exception as e:
        print(f"❌ Erreur lors du traitement du message : {e}")
        print(f"   Message brut reçu : {msg}")


# --- Démarrage de l'écouteur ---

# On attache notre fonction de traitement au listener
open_pulsar.add_message_listener(on_message)

try:
    # Démarrage de la connexion au service de messages
    print("\n🚀 Démarrage de l'écouteur sur le canal de TEST de Tuya...")
    print("   (Utilisation de l'ancienne bibliothèque tuya-connector-python)")
    print("   Le script est maintenant en attente de messages.")
    print("   Pour tester, déclenchez un événement sur votre appareil de test.")
    print("   (CTRL+C pour arrêter le script proprement)")
    open_pulsar.start()

except KeyboardInterrupt:
    print("\n🛑 Arrêt de l'écouteur demandé par l'utilisateur.")
    open_pulsar.stop()
    print("   Connexion au service de messages fermée.")
