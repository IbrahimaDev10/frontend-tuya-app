# tuya_service.py - Code extrait exactement du test qui marche

import os
import time
import hashlib
import hmac
import json
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

def get_timestamp():
    """Timestamp pour l'API Tuya"""
    return str(int(time.time() * 1000))

def generate_sign(access_id, access_secret, timestamp, method, path, query="", body="", access_token=""):
    """Générer la signature Tuya (corrigée)"""
    # Construction du string à signer
    content_hash = hashlib.sha256(body.encode()).hexdigest()
    
    # Headers à inclure dans la signature
    headers_to_sign = ""
    
    # Construction de l'URL complète
    url_path = path
    if query:
        url_path += f"?{query}"
    
    # String to sign format: method + "\n" + content-sha256 + "\n" + headers + "\n" + url
    string_to_sign = f"{method}\n{content_hash}\n{headers_to_sign}\n{url_path}"
    
    # Ajouter client_id, access_token (si présent) et timestamp
    final_string = f"{access_id}"
    if access_token:
        final_string += access_token
    final_string += f"{timestamp}{string_to_sign}"
    
    print(f"   🔍 String to sign: {final_string}")
    
    # Génération de la signature HMAC-SHA256
    signature = hmac.new(
        access_secret.encode(),
        final_string.encode(),
        hashlib.sha256
    ).hexdigest().upper()
    
    return signature

def make_tuya_request(endpoint, access_id, access_secret, method, path, query="", body="", access_token=""):
    """Faire une requête Tuya standardisée"""
    timestamp = get_timestamp()
    signature = generate_sign(access_id, access_secret, timestamp, method, path, query, body, access_token)
    
    headers = {
        'client_id': access_id,
        'sign': signature,
        't': timestamp,
        'sign_method': 'HMAC-SHA256',
        'Content-Type': 'application/json'
    }
    
    if access_token:
        headers['access_token'] = access_token
    
    url = f"{endpoint}{path}"
    if query:
        url += f"?{query}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=body)
        else:
            raise ValueError(f"Méthode HTTP non supportée: {method}")
        
        return response.json()
    except Exception as e:
        print(f"❌ Erreur requête {method} {path}: {e}")
        return {"success": False, "error": str(e)}

class TuyaClient:
    """TuyaClient basé exactement sur le test qui fonctionne"""
    
    def __init__(self):
        # Charger explicitement le .env
        load_dotenv()
        
        self.access_token = None
        self.token_expires_at = None
        self.uid = None
        self.is_connected = False
        
        # Configuration depuis .env
        self.access_id = os.getenv('ACCESS_ID')
        self.access_secret = os.getenv('ACCESS_KEY')
        self.endpoint = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com')
        
        print(f"🔧 TuyaClient init:")
        print(f"   Access ID: {self.access_id[:10]}..." if self.access_id else "None")
        print(f"   Endpoint: {self.endpoint}")
    
    def get_access_token(self):
        """Obtenir un token d'accès - Méthode exacte du test qui marche"""
        try:
            print("🔧 Récupération du token d'accès...")
            
            if not self.access_id or not self.access_secret:
                print("❌ ACCESS_ID ou ACCESS_KEY manquants dans .env")
                return False
            
            # Utiliser la fonction exacte du test qui marche
            response = make_tuya_request(
                self.endpoint, 
                self.access_id, 
                self.access_secret, 
                "GET", 
                "/v1.0/token", 
                "grant_type=1"
            )
            
            print(f"   📊 Token response: {response}")
            
            if response.get('success') and response.get('result'):
                result = response['result']
                self.access_token = result['access_token']
                self.uid = result['uid']
                
                # Calculer l'expiration
                expire_time = result.get('expire_time', 7200)  # 2h par défaut
                self.token_expires_at = datetime.now() + timedelta(seconds=expire_time)
                
                self.is_connected = True
                print(f"   ✅ Token obtenu: {self.access_token[:20]}...")
                return True
            else:
                print(f"   ❌ Erreur récupération token: {response}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur token: {e}")
            return False
    
    def is_token_valid(self):
        """Vérifier si le token est encore valide"""
        if not self.access_token or not self.token_expires_at:
            return False
        
        # Vérifier l'expiration (avec marge de 5 minutes)
        return datetime.now() < (self.token_expires_at - timedelta(minutes=5))
    
    def ensure_token(self):
        """S'assurer qu'on a un token valide"""
        if not self.is_token_valid():
            return self.get_access_token()
        return True
    
    def connect(self, username=None, password=None, country_code=None, app_type=None):
        """Connexion - Pour compatibilité avec l'ancienne interface"""
        return self.auto_connect_from_env()
    
    def auto_connect_from_env(self):
        """Connexion automatique depuis les variables d'environnement"""
        return self.get_access_token()
    
    def get_devices(self):
        """Récupérer la liste des appareils - Méthode exacte du test qui marche"""
        if not self.ensure_token():
            return {"success": False, "result": [], "error": "Token invalide"}
        
        try:
            print("🔍 Récupération liste appareils...")
            
            # Utiliser exactement la même méthode que le test qui marche
            response = make_tuya_request(
                self.endpoint,
                self.access_id,
                self.access_secret,
                "GET",
                "/v2.0/cloud/thing/device",
                "page_size=10",  # IMPORTANT: page_size=10 comme dans le test
                "",
                self.access_token
            )
            
            print(f"📱 Response: {response}")
            
            if response.get('success') and response.get('result'):
                devices = response['result']
                print(f"✅ {len(devices)} appareils récupérés")
                return {"success": True, "result": devices}
            else:
                print(f"❌ Erreur récupération appareils: {response}")
                return {"success": False, "result": [], "error": response.get('msg', 'Erreur inconnue')}
                
        except Exception as e:
            print(f"❌ Erreur get_devices: {e}")
            return {"success": False, "result": [], "error": str(e)}
    
    def get_device_status(self, device_id):
        """Récupérer le statut d'un appareil"""
        if not self.ensure_token():
            return {"success": False, "result": []}
        
        try:
            print(f"🔍 Récupération statut appareil {device_id}...")
            
            response = make_tuya_request(
                self.endpoint,
                self.access_id,
                self.access_secret,
                "GET",
                f"/v1.0/iot-03/devices/{device_id}/status",
                "",
                "",
                self.access_token
            )
            
            if response.get('success'):
                print(f"✅ Statut récupéré pour {device_id}")
                return response
            else:
                print(f"❌ Erreur statut {device_id}: {response}")
                return {"success": False, "result": [], "error": response.get('msg', 'Erreur')}
                
        except Exception as e:
            print(f"❌ Erreur get_device_status: {e}")
            return {"success": False, "result": [], "error": str(e)}
    
    def send_device_command(self, device_id, commands):
        """Envoyer une commande à un appareil"""
        if not self.ensure_token():
            return {"success": False, "error": "Token invalide"}
        
        try:
            print(f"🔧 Envoi commande à {device_id}: {commands}")
            
            # Corps de la requête
            body = json.dumps(commands)
            
            response = make_tuya_request(
                self.endpoint,
                self.access_id,
                self.access_secret,
                "POST",
                f"/v1.0/iot-03/devices/{device_id}/commands",
                "",
                body,
                self.access_token
            )
            
            if response.get('success'):
                print(f"✅ Commande envoyée à {device_id}")
                return response
            else:
                print(f"❌ Erreur commande {device_id}: {response}")
                return {"success": False, "error": response.get('msg', 'Erreur')}
                
        except Exception as e:
            print(f"❌ Erreur send_device_command: {e}")
            return {"success": False, "error": str(e)}
    
    def get_all_devices_with_details(self):
        """Récupérer tous les appareils avec détails complets"""
        try:
            print("🔍 Récupération tous appareils avec détails...")
            
            devices_response = self.get_devices()
            if not devices_response.get("success"):
                return {"success": False, "result": [], "error": "Impossible de récupérer les appareils"}
            
            devices = devices_response.get("result", [])
            print(f"📊 {len(devices)} appareils trouvés")
            
            # Les appareils de l'endpoint /v2.0/cloud/thing/device ont déjà tous les détails
            detailed_devices = []
            for device in devices:
                # Ajouter des infos calculées
                device_info = device.copy()
                device_info["device_id"] = device.get("id")  # Normaliser l'ID
                device_info["online_status"] = "Online" if device.get("isOnline") else "Offline"
                detailed_devices.append(device_info)
            
            print(f"✅ {len(detailed_devices)} appareils avec détails")
            return {"success": True, "result": detailed_devices}
            
        except Exception as e:
            print(f"❌ Erreur récupération appareils détaillés: {e}")
            return {"success": False, "result": [], "error": str(e)}
    
    def get_device_current_values(self, device_id):
        """Récupérer les valeurs actuelles d'un appareil"""
        try:
            print(f"🔍 Récupération valeurs actuelles {device_id}...")
            status_response = self.get_device_status(device_id)
            
            if not status_response.get("success"):
                return {"success": False, "message": "Erreur récupération statut"}
            
            status_data = status_response.get("result", [])
            print(f"📊 Status data: {len(status_data)} éléments")
            
            # Mapper les codes Tuya vers des noms plus clairs
            values = {}
            for item in status_data:
                code = item.get("code", "")
                value = item.get("value")
                
                # Mapping pour les compteurs d'énergie
                if code == "cur_voltage":
                    values["tension"] = value / 100 if value else None
                elif code == "cur_current":
                    values["courant"] = value / 1000 if value else None
                elif code == "cur_power":
                    values["puissance"] = value / 10 if value else None
                elif code == "add_ele":
                    values["energie"] = value / 1000 if value else None
                elif code == "switch":
                    values["etat_switch"] = bool(value)
                else:
                    values[code] = value
            
            print(f"✅ Valeurs mappées: {values}")
            
            return {
                "success": True,
                "device_id": device_id,
                "timestamp": datetime.utcnow().isoformat(),
                "values": values,
                "raw_status": status_data
            }
            
        except Exception as e:
            print(f"❌ Erreur valeurs actuelles {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def toggle_device(self, device_id, state=None):
        """Allumer/éteindre un appareil avec détection automatique du code switch"""
        try:
            print(f"🔧 Toggle appareil {device_id} - state: {state}")
            
            # 1. Récupérer l'état actuel pour détecter le bon code switch
            print(f"🔍 Récupération valeurs actuelles {device_id}...")
            status_response = self.get_device_status(device_id)
            
            if not status_response.get("success"):
                return {"success": False, "error": "Impossible de récupérer le statut de l'appareil"}
            
            status_data = status_response.get("result", [])
            print(f"📊 Status data: {len(status_data)} éléments")
            
            # 2. ✅ DÉTECTER LE BON CODE SWITCH automatiquement
            switch_code = None
            current_state = None
            
            # Mapper tous les codes disponibles
            current_values = {}
            for item in status_data:
                code = item.get("code", "")
                value = item.get("value")
                current_values[code] = value
            
            print(f"✅ Valeurs mappées: {current_values}")
            
            # Chercher le bon code de switch dans l'ordre de priorité
            switch_candidates = ['switch_1', 'switch', 'switch_led', 'power', 'switch_2']
            
            for candidate in switch_candidates:
                if candidate in current_values:
                    switch_code = candidate
                    current_state = current_values[candidate]
                    print(f"🔍 Code switch détecté: {switch_code} = {current_state}")
                    break
            
            if switch_code is None:
                available_codes = list(current_values.keys())
                return {
                    "success": False, 
                    "error": f"Aucun switch trouvé. Codes disponibles: {available_codes}"
                }
            
            # 3. Calculer le nouvel état
            if state is None:
                # Mode toggle : inverser l'état actuel
                new_state = not current_state
                action = "Basculé"
                print(f"🔄 Toggle: {current_state} -> {new_state}")
            else:
                new_state = bool(state)
                action = "Allumé" if new_state else "Éteint"
                print(f"🔧 État forcé: {new_state}")
            
            # 4. ✅ Envoyer la commande avec le BON CODE détecté
            commands = {
                "commands": [
                    {
                        "code": switch_code,  # ← CORRECTION ICI: utilise le code détecté
                        "value": new_state
                    }
                ]
            }
            
            print(f"🔧 Envoi commande à {device_id}: {commands}")
            
            response = self.send_device_command(device_id, commands)
            
            if response.get("success"):
                return {
                    "success": True,
                    "new_state": new_state,
                    "previous_state": current_state,
                    "action": action.lower(),
                    "message": f"Appareil {action.lower()} avec succès",
                    "switch_code_used": switch_code,  # Info debug
                    "device_id": device_id,
                    "response": response
                }
            else:
                return {
                    "success": False,
                    "error": f"Erreur commande: {response.get('msg', 'Inconnue')}",
                    "attempted_code": switch_code,
                    "response": response
                }
            
        except Exception as e:
            print(f"❌ Erreur toggle appareil {device_id}: {e}")
            return {"success": False, "error": str(e)}
        
    def get_connection_info(self):
        """Récupérer les informations de connexion actuelle"""
        return {
            "is_connected": self.is_connected,
            "endpoint": self.endpoint,
            "access_id": self.access_id[:10] + "..." if self.access_id else None,
            "uid": self.uid,
            "token_valid": self.is_token_valid(),
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "last_check": datetime.utcnow().isoformat()
        }
    
    def reconnect_if_needed(self):
        """Reconnexion automatique si nécessaire"""
        if not self.is_token_valid():
            print("🔄 Reconnexion Tuya nécessaire...")
            return self.auto_connect_from_env()
        return True
    
    def check_connection(self):
        """Vérifier si la connexion est toujours active"""
        if not self.is_connected:
            return False
        
        try:
            # Test simple avec récupération d'un appareil (page_size=1)
            response = make_tuya_request(
                self.endpoint,
                self.access_id,
                self.access_secret,
                "GET",
                "/v2.0/cloud/thing/device",
                "page_size=1",
                "",
                self.access_token
            )
            success = response.get("success", False)
            
            print(f"🔍 Test connexion - Success: {success}")
            return success
        except Exception as e:
            print(f"❌ Erreur test connexion: {e}")
            self.is_connected = False
            return False
    
    # Aliases pour compatibilité
    def get_spaces(self):
        """Alias pour get_devices (compatibilité)"""
        return self.get_devices()
    
    def get_token_info(self):
        """Récupérer les informations du token"""
        return {
            "access_token": self.access_token,
            "uid": self.uid,
            "expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "valid": self.is_token_valid()
        }