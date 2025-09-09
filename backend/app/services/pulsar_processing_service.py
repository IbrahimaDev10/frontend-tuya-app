# app/services/pulsar_processing_service.py
import json
import logging
from datetime import datetime
from app import db
from app.models.device import Device
from app.models.device_data import DeviceData
# Assurez-vous que votre décodeur Veratti est accessible
# Le chemin peut varier selon votre structure, ajustez si besoin
from .tuya_to_devicedata_service import VerattiDecoder

log = logging.getLogger(__name__)

class PulsarProcessingService:
    """
    🧠 Service intelligent v2.0 pour traiter les messages Pulsar en temps réel.
    Gère les appareils monophasés et triphasés (VERATTI) détectés dans les logs.
    """

    def __init__(self):
        self.veratti_decoder = VerattiDecoder(debug=True) # Mettez à False en production
        log.info("✅ PulsarProcessingService initialisé (avec décodeur VERATTI)")

    def process_message(self, decrypted_payload: str):
        """
        Point d'entrée principal pour traiter un message Pulsar déchiffré.
        """
        try:
            data = json.loads(decrypted_payload)
            device_id = data.get('devId')
            
            if not device_id or 'status' not in data:
                log.warning(f"Message Pulsar ignoré (manque devId ou status): {data}")
                return {"success": False, "reason": "missing_payload_keys"}

            log.info(f"🔄 Traitement du message Pulsar pour l'appareil : {device_id}")

            # 1. Mise à jour rapide de l'état principal (ON/OFF, online)
            self.update_device_main_status(device_id, data.get('status', []))

            # 2. Sauvegarde des données dans l'historique (DeviceData)
            self.save_to_device_data(device_id, data)

            return {"success": True, "device_id": device_id}

        except json.JSONDecodeError:
            log.error(f"❌ Erreur de décodage JSON pour le payload: {decrypted_payload}")
            return {"success": False, "reason": "json_decode_error"}
        except Exception as e:
            log.error(f"❌ Erreur inattendue lors du traitement du message Pulsar: {e}", exc_info=True)
            db.session.rollback()
            return {"success": False, "reason": str(e)}

    def update_device_main_status(self, tuya_device_id: str, status_list: list):
        """
        Mise à jour ultra-rapide de la table `Device` pour le temps réel.
        """
        device = Device.get_by_tuya_id(tuya_device_id)
        if not device:
            log.warning(f"Appareil avec Tuya ID {tuya_device_id} non trouvé. Message ignoré.")
            return

        has_changed = False
        for status in status_list:
            code, value = status.get('code'), status.get('value')

            if code in ['switch', 'switch_1', 'switch_led']:
                new_state = bool(value)
                if device.etat_actuel_tuya != new_state:
                    device.etat_actuel_tuya = new_state
                    device.derniere_maj_etat_tuya = datetime.utcnow()
                    has_changed = True
                    log.info(f"✅ [TEMPS RÉEL] Appareil '{device.nom_appareil}' est passé à {'ON' if new_state else 'OFF'}.")
            
            if code == 'online':
                new_online_status = bool(value)
                if device.en_ligne != new_online_status:
                    device.en_ligne = new_online_status
                    has_changed = True
                    log.info(f"✅ [TEMPS RÉEL] Appareil '{device.nom_appareil}' est maintenant {'EN LIGNE' if new_online_status else 'HORS LIGNE'}.")

        if has_changed:
            try:
                db.session.commit()
            except Exception as e:
                log.error(f"❌ Erreur DB lors de la mise à jour du statut de {device.nom_appareil}: {e}")
                db.session.rollback()

    def save_to_device_data(self, tuya_device_id: str, pulsar_data: dict):
        """
        Sauvegarde les données reçues dans la table `DeviceData` pour l'historique.
        """
        device = Device.get_by_tuya_id(tuya_device_id)
        if not device or not device.is_assigne():
            return

        try:
            device_data = DeviceData(
                appareil_id=device.id,
                client_id=device.client_id,
                type_systeme=device.type_systeme,
                horodatage=datetime.utcfromtimestamp(pulsar_data.get('t') / 1000.0),
                donnees_brutes={'source': 'pulsar', 'payload': pulsar_data}
            )

            status_map = {item['code']: item['value'] for item in pulsar_data.get('status', [])}

            if device.is_triphase():
                # Pour le triphasé, nous devons agréger les données avant de les traiter.
                # Pulsar envoie une phase à la fois. La logique d'agrégation est plus complexe.
                # Pour l'instant, nous traitons chaque message de phase individuellement.
                log.debug(f"Traitement d'un message de phase pour appareil triphasé {device.nom_appareil}")
                # Le décodage complet nécessiterait de "mettre en cache" les 3 phases.
                # Simplifions pour l'instant : on ne remplit que ce qu'on peut.
                if 'phase_a' in status_map:
                    decoded = self.veratti_decoder.decode_phase_simple_data(status_map['phase_a'], 'L1')
                    if decoded.get('success'):
                        device_data.tension_l1 = decoded.get('tension')
                        device_data.courant_l1 = decoded.get('courant')
                        device_data.puissance_l1 = decoded.get('puissance')
                if 'phase_b' in status_map:
                    decoded = self.veratti_decoder.decode_phase_simple_data(status_map['phase_b'], 'L2')
                    if decoded.get('success'):
                        device_data.tension_l2 = decoded.get('tension')
                        device_data.courant_l2 = decoded.get('courant')
                        device_data.puissance_l2 = decoded.get('puissance')
                if 'phase_c' in status_map:
                    decoded = self.veratti_decoder.decode_phase_simple_data(status_map['phase_c'], 'L3')
                    if decoded.get('success'):
                        device_data.tension_l3 = decoded.get('tension')
                        device_data.courant_l3 = decoded.get('courant')
                        device_data.puissance_l3 = decoded.get('puissance')
                        
            else: # Monophasé
                log.debug(f"Traitement d'un message pour appareil monophasé {device.nom_appareil}")
                if 'cur_voltage' in status_map:
                    device_data.tension = float(status_map['cur_voltage']) / 100.0
                if 'cur_current' in status_map:
                    device_data.courant = float(status_map['cur_current']) / 1000.0
                if 'cur_power' in status_map:
                    device_data.puissance = float(status_map['cur_power']) / 10.0
                if 'add_ele' in status_map:
                    device_data.energie = float(status_map['add_ele']) / 100.0
                if 'switch' in status_map:
                    device_data.etat_switch = bool(status_map['switch'])

            db.session.add(device_data)
            db.session.commit()
            log.info(f"💾 Données Pulsar sauvegardées dans l'historique pour {device.nom_appareil}.")

        except Exception as e:
            log.error(f"❌ Erreur lors de la sauvegarde des données Pulsar pour {tuya_device_id}: {e}", exc_info=True)
            db.session.rollback()

# Instance globale du service pour être facilement importable
pulsar_processor = PulsarProcessingService()
