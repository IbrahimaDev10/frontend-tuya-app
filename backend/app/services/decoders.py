# app/services/decoders.py
import base64
import struct
import logging

log = logging.getLogger(__name__)

# On intègre ici votre classe VerattiDecoder, qui est excellente.
class VerattiDecoder:
    """
    🧠 Décodeur intelligent v5.3 - Intégré dans le flux Pulsar.
    """
    def __init__(self, debug=True):
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        if self.debug:
            self.logger.info("🧠 Décodeur VERATTI v5.3 (Puissance Fiabilisée) initialisé pour Pulsar.")

    def decode_phase_simple_data(self, base64_data: str, phase_name: str) -> dict:
        """
        Décode les données de phase simples (V, A) et calcule la puissance.
        Utilisé par le flux Pulsar qui envoie les phases séparément.
        """
        try:
            bytes_data = base64.b64decode(base64_data)
        except Exception as e:
            return {'success': False, 'error': f'invalid_base64: {e}'}

        # La trame simple de Pulsar contient V, I, P sur 8 octets
        if len(bytes_data) < 8:
            return {'success': False, 'error': 'data_too_short'}
            
        try:
            result = {'success': True, 'phase': phase_name}
            
            result['tension'] = round(struct.unpack('>H', bytes_data[0:2])[0] / 10.0, 1)
            result['courant'] = round(int.from_bytes(bytes_data[2:5], 'big') / 1000.0, 3)
            result['puissance'] = round(int.from_bytes(bytes_data[5:8], 'big') / 10.0, 2) # La puissance est lue directement
            
            if self.debug:
                self.logger.debug(f"  ✅ {phase_name} (Pulsar) décodé: {result['tension']}V, {result['courant']}A, {result['puissance']}W")

            return result
        except Exception as e:
            return {'success': False, 'error': f'struct_unpack_error: {e}'}

# On instancie le décodeur une seule fois pour toute l'application
veratti_decoder = VerattiDecoder()
