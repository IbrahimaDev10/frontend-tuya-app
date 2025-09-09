# app/services/data_aggregator_service.py
import logging
import json
from app import get_redis # Assurez-vous que cette fonction existe et retourne un client Redis

log = logging.getLogger(__name__)

# On donne 10 secondes à un snapshot pour se compléter.
AGGREGATION_EXPIRATION_SECONDS = 10

def aggregate_and_check_completeness(device_id: str, code: str, value: any, timestamp: int):
    """
    Ajoute une donnée au cache Redis et vérifie si un snapshot complet est disponible.
    Retourne le snapshot complet et un booléen.
    """
    redis_client = get_redis()
    if not redis_client:
        log.error("❌ [AGGREGATEUR] Redis n'est pas disponible.")
        return None, False

    cache_key = f"device_agg_cache:{device_id}"

    try:
        # Utiliser une transaction Redis pour garantir l'atomicité
        pipe = redis_client.pipeline()
        
        # Si c'est la première donnée du snapshot, on stocke le timestamp
        pipe.hsetnx(cache_key, 'timestamp', timestamp)
        
        # On ajoute la nouvelle donnée
        pipe.hset(cache_key, code, json.dumps(value))
        
        # On rafraîchit l'expiration à chaque mise à jour
        pipe.expire(cache_key, AGGREGATION_EXPIRATION_SECONDS)
        
        # On exécute la transaction
        pipe.execute()

        # On récupère l'état actuel du cache pour le vérifier
        current_data_raw = redis_client.hgetall(cache_key)
        current_data = {k.decode('utf-8'): json.loads(v.decode('utf-8')) for k, v in current_data_raw.items()}
        current_keys = set(current_data.keys())
        
        log.debug(f"Cache pour {device_id} mis à jour. Contenu: {current_keys}")

        # --- LOGIQUE DE COMPLÉTUDE ---
        required_triphase = {'phase_a', 'phase_b', 'phase_c'}
        required_monophase = {'cur_voltage', 'cur_current', 'cur_power'}

        is_complete = False
        # Vérifie si l'ensemble des clés requises est un sous-ensemble des clés actuelles
        if required_triphase.issubset(current_keys):
            is_complete = True
            log.info(f"✅ [AGGREGATEUR] Snapshot TRIphasé complet pour {device_id} détecté.")
        elif required_monophase.issubset(current_keys):
            is_complete = True
            log.info(f"✅ [AGGREGATEUR] Snapshot MONOphasé complet pour {device_id} détecté.")
        
        if is_complete:
            # On supprime le cache pour le prochain snapshot et on retourne les données
            redis_client.delete(cache_key)
            return current_data, True
        else:
            # Le snapshot n'est pas encore complet
            return None, False

    except Exception as e:
        log.error(f"❌ [AGGREGATEUR] Erreur Redis: {e}", exc_info=True)
        return None, False
