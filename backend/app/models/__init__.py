# Import des modèles nécessaires pour l'application
from .user import User
from .client import Client  
from .site import Site
from .device import Device
from .device_data import DeviceData
from .alert import Alert
from .device_access import DeviceAccess
from .protection_event import ProtectionEvent 
from .scheduled_action import ScheduledAction  
from .device_action_log import DeviceActionLog  

# Importer tous les modèles pour que Flask-Migrate les trouve
__all__ = [
    'Client', 'User', 'Site', 'Device', 
    'DeviceData', 'Alert', 'DeviceAccess', 'ProtectionEvent', 'ScheduledAction' , 'DeviceActionLog' 
]