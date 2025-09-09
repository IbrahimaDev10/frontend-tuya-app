# app/services/data_processor.py
import logging
import json
from datetime import datetime

# Importations corrigées pour éviter la dépendance circulaire
from .data_aggregator_service import aggregate_and_check_completeness
from .event_dispatcher import dispatch_complete_snapshot

log = logging.getLogger(__name__)

# La fonction de décodage a été déplacée dans decoders.py

# --- PROCESSEUR DE MESSAGES PRINCIPAL (SIMPLIFIÉ) ---
def process_pulsar_message(raw_data: str):
    log.info(f"➡️ [PROCESSEUR] Nouveau message brut reçu : {raw_data[:200]}...")
    try:
        last_brace_index = raw_data.rfind('}')
        if last_brace_index == -1:
            log.warning("[PROCESSEUR] Message rejeté : aucune accolade fermante trouvée.")
            return

        clean_json_string = raw_data[:last_brace_index + 1]
        data = json.loads(clean_json_string)

        if "bizData" in data:
            data["devId"] = data["bizData"].get("devId")
            data["status"] = data["bizData"].get("properties")
        
        if "devId" not in data or "status" not in data:
            log.warning(f"[PROCESSEUR] Message rejeté : devId ou status manquant. Données : {data}")
            return

        device_id = data.get('devId')
        log.info(f"⚙️ [PROCESSEUR] Passage à l'agrégateur pour devId: {device_id}")

        # On boucle sur chaque propriété et on l'envoie à l'agrégateur
        timestamp = data.get("ts") or int(datetime.utcnow().timestamp() * 1000)

        for status_update in data.get("status", []):
            code = status_update.get("code")
            value = status_update.get("value")
            
            # Chaque morceau de donnée est envoyé à l'agrégateur
            snapshot, is_complete = aggregate_and_check_completeness(device_id, code, value, timestamp)
            
            # Si l'agrégateur nous dit que le snapshot est complet...
            if is_complete:
                log.info(f"✅ Snapshot complet reçu de l'agrégateur pour {device_id}. Envoi au dispatcher.")
                # ... on appelle la nouvelle fonction du dispatcher.
                dispatch_complete_snapshot(device_id, snapshot)

    except Exception as e:
        log.error(f"❌ [PROCESSEUR] Erreur inattendue: {e}", exc_info=True)
