# alert_service.py - CORRIGÉ pour compatibilité DeviceService
# Compatible avec vos modèles Device, DeviceData, Alert existants
# ✅ Détection automatique + Cache Redis + Intégration AnalyseurTriphaseService

from app import db, get_redis
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.alert import Alert
from datetime import datetime, timedelta
import json
import logging
from typing import List, Dict, Tuple, Optional, Any

class AlertService:
    """Service centralisé pour gestion intelligente des alertes mono/triphasé"""
    
    def __init__(self, redis_client=None):  # ✅ CORRIGÉ: Accepter redis_client en paramètre
        """
        Initialiser AlertService
        
        Args:
            redis_client: Client Redis optionnel (si fourni par DeviceService)
        """
        # ✅ Utiliser redis_client fourni ou récupérer depuis app
        self.redis = redis_client if redis_client is not None else get_redis()
        self.logger = logging.getLogger(__name__)
        
        # ✅ Lazy loading de l'analyseur triphasé
        self._analyseur_triphase = None
        
        # Configuration cache pour déduplication
        self.cache_config = {
            'alert_dedup_ttl': 1800,      # 30 min - Déduplication alertes
            'analysis_result_ttl': 300,    # 5 min - Résultats d'analyse
            'device_status_ttl': 600,      # 10 min - Statut appareil
            'threshold_cache_ttl': 3600    # 1h - Cache seuils
        }
        
        # Préfixe Redis
        self.redis_prefix = "alerts:"
        
        # Configuration par défaut
        self.default_config = {
            'auto_detection': True,
            'create_alerts_db': True,
            'use_cache': True,
            'enable_deduplication': True,
            'log_analysis_results': True
        }
        
        self.logger.info(f"AlertService initialisé - Redis: {'✅' if self.redis else '❌'}")
    
    @property
    def analyseur_triphase(self):
        """Lazy loading de l'analyseur triphasé"""
        if self._analyseur_triphase is None:
            try:
                from app.services.analyseur_triphase_service import AnalyseurTriphaseService
                self._analyseur_triphase = AnalyseurTriphaseService(redis_client=self.redis)
                self.logger.info("✅ AnalyseurTriphaseService chargé")
            except ImportError:
                self.logger.warning("⚠️ AnalyseurTriphaseService non disponible")
                self._analyseur_triphase = None
            except Exception as e:
                self.logger.error(f"❌ Erreur chargement AnalyseurTriphaseService: {e}")
                self._analyseur_triphase = None
        
        return self._analyseur_triphase
    
    def _get_device_thresholds_cached(self, device: Device) -> Dict:
        """Récupérer seuils appareil avec cache"""
        if not self.redis:
            return device.get_seuils_actifs()
        
        try:
            cache_key = f"{self.redis_prefix}thresholds:{device.id}"
            cached_thresholds = self.redis.get(cache_key)
            
            if cached_thresholds:
                return json.loads(cached_thresholds)
            
            # Récupérer depuis DB et cacher
            seuils = device.get_seuils_actifs()
            ttl = self.cache_config['threshold_cache_ttl']
            
            self.redis.setex(cache_key, ttl, json.dumps(seuils))
            return seuils
            
        except Exception as e:
            self.logger.error(f"Erreur cache seuils: {e}")
            return device.get_seuils_actifs()
    
    def _alert_recently_created(self, alert_type: str, device_id: str, minutes: int = 30) -> bool:
        """Vérifier déduplication alertes avec cache Redis"""
        if not self.redis:
            # Fallback DB si pas de Redis
            since = datetime.utcnow() - timedelta(minutes=minutes)
            return Alert.query.filter(
                Alert.appareil_id == device_id,
                Alert.type_alerte == alert_type,
                Alert.date_creation >= since,
                Alert.statut.in_(['nouvelle', 'vue'])
            ).first() is not None
        
        try:
            dedup_key = f"{self.redis_prefix}dedup:{alert_type}:{device_id}"
            return bool(self.redis.exists(dedup_key))
            
        except Exception as e:
            self.logger.error(f"Erreur vérification déduplication: {e}")
            return False
    
    def _cache_alert_created(self, alert_type: str, device_id: str):
        """Marquer alerte créée pour déduplication"""
        if not self.redis:
            return
        
        try:
            dedup_key = f"{self.redis_prefix}dedup:{alert_type}:{device_id}"
            ttl = self.cache_config['alert_dedup_ttl']
            
            cache_data = {
                'alert_type': alert_type,
                'device_id': device_id,
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(dedup_key, ttl, json.dumps(cache_data))
            
        except Exception as e:
            self.logger.error(f"Erreur cache déduplication: {e}")
    
    def _invalidate_device_caches(self, device_id: str):
        """Invalider tous les caches d'un appareil"""
        if not self.redis:
            return
        
        try:
            patterns = [
                f"{self.redis_prefix}analysis:*",
                f"{self.redis_prefix}thresholds:{device_id}",
                f"{self.redis_prefix}dedup:*:{device_id}",
                f"type_detection:{device_id}"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                keys = self.redis.keys(pattern)
                if keys:
                    deleted_count += self.redis.delete(*keys)
            
            self.logger.debug(f"Cache invalidé pour device {device_id}: {deleted_count} clés")
            
        except Exception as e:
            self.logger.error(f"Erreur invalidation cache device: {e}")
    
    # =================== MÉTHODES UTILITAIRES ===================
    
    def _serialize_alert_for_result(self, alert) -> Dict:
        """Sérialiser alerte pour résultat"""
        try:
            if hasattr(alert, 'to_dict'):
                return alert.to_dict()
            else:
                return {
                    'id': getattr(alert, 'id', None),
                    'type_alerte': getattr(alert, 'type_alerte', None),
                    'gravite': getattr(alert, 'gravite', None),
                    'titre': getattr(alert, 'titre', None),
                    'message': getattr(alert, 'message', None),
                    'valeur_mesuree': getattr(alert, 'valeur_mesuree', None),
                    'valeur_seuil': getattr(alert, 'valeur_seuil', None),
                    'unite': getattr(alert, 'unite', None),
                    'date_creation': getattr(alert, 'date_creation', datetime.utcnow()).isoformat()
                }
        except Exception as e:
            self.logger.error(f"Erreur sérialisation alerte: {e}")
            return {'error': 'Erreur sérialisation', 'alert_id': getattr(alert, 'id', 'unknown')}
    
    def _create_simple_alert(self, device: Device, type_alerte: str, gravite: str, 
                           titre: str, message: str, valeur: float, seuil: float, unite: str) -> Optional[Alert]:
        """Créer une alerte simple compatible avec votre modèle Alert"""
        try:
            # ✅ Créer alerte selon votre modèle existant
            alerte = Alert(
                client_id=device.client_id,
                appareil_id=device.id,
                type_alerte=type_alerte,
                gravite=gravite,
                titre=titre,
                message=message,
                valeur_mesuree=valeur,
                valeur_seuil=seuil,
                unite=unite,
                date_creation=datetime.utcnow(),
                statut='nouvelle'
            )
            
            # Sauvegarder en DB
            db.session.add(alerte)
            db.session.commit()
            
            self.logger.debug(f"✅ Alerte créée: {titre} ({gravite})")
            return alerte
            
        except Exception as e:
            self.logger.error(f"❌ Erreur création alerte: {e}")
            db.session.rollback()
            return None
    
    # =================== POINT D'ENTRÉE PRINCIPAL ===================
    
    def analyser_et_creer_alertes(self, device_data: DeviceData, device: Device, 
                                 config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Point d'entrée principal pour analyse et création d'alertes
        
        Args:
            device_data: Données DeviceData à analyser
            device: Appareil Device correspondant
            config: Configuration optionnelle
            
        Returns:
            Dict avec résultats d'analyse et alertes créées
        """
        try:
            # Configuration
            config = {**self.default_config, **(config or {})}
            
            # Résultat d'analyse
            analyse_result = {
                'device_id': device.id,
                'device_name': device.nom_appareil,
                'timestamp': datetime.utcnow().isoformat(),
                'type_systeme_detecte': None,
                'type_systeme_precedent': device.type_systeme,
                'alertes_creees': [],
                'analyses_executees': [],
                'erreurs': [],
                'from_cache': False,
                'cache_used': config['use_cache']
            }
            
            self.logger.info(f"🔍 Analyse alertes - Device: {device.id} ({device.nom_appareil})")
            
            # ✅ ÉTAPE 1: Détection automatique du type de système
            if config['auto_detection']:
                type_detecte = self._detecter_type_systeme_auto(device_data, device)
                analyse_result['type_systeme_detecte'] = type_detecte
                
                # Mettre à jour Device si type changé
                if type_detecte != device.type_systeme:
                    self._update_device_type(device, type_detecte)
                    analyse_result['type_changed'] = True
                    self.logger.info(f"🔄 Type système mis à jour: {device.type_systeme} → {type_detecte}")
            else:
                type_detecte = device.type_systeme
                analyse_result['type_systeme_detecte'] = type_detecte
            
            # ✅ ÉTAPE 2: Vérifier cache d'analyse récente
            cache_key = f"{device.id}_{int(device_data.horodatage.timestamp()) if device_data.horodatage else int(datetime.utcnow().timestamp())}"
            
            if config['use_cache']:
                cached_analysis = self._get_cached_analysis(cache_key)
                if cached_analysis:
                    self.logger.debug(f"📦 Analyse depuis cache pour {device.id}")
                    cached_analysis['from_cache'] = True
                    return cached_analysis
            
            # ✅ ÉTAPE 3: Dispatcher vers analyseurs spécialisés
            alertes_creees = []
            
            # Analyse selon type détecté
            if type_detecte == 'triphase':
                alertes_triphase = self._analyser_triphase(device_data, device, config)
                alertes_creees.extend(alertes_triphase)
                analyse_result['analyses_executees'].append('triphase')
                
            elif type_detecte == 'monophase':
                alertes_mono = self._analyser_monophase(device_data, device, config)
                alertes_creees.extend(alertes_mono)
                analyse_result['analyses_executees'].append('monophase')
            
            # ✅ ÉTAPE 4: Analyses communes (température, communication, etc.)
            alertes_communes = self._analyser_conditions_communes(device_data, device, config)
            alertes_creees.extend(alertes_communes)
            analyse_result['analyses_executees'].append('conditions_communes')
            
            # ✅ ÉTAPE 5: Finaliser résultats
            analyse_result['alertes_creees'] = [
                self._serialize_alert_for_result(alert) for alert in alertes_creees
            ]
            analyse_result['nb_alertes'] = len(alertes_creees)
            analyse_result['nb_alertes_critiques'] = len([a for a in alertes_creees if hasattr(a, 'gravite') and a.gravite == 'critique'])
            
            # ✅ ÉTAPE 6: Mettre en cache
            if config['use_cache']:
                self._cache_analysis_result(cache_key, analyse_result)
            
            # ✅ ÉTAPE 7: Log résultat
            if config['log_analysis_results']:
                self.logger.info(f"✅ Analyse terminée - {len(alertes_creees)} alertes créées ({analyse_result['nb_alertes_critiques']} critiques)")
            
            return analyse_result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse alertes device {device.id}: {e}")
            return {
                'device_id': device.id,
                'timestamp': datetime.utcnow().isoformat(),
                'success': False,
                'error': str(e),
                'alertes_creees': [],
                'nb_alertes': 0
            }
    
    # =================== DÉTECTION AUTOMATIQUE TYPE SYSTÈME ===================
    
    def _detecter_type_systeme_auto(self, device_data: DeviceData, device: Device) -> str:
        """Détection automatique intelligente du type de système"""
        try:
            # ✅ Vérifier données triphasées présentes
            has_triphase_data = all([
                device_data.tension_l1 is not None,
                device_data.tension_l2 is not None,
                device_data.tension_l3 is not None
            ])
            
            # ✅ Vérifier données monophasées seulement
            has_mono_only = (
                device_data.tension is not None and 
                not has_triphase_data
            )
            
            # ✅ Vérifier configuration Device existante
            device_configured_type = device.type_systeme
            
            # ✅ Logique de détection
            if has_triphase_data:
                # Données triphasées détectées → Forcer triphasé
                detected_type = 'triphase'
                self.logger.debug(f"🔍 Détection triphasé: données L1/L2/L3 présentes")
                
            elif has_mono_only:
                # Seulement données monophasées → Monophasé probable
                if device_configured_type == 'triphase':
                    # Device configuré triphasé mais données mono → Garder config
                    detected_type = 'triphase'
                    self.logger.debug(f"🔍 Device configuré triphasé, gardé malgré données mono")
                else:
                    detected_type = 'monophase'
                    self.logger.debug(f"🔍 Détection monophasé: données mono seulement")
            
            else:
                # Pas de données exploitables → Garder configuration existante
                detected_type = device_configured_type or 'monophase'
                self.logger.debug(f"🔍 Données insuffisantes, type gardé: {detected_type}")
            
            # ✅ Cache de la détection
            if self.redis:
                detection_cache = {
                    'detected_type': detected_type,
                    'has_triphase_data': has_triphase_data,
                    'has_mono_data': has_mono_only,
                    'device_configured': device_configured_type,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                cache_key = f"type_detection:{device.id}"
                self.redis.setex(cache_key, 3600, json.dumps(detection_cache))  # 1h
            
            return detected_type
            
        except Exception as e:
            self.logger.error(f"Erreur détection type système device {device.id}: {e}")
            return device.type_systeme or 'monophase'
    
    def _update_device_type(self, device: Device, new_type: str):
        """Mettre à jour le type de système d'un appareil"""
        try:
            old_type = device.type_systeme
            device.type_systeme = new_type
            
            # ✅ Mettre à jour seuils si nécessaire
            if new_type == 'triphase' and old_type == 'monophase':
                if hasattr(device, '_init_triphasé_seuils'):
                    device._init_triphasé_seuils()
            elif new_type == 'monophase' and old_type == 'triphase':
                if hasattr(device, '_reset_triphasé_seuils'):
                    device._reset_triphasé_seuils()
            
            db.session.add(device)
            db.session.commit()
            
            # ✅ Invalider caches liés
            if self.redis:
                self._invalidate_device_caches(device.id)
            
            self.logger.info(f"🔄 Device {device.id} type mis à jour: {old_type} → {new_type}")
            
        except Exception as e:
            self.logger.error(f"Erreur mise à jour type device {device.id}: {e}")
            db.session.rollback()
    
    # =================== ANALYSEURS SPÉCIALISÉS ===================
    
    def _analyser_triphase(self, device_data: DeviceData, device: Device, config: Dict) -> List[Alert]:
        """Analyser système triphasé via AnalyseurTriphaseService"""
        try:
            if not self.analyseur_triphase:
                self.logger.warning("⚠️ AnalyseurTriphaseService non disponible pour analyse triphasé")
                return []
            
            # ✅ Forcer type_systeme sur device_data
            device_data.type_systeme = 'triphase'
            
            # ✅ Déléguer à l'analyseur triphasé existant
            alertes_triphase = self.analyseur_triphase.analyser_donnees_temps_reel(
                device_data, 
                use_cache=config.get('use_cache', True)
            )
            
            if isinstance(alertes_triphase, list):
                self.logger.debug(f"🔧 Analyse triphasé: {len(alertes_triphase)} alertes créées")
                return alertes_triphase
            else:
                self.logger.warning(f"⚠️ Analyse triphasé retour inattendu: {type(alertes_triphase)}")
                return []
                
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse triphasé device {device.id}: {e}")
            return []
    
    def _analyser_monophase(self, device_data: DeviceData, device: Device, config: Dict) -> List[Alert]:
        """Analyser système monophasé avec vos seuils existants"""
        try:
            alertes_mono = []
            
            # ✅ Forcer type_systeme sur device_data
            device_data.type_systeme = 'monophase'
            
            # ✅ Récupérer seuils avec cache
            seuils = self._get_device_thresholds_cached(device)
            
            self.logger.debug(f"🔍 Analyse monophasé - Seuils: {seuils}")
            
            # ✅ Analyser tension monophasée
            if device_data.tension is not None:
                tension_alerts = self._check_tension_monophase(device_data, device, seuils)
                alertes_mono.extend(tension_alerts)
            
            # ✅ Analyser courant monophasé
            if device_data.courant is not None:
                courant_alerts = self._check_courant_monophase(device_data, device, seuils)
                alertes_mono.extend(courant_alerts)
            
            # ✅ Analyser puissance monophasée
            if device_data.puissance is not None:
                puissance_alerts = self._check_puissance_monophase(device_data, device, seuils)
                alertes_mono.extend(puissance_alerts)
            
            self.logger.debug(f"🔧 Analyse monophasé: {len(alertes_mono)} alertes créées")
            return alertes_mono
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse monophasé device {device.id}: {e}")
            return []
    
    def _analyser_conditions_communes(self, device_data: DeviceData, device: Device, config: Dict) -> List[Alert]:
        """Analyser conditions communes (température, communication, etc.)"""
        try:
            alertes_communes = []
            
            # ✅ Analyser température
            if device_data.temperature is not None:
                temp_alerts = self._check_temperature(device_data, device)
                alertes_communes.extend(temp_alerts)
            
            # ✅ Analyser humidité
            if device_data.humidite is not None:
                humidity_alerts = self._check_humidity(device_data, device)
                alertes_communes.extend(humidity_alerts)
            
            # ✅ Analyser état communication
            comm_alerts = self._check_communication_status(device_data, device)
            alertes_communes.extend(comm_alerts)
            
            self.logger.debug(f"🔧 Analyse commune: {len(alertes_communes)} alertes créées")
            return alertes_communes
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse commune device {device.id}: {e}")
            return []
    
    # =================== ANALYSEURS MONOPHASÉ DÉTAILLÉS ===================
    
    def _check_tension_monophase(self, device_data: DeviceData, device: Device, seuils: Dict) -> List[Alert]:
        """Vérifier seuils tension monophasée"""
        alertes = []
        tension = device_data.tension
        
        try:
            seuil_min = seuils.get('seuil_tension_min', 200.0)
            seuil_max = seuils.get('seuil_tension_max', 250.0)
            
            # ✅ Tension trop basse
            if tension < seuil_min and not self._alert_recently_created('tension_low', device.id, minutes=20):
                alerte = self._create_simple_alert(
                    device=device,
                    type_alerte='seuil_depasse',
                    gravite='warning',
                    titre='Tension trop basse',
                    message=f'Tension {tension}V inférieure au seuil minimum {seuil_min}V',
                    valeur=tension,
                    seuil=seuil_min,
                    unite='V'
                )
                
                if alerte:
                    alertes.append(alerte)
                    self._cache_alert_created('tension_low', device.id)
            
            # ✅ Tension trop élevée
            elif tension > seuil_max and not self._alert_recently_created('tension_high', device.id, minutes=20):
                alerte = self._create_simple_alert(
                    device=device,
                    type_alerte='seuil_depasse',
                    gravite='critique',
                    titre='Tension trop élevée',
                    message=f'Tension {tension}V supérieure au seuil maximum {seuil_max}V',
                    valeur=tension,
                    seuil=seuil_max,
                    unite='V'
                )
                
                if alerte:
                    alertes.append(alerte)
                    self._cache_alert_created('tension_high', device.id)
                    
        except Exception as e:
            self.logger.error(f"Erreur check tension monophasé: {e}")
        
        return alertes
    
    def _check_courant_monophase(self, device_data: DeviceData, device: Device, seuils: Dict) -> List[Alert]:
        """Vérifier seuils courant monophasé"""
        alertes = []
        courant = device_data.courant
        
        try:
            seuil_max = seuils.get('seuil_courant_max', 20.0)
            
            # ✅ Courant trop élevé
            if courant > seuil_max and not self._alert_recently_created('courant_high', device.id, minutes=15):
                alerte = self._create_simple_alert(
                    device=device,
                    type_alerte='seuil_depasse',
                    gravite='critique',
                    titre='Courant élevé détecté',
                    message=f'Courant {courant}A supérieur au seuil {seuil_max}A',
                    valeur=courant,
                    seuil=seuil_max,
                    unite='A'
                )
                
                if alerte:
                    alertes.append(alerte)
                    self._cache_alert_created('courant_high', device.id)
                    
        except Exception as e:
            self.logger.error(f"Erreur check courant monophasé: {e}")
        
        return alertes
    
    def _check_puissance_monophase(self, device_data: DeviceData, device: Device, seuils: Dict) -> List[Alert]:
        """Vérifier seuils puissance monophasée"""
        alertes = []
        puissance = device_data.puissance
        
        try:
            seuil_max = seuils.get('seuil_puissance_max', 5000.0)
            
            # ✅ Puissance élevée
            if puissance > seuil_max and not self._alert_recently_created('puissance_high', device.id, minutes=30):
                alerte = self._create_simple_alert(
                    device=device,
                    type_alerte='seuil_depasse',
                    gravite='warning',
                    titre='Puissance élevée',
                    message=f'Puissance {puissance}W supérieure au seuil {seuil_max}W',
                    valeur=puissance,
                    seuil=seuil_max,
                    unite='W'
                )
                
                if alerte:
                    alertes.append(alerte)
                    self._cache_alert_created('puissance_high', device.id)
                    
        except Exception as e:
            self.logger.error(f"Erreur check puissance monophasé: {e}")
        
        return alertes
    
    # =================== ANALYSEURS CONDITIONS COMMUNES ===================
    
    def _check_temperature(self, device_data: DeviceData, device: Device) -> List[Alert]:
        """Vérifier température"""
        alertes = []
        temperature = device_data.temperature
        
        try:
            # Seuils par défaut température
            seuil_max = 60.0  # °C
            seuil_critique = 80.0  # °C
            
            if temperature > seuil_critique and not self._alert_recently_created('temp_critical', device.id, minutes=10):
                alerte = self._create_simple_alert(
                    device=device,
                    type_alerte='temperature_haute',
                    gravite='critique',
                    titre='Température critique',
                    message=f'Température {temperature}°C critique (seuil: {seuil_critique}°C)',
                    valeur=temperature,
                    seuil=seuil_critique,
                    unite='°C'
                )
                
                if alerte:
                    alertes.append(alerte)
                    self._cache_alert_created('temp_critical', device.id)
                    
            elif temperature > seuil_max and not self._alert_recently_created('temp_high', device.id, minutes=30):
                alerte = self._create_simple_alert(
                    device=device,
                    type_alerte='temperature_haute',
                    gravite='warning',
                    titre='Température élevée',
                    message=f'Température {temperature}°C élevée (seuil: {seuil_max}°C)',
                    valeur=temperature,
                    seuil=seuil_max,
                    unite='°C'
                )
                
                if alerte:
                    alertes.append(alerte)
                    self._cache_alert_created('temp_high', device.id)
                    
        except Exception as e:
            self.logger.error(f"Erreur check température: {e}")
        
        return alertes
    
    def _check_humidity(self, device_data: DeviceData, device: Device) -> List[Alert]:
        """Vérifier humidité"""
        alertes = []
        humidite = device_data.humidite
        
        try:
            # Seuils humidité
            seuil_min = 10.0  # %
            seuil_max = 90.0  # %
            
            if humidite < seuil_min and not self._alert_recently_created('humidity_low', device.id, minutes=60):
                alerte = self._create_simple_alert(
                    device=device,
                    type_alerte='autre',
                    gravite='info',
                    titre='Humidité très basse',
                    message=f'Humidité {humidite}% très basse',
                    valeur=humidite,
                    seuil=seuil_min,
                    unite='%'
                )
                
                if alerte:
                    alertes.append(alerte)
                    self._cache_alert_created('humidity_low', device.id)
                    
            elif humidite > seuil_max and not self._alert_recently_created('humidity_high', device.id, minutes=60):
                alerte = self._create_simple_alert(
                    device=device,
                    type_alerte='autre',
                    gravite='warning',
                    titre='Humidité très élevée',
                    message=f'Humidité {humidite}% très élevée',
                    valeur=humidite,
                    seuil=seuil_max,
                    unite='%'
                )
                
                if alerte:
                    alertes.append(alerte)
                    self._cache_alert_created('humidity_high', device.id)
                    
        except Exception as e:
            self.logger.error(f"Erreur check humidité: {e}")
        
        return alertes
    
    def _check_communication_status(self, device_data: DeviceData, device: Device) -> List[Alert]:
        """Vérifier état communication appareil"""
        alertes = []
        
        try:
            # ✅ Vérifier si l'appareil était hors ligne longtemps
            if hasattr(device, 'derniere_donnee') and device.derniere_donnee:
                temps_silence = datetime.utcnow() - device.derniere_donnee
                silence_minutes = temps_silence.total_seconds() / 60
                
                # Alerte si plus de 30 minutes sans données
                if silence_minutes > 30 and not self._alert_recently_created('comm_lost', device.id, minutes=60):
                    alerte = self._create_simple_alert(
                        device=device,
                        type_alerte='erreur_communication',
                        gravite='warning',
                        titre='Perte de communication',
                        message=f'Aucune donnée reçue depuis {int(silence_minutes)} minutes',
                        valeur=silence_minutes,
                        seuil=30,
                        unite='min'
                    )
                    
                    if alerte:
                        alertes.append(alerte)
                        self._cache_alert_created('comm_lost', device.id)
            
            # ✅ Vérifier cohérence des données
            if self._detect_data_anomaly(device_data):
                if not self._alert_recently_created('data_anomaly', device.id, minutes=45):
                    alerte = self._create_simple_alert(
                        device=device,
                        type_alerte='autre',
                        gravite='info',
                        titre='Anomalie données',
                        message='Données incohérentes détectées',
                        valeur=0,
                        seuil=0,
                        unite=''
                    )
                    
                    if alerte:
                        alertes.append(alerte)
                        self._cache_alert_created('data_anomaly', device.id)
                        
        except Exception as e:
            self.logger.error(f"Erreur check communication: {e}")
        
        return alertes
    
    def _detect_data_anomaly(self, device_data: DeviceData) -> bool:
        """Détecter anomalies dans les données"""
        try:
            # Vérifications basiques de cohérence
            
            # 1. Tensions négatives
            if device_data.tension and device_data.tension < 0:
                return True
            
            if any(t and t < 0 for t in [device_data.tension_l1, device_data.tension_l2, device_data.tension_l3]):
                return True
            
            # 2. Courants négatifs
            if device_data.courant and device_data.courant < 0:
                return True
            
            if any(c and c < 0 for c in [device_data.courant_l1, device_data.courant_l2, device_data.courant_l3]):
                return True
            
            # 3. Puissance négative sans justification
            if device_data.puissance and device_data.puissance < -100:  # Tolérance pour injection
                return True
            
            # 4. Valeurs irréalistes
            if device_data.tension and device_data.tension > 500:  # > 500V suspect
                return True
            
            if device_data.courant and device_data.courant > 1000:  # > 1000A suspect
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Erreur détection anomalie données: {e}")
            return False
    
    # =================== GESTION CACHE REDIS ===================
    
    def _get_cached_analysis(self, cache_key: str) -> Optional[Dict]:
        """Récupérer analyse depuis cache"""
        if not self.redis:
            return None
        
        try:
            full_key = f"{self.redis_prefix}analysis:{cache_key}"
            cached_data = self.redis.get(full_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur récupération cache analyse: {e}")
            return None
    
    def _cache_analysis_result(self, cache_key: str, result: Dict):
        """Mettre en cache résultat d'analyse"""
        if not self.redis:
            return
        
        try:
            full_key = f"{self.redis_prefix}analysis:{cache_key}"
            ttl = self.cache_config['analysis_result_ttl']
            
            # Préparer données pour cache (sérialiser)
            cache_data = {
                **result,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(full_key, ttl, json.dumps(cache_data))
            self.logger.debug(f"Cache analysis SET: {full_key} (TTL: {ttl}s)")
            
        except Exception as e:
            self.logger.error(f"Erreur cache analyse: {e}")
    
    # =================== MÉTHODES D'ADMINISTRATION ===================
    
    def analyser_device_batch(self, device_ids: List[str], config: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyser plusieurs appareils en batch"""
        try:
            config = {**self.default_config, **(config or {})}
            
            resultats = []
            total_alertes = 0
            devices_analysed = 0
            
            self.logger.info(f"🔍 Analyse batch: {len(device_ids)} appareils")
            
            for device_id in device_ids:
                try:
                    # Récupérer appareil et dernière donnée
                    device = Device.query.get(device_id)
                    if not device or not device.actif:
                        continue
                    
                    derniere_donnee = DeviceData.query.filter_by(
                        appareil_id=device_id
                    ).order_by(DeviceData.horodatage.desc()).first()
                    
                    if not derniere_donnee:
                        resultats.append({
                            'device_id': device_id,
                            'device_name': device.nom_appareil,
                            'statut': 'pas_de_donnees',
                            'alertes_creees': 0
                        })
                        continue
                    
                    # Analyser avec AlertService
                    analyse_result = self.analyser_et_creer_alertes(
                        derniere_donnee, device, config
                    )
                    
                    if analyse_result.get('success', True):  # Par défaut success
                        nb_alertes = analyse_result.get('nb_alertes', 0)
                        total_alertes += nb_alertes
                        devices_analysed += 1
                        
                        resultats.append({
                            'device_id': device_id,
                            'device_name': device.nom_appareil,
                            'statut': 'analysé',
                            'type_systeme': analyse_result.get('type_systeme_detecte'),
                            'alertes_creees': nb_alertes,
                            'alertes_critiques': analyse_result.get('nb_alertes_critiques', 0),
                            'from_cache': analyse_result.get('from_cache', False)
                        })
                    else:
                        resultats.append({
                            'device_id': device_id,
                            'device_name': device.nom_appareil,
                            'statut': 'erreur',
                            'erreur': analyse_result.get('error', 'Erreur inconnue')
                        })
                        
                except Exception as e:
                    self.logger.error(f"Erreur analyse device {device_id}: {e}")
                    resultats.append({
                        'device_id': device_id,
                        'statut': 'erreur',
                        'erreur': str(e)
                    })
            
            return {
                'success': True,
                'timestamp': datetime.utcnow().isoformat(),
                'devices_requested': len(device_ids),
                'devices_analysed': devices_analysed,
                'total_alertes': total_alertes,
                'cache_used': config['use_cache'],
                'resultats': resultats
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse batch: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Statistiques du cache AlertService"""
        try:
            if not self.redis:
                return {
                    'success': False,
                    'error': 'Redis non disponible',
                    'cache_enabled': False
                }
            
            # Compter les clés par type
            cache_types = ['analysis', 'thresholds', 'dedup']
            cache_stats = {}
            total_keys = 0
            
            for cache_type in cache_types:
                pattern = f"{self.redis_prefix}{cache_type}:*"
                keys = self.redis.keys(pattern)
                count = len(keys)
                cache_stats[cache_type] = count
                total_keys += count
            
            # Compter aussi type_detection
            detection_keys = self.redis.keys("type_detection:*")
            cache_stats['type_detection'] = len(detection_keys)
            total_keys += len(detection_keys)
            
            return {
                'success': True,
                'service': 'AlertService',
                'cache_enabled': True,
                'total_keys': total_keys,
                'keys_by_type': cache_stats,
                'cache_config': self.cache_config,
                'redis_prefix': self.redis_prefix,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erreur stats cache AlertService: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup_cache(self, cache_type: Optional[str] = None) -> Dict[str, Any]:
        """Nettoyer cache AlertService"""
        try:
            if not self.redis:
                return {'success': False, 'error': 'Redis non disponible'}
            
            deleted_count = 0
            
            if cache_type:
                # Nettoyage par type
                if cache_type == 'type_detection':
                    pattern = "type_detection:*"
                else:
                    pattern = f"{self.redis_prefix}{cache_type}:*"
                
                keys = self.redis.keys(pattern)
                if keys:
                    deleted_count = self.redis.delete(*keys)
                
                message = f"Cache {cache_type} nettoyé"
            else:
                # Nettoyage complet
                patterns = [
                    f"{self.redis_prefix}*",
                    "type_detection:*"
                ]
                
                for pattern in patterns:
                    keys = self.redis.keys(pattern)
                    if keys:
                        deleted_count += self.redis.delete(*keys)
                
                message = "Cache AlertService nettoyé complètement"
            
            self.logger.info(f"Cache cleanup AlertService: {deleted_count} clés supprimées")
            
            return {
                'success': True,
                'message': message,
                'deleted_keys': deleted_count,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erreur nettoyage cache AlertService: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_service_health(self) -> Dict[str, Any]:
        """Vérification santé du service"""
        try:
            health = {
                'service': 'AlertService',
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'unknown',
                'components': {}
            }
            
            # Test Redis
            if self.redis:
                try:
                    self.redis.ping()
                    health['components']['redis'] = {
                        'status': 'healthy',
                        'cache_enabled': True
                    }
                except Exception as e:
                    health['components']['redis'] = {
                        'status': 'error',
                        'error': str(e)
                    }
            else:
                health['components']['redis'] = {
                    'status': 'disabled',
                    'cache_enabled': False
                }
            
            # Test AnalyseurTriphaseService
            if self.analyseur_triphase:
                health['components']['analyseur_triphase'] = {
                    'status': 'available',
                    'service_loaded': True
                }
            else:
                health['components']['analyseur_triphase'] = {
                    'status': 'unavailable',
                    'service_loaded': False
                }
            
            # Test Database
            try:
                test_count = Alert.query.limit(1).count()
                health['components']['database'] = {
                    'status': 'healthy',
                    'connection': True
                }
            except Exception as e:
                health['components']['database'] = {
                    'status': 'error',
                    'error': str(e)
                }
            
            # Statut global
            all_healthy = all(
                comp.get('status') in ['healthy', 'available', 'disabled'] 
                for comp in health['components'].values()
            )
            
            health['status'] = 'healthy' if all_healthy else 'degraded'
            
            return {'success': True, 'health': health}
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'health': {
                    'service': 'AlertService',
                    'status': 'error',
                    'timestamp': datetime.utcnow().isoformat()
                }
            }