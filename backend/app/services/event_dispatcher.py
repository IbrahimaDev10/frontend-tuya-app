# event_dispatcher.py - VERSION FINALE HARMONISÉE ET PERFORMANTE

import logging
from datetime import datetime

from app import db, get_redis
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.site import Site
from app.socket_events import emit_new_device_data

# --- IMPORTS POUR L'ORCHESTRATION ---
from app.services.analyseur_triphase_service import AnalyseurTriphaseService
# Si vous avez un service d'alertes séparé, importez-le aussi.
# from app.services.alert_service import AlertService 

log = logging.getLogger(__name__)

# --- INITIALISATION DES SERVICES ---
# On initialise les services une seule fois pour de meilleures performances.
try:
    analyseur_triphase = AnalyseurTriphaseService(redis_client=get_redis())
    # alert_service = AlertService(redis_client=get_redis())
    log.info("✅ [DISPATCHER] Services d'analyse initialisés.")
except Exception as e:
    analyseur_triphase = None
    # alert_service = None
    log.error(f"❌ [DISPATCHER] Erreur à l'initialisation des services d'analyse: {e}")


def _to_float(v, scale=1.0):
    """Convertit une valeur en float avec une mise à l'échelle."""
    try:
        if v is None:
            return None
        return float(v) / scale
    except (ValueError, TypeError):
        return None


def _timestamp_to_dt(ts_ms):
    """Convertit un timestamp en millisecondes en objet datetime UTC."""
    try:
        return datetime.utcfromtimestamp(int(ts_ms) / 1000.0)
    except (ValueError, TypeError, OSError):
        return datetime.utcnow()


def dispatch_complete_snapshot(device_id: str, snapshot_data: dict):
    """
    [FINAL] Reçoit un snapshot complet, l'enrichit, l'analyse, le sauvegarde,
    et notifie le front-end. C'est le cœur de traitement des données.
    """
    log.info(f"⚡ [DISPATCHER] Traitement du snapshot complet pour devId={device_id}...")
    
    try:
        # --- 1. RÉCUPÉRATION ET VALIDATION DE L'APPAREIL ---
        device = Device.query.filter_by(tuya_device_id=device_id).first()
        if not device:
            log.warning(f"⚠️ [DISPATCHER] Appareil inconnu devId={device_id}. Snapshot ignoré.")
            return

        if not device.is_assigne():
            log.info(f"ℹ️ [DISPATCHER] Appareil {device.nom_appareil} non assigné. Snapshot ignoré.")
            return

        # --- 2. PRÉPARATION DE L'OBJET DE DONNÉES (DeviceData) ---
        horodatage = _timestamp_to_dt(snapshot_data.get('timestamp'))
        keys = set(snapshot_data.keys())
        is_triphase_snapshot = all(k in keys for k in ('phase_a', 'phase_b', 'phase_c'))
        
        device_data = DeviceData(
            appareil_id=device.id,
            client_id=device.client_id,
            type_systeme='triphase' if is_triphase_snapshot else 'monophase',
            horodatage=horodatage,
            donnees_brutes=snapshot_data
        )

        # --- 3. REMPLISSAGE DES DONNÉES STRUCTURÉES ---
        if is_triphase_snapshot:
            log.info(f"⚡ Remplissage TRI (Pulsar) pour {device.nom_appareil}")
            from app.services.decoders import veratti_decoder
            
            pa = veratti_decoder.decode_phase_simple_data(snapshot_data['phase_a'], 'L1')
            pb = veratti_decoder.decode_phase_simple_data(snapshot_data['phase_b'], 'L2')
            pc = veratti_decoder.decode_phase_simple_data(snapshot_data['phase_c'], 'L3')

            if pa.get('success'):
                device_data.tension_l1, device_data.courant_l1, device_data.puissance_l1 = pa.get('tension'), pa.get('courant'), pa.get('puissance')
            if pb.get('success'):
                device_data.tension_l2, device_data.courant_l2, device_data.puissance_l2 = pb.get('tension'), pb.get('courant'), pb.get('puissance')
            if pc.get('success'):
                device_data.tension_l3, device_data.courant_l3, device_data.puissance_l3 = pc.get('tension'), pc.get('courant'), pc.get('puissance')
            
            device_data.puissance_totale = sum(filter(None, [device_data.puissance_l1, device_data.puissance_l2, device_data.puissance_l3]))
            tensions = [v for v in [device_data.tension_l1, device_data.tension_l2, device_data.tension_l3] if v is not None]
            device_data.tension = round(sum(tensions) / len(tensions), 1) if tensions else None
            currents = [v for v in [device_data.courant_l1, device_data.courant_l2, device_data.courant_l3] if v is not None]
            device_data.courant = round(sum(currents), 3) if currents else None
            device_data.puissance = device_data.puissance_totale

        else: # Monophasé
            log.info(f"🔌 Remplissage MONO (Pulsar) pour {device.nom_appareil}")
            device_data.tension = _to_float(snapshot_data.get('cur_voltage'), 100)
            device_data.courant = _to_float(snapshot_data.get('cur_current'), 1000)
            device_data.puissance = _to_float(snapshot_data.get('cur_power'), 100)
            device_data.energie = _to_float(snapshot_data.get('add_ele'), 1000)

        # Remplissage des champs communs (état switch, etc.)
        switch_candidates = ['switch', 'switch_1', 'switch_led', 'power']
        sw = next((snapshot_data.get(c) for c in switch_candidates if c in snapshot_data), None)
        if sw is not None:
            device_data.etat_switch = bool(sw)

        # --- 4. ORCHESTRATION : APPEL DES SERVICES D'ANALYSE ---
        db.session.add(device_data)
        
        if device_data.is_triphase() and analyseur_triphase:
            log.info(f"🧠 [DISPATCHER] Lancement de l'analyse triphasée pour {device.nom_appareil}...")
            analyseur_triphase.analyser_donnees_temps_reel(device_data, use_cache=False)
        
        # if alert_service:
        #     log.info(f"🔔 [DISPATCHER] Lancement de l'analyse d'alertes pour {device.nom_appareil}...")
        #     alert_service.analyser_et_creer_alertes(device_data, device)

        # --- 5. COMMIT ATOMIQUE ---
        db.session.commit()
        log.info(f"💾 [DISPATCHER] Snapshot et analyses sauvegardés pour {device.nom_appareil} (ID: {device_data.id}).")

        # --- 6. NOTIFICATION FRONT-END ---
        # On construit un payload plat et propre pour le front-end.
        final_payload = {
            # L'ID que le front-end utilise pour faire le lien
            'device_id': device.tuya_device_id,
            
            # Informations générales
            'appareil_id': device.id,
            'client_id': device.client_id,
            'type_systeme': device_data.type_systeme,
            'horodatage': device_data.horodatage.isoformat(),
            'etat_switch': getattr(device_data, 'etat_switch', None),

            # Données Monophasées (toujours présentes pour compatibilité)
            'tension': getattr(device_data, 'tension', None),
            'courant': getattr(device_data, 'courant', None),
            'puissance': getattr(device_data, 'puissance', None),
            'energie': getattr(device_data, 'energie', None),

            # Données Spécifiques au Triphasé
            'tension_l1': getattr(device_data, 'tension_l1', None),
            'courant_l1': getattr(device_data, 'courant_l1', None),
            'puissance_l1': getattr(device_data, 'puissance_l1', None),
            
            'tension_l2': getattr(device_data, 'tension_l2', None),
            'courant_l2': getattr(device_data, 'courant_l2', None),
            'puissance_l2': getattr(device_data, 'puissance_l2', None),
            
            'tension_l3': getattr(device_data, 'tension_l3', None),
            'courant_l3': getattr(device_data, 'courant_l3', None),
            'puissance_l3': getattr(device_data, 'puissance_l3', None),
            
            'puissance_totale': getattr(device_data, 'puissance_totale', None),
        }

        emit_new_device_data(final_payload)
        log.info(f"🚀 [DISPATCHER] Notification WebSocket envoyée pour {device.nom_appareil}.")

    except Exception as e:
        log.error(f"❌ [DISPATCHER] Erreur critique lors du traitement du snapshot pour {device_id}: {e}", exc_info=True)
        db.session.rollback()

