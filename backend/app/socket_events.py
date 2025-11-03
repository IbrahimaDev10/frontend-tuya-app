# app/socket_events.py
from . import socketio
from flask import request
from flask_socketio import emit, join_room, leave_room, disconnect
import logging
import jwt as pyjwt
from functools import wraps
from datetime import datetime
import os

log = logging.getLogger(__name__)

# Configuration JWT (à adapter selon votre config)
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key')

def token_required(f):
    """Décorateur pour vérifier l'authentification Socket.IO"""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            # Récupérer le token depuis l'auth
            auth = kwargs.get('auth', {})
            token = auth.get('token') if isinstance(auth, dict) else None
            
            if not token:
                log.warning(f"❌ [WebSocket] Connexion refusée pour {request.sid} : pas de token")
                return False
            
            # Vérifier le token JWT
            payload = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user_id = payload.get('sub') or payload.get('user_id')
            request.username = payload.get('username') or payload.get('identity')
            
            return f(*args, **kwargs)
            
        except pyjwt.ExpiredSignatureError:
            log.warning(f"❌ [WebSocket] Token expiré pour {request.sid}")
            emit('connection_error', {'error': 'Token expiré'})
            return False
        except pyjwt.InvalidTokenError as e:
            log.warning(f"❌ [WebSocket] Token invalide pour {request.sid}: {e}")
            emit('connection_error', {'error': 'Token invalide'})
            return False
        except Exception as e:
            log.error(f"❌ [WebSocket] Erreur d'authentification pour {request.sid}: {e}")
            emit('connection_error', {'error': 'Erreur serveur'})
            return False
    
    return decorated


@socketio.on('connect')
def handle_connect(auth=None):
    """
    Événement déclenché lorsqu'un client se connecte.
    Auth contient le token si fourni via socket.io-client.
    """
    try:
        client_id = request.sid
        log.info(f"🔌 [WebSocket] Tentative de connexion : {client_id}")
        
        # Vérification du token si fourni
        if auth and isinstance(auth, dict) and 'token' in auth:
            try:
                payload = pyjwt.decode(auth['token'], SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get('sub') or payload.get('user_id')
                username = payload.get('username') or payload.get('identity')
                
                # Joindre une room spécifique à l'utilisateur
                user_room = f"user_{user_id}"
                join_room(user_room)
                
                log.info(f"✅ [WebSocket] Client authentifié : {username} (ID: {user_id}, SID: {client_id})")
                
                # Envoyer une confirmation au client
                emit('connection_success', {
                    'message': 'Connexion réussie',
                    'user_id': user_id,
                    'username': username,
                    'sid': client_id
                })
                
                return True
                
            except pyjwt.ExpiredSignatureError:
                log.warning(f"❌ [WebSocket] Token expiré pour {client_id}")
                emit('connection_error', {'error': 'Token expiré'})
                disconnect()
                return False
                
            except pyjwt.InvalidTokenError as e:
                log.warning(f"❌ [WebSocket] Token invalide pour {client_id}: {e}")
                emit('connection_error', {'error': 'Token invalide'})
                disconnect()
                return False
        else:
            # Connexion sans authentification (à adapter selon vos besoins)
            log.info(f"⚠️ [WebSocket] Connexion non authentifiée : {client_id}")
            join_room('anonymous')
            emit('connection_success', {
                'message': 'Connexion anonyme acceptée',
                'sid': client_id
            })
            return True
            
    except Exception as e:
        log.error(f"❌ [WebSocket] Erreur lors de la connexion : {e}", exc_info=True)
        emit('connection_error', {'error': 'Erreur serveur'})
        return False


@socketio.on('disconnect')
def handle_disconnect():
    """Événement déclenché lorsqu'un client se déconnecte."""
    client_id = request.sid
    log.info(f"🔌 [WebSocket] Client déconnecté : {client_id}")


@socketio.on('join_device')
def handle_join_device(data):
    """
    Permet à un client de rejoindre la room d'un appareil spécifique.
    Usage frontend : socket.emit('join_device', { device_id: '12345' })
    """
    try:
        device_id = data.get('device_id') if isinstance(data, dict) else None
        if not device_id:
            emit('error', {'message': 'device_id manquant'})
            return
        
        room = f"device_{device_id}"
        join_room(room)
        log.info(f"📱 [WebSocket] Client {request.sid} a rejoint la room : {room}")
        emit('joined_device', {
            'device_id': device_id,
            'room': room,
            'message': f'Vous suivez maintenant l\'appareil {device_id}'
        })
        
    except Exception as e:
        log.error(f"❌ [WebSocket] Erreur join_device : {e}", exc_info=True)
        emit('error', {'message': str(e)})


@socketio.on('leave_device')
def handle_leave_device(data):
    """
    Permet à un client de quitter la room d'un appareil.
    Usage frontend : socket.emit('leave_device', { device_id: '12345' })
    """
    try:
        device_id = data.get('device_id') if isinstance(data, dict) else None
        if not device_id:
            emit('error', {'message': 'device_id manquant'})
            return
        
        room = f"device_{device_id}"
        leave_room(room)
        log.info(f"📱 [WebSocket] Client {request.sid} a quitté la room : {room}")
        emit('left_device', {
            'device_id': device_id,
            'message': f'Vous ne suivez plus l\'appareil {device_id}'
        })
        
    except Exception as e:
        log.error(f"❌ [WebSocket] Erreur leave_device : {e}", exc_info=True)
        emit('error', {'message': str(e)})


@socketio.on('ping')
def handle_ping():
    """
    Événement de test pour vérifier la connexion.
    Usage frontend : socket.emit('ping')
    """
    log.debug(f"🏓 [WebSocket] Ping reçu de {request.sid}")
    emit('pong', {
        'timestamp': datetime.now().isoformat(),
        'message': 'pong'
    })


@socketio.on('subscribe_all_devices')
def handle_subscribe_all():
    """
    Permet à un client de s'abonner à tous les appareils.
    Utile pour les dashboards admin.
    """
    try:
        join_room('all_devices')
        log.info(f"📡 [WebSocket] Client {request.sid} suit tous les appareils")
        emit('subscribed_all', {
            'message': 'Vous suivez maintenant tous les appareils',
            'room': 'all_devices'
        })
    except Exception as e:
        log.error(f"❌ [WebSocket] Erreur subscribe_all : {e}", exc_info=True)
        emit('error', {'message': str(e)})


# ========================================
# FONCTIONS D'ÉMISSION (appelées par le backend)
# ========================================

def emit_new_device_data(data: dict, broadcast=True, to_specific_users=None):
    """
    Fonction centrale pour envoyer les nouvelles données de l'appareil.
    Appelée par data_processor.py après une sauvegarde en BDD.
    
    Args:
        data (dict): Les données de l'appareil formatées.
        broadcast (bool): Si True, envoie à tous les clients de la room de l'appareil.
        to_specific_users (list): Liste d'user_id pour un envoi ciblé.
    
    Exemple d'utilisation:
        from app.socket_events import emit_new_device_data
        emit_new_device_data({'device_id': '123', 'temperature': 25.5})
    """
    try:
        device_id = data.get('device_id')
        if not device_id:
            log.warning("⚠️ [WebSocket] Tentative d'émission sans device_id.")
            return
        
        # Envoi ciblé vers la room de l'appareil
        room = f"device_{device_id}"
        log.info(f"🚀 [WebSocket] Émission de 'new_data' pour l'appareil {device_id}")
        
        if broadcast:
            # Envoyer à tous dans la room de cet appareil
            socketio.emit('new_data', data, room=room)
            
            # Également envoyer à la room "all_devices" pour les dashboards
            socketio.emit('new_data', data, room='all_devices')
        
        if to_specific_users:
            # Envoyer à des utilisateurs spécifiques
            for user_id in to_specific_users:
                user_room = f"user_{user_id}"
                socketio.emit('new_data', data, room=user_room)
                log.debug(f"📤 [WebSocket] Données envoyées à l'utilisateur {user_id}")
        
    except Exception as e:
        log.error(f"❌ [WebSocket] Erreur lors de l'émission de l'événement : {e}", exc_info=True)


def emit_device_status(device_id: str, status: str, additional_data=None):
    """
    Émettre un changement de statut d'appareil.
    
    Args:
        device_id (str): ID de l'appareil
        status (str): online, offline, error, etc.
        additional_data (dict): Données supplémentaires optionnelles
    
    Exemple:
        emit_device_status('device123', 'offline', {'last_seen': '2024-01-01'})
    """
    try:
        room = f"device_{device_id}"
        payload = {
            'device_id': device_id,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        if additional_data:
            payload.update(additional_data)
        
        socketio.emit('device_status', payload, room=room)
        socketio.emit('device_status', payload, room='all_devices')
        
        log.info(f"📊 [WebSocket] Statut de l'appareil {device_id} : {status}")
    except Exception as e:
        log.error(f"❌ [WebSocket] Erreur emit_device_status : {e}", exc_info=True)


def emit_alert(message: str, level: str = 'info', to_user=None, to_device=None):
    """
    Émettre une alerte aux utilisateurs.
    
    Args:
        message (str): Message de l'alerte
        level (str): info, warning, error, success
        to_user (str): user_id spécifique (optionnel)
        to_device (str): device_id spécifique (optionnel)
    
    Exemples:
        emit_alert('Température trop élevée!', 'warning', to_device='device123')
        emit_alert('Maintenance programmée', 'info')
    """
    try:
        alert_data = {
            'message': message,
            'level': level,
            'timestamp': datetime.now().isoformat()
        }
        
        if to_user:
            room = f"user_{to_user}"
            socketio.emit('alert', alert_data, room=room)
            log.info(f"🚨 [WebSocket] Alerte envoyée à l'utilisateur {to_user}")
        elif to_device:
            room = f"device_{to_device}"
            socketio.emit('alert', alert_data, room=room)
            log.info(f"🚨 [WebSocket] Alerte envoyée pour l'appareil {to_device}")
        else:
            socketio.emit('alert', alert_data, broadcast=True)
            log.info(f"🚨 [WebSocket] Alerte broadcast : {message}")
            
    except Exception as e:
        log.error(f"❌ [WebSocket] Erreur emit_alert : {e}", exc_info=True)


def emit_bulk_update(devices_data: list):
    """
    Émettre des mises à jour en masse pour plusieurs appareils.
    Optimisé pour les synchronisations périodiques.
    
    Args:
        devices_data (list): Liste de dictionnaires contenant les données des appareils
    
    Exemple:
        emit_bulk_update([
            {'device_id': '123', 'status': 'online'},
            {'device_id': '456', 'status': 'offline'}
        ])
    """
    try:
        log.info(f"📦 [WebSocket] Émission de mise à jour en masse pour {len(devices_data)} appareils")
        
        socketio.emit('bulk_update', {
            'devices': devices_data,
            'timestamp': datetime.now().isoformat(),
            'count': len(devices_data)
        }, room='all_devices')
        
        # Également envoyer à chaque room d'appareil individuellement
        for device_data in devices_data:
            device_id = device_data.get('device_id')
            if device_id:
                room = f"device_{device_id}"
                socketio.emit('device_update', device_data, room=room)
        
    except Exception as e:
        log.error(f"❌ [WebSocket] Erreur emit_bulk_update : {e}", exc_info=True)


def emit_notification(user_id: str, notification: dict):
    """
    Envoyer une notification à un utilisateur spécifique.
    
    Args:
        user_id (str): ID de l'utilisateur
        notification (dict): Contenu de la notification
    
    Exemple:
        emit_notification('user123', {
            'title': 'Nouvelle alerte',
            'body': 'Température anormale détectée',
            'type': 'warning'
        })
    """
    try:
        room = f"user_{user_id}"
        payload = {
            **notification,
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('notification', payload, room=room)
        log.info(f"🔔 [WebSocket] Notification envoyée à l'utilisateur {user_id}")
        
    except Exception as e:
        log.error(f"❌ [WebSocket] Erreur emit_notification : {e}", exc_info=True)


# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def get_connected_clients_count():
    """Retourne le nombre de clients connectés"""
    try:
        # Cette méthode peut varier selon la version de Flask-SocketIO
        return len(socketio.server.manager.rooms.get('/', {}).keys())
    except:
        return None


def disconnect_user(user_id: str, reason: str = "Déconnexion serveur"):
    """
    Déconnecter un utilisateur spécifique.
    
    Args:
        user_id (str): ID de l'utilisateur à déconnecter
        reason (str): Raison de la déconnexion
    """
    try:
        room = f"user_{user_id}"
        socketio.emit('force_disconnect', {
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }, room=room)
        
        log.info(f"⚠️ [WebSocket] Déconnexion forcée de l'utilisateur {user_id} : {reason}")
        
    except Exception as e:
        log.error(f"❌ [WebSocket] Erreur disconnect_user : {e}", exc_info=True)


# ========================================
# GESTIONNAIRE D'ERREURS WEBSOCKET
# ========================================

@socketio.on_error()
def error_handler(e):
    """Gestionnaire d'erreurs global pour Socket.IO"""
    log.error(f"❌ [WebSocket] Erreur Socket.IO : {e}", exc_info=True)
    emit('error', {
        'message': 'Une erreur est survenue',
        'timestamp': datetime.now().isoformat()
    })


@socketio.on_error_default
def default_error_handler(e):
    """Gestionnaire d'erreurs par défaut"""
    log.error(f"❌ [WebSocket] Erreur non gérée : {e}", exc_info=True)