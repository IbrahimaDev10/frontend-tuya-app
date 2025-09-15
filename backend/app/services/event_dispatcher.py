import logging
from datetime import datetime

from app import db
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.site import Site  # Résolution client via site si nécessaire
from .decoders import veratti_decoder
from app.socket_events import emit_new_device_data  # Émission WebSocket après commit

log = logging.getLogger(__name__)


def _to_float(v, scale=1.0):
    try:
        if v is None:
            return None
        return float(v) / scale
    except Exception:
        return None


def _timestamp_to_dt(ts_ms):
    try:
        return datetime.utcfromtimestamp(int(ts_ms) / 1000.0)
    except Exception:
        return datetime.utcnow()


def dispatch_complete_snapshot(device_id: str, snapshot_data: dict):
    """
    Reçoit un snapshot complet (toutes les paires code→valeur accumulées par Redis),
    détecte mono/tri, remplit DeviceData, commit en base (atomique), puis émet 'new_data'.
    - Résolution client_id:
      * device.client_id si présent
      * sinon via device.site.client_id
      * sinon snapshot ignoré proprement
    """
    try:
        # Déterminer mono/tri
        keys = set(snapshot_data.keys())
        is_triphase_snapshot = all(k in keys for k in ('phase_a', 'phase_b', 'phase_c'))

        # Horodatage
        ts = snapshot_data.get('timestamp')
        horodatage = _timestamp_to_dt(ts) if ts else datetime.utcnow()

        # Appareil
        device = Device.get_by_tuya_id(device_id) if hasattr(Device, 'get_by_tuya_id') \
                 else Device.query.filter_by(tuya_device_id=device_id).first()
        if not device:
            log.warning(f"⚠️ [DISPATCHER] Appareil inconnu devId={device_id}. Snapshot ignoré.")
            return

        # Résoudre client_id (fallback via site)
        resolved_client_id = device.client_id
        if not resolved_client_id and getattr(device, 'site_id', None):
            try:
                site = Site.query.get(device.site_id)
            except Exception:
                site = None
            if site and site.client_id:
                resolved_client_id = site.client_id
                # Optionnel: auto-renseigner l’appareil
                try:
                    device.client_id = resolved_client_id
                    device.statut_assignation = 'assigne'
                    db.session.add(device)
                    db.session.flush()
                except Exception as e:
                    db.session.rollback()
                    log.warning(f"⚠️ [DISPATCHER] Impossible d’auto-renseigner client_id pour {device.nom_appareil}: {e}")

        if not resolved_client_id:
            log.warning(f"⚠️ [DISPATCHER] client_id introuvable pour {device.nom_appareil} (devId={device_id}). Snapshot ignoré.")
            return

        # Créer DeviceData
        device_data = DeviceData(
            appareil_id=device.id,
            client_id=resolved_client_id,
            type_systeme='triphase' if is_triphase_snapshot else 'monophase',
            horodatage=horodatage,
            donnees_brutes=snapshot_data
        )

        if is_triphase_snapshot:
            log.info(f"⚡ Remplissage TRI (Pulsar) pour {device.nom_appareil}")

            # Décodage phases (base64)
            pa = veratti_decoder.decode_phase_simple_data(snapshot_data['phase_a'], 'L1')
            pb = veratti_decoder.decode_phase_simple_data(snapshot_data['phase_b'], 'L2')
            pc = veratti_decoder.decode_phase_simple_data(snapshot_data['phase_c'], 'L3')

            if pa.get('success'):
                device_data.tension_l1 = pa.get('tension')
                device_data.courant_l1 = pa.get('courant')
                device_data.puissance_l1 = pa.get('puissance')
            if pb.get('success'):
                device_data.tension_l2 = pb.get('tension')
                device_data.courant_l2 = pb.get('courant')
                device_data.puissance_l2 = pb.get('puissance')
            if pc.get('success'):
                device_data.tension_l3 = pc.get('tension')
                device_data.courant_l3 = pc.get('courant')
                device_data.puissance_l3 = pc.get('puissance')

            # Détecter l’état ON/OFF si présent dans le snapshot (ajout TRI)
            switch_candidates = ['switch', 'switch_1', 'switch_led', 'power']
            sw = next((snapshot_data.get(c) for c in switch_candidates if c in snapshot_data), None)
            if sw is not None:
                device_data.etat_switch = bool(sw)

            # Totaux + champs compat mono
            device_data.puissance_totale = sum([
                device_data.puissance_l1 or 0,
                device_data.puissance_l2 or 0,
                device_data.puissance_l3 or 0
            ]) or None

            tensions = [v for v in [device_data.tension_l1, device_data.tension_l2, device_data.tension_l3] if v is not None]
            device_data.tension = round(sum(tensions) / len(tensions), 1) if tensions else None
            currents = [v for v in [device_data.courant_l1, device_data.courant_l2, device_data.courant_l3] if v is not None]
            device_data.courant = round(sum(currents), 3) if currents else None
            device_data.puissance = device_data.puissance_totale

        else:
            log.info(f"🔌 Remplissage MONO (Pulsar) pour {device.nom_appareil}")

            # Mapping mono
            device_data.tension = _to_float(snapshot_data.get('cur_voltage'), 100)
            device_data.courant = _to_float(snapshot_data.get('cur_current'), 1000)
            device_data.puissance = _to_float(snapshot_data.get('cur_power'), 100)
            device_data.energie = _to_float(snapshot_data.get('add_ele'), 1000)

            # ON/OFF mono
            sw = snapshot_data.get('switch') if 'switch' in snapshot_data else snapshot_data.get('switch_1')
            device_data.etat_switch = bool(sw) if sw is not None else None

            # Température & fréquence
            device_data.temperature = _to_float(snapshot_data.get('temp_current'), 10) if snapshot_data.get('temp_current') is not None else None
            if snapshot_data.get('cur_frequency') is not None:
                device_data.frequence = _to_float(snapshot_data.get('cur_frequency'), 100)
            else:
                device_data.frequence = _to_float(snapshot_data.get('supply_frequency'))

        # Commit atomique
        db.session.add(device_data)
        db.session.commit()
        log.info(f"💾 [DB] Snapshot Pulsar sauvegardé pour {device.nom_appareil} (id={device_data.id}).")

        # Payload WebSocket (inclut etat_switch)
        payload = {
            "device_id": device.tuya_device_id,
            "appareil_id": device.id,
            "client_id": resolved_client_id,
            "type_systeme": device_data.type_systeme,
            "horodatage": device_data.horodatage.isoformat(),
            "etat_switch": getattr(device_data, 'etat_switch', None),
            # Mono
            "tension": device_data.tension,
            "courant": device_data.courant,
            "puissance": device_data.puissance,
            "energie": getattr(device_data, 'energie', None),
            # Tri
            "tension_l1": getattr(device_data, 'tension_l1', None),
            "tension_l2": getattr(device_data, 'tension_l2', None),
            "tension_l3": getattr(device_data, 'tension_l3', None),
            "courant_l1": getattr(device_data, 'courant_l1', None),
            "courant_l2": getattr(device_data, 'courant_l2', None),
            "courant_l3": getattr(device_data, 'courant_l3', None),
            "puissance_l1": getattr(device_data, 'puissance_l1', None),
            "puissance_l2": getattr(device_data, 'puissance_l2', None),
            "puissance_l3": getattr(device_data, 'puissance_l3', None),
            "puissance_totale": getattr(device_data, 'puissance_totale', None),
        }
        emit_new_device_data(payload)

    except Exception as e:
        log.error(f"❌ [DISPATCHER] Erreur DB lors de la sauvegarde du snapshot Pulsar pour {device_id}: {e}", exc_info=True)
        db.session.rollback()