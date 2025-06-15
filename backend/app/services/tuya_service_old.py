import os
from tuya_iot import TuyaOpenAPI
from datetime import datetime, timedelta

class TuyaClient:
    def __init__(self):
        self.openapi = None
        self.token_info = None
        self.is_connected = False
        
    def connect(self, username, password, country_code="221", app_type="smart_life"):
        """Connexion à Tuya avec les identifiants utilisateur"""
        try:
            # Configuration depuis les variables d'environnement
            endpoint = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com')
            access_id = os.getenv('ACCESS_ID')
            access_key = os.getenv('ACCESS_KEY')
            
            print(f"🔧 Tentative connexion Tuya:")
            print(f"   Endpoint: {endpoint}")
            print(f"   Access ID: {access_id[:10]}..." if access_id else "None")
            print(f"   Username: {username}")
            
            # Créer l'instance TuyaOpenAPI
            self.openapi = TuyaOpenAPI(
                endpoint=endpoint,
                access_id=access_id,
                access_secret=access_key  # ✅ CORRIGÉ: access_secret au lieu de access_key
            )
            
            # ✅ CORRIGÉ: Logique de connexion adaptée aux vraies réponses
            print(f"🔧 Test connexion Tuya avec connect()")
            try:
                # La méthode connect() retourne un dict avec code, même si ça marche
                connected_response = self.openapi.connect(username, password, country_code, "smart_life")
                print(f"📊 Résultat connect(): {connected_response}")
                
                # Vérifier si c'est vraiment connecté, même si success=False
                # Code 0 ou 1000 peut indiquer succès selon l'API Tuya
                is_connected = False
                
                if isinstance(connected_response, dict):
                    code = connected_response.get('code', -1)
                    success = connected_response.get('success', False)
                    
                    # Code 0 = succès dans certains cas Tuya
                    if code == 0 or success:
                        is_connected = True
                elif connected_response is True:
                    is_connected = True
                
                # Test de l'API pour vérifier la vraie connexion
                if not is_connected:
                    try:
                        # Tester avec un endpoint simple
                        test_response = self.openapi.get('/v2.0/cloud/thing/device?page_size=1')
                        if test_response.get('success') or 'result' in test_response:
                            is_connected = True
                            print("📊 Connexion confirmée par test API")
                    except:
                        pass
                
                if is_connected:
                    # Récupération manuelle du token si nécessaire
                    self.token_info = getattr(self.openapi, 'token_info', None)
                    
                    # Si pas de token_info, essayer de le récupérer
                    if not self.token_info:
                        try:
                            token_response = self.openapi.get('/v1.0/token')
                            if token_response.get('success'):
                                self.token_info = token_response.get('result')
                        except:
                            pass
                    
                    self.is_connected = True
                    print(f"✅ Connexion Tuya réussie pour {username}")
                    print(f"🎫 Token info: {self.token_info}")
                    return True
                else:
                    # Tenter avec d'autres schemas
                    schemas_to_try = ['tuya', 'smartlife', 'Smart Life']
                    for schema in schemas_to_try:
                        print(f"🔧 Test connexion avec schema: {schema}")
                        try:
                            alt_response = self.openapi.connect(username, password, country_code, schema)
                            print(f"📊 Résultat connect {schema}: {alt_response}")
                            
                            # Même logique de vérification
                            alt_connected = False
                            if isinstance(alt_response, dict):
                                code = alt_response.get('code', -1)
                                success = alt_response.get('success', False)
                                if code == 0 or success:
                                    alt_connected = True
                            elif alt_response is True:
                                alt_connected = True
                            
                            if alt_connected:
                                self.token_info = getattr(self.openapi, 'token_info', None)
                                self.is_connected = True
                                print(f"✅ Connexion Tuya réussie avec {schema} pour {username}")
                                print(f"🎫 Token info: {self.token_info}")
                                return True
                                
                        except Exception as e:
                            print(f"❌ Erreur schema {schema}: {e}")
                            continue
                    
                    # Si aucun schema ne marche
                    self.is_connected = False
                    print(f"❌ Connexion Tuya échouée pour {username} avec tous les schemas")
                    return False
                    
            except Exception as e:
                print(f"❌ Erreur connect principal: {e}")
                self.is_connected = False
                return False
                
        except Exception as e:
            print(f"❌ Erreur connexion Tuya: {e}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            self.is_connected = False
            return False
    
    def auto_connect_from_env(self):
        """Connexion automatique depuis les variables d'environnement"""
        try:
            # ✅ CORRIGÉ: Priorité à TUYA_USERNAME
            username = os.getenv('TUYA_USERNAME')
            if not username:
                username = os.getenv('USERNAME')
                # Si c'est "simplon", forcer le bon username
                if username == "simplon":
                    username = "ibrahman1970@gmail.com"
                    print("🔧 Username 'simplon' corrigé vers ibrahman1970@gmail.com")
            
            password = os.getenv('PASSWORD')
            country_code = os.getenv('COUNTRY_CODE', '221')
            
            print(f"🔍 Variables récupérées:")
            print(f"   TUYA_USERNAME: {os.getenv('TUYA_USERNAME')}")
            print(f"   USERNAME: {os.getenv('USERNAME')}")
            print(f"   Username final: {username}")
            print(f"   Password: {'***' if password else 'None'}")
            print(f"   Country: {country_code}")
            
            if not username or not password:
                print("❌ USERNAME ou PASSWORD manquants dans .env")
                return False
            
            return self.connect(username, password, country_code)
            
        except Exception as e:
            print(f"❌ Erreur connexion auto depuis .env: {e}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            return False
    
    def check_connection(self):
        """Vérifier si la connexion est toujours active"""
        if not self.is_connected or not self.openapi:
            return False
        
        try:
            # ✅ CORRIGÉ: Test plus simple avec les homes
            response = self.get_user_homes()
            success = response.get("success", False)
            has_result = "result" in response and len(response.get("result", [])) > 0
            
            print(f"🔍 Test connexion - Success: {success}, Has result: {has_result}")
            return success and has_result
        except Exception as e:
            print(f"❌ Erreur test connexion: {e}")
            self.is_connected = False
            return False
    
    def reconnect_if_needed(self):
        """Reconnexion automatique si nécessaire"""
        if not self.check_connection():
            print("🔄 Reconnexion Tuya nécessaire...")
            return self.auto_connect_from_env()
        return True
    
    def get_token_info(self):
        """Récupérer les informations du token"""
        return self.token_info
    
    def get_connection_info(self):
        """Récupérer les informations de connexion actuelle"""
        # ✅ CORRIGÉ: Utiliser TUYA_USERNAME en priorité
        username = os.getenv('TUYA_USERNAME') or os.getenv('USERNAME', '')
        if username == "simplon":
            username = "ibrahman1970@gmail.com (corrigé)"
            
        return {
            "is_connected": self.is_connected,
            "endpoint": os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com'),
            "access_id": os.getenv('ACCESS_ID', '')[:10] + "..." if os.getenv('ACCESS_ID') else None,
            "username": username,
            "token_info": self.token_info,
            "last_check": datetime.utcnow().isoformat()
        }
    
    # =================== MÉTHODES API CORRIGÉES ===================
    
    def get_user_homes(self):
        """Récupérer les homes/espaces de l'utilisateur"""
        if not self.is_connected or not self.openapi:
            raise Exception("Client Tuya non connecté")
        
        try:
            if not self.token_info or not self.token_info.get('uid'):
                print("❌ Token info manquant ou UID non trouvé")
                return {"success": False, "result": []}
                
            uid = self.token_info.get('uid')
            print(f"🔍 Récupération homes pour UID: {uid}")
            response = self.openapi.get(f"/v1.0/users/{uid}/homes")
            print(f"📊 Réponse homes: {response}")
            return response
        except Exception as e:
            print(f"❌ Erreur récupération homes: {e}")
            return {"success": False, "result": []}
    
    def get_devices(self):
        """Récupérer la liste des appareils"""
        if not self.reconnect_if_needed():
            raise Exception("Impossible de se connecter à Tuya")
        
        try:
            # ✅ CORRIGÉ: Utiliser la méthode homes -> devices
            homes_response = self.get_user_homes()
            if not homes_response.get("success") or not homes_response.get("result"):
                print("❌ Aucun home trouvé")
                return {"success": False, "result": []}
            
            all_devices = []
            homes = homes_response.get("result", [])
            
            for home in homes:
                home_id = home.get("home_id")
                home_name = home.get("name", "Home")
                print(f"🏠 Récupération appareils pour home: {home_name} ({home_id})")
                
                try:
                    response = self.openapi.get(f"/v1.0/homes/{home_id}/devices")
                    print(f"📊 Réponse appareils home {home_id}: {response}")
                    
                    if response.get("success") and response.get("result"):
                        devices = response.get("result", [])
                        # Ajouter l'info du home à chaque appareil
                        for device in devices:
                            device["home_id"] = home_id
                            device["home_name"] = home_name
                        all_devices.extend(devices)
                        print(f"✅ {len(devices)} appareils trouvés dans {home_name}")
                    else:
                        print(f"⚠️ Aucun appareil dans home {home_name}")
                        
                except Exception as e:
                    print(f"❌ Erreur appareils home {home_id}: {e}")
                    continue
            
            print(f"📊 Total: {len(all_devices)} appareils trouvés")
            return {"success": True, "result": all_devices}
            
        except Exception as e:
            print(f"❌ Erreur récupération appareils: {e}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            return {"success": False, "result": []}
    
    def get_device_status(self, device_id):
        """Récupérer le statut d'un appareil"""
        if not self.reconnect_if_needed():
            raise Exception("Impossible de se connecter à Tuya")
        
        try:
            print(f"🔍 Récupération statut appareil {device_id}...")
            # ✅ CORRIGÉ: Utiliser l'endpoint correct
            response = self.openapi.get(f"/v1.0/iot-03/devices/{device_id}/status")
            print(f"📊 Réponse statut: {response}")
            return response
        except Exception as e:
            print(f"❌ Erreur statut appareil {device_id}: {e}")
            return {"success": False, "result": []}
    
    def send_device_command(self, device_id, commands):
        """Envoyer une commande à un appareil"""
        if not self.reconnect_if_needed():
            raise Exception("Impossible de se connecter à Tuya")
        
        try:
            print(f"🔧 Envoi commande à {device_id}: {commands}")
            response = self.openapi.post(f"/v1.0/iot-03/devices/{device_id}/commands", commands)
            print(f"📊 Réponse commande: {response}")
            return response
        except Exception as e:
            print(f"❌ Erreur commande appareil {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_spaces(self):
        """Récupérer les espaces (alias pour get_user_homes)"""
        return self.get_user_homes()
    
    def get_device_logs(self, device_id, code, start_time, end_time):
        """Récupérer les logs d'un appareil"""
        if not self.reconnect_if_needed():
            raise Exception("Impossible de se connecter à Tuya")
        
        try:
            url = f"/v1.0/iot-03/devices/{device_id}/logs"
            params = {
                "codes": code,
                "end_time": end_time,
                "size": 100,
                "start_time": start_time
            }
            print(f"🔍 Récupération logs {device_id} pour {code}...")
            response = self.openapi.get(url, params)
            print(f"📊 Réponse logs: {response}")
            return response
        except Exception as e:
            print(f"❌ Erreur logs appareil {device_id}: {e}")
            return {"success": False, "result": []}
    
    # =================== MÉTHODES UTILES ===================
    
    def get_device_details(self, device_id):
        """Récupérer les détails complets d'un appareil"""
        if not self.reconnect_if_needed():
            raise Exception("Impossible de se connecter à Tuya")
        
        try:
            print(f"🔍 Récupération détails appareil {device_id}...")
            response = self.openapi.get(f"/v1.0/iot-03/devices/{device_id}")
            print(f"📊 Réponse détails: {response}")
            return response
        except Exception as e:
            print(f"❌ Erreur détails appareil {device_id}: {e}")
            return {"success": False, "result": []}
    
    def get_all_devices_with_details(self):
        """Récupérer tous les appareils avec détails complets"""
        try:
            print("🔍 Récupération tous appareils avec détails...")
            devices_response = self.get_devices()
            
            if not devices_response.get("success"):
                return {"success": False, "result": [], "error": "Impossible de récupérer les appareils"}
            
            devices = devices_response.get("result", [])
            print(f"📊 {len(devices)} appareils trouvés")
            
            detailed_devices = []
            for device in devices:
                device_id = device.get("id") or device.get("device_id", "")
                if device_id:
                    # Récupérer les détails pour chaque appareil
                    details_response = self.get_device_details(device_id)
                    if details_response.get("success") and details_response.get("result"):
                        # Fusionner les informations
                        device_info = details_response.get("result")
                        device_info.update(device)  # Ajouter les infos de base
                        detailed_devices.append(device_info)
                    else:
                        detailed_devices.append(device)
                else:
                    print(f"⚠️ Appareil sans device_id trouvé: {device}")
                    detailed_devices.append(device)
            
            print(f"✅ {len(detailed_devices)} appareils avec détails")
            return {"success": True, "result": detailed_devices}
            
        except Exception as e:
            print(f"❌ Erreur récupération appareils détaillés: {e}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            return {"success": False, "result": [], "error": str(e)}
    
    def get_device_current_values(self, device_id):
        """Récupérer les valeurs actuelles d'un appareil (tension, courant, etc.)"""
        try:
            print(f"🔍 Récupération valeurs actuelles {device_id}...")
            status_response = self.get_device_status(device_id)
            
            if not status_response.get("success"):
                return {"success": False, "message": "Erreur récupération statut"}
            
            status_data = status_response.get("result", [])
            print(f"📊 Status data brut: {status_data}")
            
            # Mapper les codes Tuya vers des noms plus clairs
            values = {}
            for item in status_data:
                code = item.get("code", "")
                value = item.get("value")
                
                # Mapping pour les compteurs ATORCH
                if code == "cur_voltage":
                    values["tension"] = value / 10 if value else None  # Diviser par 10 pour avoir les volts
                elif code == "cur_current":
                    values["courant"] = value / 1000 if value else None  # Diviser par 1000 pour avoir les ampères
                elif code == "cur_power":
                    values["puissance"] = value / 10 if value else None  # Diviser par 10 pour avoir les watts
                elif code == "add_ele":
                    values["energie"] = value / 1000 if value else None  # Diviser par 1000 pour avoir les kWh
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
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
    
    def toggle_device(self, device_id, state=None):
        """Allumer/éteindre un appareil (toggle ou état spécifique)"""
        try:
            print(f"🔧 Toggle appareil {device_id} - state: {state}")
            
            if state is None:
                # Mode toggle : récupérer l'état actuel d'abord
                current_status = self.get_device_current_values(device_id)
                if current_status.get("success"):
                    current_state = current_status.get("values", {}).get("etat_switch", False)
                    new_state = not current_state
                    print(f"🔄 Toggle: {current_state} -> {new_state}")
                else:
                    new_state = True  # Par défaut allumer si on ne peut pas récupérer l'état
                    print("🔄 État inconnu, allumer par défaut")
            else:
                new_state = bool(state)
                print(f"🔧 État forcé: {new_state}")
            
            commands = {
                "commands": [
                    {
                        "code": "switch",
                        "value": new_state
                    }
                ]
            }
            
            response = self.send_device_command(device_id, commands)
            
            return {
                "success": response.get("success", False),
                "new_state": new_state,
                "action": "allumé" if new_state else "éteint",
                "response": response
            }
            
        except Exception as e:
            print(f"❌ Erreur toggle appareil {device_id}: {e}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
    
    def get_device_logs_formatted(self, device_id, code, hours_back=24):
        """Récupérer les logs avec formatage automatique des dates"""
        try:
            print(f"🔍 Récupération logs formatés {device_id} - {code} - {hours_back}h")
            
            # Calculer les timestamps
            end_time = int(datetime.utcnow().timestamp() * 1000)
            start_time = int((datetime.utcnow() - timedelta(hours=hours_back)).timestamp() * 1000)
            
            logs_response = self.get_device_logs(device_id, code, start_time, end_time)
            logs = logs_response.get("result", [])
            
            # Formatter les données
            formatted_logs = []
            for log in logs:
                formatted_log = {
                    "timestamp": datetime.fromtimestamp(log.get("event_time", 0) / 1000).isoformat(),
                    "code": log.get("code"),
                    "value": log.get("value"),
                    "event_time": log.get("event_time")
                }
                formatted_logs.append(formatted_log)
            
            print(f"✅ {len(formatted_logs)} logs formatés")
            
            return {
                "success": True,
                "device_id": device_id,
                "code": code,
                "period_hours": hours_back,
                "count": len(formatted_logs),
                "data": formatted_logs
            }
            
        except Exception as e:
            print(f"❌ Erreur logs formatés {device_id}: {e}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
    
    def get_multiple_device_status(self, device_ids):
        """Récupérer le statut de plusieurs appareils en une fois"""
        try:
            if isinstance(device_ids, list):
                device_ids_str = ",".join(device_ids)
            else:
                device_ids_str = str(device_ids)
            
            print(f"🔍 Récupération statut multiple: {device_ids_str}")
            response = self.openapi.get(f"/v1.0/iot-03/devices/status?device_ids={device_ids_str}")
            print(f"📊 Réponse statut multiple: {response}")
            return response
            
        except Exception as e:
            print(f"❌ Erreur statut multiple appareils: {e}")
            return {"success": False, "result": []}
    
    def search_devices_by_name(self, search_term):
        """Rechercher des appareils par nom"""
        try:
            print(f"🔍 Recherche appareils par nom: {search_term}")
            all_devices = self.get_all_devices_with_details()
            if not all_devices.get("success"):
                return {"success": False, "result": []}
            
            devices = all_devices.get("result", [])
            search_term_lower = search_term.lower()
            
            filtered_devices = []
            for device in devices:
                device_name = device.get("name", "").lower()
                if search_term_lower in device_name:
                    filtered_devices.append(device)
            
            print(f"✅ {len(filtered_devices)} appareils trouvés")
            
            return {
                "success": True,
                "search_term": search_term,
                "count": len(filtered_devices),
                "result": filtered_devices
            }
            
        except Exception as e:
            print(f"❌ Erreur recherche appareils: {e}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}