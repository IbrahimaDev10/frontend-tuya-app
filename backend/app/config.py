from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') 
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=20)
    TUYA_ACCESS_ID = os.getenv('ACCESS_ID')
    TUYA_ACCESS_KEY = os.getenv('ACCESS_KEY')
    TUYA_ENDPOINT = 'https://openapi.tuyaeu.com'