# app/services/data_processor.py - VERSION FINALE HARMONISÉE

import logging
import json
from datetime import datetime

# --- NOUVELLES IMPORTATIONS ---
# On importe les deux fonctions distinctes de notre nouvel agrégateur.
from .data_aggregator_service import aggregate_data, check_and_dispatch_if_complete

log = logging.getLogger(__name__)

def process_pulsar_message(raw_data: str):
    """
    [FINAL] Traite un message brut de Pulsar.
    1. Agrège chaque morceau de donnée contenu dans le message.
    2. À la fin du message, demande à l'agrégateur de vérifier si un snapshot est complet.
    """
    log.info(f"➡️ [PROCESSEUR] Nouveau message brut reçu : {raw_data[:200]}...")
    try:
        # --- 1. Nettoyage et parsing du JSON ---
        # Cette partie est déjà correcte et robuste.
        last_brace_index = raw_data.rfind('}')
        if last_brace_index == -1:
            log.warning("[PROCESSEUR] Message rejeté : aucune accolade fermante trouvée.")
            return

        clean_json_string = raw_data[:last_brace_index + 1]
        data = json.loads(clean_json_string)

        # Normalisation du format du message
        if "bizData" in data:
            data["devId"] = data["bizData"].get("devId")
            data["status"] = data["bizData"].get("properties")
        
        if "devId" not in data or "status" not in data:
            log.warning(f"[PROCESSEUR] Message rejeté : devId ou status manquant. Données : {data}")
            return

        device_id = data.get('devId')
        timestamp = data.get("ts") or int(datetime.utcnow().timestamp() * 1000)
        
        log.info(f"⚙️ [PROCESSEUR] Agrégation des données pour devId: {device_id}")

        # --- 2. Agrégation des données ---
        # On boucle sur chaque propriété dans le message et on l'ajoute au "pot commun" dans Redis.
        # La fonction aggregate_data ne fait qu'ajouter, elle ne vérifie rien.
        status_updates = data.get("status", [])
        if not status_updates:
            log.info(f"ℹ️ [PROCESSEUR] Message pour {device_id} ne contient aucune propriété à traiter. Ignoré.")
            return
            
        for status_update in status_updates:
            code = status_update.get("code")
            value = status_update.get("value")
            
            if code:
                aggregate_data(device_id, code, value, timestamp)

        # --- 3. Vérification de la complétude ---
        # C'est la nouvelle étape clé. Une fois que toutes les données du message ont été
        # ajoutées, on demande à l'agrégateur de vérifier si, par hasard, le snapshot
        # est maintenant complet.
        log.debug(f"Vérification de la complétude pour {device_id} après traitement du message.")
        check_and_dispatch_if_complete(device_id)

    except json.JSONDecodeError as e:
        log.error(f"❌ [PROCESSEUR] Erreur de décodage JSON: {e}. Données brutes: {raw_data[:300]}")
    except Exception as e:
        log.error(f"❌ [PROCESSEUR] Erreur inattendue: {e}", exc_info=True)

