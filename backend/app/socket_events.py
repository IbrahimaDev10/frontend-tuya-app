# app/socket_events.py
from . import socketio
import logging

log = logging.getLogger(__name__)

@socketio.on('connect')
def handle_connect():
    """Événement déclenché lorsqu'un client (navigateur) se connecte."""
    log.info("🔌 [WebSocket] Un client s'est connecté.")
    # Vous pourriez ici ajouter de la logique, comme joindre un "room" spécifique à l'utilisateur.

@socketio.on('disconnect')
def handle_disconnect():
    """Événement déclenché lorsqu'un client se déconnecte."""
    log.info("🔌 [WebSocket] Un client s'est déconnecté.")

def emit_new_device_data(data: dict):
    """
    Fonction centrale pour envoyer les nouvelles données de l'appareil à tous les clients.
    Appelée par data_processor.py après une sauvegarde en BDD.
    
    Args:
        data (dict): Les données de l'appareil formatées en dictionnaire.
    """
    try:
        device_id = data.get('device_id')
        if not device_id:
            log.warning("[WebSocket] Tentative d'émission sans device_id.")
            return
            
        log.info(f"🚀 [WebSocket] Émission de 'new_data' pour l'appareil {device_id}")
        # On émet sur un "canal" (event) nommé 'new_data'.
        # Tous les clients qui écoutent cet événement le recevront.
        socketio.emit('new_data', data)
    except Exception as e:
        log.error(f"❌ [WebSocket] Erreur lors de l'émission de l'événement : {e}")

