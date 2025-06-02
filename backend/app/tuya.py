from tuya_iot import TuyaOpenAPI, TUYA_LOGGER
import logging
from .config import Config

class TuyaClient:
    def __init__(self):
        self.openapi = TuyaOpenAPI(
            Config.TUYA_ENDPOINT,
            Config.TUYA_ACCESS_ID,
            Config.TUYA_ACCESS_KEY
        )
        TUYA_LOGGER.setLevel(logging.DEBUG)
    
    def connect(self, username, password, country_code="221", app_type="Smartlife"):
        return self.openapi.connect(username, password, country_code, app_type)

    def get_token_info(self):
        return self.openapi.token_info

    def get_devices(self):
        return self.openapi.get("/v2.0/cloud/thing/device?page_size=20")

    def get_device_status(self, device_id):
        return self.openapi.get(f"/v1.0/iot-03/devices/status?device_ids={device_id}")

    def send_device_command(self, device_id, commands):
        return self.openapi.post(f"/v1.0/devices/{device_id}/commands", commands)

    def get_spaces(self):
        return self.openapi.get("/v2.0/cloud/space/child?only_sub=false&page_size=10")

    def get_device_logs(self, device_id, code, start_time, end_time):
        url = f"/v2.0/cloud/thing/{device_id}/report-logs?codes={code}&end_time={end_time}&size=100&start_time={start_time}"
        return self.openapi.get(url)