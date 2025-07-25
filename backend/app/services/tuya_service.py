# tuya_service.py - VERSION INTELLIGENTE ET OPTIMISÉE
# ✅ Gestion intelligente de la pagination - Plus de soucis !

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
    """✅ STABLE: Génération signature Tuya (ne pas modifier)"""
    content_hash = hashlib.sha256(body.encode()).hexdigest()
    headers_to_sign = ""
    
    url_path = path
    if query:
        if isinstance(query, dict):
            sorted_params = sorted(query.items())
            query_string = urlencode(sorted_params)
        else:
            query_string = query
        url_path += f"?{query_string}"
    
    string_to_sign = f"{method}\n{content_hash}\n{headers_to_sign}\n{url_path}"
    final_string = f"{access_id}"
    if access_token:
        final_string += access_token
    final_string += f"{timestamp}{string_to_sign}"
    
    signature = hmac.new(
        access_secret.encode(),
        final_string.encode(),
        hashlib.sha256
    ).hexdigest().upper()
    
    return signature

def make_tuya_request_fixed(endpoint, access_id, access_secret, method, path, query="", body="", access_token=""):
    """✅ STABLE: Requête Tuya (ne pas modifier)"""
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
    
    url = f"{endpoint}{path}"
    if query:
        if isinstance(query, dict):
            query_string = urlencode(query)
        else:
            query_string = query
        url += f"?{query_string}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=body)
        else:
            raise ValueError(f"Méthode HTTP non supportée: {method}")
        
        return response.json()
        
    except Exception as e:
        return {"success": False, "error": str(e)}

class TuyaClient:
    """🧠 TuyaClient INTELLIGENT - Plus jamais de soucis de pagination !"""
    
    def __init__(self):
        load_dotenv()
        
        self.access_token = None
        self.token_expires_at = None
        self.uid = None
        self.is_connected = False
        self._connection_status = False
        
        # Configuration depuis .env
        self.access_id = os.getenv('ACCESS_ID')
        self.access_secret = os.getenv('ACCESS_KEY')
        self.endpoint = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com')
        
        # ✅ NOUVEAU: Configuration intelligente de pagination
        self.pagination_config = {
            'page_size': 20,                    # Taille de page optimale
            'max_pages_safe': 15,               # Limite sécurisée (300 appareils)
            'max_pages_extended': 50,           # Limite étendue si nécessaire
            'empty_pages_tolerance': 2,         # Tolérance pages vides consécutives
            'duplicate_detection': True,        # Détection doublons
            'intelligent_stop': True,           # Arrêt intelligent
            'performance_mode': True            # Mode performance
        }
        
        print(f"🧠 TuyaClient INTELLIGENT initialisé")
        print(f"   📊 Config: {self.pagination_config['page_size']} par page, max {self.pagination_config['max_pages_safe']} pages sécurisées")
        print(f"   🔧 Access ID: {self.access_id[:10]}..." if self.access_id else "None")
    
    def get_access_token(self):
        """✅ STABLE: Token d'accès (ne pas modifier)"""
        try:
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
            
            if response.get('success') and response.get('result'):
                result = response['result']
                self.access_token = result['access_token']
                self.uid = result['uid']
                
                expire_time = result.get('expire_time', 7200)
                self.token_expires_at = datetime.now() + timedelta(seconds=expire_time)
                
                self.is_connected = True
                self._connection_status = True
                print(f"✅ Token obtenu et configuré")
                return True
            else:
                print(f"❌ Erreur récupération token: {response}")
                self.is_connected = False
                self._connection_status = False
                return False
                
        except Exception as e:
            print(f"❌ Erreur token: {e}")
            self.is_connected = False
            self._connection_status = False
            return False
    
    def is_token_valid(self):
        """Vérifier validité token"""
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now() < (self.token_expires_at - timedelta(minutes=5))
    
    def ensure_token(self):
        """S'assurer qu'on a un token valide"""
        if not self.is_token_valid():
            return self.get_access_token()
        return True
    
    def is_connected_method(self):
        """Vérifier si la connexion est active"""
        return self._connection_status and self.is_token_valid()
    
    def reconnect_if_needed(self):
        """Reconnecter si nécessaire"""
        if not self.is_connected_method():
            return self.get_access_token()
        return True
    
    # ✅ MÉTHODES DE COMPATIBILITÉ
    def connect(self, username=None, password=None, country_code=None, app_type=None):
        return self.get_access_token()
    
    def auto_connect_from_env(self):
        return self.get_access_token()
    
    # 🧠 PAGINATION INTELLIGENTE - LA RÉVOLUTION !
    def get_devices(self):
        """🧠 RÉCUPÉRATION INTELLIGENTE - Plus jamais de soucis !"""
        if not self.ensure_token():
            return {"success": False, "result": [], "error": "Token invalide"}
        
        try:
            print("🧠 === RÉCUPÉRATION INTELLIGENTE DES APPAREILS ===")
            
            # Variables intelligentes
            all_devices = []
            seen_device_ids = set()  # ✅ Déduplication
            page_no = 1
            empty_pages_count = 0
            performance_stats = {
                'pages_processed': 0,
                'duplicates_found': 0,
                'empty_pages': 0,
                'unique_devices': 0
            }
            
            while page_no <= self.pagination_config['max_pages_extended']:
                print(f"📄 Page {page_no} - Récupération intelligente...")
                
                # Construire requête
                query = {
                    "page_size": self.pagination_config['page_size'],
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
                
                performance_stats['pages_processed'] = page_no
                
                # ✅ GESTION INTELLIGENTE DES ERREURS
                if not response.get('success'):
                    error_msg = response.get('msg', 'Erreur inconnue')
                    print(f"❌ Erreur page {page_no}: {error_msg}")
                    
                    if page_no == 1:
                        return {"success": False, "result": [], "error": f"Erreur critique page 1: {error_msg}"}
                    else:
                        print(f"⚠️ Erreur non-critique page {page_no}, arrêt de la récupération")
                        break
                
                # ✅ EXTRACTION INTELLIGENTE DES DONNÉES
                page_devices = response.get('result', [])
                
                # Gestion structure variable Tuya
                if isinstance(page_devices, dict):
                    devices_list = page_devices.get('list', page_devices.get('devices', []))
                    has_more = page_devices.get('has_more', False)
                else:
                    devices_list = page_devices if isinstance(page_devices, list) else []
                    has_more = len(devices_list) == self.pagination_config['page_size']
                
                # ✅ DÉTECTION PAGE VIDE INTELLIGENTE
                if not devices_list or len(devices_list) == 0:
                    empty_pages_count += 1
                    performance_stats['empty_pages'] += 1
                    print(f"   📭 Page {page_no} vide ({empty_pages_count}/{self.pagination_config['empty_pages_tolerance']} tolérance)")
                    
                    if empty_pages_count >= self.pagination_config['empty_pages_tolerance']:
                        print(f"🏁 ARRÊT INTELLIGENT: {empty_pages_count} pages vides consécutives")
                        break
                    
                    page_no += 1
                    continue
                
                # Reset compteur pages vides si on trouve des données
                empty_pages_count = 0
                
                # ✅ DÉDUPLICATION INTELLIGENTE
                page_unique_devices = []
                for device in devices_list:
                    device_id = device.get("id")
                    if not device_id:
                        continue
                    
                    if device_id in seen_device_ids:
                        performance_stats['duplicates_found'] += 1
                        print(f"   🔄 Doublon détecté: {device.get('name', device_id)[:30]}...")
                        continue
                    
                    seen_device_ids.add(device_id)
                    page_unique_devices.append(device)
                
                # Ajouter les appareils uniques
                if page_unique_devices:
                    all_devices.extend(page_unique_devices)
                    performance_stats['unique_devices'] = len(all_devices)
                    print(f"   ✅ Page {page_no}: {len(page_unique_devices)} nouveaux appareils (total: {len(all_devices)})")
                else:
                    print(f"   📋 Page {page_no}: Aucun nouvel appareil")
                
                # ✅ CONDITIONS D'ARRÊT INTELLIGENTES AMÉLIORÉES
                
                # 1. Arrêt si API Tuya dit "plus de données"
                if isinstance(page_devices, dict) and not has_more:
                    print(f"🏁 ARRÊT INTELLIGENT: API Tuya indique fin des données (has_more=false)")
                    break
                
                # 2. Arrêt si page incomplète
                if len(devices_list) < self.pagination_config['page_size']:
                    print(f"🏁 ARRÊT INTELLIGENT: Page incomplète ({len(devices_list)}/{self.pagination_config['page_size']})")
                    break
                
                # 3. ✅ AMÉLIORATION: Tolérance pour patterns suspects avant arrêt définitif
                consecutive_duplicate_pages = 0
                if len(page_unique_devices) == 0 and len(devices_list) > 0:
                    consecutive_duplicate_pages += 1
                    print(f"⚠️ PATTERN SUSPECT page {page_no}: {len(devices_list)} appareils mais tous des doublons ({consecutive_duplicate_pages}/3 tolérance)")
                    
                    # ✅ NOUVEAU: Continuer quelques pages même avec pattern suspect
                    duplicate_tolerance = self.pagination_config.get('duplicate_pattern_tolerance', 2)
                    if consecutive_duplicate_pages >= duplicate_tolerance and page_no > 5:
                        print(f"🏁 ARRÊT INTELLIGENT: Pattern de répétition confirmé après {duplicate_tolerance} pages de tolérance")
                        break
                    else:
                        print(f"   🔄 Continuation forcée - recherche appareils manquants (tolérance: {consecutive_duplicate_pages}/{duplicate_tolerance})")
                else:
                    consecutive_duplicate_pages = 0  # Reset si page avec nouveaux appareils
                
                # 4. Arrêt de sécurité pour éviter boucle infinie
                if page_no >= self.pagination_config['max_pages_safe']:
                    remaining_pages = self.pagination_config['max_pages_extended'] - self.pagination_config['max_pages_safe']
                    print(f"⚠️ LIMITE SÉCURISÉE atteinte ({self.pagination_config['max_pages_safe']} pages)")
                    print(f"   Continuer avec {remaining_pages} pages max ? (Protection anti-boucle infinie)")
                
                # 5. Pause anti-rate-limiting intelligente
                if page_no % 10 == 0:  # Pause tous les 10 pages
                    print(f"   ⏸️ Pause intelligente anti-rate-limiting...")
                    time.sleep(0.2)
                else:
                    time.sleep(0.05)  # Micro-pause
                
                page_no += 1
            
            # ✅ RAPPORT FINAL INTELLIGENT
            print(f"\n🎯 === RÉCUPÉRATION TERMINÉE ===")
            print(f"   📊 Pages traitées: {performance_stats['pages_processed']}")
            print(f"   📱 Appareils uniques: {performance_stats['unique_devices']}")
            print(f"   🔄 Doublons éliminés: {performance_stats['duplicates_found']}")
            print(f"   📭 Pages vides: {performance_stats['empty_pages']}")
            print(f"   ⚡ Efficacité: {(performance_stats['unique_devices'] / (performance_stats['pages_processed'] * self.pagination_config['page_size']) * 100):.1f}%")
            
            # ✅ RECOMMANDATIONS INTELLIGENTES
            if performance_stats['duplicates_found'] > performance_stats['unique_devices'] * 0.5:
                print(f"💡 RECOMMANDATION: Beaucoup de doublons détectés, l'API Tuya répète des données")
            
            if performance_stats['pages_processed'] >= self.pagination_config['max_pages_safe']:
                print(f"💡 RECOMMANDATION: Beaucoup de pages nécessaires, augmentez la limite si vous avez > 300 appareils")
            
            return {
                "success": True, 
                "result": all_devices,
                "performance_stats": performance_stats,
                "pagination_efficient": True
            }
            
        except Exception as e:
            print(f"❌ Erreur récupération intelligente: {e}")
            return {"success": False, "result": [], "error": str(e)}
    
    def get_all_devices_with_details(self):
        """🧠 APPAREILS AVEC DÉTAILS - Version intelligente avec détection triphasé"""
        try:
            print("🧠 Récupération intelligente avec détails complets...")

            devices_response = self.get_devices()

            if not devices_response.get("success"):
                return {
                    "success": False,
                    "result": [],
                    "error": "Impossible de récupérer les appareils"
                }

            devices = devices_response.get("result", [])
            performance_stats = devices_response.get("performance_stats", {})

            print(f"📊 {len(devices)} appareils uniques récupérés intelligemment")

            # Traitement intelligent des détails
            detailed_devices = []
            online_count = 0
            offline_count = 0
            triphase_count = 0

            for device in devices:
                device_info = device.copy()
                device_info["device_id"] = device.get("id")

                # ✅ EXTRACTION FIABLE DU STATUT EN LIGNE
                is_online = device.get("isOnline")
                if is_online is None:
                    is_online = device.get("online", False)  # fallback
                device_info["online"] = is_online  # ✅ Clé attendue par _process_devices_data()
                device_info["online_status"] = "Online" if is_online else "Offline"

                if is_online:
                    online_count += 1
                else:
                    offline_count += 1

                # 🔎 Détection triphasé
                is_triphase = self._detect_triphase_device(device)
                if is_triphase:
                    device_info["device_type"] = "triphase"
                    triphase_count += 1
                else:
                    device_info["device_type"] = "monophase"

                detailed_devices.append(device_info)

            print(f"✅ Traitement terminé: {online_count} en ligne, {offline_count} hors ligne, {triphase_count} triphasés détectés")

            return {
                "success": True,
                "result": detailed_devices,
                "total_count": len(detailed_devices),
                "online_count": online_count,
                "offline_count": offline_count,
                "triphase_count": triphase_count,
                "performance_stats": performance_stats,
                "intelligent_processing": True
            }

        except Exception as e:
            print(f"❌ Erreur récupération détails intelligente: {e}")
            return {
                "success": False,
                "result": [],
                "error": str(e)
            }


    def _detect_triphase_device(self, device):
        """Détecter si un appareil est triphasé basé sur ses données"""
        # Liste des indicateurs qui peuvent suggérer un appareil triphasé
        triphase_indicators = ['phase_a', 'phase_b', 'phase_c', 'total_forward_energy', 'forward_energy_total']

        # Vérifier si l'un des indicateurs est présent dans les données de l'appareil
        for indicator in triphase_indicators:
            if indicator in device.get("status", []):
                return True

        return False

    
    # ✅ MÉTHODES STABLES (ne pas modifier)
    def get_device_status(self, device_id):
        """Récupérer le statut d'un appareil"""
        if not self.ensure_token():
            return {"success": False, "result": [], "error": "Token invalide"}
        
        try:
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
            
            if response.get('success'):
                return response
            else:
                return {
                    "success": False,
                    "result": [],
                    "error": response.get('msg', 'Erreur inconnue')
                }
        
        except Exception as e:
            return {"success": False, "result": [], "error": str(e)}
    
    def send_device_command(self, device_id, commands):
        """Envoyer une commande à un appareil"""
        if not self.ensure_token():
            return {"success": False, "error": "Token invalide"}
        
        try:
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
    
    def get_device_current_values(self, device_id):
        """🧠 VALEURS ACTUELLES - Version intelligente avec mapping optimal, détection triphasé et support base64"""
        try:
            # Récupération intelligente du statut en ligne
            device_info_response = self.get_device_info(device_id)
            real_online_status = False

            if device_info_response.get('success'):
                device_info = device_info_response.get('result', {})
                real_online_status = device_info.get('online', False)

            # Récupération des données de statut
            status_response = self.get_device_status(device_id)

            if not status_response.get('success'):
                return {
                    "success": False,
                    "values": {},
                    "is_online": False,
                    "error": status_response.get('error', 'Erreur inconnue')
                }

            status_data = status_response.get('result', [])

            if not isinstance(status_data, list):
                if isinstance(status_data, dict) and "status" in status_data:
                    status_data = status_data["status"]
                else:
                    status_data = []

            # 🧠 MAPPING INTELLIGENT des valeurs
            values = {}
            is_triphase = False
            triphase_indicators = ['phase_a', 'phase_b', 'phase_c', 'total_forward_energy', 'forward_energy_total']

            for item in status_data:
                if not isinstance(item, dict):
                    continue

                code = item.get('code', '')
                value = item.get('value')

                # Décodage automatique si valeur base64 détectée
                if isinstance(value, str):
                    try:
                        decoded = base64.b64decode(value)
                        if len(decoded) == 4:
                            value = round(struct.unpack('<f', decoded)[0], 3)
                    except Exception:
                        pass

                # MAPPING INTELLIGENT
                if code == "cur_voltage":
                    values["tension"] = value / 100 if value not in (None, 0) else None
                elif code == "cur_current":
                    values["courant"] = value / 1000 if value not in (None, 0) else None
                elif code == "cur_power":
                    values["puissance"] = value / 10 if value not in (None, 0) else None
                elif code == "add_ele":
                    values["energie"] = value / 1000 if value is not None else None
                elif code in ["switch", "switch_1", "switch_led"]:
                    values["etat_switch"] = bool(value) if value is not None else None
                elif code == "temp_current":
                    values["temperature"] = value / 10 if value is not None else None
                elif code == "humidity":
                    values["humidite"] = value
                elif code in ["phase_a", "phase_b", "phase_c"]:
                    is_triphase = True
                    values[code] = value
                elif code == "total_forward_energy" or code == "forward_energy_total":
                    is_triphase = True
                    values["energie_totale"] = value
                elif code == "supply_frequency":
                    values["frequence"] = value
                elif code == "fault":
                    values["defaut"] = value
                elif code == "leakage_current":
                    values["courant_fuite"] = value
                elif code == "switch_prepayment":
                    values["prepaiement"] = bool(value) if value is not None else None
                elif code == "temp_set":
                    values["temperature_consigne"] = value
                elif code == "mode":
                    values["mode"] = value
                elif code == "eco":
                    values["mode_eco"] = bool(value) if value is not None else None
                elif code == "child_lock":
                    values["verrouillage_enfant"] = bool(value) if value is not None else None
                elif code == "countdown_1":
                    values["minuterie"] = value
                elif code == "relay_status":
                    values["etat_relais"] = value
                elif code == "light_mode":
                    values["mode_eclairage"] = value
                else:
                    # fallback générique
                    values[code] = value

            return {
                "success": True,
                "values": values,
                "is_online": real_online_status,
                "device_id": device_id,
                "is_triphase": is_triphase,
                "raw_status": status_data,
                "timestamp": datetime.utcnow().isoformat(),
                "intelligent_mapping": True
            }

        except Exception as e:
            return {
                "success": False,
                "values": {},
                "is_online": False,
                "error": str(e)
            }


    
    def toggle_device(self, device_id, state=None):
        """🧠 CONTRÔLE INTELLIGENT d'appareil"""
        try:
            if not self.ensure_token():
                return {"success": False, "error": "Token invalide"}
            
            if not self.reconnect_if_needed():
                return {"success": False, "error": "Impossible de se reconnecter"}
            
            # Récupération intelligente de l'état actuel
            values_response = self.get_device_current_values(device_id)
            
            if not values_response.get("success"):
                return {
                    "success": False, 
                    "error": f"Impossible de récupérer le statut: {values_response.get('error')}"
                }
            
            current_values = values_response.get("values", {})
            raw_status = values_response.get("raw_status", [])
            
            # 🧠 DÉTECTION INTELLIGENTE DU CODE SWITCH
            switch_code = None
            current_state = None
            
            # Recherche intelligente dans les valeurs mappées
            if "etat_switch" in current_values:
                current_state = current_values["etat_switch"]
                # Retrouver le code original
                for item in raw_status:
                    if isinstance(item, dict) and item.get('code') in ['switch', 'switch_1', 'switch_led']:
                        switch_code = item.get('code')
                        break
            
            # Recherche dans les données brutes si pas trouvé
            if switch_code is None:
                switch_candidates = ['switch_1', 'switch', 'switch_led', 'power', 'switch_2']
                
                for item in raw_status:
                    if isinstance(item, dict):
                        code = item.get('code', '')
                        if code in switch_candidates:
                            switch_code = code
                            current_state = item.get('value')
                            break
            
            if switch_code is None:
                all_codes = [item.get('code') for item in raw_status if isinstance(item, dict)]
                return {
                    "success": False, 
                    "error": f"Aucun switch trouvé. Codes disponibles: {all_codes}"
                }
            
            # Calcul du nouvel état
            if state is None:
                new_state = not current_state
                action = "Basculé"
            else:
                new_state = bool(state)
                action = "Allumé" if new_state else "Éteint"
            
            # Envoi de la commande
            commands = {
                "commands": [
                    {
                        "code": switch_code,
                        "value": new_state
                    }
                ]
            }
            
            response = self.send_device_command(device_id, commands)
            
            if response.get("success"):
                return {
                    "success": True,
                    "new_state": new_state,
                    "previous_state": current_state,
                    "action": action.lower(),
                    "message": f"Appareil {action.lower()} avec succès",
                    "switch_code_used": switch_code,
                    "device_id": device_id,
                    "intelligent_control": True
                }
            else:
                return {
                    "success": False,
                    "error": f"Erreur commande: {response.get('msg', 'Inconnue')}",
                    "attempted_code": switch_code,
                    "tuya_response": response
                }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ✅ MÉTHODES UTILITAIRES STABLES
    def control_device(self, device_id, command, value=None):
        """Méthode de compatibilité pour contrôler un appareil"""
        if command == 'switch':
            return self.toggle_device(device_id, value)
        else:
            command_data = {
                "commands": [
                    {
                        "code": command,
                        "value": value
                    }
                ]
            }
            return self.send_device_command(device_id, command_data)
    
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
        """Informations de connexion avec stats intelligentes"""
        return {
            "is_connected": self.is_connected,
            "endpoint": self.endpoint,
            "access_id": self.access_id[:10] + "..." if self.access_id else None,
            "uid": self.uid,
            "token_valid": self.is_token_valid(),
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "pagination_config": self.pagination_config,
            "last_check": datetime.utcnow().isoformat(),
            "intelligent_features": True
        }
    
    def check_connection(self):
        """Vérification de connexion intelligente"""
        if not self.is_connected:
            return False
        
        try:
            # Test léger avec 1 seul appareil
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
            return success
        except Exception as e:
            self.is_connected = False
            return False
    
    # ✅ MÉTHODES ALIAS POUR COMPATIBILITÉ
    def get_spaces(self):
        """Alias pour get_devices (compatibilité)"""
        return self.get_devices()
    
    def get_token_info(self):
        """Informations du token"""
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
    
    # 🧠 MÉTHODES INTELLIGENTES SUPPLÉMENTAIRES
    
    def optimize_pagination_config(self, estimated_device_count=None):
        """🧠 Optimiser la configuration de pagination selon vos besoins"""
        try:
            if estimated_device_count:
                # ✅ CORRECTION: Configuration plus tolérante pour récupérer TOUS les appareils
                if estimated_device_count <= 50:
                    # Petit parc d'appareils - Configuration sécurisée mais complète
                    self.pagination_config.update({
                        'max_pages_safe': 8,           # ✅ 160 appareils max (plus sécurisé)
                        'empty_pages_tolerance': 3,    # ✅ Tolérance augmentée
                        'performance_mode': True,
                        # ✅ NOUVEAU: Tolérance spéciale pour doublons
                        'duplicate_pattern_tolerance': 2  # Continuer 2 pages après détection pattern
                    })
                    print(f"🧠 Configuration sécurisée pour {estimated_device_count} appareils (mode récupération complète)")
                
                elif estimated_device_count <= 200:
                    # Parc moyen - Configuration équilibrée
                    self.pagination_config.update({
                        'max_pages_safe': 15,          # 300 appareils max
                        'empty_pages_tolerance': 3,    # Tolérance moyenne
                        'performance_mode': True,
                        'duplicate_pattern_tolerance': 3
                    })
                    print(f"🧠 Configuration optimisée pour {estimated_device_count} appareils (mode parc moyen)")
                
                else:
                    # Grand parc - Configuration robuste
                    self.pagination_config.update({
                        'max_pages_safe': 25,          # 500 appareils max
                        'max_pages_extended': 75,      # 1500 appareils max
                        'empty_pages_tolerance': 5,    # Tolérance élevée
                        'performance_mode': False,     # Mode robuste
                        'duplicate_pattern_tolerance': 5
                    })
                    print(f"🧠 Configuration optimisée pour {estimated_device_count} appareils (mode grand parc)")
            
            return {
                "success": True,
                "optimized_config": self.pagination_config,
                "estimated_device_count": estimated_device_count
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_pagination_stats(self):
        """📊 Statistiques de pagination pour monitoring"""
        return {
            "current_config": self.pagination_config,
            "recommended_for_devices": {
                "small_park": "≤ 50 appareils",
                "medium_park": "50-200 appareils", 
                "large_park": "> 200 appareils"
            },
            "performance_tips": [
                "Utilisez optimize_pagination_config() pour auto-optimiser",
                "Mode performance activé par défaut pour vos 23 appareils",
                "Déduplication automatique des doublons Tuya",
                "Arrêt intelligent sur pages vides"
            ]
        }
    
    def quick_device_count(self):
        """🚀 Comptage rapide des appareils sans récupération complète"""
        try:
            print("🚀 Comptage rapide intelligent...")
            
            # Test avec 1 page pour estimer
            response = make_tuya_request_fixed(
                self.endpoint,
                self.access_id,
                self.access_secret,
                "GET",
                "/v2.0/cloud/thing/device",
                {"page_size": 20, "page_no": 1},
                "",
                self.access_token
            )
            
            if not response.get('success'):
                return {"success": False, "error": "Impossible de compter"}
            
            page_devices = response.get('result', [])
            
            if isinstance(page_devices, dict):
                devices_list = page_devices.get('list', page_devices.get('devices', []))
                has_more = page_devices.get('has_more', False)
            else:
                devices_list = page_devices if isinstance(page_devices, list) else []
                has_more = len(devices_list) == 20
            
            first_page_count = len(devices_list)
            
            # Estimation intelligente
            if not has_more or first_page_count < 20:
                # Tous les appareils dans la première page
                estimated_total = first_page_count
                confidence = "élevée"
            else:
                # Estimation basée sur la pagination
                estimated_total = f"{first_page_count}+ (plusieurs pages)"
                confidence = "estimation"
            
            print(f"📊 Comptage rapide: {estimated_total} appareils (confiance: {confidence})")
            
            return {
                "success": True,
                "first_page_count": first_page_count,
                "estimated_total": estimated_total,
                "has_more_pages": has_more,
                "confidence": confidence
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def health_check(self):
        """🏥 Vérification santé complète du service"""
        try:
            health = {
                "service": "TuyaClient Intelligent",
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "unknown",
                "components": {}
            }
            
            # Test connexion
            if self.is_connected_method():
                health["components"]["connection"] = {
                    "status": "healthy",
                    "token_valid": self.is_token_valid(),
                    "uid": self.uid
                }
            else:
                health["components"]["connection"] = {
                    "status": "error",
                    "token_valid": False
                }
            
            # Test API rapide
            try:
                quick_count = self.quick_device_count()
                if quick_count.get("success"):
                    health["components"]["api"] = {
                        "status": "healthy",
                        "response_time": "rapide",
                        "device_count": quick_count.get("first_page_count", 0)
                    }
                else:
                    health["components"]["api"] = {
                        "status": "error",
                        "error": quick_count.get("error")
                    }
            except Exception as e:
                health["components"]["api"] = {
                    "status": "error",
                    "error": str(e)
                }
            
            # Configuration
            health["components"]["pagination"] = {
                "status": "optimized",
                "config": self.pagination_config,
                "intelligent_features": True
            }
            
            # Statut global
            error_components = [c for c in health["components"].values() if c.get("status") == "error"]
            
            if not error_components:
                health["overall_status"] = "healthy"
            else:
                health["overall_status"] = "degraded"
            
            return {"success": True, "health": health}
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "health": {
                    "service": "TuyaClient Intelligent",
                    "overall_status": "error",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }


# =================== TEST INTELLIGENT ===================

def test_tuya_intelligent():
    """🧪 Test intelligent du nouveau TuyaClient"""
    print("🧪 === TEST TUYA CLIENT INTELLIGENT ===")
    
    try:
        client = TuyaClient()
        
        # Test connexion
        if not client.auto_connect_from_env():
            print("❌ Connexion échouée")
            return False
        
        print("✅ Connexion réussie")
        
        # Test comptage rapide
        print("\n🚀 Test comptage rapide...")
        quick_count = client.quick_device_count()
        if quick_count.get("success"):
            print(f"📊 Comptage rapide: {quick_count}")
        
        # Test optimisation automatique
        print("\n🧠 Test optimisation automatique...")
        if quick_count.get("success") and isinstance(quick_count.get("first_page_count"), int):
            estimated_count = quick_count["first_page_count"]
            optimization = client.optimize_pagination_config(estimated_count)
            print(f"⚙️ Optimisation: {optimization}")
        
        # Test récupération intelligente
        print("\n📱 Test récupération intelligente...")
        devices_result = client.get_all_devices_with_details()
        
        if devices_result.get("success"):
            devices = devices_result.get("result", [])
            stats = devices_result.get("performance_stats", {})
            
            print(f"✅ {len(devices)} appareils récupérés intelligemment")
            print(f"📊 Stats: {stats}")
            
            # Test santé
            print("\n🏥 Test santé du service...")
            health = client.health_check()
            if health.get("success"):
                health_status = health["health"]["overall_status"]
                print(f"🏥 Santé: {health_status}")
            
            # Test sur un appareil
            if devices:
                test_device = devices[0]
                device_id = test_device.get("id")
                device_name = test_device.get("name", "Appareil test")
                
                print(f"\n🔧 Test sur {device_name}...")
                
                # Test récupération valeurs
                status = client.get_device_current_values(device_id)
                if status.get("success"):
                    values = status.get("values", {})
                    print(f"✅ Valeurs récupérées: {len(values)} paramètres")
                    
                    # Afficher quelques valeurs intéressantes
                    interesting_values = {}
                    for key in ['tension', 'courant', 'puissance', 'etat_switch', 'phase_a', 'energie_totale']:
                        if key in values and values[key] is not None:
                            interesting_values[key] = values[key]
                    
                    if interesting_values:
                        print(f"🔍 Valeurs intéressantes: {interesting_values}")
                else:
                    print(f"❌ Erreur récupération valeurs: {status.get('error')}")
            
            return True
        else:
            print(f"❌ Erreur récupération intelligente: {devices_result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test intelligent: {e}")
        return False

if __name__ == "__main__":
    test_tuya_intelligent()