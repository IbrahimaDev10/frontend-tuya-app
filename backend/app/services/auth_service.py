
from flask_jwt_extended import create_access_token
# ❌ ANCIEN : from .tuya import TuyaClient
# ✅ NOUVEAU : Import depuis la nouvelle structure
from .tuya_service import TuyaClient

class Auth:
    def __init__(self):
        self.tuya_client = TuyaClient()
        self.tokens = {}

    def login(self, username, password, country_code="221", app_type="Smartlife"):
        """Connexion utilisateur via Tuya"""
        try:
            # Connexion via le service Tuya
            connected = self.tuya_client.connect(username, password, country_code, app_type)
            if not connected:
                return None, "Échec de la connexion à Tuya."

            # Récupération des informations du token
            token_info = self.tuya_client.get_token_info()
            
            # Stockage du token Tuya
            self.tokens[token_info.uid] = token_info.access_token
            
            # Création du JWT
            jwt_token = create_access_token(identity=token_info.uid)
            
            return jwt_token, None
            
        except Exception as e:
            return None, f"Erreur lors de la connexion: {str(e)}"