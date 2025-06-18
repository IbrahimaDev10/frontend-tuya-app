from tuya_iot import TuyaOpenAPI, TUYA_LOGGER
import logging
from .config import Config

class TuyaClient:
    def __init__(self):
        self.endpoint = Config.TUYA_ENDPOINT
        self.access_id = Config.TUYA_ACCESS_ID
        self.access_key = Config.TUYA_ACCESS_KEY

    def with_token(self, token):
        """Crée une instance TuyaOpenAPI avec un token spécifique (par utilisateur)"""
        openapi = TuyaOpenAPI(self.endpoint, self.access_id, self.access_key)
        openapi.token_info = type('TokenInfo', (object,), {
            'access_token': token
        })()
        return openapi

    def get_devices(self, openapi):
        return openapi.get("/v2.0/cloud/thing/device?page_size=20")

    def get_device_status(self, openapi, device_id):
        return openapi.get(f"/v1.0/iot-03/devices/status?device_ids={device_id}")

    def send_device_command(self, openapi, device_id, commands):
        return openapi.post(f"/v1.0/devices/{device_id}/commands", commands)

    def get_spaces(self, openapi):
        return openapi.get("/v2.0/cloud/space/child?only_sub=false&page_size=10")

    def get_device_logs(self, openapi, device_id, code, start_time, end_time):
        url = f"/v2.0/cloud/thing/{device_id}/report-logs?codes={code}&end_time={end_time}&size=100&start_time={start_time}"
        return openapi.get(url)
