# app/services/pulsar_listener.py
import pulsar
import logging
from threading import Thread
from .pulsar_utils.mq_authentication import get_authentication
from .pulsar_utils.message_util import decrypt_message, message_id
from .data_processor import process_pulsar_message

log = logging.getLogger(__name__)

class TuyaPulsarListener(Thread):
    def __init__(self, access_id, access_key, pulsar_url, mq_env, app):
        super().__init__()
        self.daemon = True
        self.access_id = access_id
        self.access_key = access_key
        self.pulsar_url = pulsar_url
        self.mq_env = mq_env
        self.client = None
        self.app = app

    def run(self):
        log.info(f"🚀 [PULSAR] Démarrage du listener Pulsar pour l'environnement '{self.mq_env}'...")
        try:
            self.client = pulsar.Client(
                self.pulsar_url,
                authentication=get_authentication(self.access_id, self.access_key),
                tls_allow_insecure_connection=True
            )
            topic = f"{self.access_id}/out/{self.mq_env}"
            subscription_name = f"{self.access_id}-sub"
            consumer = self.client.subscribe(
                topic,
                subscription_name,
                consumer_type=pulsar.ConsumerType.Failover
            )
            log.info(f"✅ [PULSAR] Connecté et abonné au topic '{topic}'.")

            while True:
                pulsar_message = consumer.receive()
                msg_id_str = message_id(pulsar_message.message_id())
                
                try:
                    log.info(f"--- 📩 [PULSAR] Message reçu ! ID: {msg_id_str} ---")
                    decrypted_data = decrypt_message(pulsar_message, self.access_key)
                    log.info(f"✅ [PULSAR] Message déchiffré: {decrypted_data}")

                    # On exécute le traitement DANS le contexte de l'application
                    with self.app.app_context():
                        process_pulsar_message(decrypted_data)

                    consumer.acknowledge(pulsar_message)
                except Exception as e:
                    log.error(f"❌ [PULSAR] Erreur lors du traitement du message ID {msg_id_str}: {e}", exc_info=True)
                    consumer.negative_acknowledge(pulsar_message)

        except pulsar.Interrupted:
            log.warning("[PULSAR] Le listener a été interrompu.")
        except Exception as e:
            log.critical(f"❌ [PULSAR] Erreur critique du listener: {e}", exc_info=True)
        finally:
            if self.client:
                self.client.close()
                log.info("[PULSAR] Client Pulsar fermé.")
