# tuya_service.py - VERSION CORRIGÉE SANS ERREURS

import os
import time
import hashlib
import hmac
import json
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote

def get_timestamp():
    """Timestamp pour l'API Tuya"""
    return str(int(time.time() * 1000))

def generate_sign_fixed(access_id, access_secret, timestamp, method, path, query="", body="", access_token=""):
    """✅ CORRIGÉ: Générer la signature Tuya avec gestion correcte de la pagination"""
    # Construction du hash du body
    content_hash = hashlib.sha256(body.encode()).hexdigest()
    
    # Headers à inclure dans la signature (vide pour Tuya)
    headers_to_sign = ""
    
    # ✅ CORRECTION: Construction correcte de l'URL avec query
    url_path = path
    if query:
        # S'assurer que les paramètres sont correctement ordonnés et encodés
        if isinstance(query, dict):
            # Si c'est un dict, le convertir en string
            sorted_params = sorted(query.items())
            query_string = urlencode(sorted_params)
        else:
            # Si c'est déjà un string, le garder tel quel
            query_string = query
        
        url_path += f"?{query_string}"
    
    # String to sign format: method + "\n" + content-sha256 + "\n" + headers + "\n" + url
    string_to_sign = f"{method}\n{content_hash}\n{headers_to_sign}\n{url_path}"
    
    # ✅ CORRECTION: Construction finale du string avec le bon ordre
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

def make_tuya_request_fixed(endpoint, access_id, access_secret, method, path, query="", body="", access_token=""):
    """✅ CORRIGÉ: Requête Tuya avec signature corrigée pour pagination"""
    timestamp = get_timestamp()
    signature = generate_sign_fixed(access_id, access_secret, timestamp, method, path, query, body, access_token)
    
    headers = {
        'client_id': access_id,
        'sign': signature,
        't': timestamp,
        'sign_method': 'HMAC-SHA256',
        'Content-Type': 'application/json'
    }
    
    if access_token:
        headers['access_token'] = access_token
    
    # ✅ CORRECTION: Construction URL avec gestion correcte des paramètres
    url = f"{endpoint}{path}"
    if query:
        if isinstance(query, dict):
            # Si c'est un dict, le convertir proprement
            query_string = urlencode(query)
        else:
            # Si c'est déjà un string
            query_string = query
        url += f"?{query_string}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=body)
        else:
            raise ValueError(f"Méthode HTTP non supportée: {method}")
        
        response_json = response.json()
        
        # Debug pour les erreurs de signature
        if not response_json.get('success') and response_json.get('code') == 1010:
            print(f"   ❌ Erreur signature détectée:")
            print(f"      URL: {url}")
            print(f"      Headers: {headers}")
            print(f"      Response: {response_json}")
        
        return response_json
        
    except Exception as e:
        print(f"❌ Erreur requête {method} {path}: {e}")
        return {"success": False, "error": str(e)}

class TuyaClient:
    """TuyaClient COMPLET avec toutes les méthodes nécessaires"""
    
    def __init__(self):
        load_dotenv()
        
        self.access_token = None
        self.token_expires_at = None
        self.uid = None
        self.is_connected = False
        self._connection_status = False  # ✅ AJOUTÉ: Pour is_connected()
        
        # Configuration depuis .env
        self.access_id = os.getenv('ACCESS_ID')
        self.access_secret = os.getenv('ACCESS_KEY')
        self.endpoint = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com')
        
        print(f"🔧 TuyaClient init:")
        print(f"   Access ID: {self.access_id[:10]}..." if self.access_id else "None")
        print(f"   Endpoint: {self.endpoint}")
    
    def get_access_token(self):
        """Obtenir un token d'accès"""
        try:
            print("🔧 Récupération du token d'accès...")
            
            if not self.access_id or not self.access_secret:
                print("❌ ACCESS_ID ou ACCESS_KEY manquants dans .env")
                return False
            
            response = make_tuya_request_fixed(
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
                
                expire_time = result.get('expire_time', 7200)
                self.token_expires_at = datetime.now() + timedelta(seconds=expire_time)
                
                self.is_connected = True
                self._connection_status = True  # ✅ AJOUTÉ
                print(f"   ✅ Token obtenu: {self.access_token[:20]}...")
                return True
            else:
                print(f"   ❌ Erreur récupération token: {response}")
                self.is_connected = False
                self._connection_status = False  # ✅ AJOUTÉ
                return False
                
        except Exception as e:
            print(f"❌ Erreur token: {e}")
            self.is_connected = False
            self._connection_status = False  # ✅ AJOUTÉ
            return False
    
    def is_token_valid(self):
        """Vérifier si le token est encore valide"""
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now() < (self.token_expires_at - timedelta(minutes=5))
    
    def ensure_token(self):
        """S'assurer qu'on a un token valide"""
        if not self.is_token_valid():
            return self.get_access_token()
        return True
    
    # ✅ AJOUTÉ: Méthode manquante pour vérifier la connexion
    def is_connected_method(self):
        """Vérifier si la connexion est active"""
        return self._connection_status and self.is_token_valid()
    
    # ✅ AJOUTÉ: Méthode manquante pour reconnecter
    def reconnect_if_needed(self):
        """Reconnecter si nécessaire"""
        try:
            print("🔄 Vérification reconnexion...")
            
            # Vérifier si une reconnexion est nécessaire
            if not self.is_connected_method():
                print("   ℹ️ Reconnexion nécessaire")
                success = self.get_access_token()
                if success:
                    print("   ✅ Reconnexion réussie")
                    return True
                else:
                    print("   ❌ Reconnexion échouée")
                    return False
            else:
                print("   ✅ Connexion déjà active")
                return True
                
        except Exception as e:
            print(f"❌ Erreur lors de la reconnexion: {e}")
            return False
    
    # ✅ MÉTHODES DE COMPATIBILITÉ
    def connect(self, username=None, password=None, country_code=None, app_type=None):
        """Compatibilité: méthode connect"""
        return self.get_access_token()
    
    def auto_connect_from_env(self):
        """Compatibilité: auto-connect depuis env"""
        return self.get_access_token()
    
    def get_devices(self):
        """Récupérer la liste des appareils - VERSION OPTIMISÉE"""
        if not self.ensure_token():
            return {"success": False, "result": [], "error": "Token invalide"}
        
        try:
            print("🔍 Récupération liste appareils...")
            
            # ✅ UTILISER LA PAGINATION CORRIGÉE
            all_devices = []
            page_no = 1
            max_pages = 50
            page_size = 20  # Taille de page qui fonctionne
            
            while page_no <= max_pages:
                print(f"📄 Récupération page {page_no}...")
                
                # Construire query pour pagination
                query = {
                    "page_size": page_size,
                    "page_no": page_no
                }
                
                response = make_tuya_request_fixed(
                    self.endpoint,
                    self.access_id,
                    self.access_secret,
                    "GET",
                    "/v2.0/cloud/thing/device",
                    query,
                    "",
                    self.access_token
                )
                
                if not response.get('success'):
                    error_msg = response.get('msg', 'Erreur inconnue')
                    print(f"❌ Erreur page {page_no}: {error_msg}")
                    
                    if page_no == 1:
                        return {"success": False, "result": [], "error": f"Erreur page 1: {error_msg}"}
                    else:
                        print(f"⚠️ Arrêt à la page {page_no}")
                        break
                
                # Extraire les appareils
                page_devices = response.get('result', [])
                
                if isinstance(page_devices, dict):
                    devices_list = page_devices.get('list', page_devices.get('devices', []))
                    has_more = page_devices.get('has_more', False)
                else:
                    devices_list = page_devices if isinstance(page_devices, list) else []
                    has_more = len(devices_list) == page_size
                
                if devices_list:
                    all_devices.extend(devices_list)
                    print(f"   ✅ Page {page_no}: {len(devices_list)} appareils (total: {len(all_devices)})")
                else:
                    print(f"   ℹ️ Page {page_no}: Aucun appareil, fin")
                    break
                
                # Conditions d'arrêt
                if len(devices_list) < page_size:
                    print(f"   🏁 Page incomplète, fin de pagination")
                    break
                
                if isinstance(page_devices, dict) and not has_more:
                    print(f"   🏁 API indique fin des données")
                    break
                
                page_no += 1
                time.sleep(0.1)  # Pause pour éviter rate limiting
            
            print(f"✅ Total: {len(all_devices)} appareils récupérés")
            return {"success": True, "result": all_devices}
            
        except Exception as e:
            print(f"❌ Erreur get_devices: {e}")
            return {"success": False, "result": [], "error": str(e)}
    
    def get_all_devices_with_details(self):
        """Récupérer tous les appareils avec détails complets"""
        try:
            print("🔍 Récupération tous appareils avec détails...")
            
            devices_response = self.get_devices()
            
            if not devices_response.get("success"):
                return {"success": False, "result": [], "error": "Impossible de récupérer les appareils"}
            
            devices = devices_response.get("result", [])
            print(f"📊 {len(devices)} appareils trouvés")
            
            # Traiter chaque appareil
            detailed_devices = []
            online_count = 0
            offline_count = 0
            
            for device in devices:
                device_info = device.copy()
                device_info["device_id"] = device.get("id")
                is_online = device.get("isOnline", False)
                device_info["online_status"] = "Online" if is_online else "Offline"
                
                if is_online:
                    online_count += 1
                else:
                    offline_count += 1
                
                detailed_devices.append(device_info)
            
            print(f"✅ {len(detailed_devices)} appareils avec détails")
            print(f"📊 Statuts: {online_count} en ligne, {offline_count} hors ligne")
            
            return {
                "success": True, 
                "result": detailed_devices,
                "total_count": len(detailed_devices),
                "online_count": online_count,
                "offline_count": offline_count
            }
            
        except Exception as e:
            print(f"❌ Erreur récupération appareils détaillés: {e}")
            return {"success": False, "result": [], "error": str(e)}
    
    def get_device_status(self, device_id):
        """Récupérer le statut d'un appareil - VERSION CORRIGÉE SANS NORMALISATION"""
        if not self.ensure_token():
            return {"success": False, "result": [], "error": "Token invalide"}
        
        try:
            # Vérifier la reconnexion
            if not self.reconnect_if_needed():
                return {"success": False, "result": [], "error": "Impossible de se reconnecter"}
            
            response = make_tuya_request_fixed(
                self.endpoint,
                self.access_id,
                self.access_secret,
                "GET",
                f"/v1.0/iot-03/devices/{device_id}/status",
                "",
                "",
                self.access_token
            )

            # ✅ CORRECTION PRINCIPALE : RETOURNER DIRECTEMENT LA RÉPONSE TUYA
            # L'API Tuya retourne {"success": true, "result": [...]}
            # On ne doit PAS modifier cette structure !
            
            if response.get('success'):
                # Retourner directement la réponse Tuya sans modification
                return response
            else:
                return {
                    "success": False,
                    "result": [],
                    "error": response.get('msg', 'Erreur inconnue')
                }
        
        except Exception as e:
            return {
                "success": False,
                "result": [],
                "error": str(e)
            }


    def send_device_command(self, device_id, commands):
        """Envoyer une commande à un appareil"""
        if not self.ensure_token():
            return {"success": False, "error": "Token invalide"}
        
        try:
            # ✅ AJOUTÉ: Vérifier reconnexion si nécessaire
            if not self.reconnect_if_needed():
                return {"success": False, "error": "Impossible de se reconnecter"}
            
            body = json.dumps(commands)
            
            response = make_tuya_request_fixed(
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
                return response
            else:
                return {"success": False, "error": response.get('msg', 'Erreur')}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    from datetime import datetime

    # ✅ AJOUTÉ: Méthode manquante get_device_current_values - VERSION AMÉLIORÉE
    def get_device_current_values(self, device_id):
        """Récupérer les valeurs actuelles d'un appareil avec mapping intelligent et VRAI statut en ligne"""
        try:
            print(f"🔍 Récupération valeurs actuelles pour {device_id}")
            
            # ✅ CORRECTION 1: D'abord récupérer le VRAI statut en ligne
            device_info_response = self.get_device_info(device_id)
            real_online_status = False
            
            if device_info_response.get('success'):
                device_info = device_info_response.get('result', {})
                real_online_status = device_info.get('online', False)  # Vrai statut Tuya
                print(f"🌐 Statut réel en ligne depuis Tuya: {real_online_status}")
            else:
                print(f"⚠️ Impossible de récupérer le statut en ligne, utilisation de fallback")
            
            # ✅ CORRECTION 2: Récupérer les données de statut
            status_response = self.get_device_status(device_id)
            
            if not status_response.get('success'):
                print(f"❌ Erreur récupération statut: {status_response.get('error', 'Erreur inconnue')}")
                return {
                    "success": False, 
                    "values": {}, 
                    "is_online": False,
                    "error": status_response.get('error', 'Erreur inconnue')
                }
            
            # L'API Tuya retourne TOUJOURS une liste dans result
            status_data = status_response.get('result', [])
            
            # Vérification de sécurité
            if not isinstance(status_data, list):
                print(f"⚠️ Format de réponse inattendu: {type(status_data)} - {status_data}")
                if isinstance(status_data, dict) and "status" in status_data:
                    status_data = status_data["status"]
                else:
                    status_data = []
            
            print(f"📊 Status data reçu: {len(status_data)} éléments")
            print(f"🔍 Données brutes: {status_data}")
            
            # ✅ CORRECTION 3: Si pas de statut réel récupéré, utiliser une heuristique intelligente
            if device_info_response.get('success') == False:
                real_online_status = self._detect_online_from_values(status_data)
                print(f"🔍 Statut détecté par heuristique: {real_online_status}")
            
            # ✅ MAPPING INTELLIGENT des valeurs Tuya
            values = {}
            for item in status_data:
                if isinstance(item, dict):
                    code = item.get('code', '')
                    value = item.get('value')
                    
                    print(f"   🔍 Processing: {code} = {value}")

                    # 🧠 Mapping des champs courants avec gestion des valeurs null/0
                    if code == "cur_voltage":
                        # Tension en centièmes de volts -> Volts
                        values["tension"] = value / 100 if value is not None and value != 0 else None
                    elif code == "cur_current":
                        # Courant en millièmes d'ampères -> Ampères  
                        values["courant"] = value / 1000 if value is not None and value != 0 else None
                    elif code == "cur_power":
                        # Puissance en dixièmes de watts -> Watts
                        values["puissance"] = value / 10 if value is not None and value != 0 else None
                    elif code == "add_ele":
                        # Énergie en millièmes de kWh -> kWh
                        values["energie"] = value / 1000 if value is not None else None
                    elif code in ["switch", "switch_1", "switch_led"]:
                        # État du switch
                        values["etat_switch"] = bool(value) if value is not None else None
                    elif code == "temp_current":
                        # Température en dixièmes de degrés -> Degrés
                        values["temperature"] = value / 10 if value is not None else None
                    elif code == "humidity":
                        # Humidité en pourcentage
                        values["humidite"] = value if value is not None else None
                    
                    # ✅ AJOUT: Gestion des appareils triphasés
                    elif code == "phase_a":
                        values["phase_a"] = value  # Données encodées en base64
                    elif code == "phase_b":
                        values["phase_b"] = value  # Données encodées en base64
                    elif code == "phase_c":
                        values["phase_c"] = value  # Données encodées en base64
                    elif code == "total_forward_energy":
                        values["energie_totale"] = value  # Énergie totale consommée
                    elif code == "forward_energy_total":
                        values["energie_totale"] = value  # Autre nom pour l'énergie totale
                    elif code == "supply_frequency":
                        values["frequence"] = value  # Fréquence du réseau (50Hz)
                    elif code == "fault":
                        values["defaut"] = value  # Code de défaut
                    elif code == "leakage_current":
                        values["courant_fuite"] = value  # Courant de fuite
                    elif code == "switch_prepayment":
                        values["prepaiement"] = bool(value) if value is not None else None
                    
                    # ✅ AJOUT: Gestion des thermostats
                    elif code == "temp_set":
                        values["temperature_consigne"] = value
                    elif code == "mode":
                        values["mode"] = value  # manuel, auto, etc.
                    elif code == "eco":
                        values["mode_eco"] = bool(value) if value is not None else None
                    elif code == "child_lock":
                        values["verrouillage_enfant"] = bool(value) if value is not None else None
                    
                    # ✅ AJOUT: Autres codes courants
                    elif code == "countdown_1":
                        values["minuterie"] = value  # Minuterie en secondes
                    elif code == "relay_status":
                        values["etat_relais"] = value  # État du relais
                    elif code == "light_mode":
                        values["mode_eclairage"] = value  # Mode éclairage
                    
                    else:
                        # Conserver tous les autres codes bruts pour debug et compatibilité future
                        values[code] = value
            
            print(f"✅ Valeurs actuelles récupérées: {len(values)} paramètres")
            print(f"🔍 Valeurs mappées: {values}")
            print(f"🌐 Statut final en ligne: {real_online_status}")
            
            return {
                "success": True,
                "values": values,
                "is_online": real_online_status,  # ✅ VRAI STATUT EN LIGNE
                "device_id": device_id,
                "raw_status": status_data,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"❌ Erreur get_device_current_values {device_id}: {e}")
            import traceback
            print(f"🔍 Traceback: {traceback.format_exc()}")
            return {
                "success": False, 
                "values": {}, 
                "is_online": False,
                "error": str(e)
            }
    
    # ✅ AJOUTÉ: Méthode toggle_device COMPLÈTE et ROBUSTE
    def toggle_device(self, device_id, state=None):
        """Allumer/éteindre un appareil avec détection automatique du code switch - VERSION CORRIGÉE"""
        try:
            print(f"🔧 Toggle appareil {device_id} - state: {state}")
            
            if not self.ensure_token():
                return {"success": False, "error": "Token invalide"}
            
            if not self.reconnect_if_needed():
                return {"success": False, "error": "Impossible de se reconnecter"}
            
            # 1. Récupérer l'état actuel avec la fonction corrigée
            print(f"🔍 Récupération valeurs actuelles {device_id}...")
            values_response = self.get_device_current_values(device_id)
            
            if not values_response.get("success"):
                return {
                    "success": False, 
                    "error": f"Impossible de récupérer le statut: {values_response.get('error')}"
                }
            
            current_values = values_response.get("values", {})
            raw_status = values_response.get("raw_status", [])
            
            print(f"✅ Valeurs disponibles: {list(current_values.keys())}")
            print(f"📊 Raw status: {raw_status}")
            
            # 2. ✅ DÉTECTER LE BON CODE SWITCH dans les données brutes ET mappées
            switch_code = None
            current_state = None
            
            # Chercher dans les valeurs mappées d'abord
            if "etat_switch" in current_values:
                current_state = current_values["etat_switch"]
                # Retrouver le code original dans raw_status
                for item in raw_status:
                    if isinstance(item, dict) and item.get('code') in ['switch', 'switch_1', 'switch_led']:
                        switch_code = item.get('code')
                        break
            
            # Si pas trouvé, chercher directement dans raw_status
            if switch_code is None:
                switch_candidates = ['switch_1', 'switch', 'switch_led', 'power', 'switch_2']
                
                for item in raw_status:
                    if isinstance(item, dict):
                        code = item.get('code', '')
                        if code in switch_candidates:
                            switch_code = code
                            current_state = item.get('value')
                            print(f"🔍 Code switch détecté dans raw: {switch_code} = {current_state}")
                            break
            
            if switch_code is None:
                # Debug complet
                all_codes = []
                for item in raw_status:
                    if isinstance(item, dict):
                        all_codes.append(item.get('code'))
                
                return {
                    "success": False, 
                    "error": f"Aucun switch trouvé. Codes disponibles: {all_codes}",
                    "debug_raw_status": raw_status,
                    "debug_mapped_values": current_values
                }
            
            print(f"✅ Switch trouvé: {switch_code} = {current_state}")
            
            # 3. Calculer le nouvel état
            if state is None:
                new_state = not current_state
                action = "Basculé"
            else:
                new_state = bool(state)
                action = "Allumé" if new_state else "Éteint"
            
            print(f"🔄 {action}: {current_state} -> {new_state}")
            
            # 4. Envoyer la commande
            commands = {
                "commands": [
                    {
                        "code": switch_code,
                        "value": new_state
                    }
                ]
            }
            
            print(f"🔧 Envoi commande: {commands}")
            
            response = self.send_device_command(device_id, commands)
            
            if response.get("success"):
                return {
                    "success": True,
                    "new_state": new_state,
                    "previous_state": current_state,
                    "action": action.lower(),
                    "message": f"Appareil {action.lower()} avec succès",
                    "switch_code_used": switch_code,
                    "device_id": device_id
                }
            else:
                return {
                    "success": False,
                    "error": f"Erreur commande: {response.get('msg', 'Inconnue')}",
                    "attempted_code": switch_code,
                    "tuya_response": response
                }
            
        except Exception as e:
            print(f"❌ Erreur toggle appareil {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    # ✅ AJOUTÉ: Méthode control_device pour compatibilité
    def control_device(self, device_id, command, value=None):
        """Méthode de compatibilité pour contrôler un appareil"""
        if command == 'switch':
            return self.toggle_device(device_id, value)
        else:
            # Autres commandes
            command_data = {
                "commands": [
                    {
                        "code": command,
                        "value": value
                    }
                ]
            }
            return self.send_device_command(device_id, command_data)
    
    # ✅ AJOUTÉ: Méthodes supplémentaires pour compatibilité
    def get_device_info(self, device_id):
        """Récupérer les informations d'un appareil"""
        if not self.ensure_token():
            return {"success": False, "result": {}, "error": "Token invalide"}
        
        try:
            if not self.reconnect_if_needed():
                return {"success": False, "result": {}, "error": "Impossible de se reconnecter"}
            
            response = make_tuya_request_fixed(
                self.endpoint,
                self.access_id,
                self.access_secret,
                "GET",
                f"/v1.0/iot-03/devices/{device_id}",
                "",
                "",
                self.access_token
            )
            
            if response.get('success'):
                return response
            else:
                return {"success": False, "result": {}, "error": response.get('msg', 'Erreur')}
                
        except Exception as e:
            return {"success": False, "result": {}, "error": str(e)}
    
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
    
    def check_connection(self):
        """Vérifier si la connexion est toujours active"""
        if not self.is_connected:
            return False
        
        try:
            # Test simple avec récupération d'un appareil (page_size=1)
            response = make_tuya_request_fixed(
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
    
    # ✅ AJOUTÉ: Méthodes d'alias pour compatibilité
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
    
    def get_device_logs(self, device_id, start_time=None, end_time=None):
        """Récupérer les logs d'un appareil"""
        if not self.ensure_token():
            return {"success": False, "result": [], "error": "Token invalide"}
        
        try:
            if not self.reconnect_if_needed():
                return {"success": False, "result": [], "error": "Impossible de se reconnecter"}
            
            # Paramètres de requête
            query_params = {}
            if start_time:
                query_params['start_time'] = str(int(start_time.timestamp() * 1000))
            if end_time:
                query_params['end_time'] = str(int(end_time.timestamp() * 1000))
            
            response = make_tuya_request_fixed(
                self.endpoint,
                self.access_id,
                self.access_secret,
                "GET",
                f"/v1.0/iot-03/devices/{device_id}/logs",
                query_params,
                "",
                self.access_token
            )
            
            if response.get('success'):
                return response
            else:
                return {"success": False, "result": [], "error": response.get('msg', 'Erreur')}
                
        except Exception as e:
            return {"success": False, "result": [], "error": str(e)}


# =================== SCRIPT DE TEST ===================

def test_tuya_complete():
    """Test complet du TuyaClient"""
    print("🧪 === TEST TUYA CLIENT COMPLET ===")
    
    try:
        client = TuyaClient()
        
        # Test connexion
        if not client.auto_connect_from_env():
            print("❌ Connexion échouée")
            return False
        
        print("✅ Connexion réussie")
        
        # Test récupération appareils
        devices_result = client.get_all_devices_with_details()
        
        if devices_result.get("success"):
            devices = devices_result.get("result", [])
            print(f"✅ {len(devices)} appareils récupérés")
            
            # Test sur le premier appareil
            if devices:
                test_device = devices[0]
                device_id = test_device.get("id")
                device_name = test_device.get("name", "Appareil test")
                
                print(f"🔧 Test sur {device_name} ({device_id})")
                
                # Test statut
                status = client.get_device_current_values(device_id)
                if status.get("success"):
                    print(f"✅ Statut: {status.get('values', {})}")
                    
                    # Test toggle (attention: cela va vraiment contrôler l'appareil!)
                    # Décommentez seulement si vous voulez tester le contrôle
                    # toggle_result = client.toggle_device(device_id)
                    # print(f"🔧 Toggle: {toggle_result}")
                    
                else:
                    print(f"❌ Erreur statut: {status.get('error')}")
                
                return True
            else:
                print("⚠️ Aucun appareil trouvé pour test")
                return True
        else:
            print(f"❌ Erreur récupération appareils: {devices_result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test: {e}")
        return False

if __name__ == "__main__":
    test_tuya_complete()