

import os
from tuya_iot import TuyaOpenAPI

class TuyaClient:
    def __init__(self):
        self.openapi = None
        self.token_info = None
        self.is_connected = False
        
    def connect(self, username, password, country_code="221", app_type="Smartlife"):
        """Connexion à Tuya avec les identifiants utilisateur"""
        try:
            # Configuration depuis les variables d'environnement
            self.openapi = TuyaOpenAPI(
                endpoint=os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com'),
                access_id=os.getenv('ACCESS_ID'),
                access_key=os.getenv('ACCESS_KEY')
            )
            
            # Connexion avec les identifiants utilisateur
            connected = self.openapi.connect(username, password, country_code, app_type)
            
            if connected:
                self.token_info = self.openapi.token_info
                self.is_connected = True
                return True
            else:
                self.is_connected = False
                return False
                
        except Exception as e:
            print(f"Erreur connexion Tuya: {e}")
            self.is_connected = False
            return False
    
    def get_token_info(self):
        """Récupérer les informations du token"""
        return self.token_info
    
    def get_devices(self):
        """Récupérer la liste des appareils"""
        if not self.is_connected or not self.openapi:
            raise Exception("Client Tuya non connecté")
        
        try:
            response = self.openapi.get("/v2.0/cloud/thing/device?page_size=100")
            return response
        except Exception as e:
            print(f"Erreur récupération appareils: {e}")
            return {"result": []}
    
    def get_device_status(self, device_id):
        """Récupérer le statut d'un appareil"""
        if not self.is_connected or not self.openapi:
            raise Exception("Client Tuya non connecté")
        
        try:
            response = self.openapi.get(f"/v1.0/iot-03/devices/status?device_ids={device_id}")
            return response
        except Exception as e:
            print(f"Erreur statut appareil {device_id}: {e}")
            return {"result": []}
    
    def send_device_command(self, device_id, commands):
        """Envoyer une commande à un appareil"""
        if not self.is_connected or not self.openapi:
            raise Exception("Client Tuya non connecté")
        
        try:
            response = self.openapi.post(f"/v1.0/devices/{device_id}/commands", commands)
            return response
        except Exception as e:
            print(f"Erreur commande appareil {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_spaces(self):
        """Récupérer les espaces"""
        if not self.is_connected or not self.openapi:
            raise Exception("Client Tuya non connecté")
        
        try:
            response = self.openapi.get("/v2.0/cloud/space/child?only_sub=false&page_size=10")
            return response
        except Exception as e:
            print(f"Erreur récupération espaces: {e}")
            return {"result": []}
    
    def get_device_logs(self, device_id, code, start_time, end_time):
        """Récupérer les logs d'un appareil"""
        if not self.is_connected or not self.openapi:
            raise Exception("Client Tuya non connecté")
        
        try:
            url = f"/v2.0/cloud/thing/{device_id}/report-logs"
            params = {
                "codes": code,
                "end_time": end_time,
                "size": 100,
                "start_time": start_time
            }
            response = self.openapi.get(url, params)
            return response
        except Exception as e:
            print(f"Erreur logs appareil {device_id}: {e}")
            return {"result": []}