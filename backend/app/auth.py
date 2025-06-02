from flask_jwt_extended import create_access_token
from .tuya import TuyaClient

class Auth:
    def __init__(self):
        self.tuya_client = TuyaClient()
        self.tokens = {}

    def login(self, username, password, country_code="221", app_type="Smartlife"):
        connected = self.tuya_client.connect(username, password, country_code, app_type)
        if not connected:
            return None, "Échec de la connexion à Tuya."

        token_info = self.tuya_client.get_token_info()
        self.tokens[token_info.uid] = token_info.access_token
        jwt_token = create_access_token(identity=token_info.uid)
        
        return jwt_token, None