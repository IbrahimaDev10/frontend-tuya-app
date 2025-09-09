# app/services/event_dispatcher.py
import logging
from datetime import datetime
from app import db, socketio
from app.models.device import Device
from app.models.device_data import DeviceData

# MODIFICATION : On importe l'instance du décodeur depuis notre module
from .decoders import veratti_decoder

log = logging.getLogger(__name__)

def dispatch_complete_snapshot(device_id: str, snapshot_data: dict):
    # ... (le début de la fonction est inchangé) ...
    try:
        # ... (la récupération du device est inchangée) ...

        if is_triphase_snapshot:
            log.info(f"Remplissage des données TRIphasées (via Pulsar) pour {device.nom_appareil}")
            
            # MODIFICATION : On utilise notre décodeur de classe
            phase_a = veratti_decoder.decode_phase_simple_data(snapshot_data['phase_a'], 'L1')
            if phase_a.get('success'):
                device_data.tension_l1, device_data.courant_l1, device_data.puissance_l1 = phase_a.get('tension'), phase_a.get('courant'), phase_a.get('puissance')
            
            phase_b = veratti_decoder.decode_phase_simple_data(snapshot_data['phase_b'], 'L2')
            if phase_b.get('success'):
                device_data.tension_l2, device_data.courant_l2, device_data.puissance_l2 = phase_b.get('tension'), phase_b.get('courant'), phase_b.get('puissance')
            
            phase_c = veratti_decoder.decode_phase_simple_data(snapshot_data['phase_c'], 'L3')
            if phase_c.get('success'):
                device_data.tension_l3, device_data.courant_l3, device_data.puissance_l3 = phase_c.get('tension'), phase_c.get('courant'), phase_c.get('puissance')
            
            # On peut aussi calculer les totaux pour la compatibilité
            device_data.puissance_totale = (device_data.puissance_l1 or 0) + (device_data.puissance_l2 or 0) + (device_data.puissance_l3 or 0)

        else: # Monophasé
            # ... (la logique monophasée reste la même, elle est déjà correcte) ...
            log.info(f"Remplissage des données MONOphasées (via Pulsar) pour {device.nom_appareil}")
            # ...

        db.session.add(device_data)
        db.session.commit()
        log.info(f"💾 [DB] Snapshot Pulsar complet sauvegardé pour {device.nom_appareil}.")

    except Exception as e:
        log.error(f"❌ [DISPATCHER] Erreur DB lors de la sauvegarde du snapshot Pulsar pour {device_id}: {e}", exc_info=True)
        db.session.rollback()
