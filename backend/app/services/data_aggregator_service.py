# app/services/data_aggregator_service.py - VERSION FINALE
import logging
import json
from app import get_redis
from .event_dispatcher import dispatch_complete_snapshot

log = logging.getLogger(__name__)

# On donne un peu de temps à un snapshot pour se compléter.
# 2 secondes est un bon compromis pour une rafale de messages.
AGGREGATION_EXPIRATION_SECONDS = 2

def aggregate_data(device_id: str, code: str, value: any, timestamp: int):
    """
    [FINAL] Ajoute une donnée au cache Redis. Ne vérifie PAS la complétude.
    Son seul rôle est d'ajouter des données à un pot commun.
    """
    redis_client = get_redis()
    if not redis_client:
        log.error("❌ [AGGREGATEUR] Redis n'est pas disponible.")
        return

    cache_key = f"device_agg_cache:{device_id}"

    try:
        pipe = redis_client.pipeline()
        
        # Si c'est la première donnée du snapshot, on stocke le timestamp
        pipe.hsetnx(cache_key, 'timestamp', timestamp)
        
        # On ajoute la nouvelle donnée
        pipe.hset(cache_key, code, json.dumps(value))
        
        # On rafraîchit l'expiration à chaque mise à jour
        pipe.expire(cache_key, AGGREGATION_EXPIRATION_SECONDS)
        
        pipe.execute()
        log.debug(f"Cache pour {device_id} mis à jour avec la clé '{code}'.")

    except Exception as e:
        log.error(f"❌ [AGGREGATEUR] Erreur Redis: {e}", exc_info=True)

def check_and_dispatch_if_complete(device_id: str):
    """
    [NOUVEAU] Vérifie si le snapshot pour un appareil est complet et, si oui,
    le dispatche et nettoie le cache.
    Cette fonction doit être appelée après chaque appel à aggregate_data.
    """
    redis_client = get_redis()
    if not redis_client:
        return

    cache_key = f"device_agg_cache:{device_id}"
    
    current_data_raw = redis_client.hgetall(cache_key)
    if not current_data_raw:
        return

    current_data = {k.decode('utf-8'): json.loads(v.decode('utf-8')) for k, v in current_data_raw.items()}
    current_keys = set(current_data.keys())
    
    # --- LOGIQUE DE COMPLÉTUDE AMÉLIORÉE ---
    # On définit les clés *essentielles* pour chaque type.
    required_triphase = {'phase_a', 'phase_b', 'phase_c'}
    required_monophase = {'cur_voltage', 'cur_current', 'cur_power'}

    is_complete = False
    if required_triphase.issubset(current_keys):
        # Pour le triphasé, on attend d'avoir aussi les données d'énergie et de facteur de puissance
        # si elles sont disponibles, en se basant sur un petit délai.
        # Cette logique est complexe. Simplifions.
        is_complete = True
        log.info(f"✅ [AGGREGATEUR] Snapshot TRIphasé complet pour {device_id} détecté.")
        
    elif required_monophase.issubset(current_keys):
        is_complete = True
        log.info(f"✅ [AGGREGATEUR] Snapshot MONOphasé complet pour {device_id} détecté.")
    
    if is_complete:
        log.info(f"Envoi du snapshot complet au dispatcher pour {device_id}.")
        # On supprime le cache AVANT de dispatcher pour éviter les doubles traitements.
        redis_client.delete(cache_key)
        # On appelle le dispatcher dans le même flux.
        dispatch_complete_snapshot(device_id, current_data)

