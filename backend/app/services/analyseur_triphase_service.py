# analyseur_triphase_service.py - Version nettoyée pour intégration AlertService
# ✅ MODIFIÉ : Suppression des fonctions d'intégration + Optimisations

from app import db
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.alert import Alert
from datetime import datetime, timedelta
import json
import logging
import hashlib

class AnalyseurTriphaseService:
    """Service d'analyse triphasé avec cache Redis optimisé - Version intégrée AlertService"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        
        # ✅ Configuration cache spécialisé triphasé
        self.cache_config = {
            'analysis_ttl': 300,          # 5 min - Analyses temps réel
            'trends_ttl': 7200,           # 2h - Tendances quotidiennes
            'quality_ttl': 1800,          # 30 min - Scores qualité
            'recommendations_ttl': 3600,  # 1h - Recommandations
            'desequilibres_ttl': 900,     # 15 min - Historique déséquilibres
            'batch_analysis_ttl': 21600,  # 6h - Analyses batch
            'alert_dedup_ttl': 1800       # 30 min - Déduplication alertes
        }
        
        # Préfixes Redis pour éviter conflits
        self.redis_prefix = "triphase:"
        
        # Seuils par défaut
        self.default_thresholds = {
            'desequilibre_tension_warning': 2.0,
            'desequilibre_tension_critical': 5.0,
            'desequilibre_courant_warning': 10.0,
            'desequilibre_courant_critical': 20.0,
            'facteur_puissance_min': 0.85,
            'tension_phase_min': 200.0,
            'tension_phase_max': 250.0,
            'quality_score_poor': 60,
            'quality_score_good': 85
        }
        
        self.logger.info(f"AnalyseurTriphaseService initialisé - Redis: {'✅' if self.redis else '❌'}")
    
    # =================== MÉTHODES DE CACHE REDIS ===================
    
    def _get_cache_key(self, key_type, *args):
        """Générer une clé de cache standardisée"""
        key_parts = [self.redis_prefix, key_type] + [str(arg) for arg in args]
        return ":".join(key_parts)
    
    def _cache_set(self, key_type, data, ttl_override=None, *key_args):
        """Mettre en cache avec TTL configuré"""
        if not self.redis:
            return False
        
        try:
            cache_key = self._get_cache_key(key_type, *key_args)
            ttl = ttl_override or self.cache_config.get(f'{key_type}_ttl', 300)
            
            cache_data = {
                'data': data,
                'cached_at': datetime.utcnow().isoformat(),
                'ttl': ttl
            }
            
            self.redis.setex(cache_key, ttl, json.dumps(cache_data))
            self.logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur cache SET {key_type}: {e}")
            return False
    
    def _cache_get(self, key_type, *key_args):
        """Récupérer depuis le cache"""
        if not self.redis:
            return None
        
        try:
            cache_key = self._get_cache_key(key_type, *key_args)
            cached_data = self.redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                cached_at = datetime.fromisoformat(data['cached_at'])
                age_seconds = (datetime.utcnow() - cached_at).total_seconds()
                
                self.logger.debug(f"Cache HIT: {cache_key} (âge: {age_seconds:.1f}s)")
                return data['data']
            
            self.logger.debug(f"Cache MISS: {cache_key}")
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur cache GET {key_type}: {e}")
            return None
    
    def _cache_delete(self, key_type, *key_args):
        """Supprimer du cache"""
        if not self.redis:
            return False
        
        try:
            cache_key = self._get_cache_key(key_type, *key_args)
            deleted = self.redis.delete(cache_key)
            
            if deleted:
                self.logger.debug(f"Cache DELETE: {cache_key}")
            
            return bool(deleted)
            
        except Exception as e:
            self.logger.error(f"Erreur cache DELETE {key_type}: {e}")
            return False
    
    def _cache_exists(self, key_type, *key_args):
        """Vérifier existence en cache"""
        if not self.redis:
            return False
        
        try:
            cache_key = self._get_cache_key(key_type, *key_args)
            return bool(self.redis.exists(cache_key))
        except:
            return False
    
    # =================== ANALYSE TEMPS RÉEL AVEC CACHE ===================
    
    def analyser_donnees_temps_reel(self, device_data, use_cache=True):
        """
        ✅ MODIFIÉ : Analyse temps réel - Compatible AlertService
        Utilisé par AlertService._analyser_triphase()
        """
        if not isinstance(device_data, DeviceData) or not device_data.is_triphase():
            return []
        
        device_id = device_data.appareil_id
        timestamp_key = int(device_data.horodatage.timestamp()) if device_data.horodatage else int(datetime.utcnow().timestamp())
        
        # ✅ Vérifier cache d'analyse
        if use_cache:
            cached_analysis = self._cache_get('analysis', device_id, timestamp_key)
            if cached_analysis:
                self.logger.debug(f"Analyse depuis cache pour device {device_id}")
                return self._reconstruct_alerts_from_cache(cached_analysis)
        
        try:
            # Récupérer l'appareil et ses seuils
            appareil = Device.query.get(device_id)
            if not appareil or not appareil.is_triphase():
                return []
            
            seuils = appareil.get_seuils_actifs()
            alertes_creees = []
            
            self.logger.info(f"🔍 Analyse temps réel triphasé - Device: {device_id}")
            
            # 1. Analyser déséquilibres avec cache
            alertes_desequilibres = self._analyser_desequilibres_cached(device_data, appareil, seuils)
            alertes_creees.extend(alertes_desequilibres)
            
            # 2. Analyser pertes de phase
            alertes_phases = self._analyser_pertes_phase_cached(device_data, appareil)
            alertes_creees.extend(alertes_phases)
            
            # 3. Analyser seuils par phase
            alertes_seuils = self._analyser_seuils_phases_cached(device_data, appareil, seuils)
            alertes_creees.extend(alertes_seuils)
            
            # 4. Analyser facteur de puissance
            alertes_fp = self._analyser_facteur_puissance_cached(device_data, appareil, seuils)
            alertes_creees.extend(alertes_fp)
            
            # 5. Analyser tensions composées
            alertes_tensions = self._analyser_tensions_composees_cached(device_data, appareil, seuils)
            alertes_creees.extend(alertes_tensions)
            
            # ✅ Mettre en cache le résultat d'analyse
            if use_cache:
                analysis_result = {
                    'device_id': device_id,
                    'timestamp': device_data.horodatage.isoformat() if device_data.horodatage else datetime.utcnow().isoformat(),
                    'alertes_count': len(alertes_creees),
                    'alertes_data': [self._serialize_alert_for_cache(a) for a in alertes_creees],
                    'anomalies_detectees': self._extract_anomalies_summary(alertes_creees),
                    'quality_impact': self._calculate_quality_impact(alertes_creees)
                }
                
                self._cache_set('analysis', analysis_result, None, device_id, timestamp_key)
            
            # ✅ Mettre à jour tendances en cache
            self._update_trends_cache(device_id, device_data, alertes_creees)
            
            self.logger.info(f"✅ Analyse terminée - {len(alertes_creees)} alertes créées")
            return alertes_creees
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse temps réel device {device_id}: {e}")
            return []
    
    # ✅ NOUVEAU : Méthode pour analyse sans création d'alertes (pure analyse)
    def analyser_donnees_sans_creation_alertes(self, device_data, use_cache=True):
        """
        Analyse pure sans création d'alertes en DB
        Retourne seulement les données d'analyse pour AlertService
        """
        if not isinstance(device_data, DeviceData) or not device_data.is_triphase():
            return {
                'success': False,
                'error': 'Données non triphasées',
                'anomalies': []
            }
        
        try:
            device_id = device_data.appareil_id
            appareil = Device.query.get(device_id)
            
            if not appareil or not appareil.is_triphase():
                return {
                    'success': False,
                    'error': 'Appareil non triphasé',
                    'anomalies': []
                }
            
            seuils = appareil.get_seuils_actifs()
            anomalies_detectees = []
            
            # Analyser sans créer d'alertes - juste détecter anomalies
            
            # 1. Vérifier déséquilibres
            desequilibre_tension = device_data.calculer_desequilibre_tension()
            desequilibre_courant = device_data.calculer_desequilibre_courant()
            
            if desequilibre_tension and desequilibre_tension > self.default_thresholds['desequilibre_tension_warning']:
                anomalies_detectees.append({
                    'type': 'desequilibre_tension',
                    'valeur': desequilibre_tension,
                    'seuil': self.default_thresholds['desequilibre_tension_warning'],
                    'gravite': 'critique' if desequilibre_tension > self.default_thresholds['desequilibre_tension_critical'] else 'warning'
                })
            
            if desequilibre_courant and desequilibre_courant > self.default_thresholds['desequilibre_courant_warning']:
                anomalies_detectees.append({
                    'type': 'desequilibre_courant',
                    'valeur': desequilibre_courant,
                    'seuil': self.default_thresholds['desequilibre_courant_warning'],
                    'gravite': 'critique' if desequilibre_courant > self.default_thresholds['desequilibre_courant_critical'] else 'warning'
                })
            
            # 2. Vérifier pertes de phase
            phases_perdues = []
            for phase, tension in [('L1', device_data.tension_l1), ('L2', device_data.tension_l2), ('L3', device_data.tension_l3)]:
                if tension is None or tension < 50:
                    phases_perdues.append(phase)
            
            if phases_perdues:
                anomalies_detectees.append({
                    'type': 'perte_phase',
                    'phases_perdues': phases_perdues,
                    'gravite': 'critique'
                })
            
            # 3. Vérifier facteur de puissance
            facteur_moyen = device_data.get_facteur_puissance_moyen()
            if facteur_moyen and facteur_moyen < self.default_thresholds['facteur_puissance_min']:
                anomalies_detectees.append({
                    'type': 'facteur_puissance_faible',
                    'valeur': facteur_moyen,
                    'seuil': self.default_thresholds['facteur_puissance_min'],
                    'gravite': 'warning'
                })
            
            return {
                'success': True,
                'device_id': device_id,
                'anomalies': anomalies_detectees,
                'nb_anomalies': len(anomalies_detectees),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse sans création: {e}")
            return {
                'success': False,
                'error': str(e),
                'anomalies': []
            }
    
    def _analyser_desequilibres_cached(self, device_data, appareil, seuils):
        """Analyser déséquilibres avec cache et déduplication"""
        alertes = []
        device_id = appareil.id
        
        # Calculer déséquilibres
        desequilibre_tension = device_data.calculer_desequilibre_tension()
        desequilibre_courant = device_data.calculer_desequilibre_courant()
        
        # Déséquilibre tension
        if desequilibre_tension is not None:
            seuil_warning = seuils.get('desequilibre_tension', self.default_thresholds['desequilibre_tension_warning'])
            seuil_critical = self.default_thresholds['desequilibre_tension_critical']
            
            if desequilibre_tension > seuil_critical:
                gravite = 'critique'
            elif desequilibre_tension > seuil_warning:
                gravite = 'warning'
            else:
                gravite = None
            
            if gravite and not self._alert_recently_created('desequilibre_tension', device_id, minutes=30):
                tensions_phases = {
                    'L1': device_data.tension_l1,
                    'L2': device_data.tension_l2,
                    'L3': device_data.tension_l3
                }
                
                alerte = Alert.create_alerte_desequilibre_tension(
                    client_id=appareil.client_id,
                    appareil_id=appareil.id,
                    pourcentage_desequilibre=desequilibre_tension,
                    seuil_max=seuil_warning,
                    tensions_phases=tensions_phases
                )
                
                if alerte:
                    alertes.append(alerte)
                    # ✅ Cache déduplication
                    self._cache_alert_created('desequilibre_tension', device_id)
                    
                    # ✅ Cache historique déséquilibres
                    self._update_desequilibres_history(device_id, 'tension', desequilibre_tension)
        
        # Déséquilibre courant (même logique)
        if desequilibre_courant is not None:
            seuil_warning = seuils.get('desequilibre_courant', self.default_thresholds['desequilibre_courant_warning'])
            seuil_critical = self.default_thresholds['desequilibre_courant_critical']
            
            if desequilibre_courant > seuil_critical:
                gravite = 'critique'
            elif desequilibre_courant > seuil_warning:
                gravite = 'warning'
            else:
                gravite = None
            
            if gravite and not self._alert_recently_created('desequilibre_courant', device_id, minutes=30):
                courants_phases = {
                    'L1': device_data.courant_l1,
                    'L2': device_data.courant_l2,
                    'L3': device_data.courant_l3
                }
                
                alerte = Alert.create_alerte_desequilibre_courant(
                    client_id=appareil.client_id,
                    appareil_id=appareil.id,
                    pourcentage_desequilibre=desequilibre_courant,
                    seuil_max=seuil_warning,
                    courants_phases=courants_phases
                )
                
                if alerte:
                    alertes.append(alerte)
                    self._cache_alert_created('desequilibre_courant', device_id)
                    self._update_desequilibres_history(device_id, 'courant', desequilibre_courant)
        
        return alertes
    
    def _analyser_pertes_phase_cached(self, device_data, appareil):
        """Analyser pertes de phase avec cache"""
        alertes = []
        device_id = appareil.id
        
        tensions = {
            'L1': device_data.tension_l1,
            'L2': device_data.tension_l2,
            'L3': device_data.tension_l3
        }
        
        phases_perdues = []
        for phase, tension in tensions.items():
            if tension is None or tension < 50:  # Seuil perte de phase
                phases_perdues.append(phase)
        
        if phases_perdues and not self._alert_recently_created('perte_phase', device_id, minutes=15):
            # Créer une alerte pour toutes les phases perdues
            alerte = Alert.create_alerte_perte_phase(
                client_id=appareil.client_id,
                appareil_id=appareil.id,
                phase_perdue=phases_perdues[0],  # Phase principale
                tensions_phases=tensions
            )
            
            if alerte:
                # Enrichir avec toutes les phases perdues
                alerte.valeurs_phases = tensions
                alerte.message = f"Perte de phase(s) détectée: {', '.join(phases_perdues)}"
                db.session.commit()
                
                alertes.append(alerte)
                self._cache_alert_created('perte_phase', device_id)
                
                # ✅ Cache événement critique
                self._cache_critical_event(device_id, 'perte_phase', {
                    'phases_perdues': phases_perdues,
                    'tensions': tensions,
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        return alertes
    
    def _analyser_seuils_phases_cached(self, device_data, appareil, seuils):
        """Analyser seuils par phase avec cache et optimisation"""
        alertes = []
        device_id = appareil.id
        
        # Données par phase
        phases_data = [
            ('L1', device_data.tension_l1, device_data.courant_l1),
            ('L2', device_data.tension_l2, device_data.courant_l2),
            ('L3', device_data.tension_l3, device_data.courant_l3)
        ]
        
        for phase, tension, courant in phases_data:
            # Vérifier tension phase
            if tension is not None:
                seuil_min = seuils.get(f'seuil_tension_{phase.lower()}_min') or self.default_thresholds['tension_phase_min']
                seuil_max = seuils.get(f'seuil_tension_{phase.lower()}_max') or self.default_thresholds['tension_phase_max']
                
                if tension < seuil_min and not self._alert_recently_created(f'tension_{phase}_low', device_id, minutes=20):
                    alerte = Alert.create_alerte_triphase(
                        client_id=appareil.client_id,
                        appareil_id=appareil.id,
                        type_alerte='seuil_depasse',
                        gravite='warning',
                        titre=f'Tension {phase} trop basse',
                        message=f'Tension phase {phase}: {tension}V < {seuil_min}V',
                        phase_concernee=phase,
                        valeur_principale=tension,
                        seuil_principal=seuil_min,
                        unite='V'
                    )
                    if alerte:
                        alertes.append(alerte)
                        self._cache_alert_created(f'tension_{phase}_low', device_id)
                
                elif tension > seuil_max and not self._alert_recently_created(f'tension_{phase}_high', device_id, minutes=20):
                    alerte = Alert.create_alerte_triphase(
                        client_id=appareil.client_id,
                        appareil_id=appareil.id,
                        type_alerte='seuil_depasse',
                        gravite='critique',
                        titre=f'Tension {phase} trop élevée',
                        message=f'Tension phase {phase}: {tension}V > {seuil_max}V',
                        phase_concernee=phase,
                        valeur_principale=tension,
                        seuil_principal=seuil_max,
                        unite='V'
                    )
                    if alerte:
                        alertes.append(alerte)
                        self._cache_alert_created(f'tension_{phase}_high', device_id)
            
            # Vérifier courant phase
            if courant is not None:
                seuil_courant_max = seuils.get(f'seuil_courant_{phase.lower()}_max')
                
                if seuil_courant_max and courant > seuil_courant_max and not self._alert_recently_created(f'courant_{phase}_high', device_id, minutes=20):
                    alerte = Alert.create_alerte_triphase(
                        client_id=appareil.client_id,
                        appareil_id=appareil.id,
                        type_alerte='seuil_depasse',
                        gravite='critique',
                        titre=f'Courant {phase} trop élevé',
                        message=f'Courant phase {phase}: {courant}A > {seuil_courant_max}A',
                        phase_concernee=phase,
                        valeur_principale=courant,
                        seuil_principal=seuil_courant_max,
                        unite='A'
                    )
                    if alerte:
                        alertes.append(alerte)
                        self._cache_alert_created(f'courant_{phase}_high', device_id)
        
        return alertes
    
    def _analyser_facteur_puissance_cached(self, device_data, appareil, seuils):
        """Analyser facteur de puissance avec cache"""
        alertes = []
        device_id = appareil.id
        
        facteur_moyen = device_data.get_facteur_puissance_moyen()
        seuil_min = seuils.get('seuil_facteur_puissance_min', self.default_thresholds['facteur_puissance_min'])
        
        if facteur_moyen and facteur_moyen < seuil_min and not self._alert_recently_created('facteur_puissance_faible', device_id, minutes=60):
            alerte = Alert.create_alerte_facteur_puissance(
                client_id=appareil.client_id,
                appareil_id=appareil.id,
                facteur_puissance=facteur_moyen,
                seuil_min=seuil_min
            )
            
            if alerte:
                alertes.append(alerte)
                self._cache_alert_created('facteur_puissance_faible', device_id)
                
                # ✅ Cache pour recommandations
                self._cache_power_factor_trend(device_id, facteur_moyen)
        
        return alertes
    
    def _analyser_tensions_composees_cached(self, device_data, appareil, seuils):
        """Analyser tensions composées avec cache"""
        alertes = []
        device_id = appareil.id
        
        tensions_composees = [
            ('L1-L2', device_data.tension_l1_l2),
            ('L2-L3', device_data.tension_l2_l3),
            ('L3-L1', device_data.tension_l3_l1)
        ]
        
        seuil_surtension = 450  # Exemple pour 400V nominal
        
        for nom, tension in tensions_composees:
            if tension and tension > seuil_surtension and not self._alert_recently_created(f'surtension_{nom}', device_id, minutes=15):
                alerte = Alert.create_alerte_triphase(
                    client_id=appareil.client_id,
                    appareil_id=appareil.id,
                    type_alerte='surtension_composee',
                    gravite='critique',
                    titre=f'Surtension composée {nom}',
                    message=f'Tension composée {nom}: {tension}V > {seuil_surtension}V',
                    valeur_principale=tension,
                    seuil_principal=seuil_surtension,
                    unite='V'
                )
                
                if alerte:
                    alertes.append(alerte)
                    self._cache_alert_created(f'surtension_{nom}', device_id)
        
        return alertes
    
    # =================== MÉTHODES DE CACHE SPÉCIALISÉES ===================
    
    def _alert_recently_created(self, alert_type, device_id, minutes=30):
        """Vérifier si une alerte similaire a été créée récemment (déduplication)"""
        if not self.redis:
            # Fallback DB si pas de Redis
            since = datetime.utcnow() - timedelta(minutes=minutes)
            return Alert.query.filter(
                Alert.appareil_id == device_id,
                Alert.type_alerte == alert_type,
                Alert.date_creation >= since,
                Alert.statut.in_(['nouvelle', 'vue'])
            ).first() is not None
        
        dedup_key = f"alert_dedup_{alert_type}_{device_id}"
        return self._cache_exists('alert_dedup', dedup_key)
    
    def _cache_alert_created(self, alert_type, device_id):
        """Marquer qu'une alerte a été créée (pour déduplication)"""
        dedup_key = f"alert_dedup_{alert_type}_{device_id}"
        ttl = self.cache_config.get('alert_dedup_ttl', 1800)
        
        self._cache_set('alert_dedup', {
            'alert_type': alert_type,
            'device_id': device_id,
            'created_at': datetime.utcnow().isoformat()
        }, ttl, dedup_key)
    
    def _update_desequilibres_history(self, device_id, type_desequilibre, valeur):
        """Mettre à jour l'historique des déséquilibres en cache"""
        try:
            history_key = f"{device_id}_{type_desequilibre}"
            existing_history = self._cache_get('desequilibres', history_key) or []
            
            # Ajouter nouvelle valeur
            new_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'valeur': valeur,
                'type': type_desequilibre
            }
            
            existing_history.append(new_entry)
            
            # Garder seulement les 100 dernières entrées
            if len(existing_history) > 100:
                existing_history = existing_history[-100:]
            
            self._cache_set('desequilibres', existing_history, None, history_key)
            
        except Exception as e:
            self.logger.error(f"Erreur mise à jour historique déséquilibres: {e}")
    
    def _cache_critical_event(self, device_id, event_type, event_data):
        """Cacher un événement critique pour monitoring"""
        event_key = f"{device_id}_{event_type}_{int(datetime.utcnow().timestamp())}"
        
        critical_event = {
            'device_id': device_id,
            'event_type': event_type,
            'event_data': event_data,
            'severity': 'critical',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # TTL plus long pour événements critiques
        self._cache_set('critical_events', critical_event, 3600, event_key)
    
    def _cache_power_factor_trend(self, device_id, facteur_puissance):
        """Cacher tendance facteur de puissance pour recommandations"""
        trend_key = f"{device_id}_power_factor"
        existing_trend = self._cache_get('power_trends', trend_key) or []
        
        new_point = {
            'timestamp': datetime.utcnow().isoformat(),
            'facteur_puissance': facteur_puissance
        }
        
        existing_trend.append(new_point)
        
        # Garder 50 derniers points
        if len(existing_trend) > 50:
            existing_trend = existing_trend[-50:]
        
        self._cache_set('power_trends', existing_trend, None, trend_key)
    
    def _update_trends_cache(self, device_id, device_data, alertes_creees):
        """Mettre à jour le cache des tendances"""
        try:
            # Trends key avec window temporelle (heure)
            hour_key = datetime.utcnow().strftime('%Y%m%d_%H')
            trends_key = f"{device_id}_{hour_key}"
            
            trend_data = {
                'device_id': device_id,
                'hour_window': hour_key,
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': {
                    'tension_moyenne': device_data.get_tension_moyenne(),
                    'courant_total': device_data.get_courant_total(),
                    'puissance_totale': device_data.get_puissance_totale_calculee(),
                    'facteur_puissance': device_data.get_facteur_puissance_moyen(),
                    'desequilibre_tension': device_data.calculer_desequilibre_tension(),
                    'desequilibre_courant': device_data.calculer_desequilibre_courant(),
                    'frequence': device_data.frequence
                },
                'alertes_count': len(alertes_creees),
                'alertes_types': [a.type_alerte for a in alertes_creees if hasattr(a, 'type_alerte')]
            }
            
            self._cache_set('trends', trend_data, None, trends_key)
            
        except Exception as e:
            self.logger.error(f"Erreur mise à jour trends cache: {e}")
    
    # =================== MÉTHODES UTILITAIRES CACHE ===================
    
    def _serialize_alert_for_cache(self, alert):
        """Sérialiser une alerte pour le cache"""
        if hasattr(alert, 'to_dict'):
            return alert.to_dict()
        else:
            return {
                'id': getattr(alert, 'id', None),
                'type_alerte': getattr(alert, 'type_alerte', None),
                'gravite': getattr(alert, 'gravite', None),
                'message': getattr(alert, 'message', None)
            }
    
    def _reconstruct_alerts_from_cache(self, cached_analysis):
        """Reconstruire les alertes depuis le cache (pour éviter re-création DB)"""
        # Retourner les données d'alertes sans créer en DB
        # Utilisé quand on veut juste les résultats d'analyse
        return cached_analysis.get('alertes_data', [])
    
    def _extract_anomalies_summary(self, alertes):
        """Extraire un résumé des anomalies détectées"""
        anomalies = {
            'desequilibres': 0,
            'pertes_phase': 0,
            'seuils_depasses': 0,
            'facteur_puissance': 0,
            'surtensions': 0
        }
        
        for alerte in alertes:
            if hasattr(alerte, 'type_alerte'):
                alerte_type = alerte.type_alerte
                if 'desequilibre' in alerte_type:
                    anomalies['desequilibres'] += 1
                elif 'perte_phase' in alerte_type:
                    anomalies['pertes_phase'] += 1
                elif 'seuil_depasse' in alerte_type:
                    anomalies['seuils_depasses'] += 1
                elif 'facteur_puissance' in alerte_type:
                    anomalies['facteur_puissance'] += 1
                elif 'surtension' in alerte_type:
                    anomalies['surtensions'] += 1
        
        return anomalies
    
    def _calculate_quality_impact(self, alertes):
        """Calculer l'impact sur la qualité du réseau"""
        if not alertes:
            return 0
        
        impact_weights = {
            'critique': 10,
            'warning': 5,
            'info': 1
        }
        
        total_impact = 0
        for alerte in alertes:
            gravite = getattr(alerte, 'gravite', 'info')
            total_impact += impact_weights.get(gravite, 1)
        
        return min(total_impact, 100)  # Cap à 100
    
    # =================== ANALYSE TENDANCES AVEC CACHE ===================
    
    def analyser_tendances_appareil_cached(self, appareil_id, hours_back=24, use_cache=True):
        """Analyser tendances avec cache intelligent"""
        try:
            # ✅ Vérifier cache tendances d'abord
            cache_key = f"{appareil_id}_{hours_back}h"
            
            if use_cache:
                cached_trends = self._cache_get('trends', cache_key)
                if cached_trends:
                    cached_at = datetime.fromisoformat(cached_trends['cached_at'])
                    age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60
                    
                    if age_minutes < 30:  # Cache valide 30 minutes
                        self.logger.debug(f"Tendances depuis cache pour appareil {appareil_id}")
                        return {
                            "success": True,
                            "from_cache": True,
                            "cache_age_minutes": age_minutes,
                            **cached_trends
                        }
            
            # Calcul depuis DB
            depuis = datetime.utcnow() - timedelta(hours=hours_back)
            
            donnees = DeviceData.query.filter(
                DeviceData.appareil_id == appareil_id,
                DeviceData.type_systeme == 'triphase',
                DeviceData.horodatage >= depuis
            ).order_by(DeviceData.horodatage.asc()).all()
            
            if len(donnees) < 10:
                return {
                    "success": False,
                    "error": "Pas assez de données pour analyse tendances",
                    "data_points": len(donnees)
                }
            
            # Calculs tendances
            analyse = {
                'appareil_id': appareil_id,
                'periode': f'{hours_back}h',
                'nb_echantillons': len(donnees),
                'cached_at': datetime.utcnow().isoformat(),
                'tensions': self._analyser_tendance_tensions_cached(donnees),
                'courants': self._analyser_tendance_courants_cached(donnees),
                'desequilibres': self._analyser_tendance_desequilibres_cached(donnees),
                'facteur_puissance': self._analyser_tendance_facteur_puissance_cached(donnees),
                'qualite_reseau': self._evaluer_qualite_reseau_cached(donnees),
                'recommandations': []
            }
            
            # Générer recommandations
            analyse['recommandations'] = self._generer_recommandations_cached(analyse)
            
            # ✅ Mettre en cache
            if use_cache:
                self._cache_set('trends', analyse, None, cache_key)
            
            self.logger.info(f"✅ Analyse tendances calculée pour {appareil_id}: {len(donnees)} échantillons")
            
            return {
                "success": True,
                "from_cache": False,
                **analyse
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse tendances {appareil_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyser_tendance_tensions_cached(self, donnees):
        """Analyser tendances tension avec cache de calculs"""
        tensions_l1 = [d.tension_l1 for d in donnees if d.tension_l1]
        tensions_l2 = [d.tension_l2 for d in donnees if d.tension_l2]
        tensions_l3 = [d.tension_l3 for d in donnees if d.tension_l3]
        
        def calculate_stats(values):
            if not values:
                return {'moyenne': 0, 'min': 0, 'max': 0, 'variation': 0, 'stabilite': 'inconnue'}
            
            moyenne = sum(values) / len(values)
            min_val = min(values)
            max_val = max(values)
            variation = max_val - min_val
            
            # Évaluer stabilité
            if variation < 5:
                stabilite = 'excellente'
            elif variation < 10:
                stabilite = 'bonne'
            elif variation < 20:
                stabilite = 'moyenne'
            else:
                stabilite = 'mauvaise'
            
            return {
                'moyenne': round(moyenne, 2),
                'min': min_val,
                'max': max_val,
                'variation': round(variation, 2),
                'stabilite': stabilite
            }
        
        return {
            'L1': calculate_stats(tensions_l1),
            'L2': calculate_stats(tensions_l2),
            'L3': calculate_stats(tensions_l3),
            'ecart_entre_phases': self._calculer_ecart_phases(tensions_l1, tensions_l2, tensions_l3)
        }
    
    def _analyser_tendance_courants_cached(self, donnees):
        """Analyser tendances courant avec cache"""
        courants_l1 = [d.courant_l1 for d in donnees if d.courant_l1]
        courants_l2 = [d.courant_l2 for d in donnees if d.courant_l2]
        courants_l3 = [d.courant_l3 for d in donnees if d.courant_l3]
        
        def calculate_current_trend(values):
            if len(values) < 3:
                return {'moyenne': 0, 'max': 0, 'tendance': 'stable'}
            
            moyenne = sum(values) / len(values)
            max_val = max(values)
            
            # Calculer tendance simple (compare première vs dernière moitié)
            mid = len(values) // 2
            first_half = sum(values[:mid]) / mid if mid > 0 else 0
            second_half = sum(values[mid:]) / (len(values) - mid) if len(values) - mid > 0 else 0
            
            if second_half > first_half * 1.1:
                tendance = 'croissante'
            elif second_half < first_half * 0.9:
                tendance = 'decroissante'
            else:
                tendance = 'stable'
            
            return {
                'moyenne': round(moyenne, 2),
                'max': round(max_val, 2),
                'tendance': tendance,
                'evolution_pct': round(((second_half - first_half) / first_half * 100) if first_half > 0 else 0, 1)
            }
        
        return {
            'L1': calculate_current_trend(courants_l1),
            'L2': calculate_current_trend(courants_l2),
            'L3': calculate_current_trend(courants_l3),
            'equilibre_global': self._evaluer_equilibre_courants(courants_l1, courants_l2, courants_l3)
        }
    
    def _analyser_tendance_desequilibres_cached(self, donnees):
        """Analyser tendances déséquilibres avec cache"""
        desequilibres_tension = []
        desequilibres_courant = []
        
        for donnee in donnees:
            deseq_tension = donnee.calculer_desequilibre_tension()
            deseq_courant = donnee.calculer_desequilibre_courant()
            
            if deseq_tension is not None:
                desequilibres_tension.append(deseq_tension)
            if deseq_courant is not None:
                desequilibres_courant.append(deseq_courant)
        
        def analyze_desequilibres(values, seuil_warning, seuil_critical):
            if not values:
                return {'moyenne': 0, 'max': 0, 'nb_depassements': 0, 'criticite': 'ok'}
            
            moyenne = sum(values) / len(values)
            max_val = max(values)
            nb_warning = len([v for v in values if v > seuil_warning])
            nb_critical = len([v for v in values if v > seuil_critical])
            
            if nb_critical > 0:
                criticite = 'critique'
            elif nb_warning > len(values) * 0.3:  # Plus de 30% au-dessus warning
                criticite = 'attention'
            else:
                criticite = 'ok'
            
            return {
                'moyenne': round(moyenne, 2),
                'max': round(max_val, 2),
                'nb_depassements_warning': nb_warning,
                'nb_depassements_critical': nb_critical,
                'criticite': criticite
            }
        
        return {
            'tension': analyze_desequilibres(desequilibres_tension, 2.0, 5.0),
            'courant': analyze_desequilibres(desequilibres_courant, 10.0, 20.0),
            'evolution': self._evaluer_evolution_desequilibres(desequilibres_tension, desequilibres_courant)
        }
    
    def _analyser_tendance_facteur_puissance_cached(self, donnees):
        """Analyser tendances facteur de puissance avec cache"""
        facteurs = [d.get_facteur_puissance_moyen() for d in donnees if d.get_facteur_puissance_moyen()]
        
        if not facteurs:
            return {'moyenne': 0, 'min': 0, 'stable': False, 'efficacite': 'inconnue'}
        
        moyenne = sum(facteurs) / len(facteurs)
        min_val = min(facteurs)
        max_val = max(facteurs)
        variation = max_val - min_val
        
        # Évaluer efficacité énergétique
        if moyenne >= 0.95:
            efficacite = 'excellente'
        elif moyenne >= 0.85:
            efficacite = 'bonne'
        elif moyenne >= 0.75:
            efficacite = 'moyenne'
        else:
            efficacite = 'mauvaise'
        
        return {
            'moyenne': round(moyenne, 3),
            'min': round(min_val, 3),
            'max': round(max_val, 3),
            'variation': round(variation, 3),
            'stable': variation < 0.05,
            'efficacite': efficacite,
            'nb_echantillons': len(facteurs)
        }
    
    def _evaluer_qualite_reseau_cached(self, donnees):
        """Évaluer qualité globale du réseau avec cache"""
        if not donnees:
            return {'score': 0, 'niveau': 'inconnu'}
        
        # Calculer score composé (0-100)
        score = 100
        
        # Pénalités pour variations de tension
        for donnee in donnees[-10:]:  # 10 derniers points
            deseq_tension = donnee.calculer_desequilibre_tension()
            if deseq_tension:
                if deseq_tension > 5:
                    score -= 15
                elif deseq_tension > 2:
                    score -= 5
            
            deseq_courant = donnee.calculer_desequilibre_courant()
            if deseq_courant:
                if deseq_courant > 20:
                    score -= 10
                elif deseq_courant > 10:
                    score -= 3
            
            facteur_puissance = donnee.get_facteur_puissance_moyen()
            if facteur_puissance and facteur_puissance < 0.85:
                score -= 2
        
        score = max(0, score)
        
        # Déterminer niveau
        if score >= 90:
            niveau = 'excellent'
        elif score >= 75:
            niveau = 'bon'
        elif score >= 60:
            niveau = 'moyen'
        else:
            niveau = 'mauvais'
        
        return {
            'score': score,
            'niveau': niveau,
            'tendance': self._calculer_tendance_qualite(donnees)
        }
    
    def _generer_recommandations_cached(self, analyse):
        """Générer recommandations basées sur l'analyse avec cache"""
        recommandations = []
        
        # Recommandations tensions
        tensions = analyse.get('tensions', {})
        for phase in ['L1', 'L2', 'L3']:
            phase_data = tensions.get(phase, {})
            if phase_data.get('stabilite') == 'mauvaise':
                recommandations.append({
                    'type': 'maintenance',
                    'priorite': 'haute',
                    'phase': phase,
                    'message': f'Tension {phase} instable (variation: {phase_data.get("variation", 0)}V). Vérifier connexions.',
                    'action': 'verification_connexions'
                })
        
        # Recommandations déséquilibres
        desequilibres = analyse.get('desequilibres', {})
        if desequilibres.get('tension', {}).get('criticite') == 'critique':
            recommandations.append({
                'type': 'maintenance',
                'priorite': 'urgente',
                'message': 'Déséquilibres de tension critiques détectés. Intervention immédiate requise.',
                'action': 'audit_installation'
            })
        
        if desequilibres.get('courant', {}).get('criticite') == 'critique':
            recommandations.append({
                'type': 'optimisation',
                'priorite': 'haute',
                'message': 'Déséquilibres de courant élevés. Rééquilibrer les charges entre phases.',
                'action': 'reequilibrage_charges'
            })
        
        # Recommandations facteur de puissance
        fp = analyse.get('facteur_puissance', {})
        if fp.get('efficacite') in ['moyenne', 'mauvaise']:
            recommandations.append({
                'type': 'optimisation',
                'priorite': 'moyenne',
                'message': f'Facteur de puissance {fp.get("efficacite")} ({fp.get("moyenne", 0):.3f}). Envisager compensation réactive.',
                'action': 'compensation_reactive',
                'economie_potentielle': self._calculer_economie_facteur_puissance(fp.get('moyenne', 0))
            })
        
        # Recommandations qualité réseau
        qualite = analyse.get('qualite_reseau', {})
        if qualite.get('niveau') == 'mauvais':
            recommandations.append({
                'type': 'audit',
                'priorite': 'haute',
                'message': f'Qualité réseau dégradée (score: {qualite.get("score", 0)}). Audit complet recommandé.',
                'action': 'audit_complet'
            })
        
        return recommandations
    
    # =================== MÉTHODES UTILITAIRES PRIVÉES ===================
    
    def _calculer_ecart_phases(self, tensions_l1, tensions_l2, tensions_l3):
        """Calculer écart maximum entre phases"""
        if not all([tensions_l1, tensions_l2, tensions_l3]):
            return {'max_ecart': 0, 'phases_concernees': []}
        
        try:
            # Moyennes par phase
            moy_l1 = sum(tensions_l1) / len(tensions_l1)
            moy_l2 = sum(tensions_l2) / len(tensions_l2)
            moy_l3 = sum(tensions_l3) / len(tensions_l3)
            
            moyennes = {'L1': moy_l1, 'L2': moy_l2, 'L3': moy_l3}
            
            # Trouver écart max
            min_phase = min(moyennes, key=moyennes.get)
            max_phase = max(moyennes, key=moyennes.get)
            max_ecart = moyennes[max_phase] - moyennes[min_phase]
            
            return {
                'max_ecart': round(max_ecart, 2),
                'phases_concernees': [min_phase, max_phase],
                'moyennes': {k: round(v, 2) for k, v in moyennes.items()}
            }
        except:
            return {'max_ecart': 0, 'phases_concernees': []}
    
    def _evaluer_equilibre_courants(self, courants_l1, courants_l2, courants_l3):
        """Évaluer équilibre global des courants"""
        if not all([courants_l1, courants_l2, courants_l3]):
            return {'equilibre': 'inconnu', 'ecart_max_pct': 0}
        
        try:
            moy_l1 = sum(courants_l1) / len(courants_l1)
            moy_l2 = sum(courants_l2) / len(courants_l2)
            moy_l3 = sum(courants_l3) / len(courants_l3)
            
            moy_globale = (moy_l1 + moy_l2 + moy_l3) / 3
            
            if moy_globale == 0:
                return {'equilibre': 'inconnu', 'ecart_max_pct': 0}
            
            # Écart max en %
            ecarts = [abs(moy - moy_globale) / moy_globale * 100 for moy in [moy_l1, moy_l2, moy_l3]]
            ecart_max_pct = max(ecarts)
            
            # Évaluation
            if ecart_max_pct < 5:
                equilibre = 'excellent'
            elif ecart_max_pct < 10:
                equilibre = 'bon'
            elif ecart_max_pct < 20:
                equilibre = 'moyen'
            else:
                equilibre = 'mauvais'
            
            return {
                'equilibre': equilibre,
                'ecart_max_pct': round(ecart_max_pct, 1),
                'moyennes': {
                    'L1': round(moy_l1, 2),
                    'L2': round(moy_l2, 2),
                    'L3': round(moy_l3, 2)
                }
            }
        except:
            return {'equilibre': 'inconnu', 'ecart_max_pct': 0}
    
    def _evaluer_evolution_desequilibres(self, desequilibres_tension, desequilibres_courant):
        """Évaluer évolution des déséquilibres"""
        evolution = {'tension': 'stable', 'courant': 'stable'}
        
        if len(desequilibres_tension) >= 4:
            mid = len(desequilibres_tension) // 2
            first_half = sum(desequilibres_tension[:mid]) / mid
            second_half = sum(desequilibres_tension[mid:]) / (len(desequilibres_tension) - mid)
            
            if second_half > first_half * 1.2:
                evolution['tension'] = 'deterioration'
            elif second_half < first_half * 0.8:
                evolution['tension'] = 'amelioration'
        
        if len(desequilibres_courant) >= 4:
            mid = len(desequilibres_courant) // 2
            first_half = sum(desequilibres_courant[:mid]) / mid
            second_half = sum(desequilibres_courant[mid:]) / (len(desequilibres_courant) - mid)
            
            if second_half > first_half * 1.2:
                evolution['courant'] = 'deterioration'
            elif second_half < first_half * 0.8:
                evolution['courant'] = 'amelioration'
        
        return evolution
    
    def _calculer_tendance_qualite(self, donnees):
        """Calculer tendance de qualité réseau"""
        if len(donnees) < 6:
            return 'insuffisant_donnees'
        
        # Diviser en 3 périodes
        third = len(donnees) // 3
        
        periodes = [
            donnees[:third],
            donnees[third:2*third],
            donnees[2*third:]
        ]
        
        scores = []
        for periode in periodes:
            score = 100
            for donnee in periode:
                deseq_tension = donnee.calculer_desequilibre_tension()
                if deseq_tension and deseq_tension > 2:
                    score -= 10
                
                deseq_courant = donnee.calculer_desequilibre_courant()
                if deseq_courant and deseq_courant > 10:
                    score -= 5
            
            scores.append(max(0, score))
        
        # Analyser tendance
        if scores[2] > scores[0] * 1.1:
            return 'amelioration'
        elif scores[2] < scores[0] * 0.9:
            return 'deterioration'
        else:
            return 'stable'
    
    def _calculer_economie_facteur_puissance(self, facteur_actuel):
        """Calculer économie potentielle avec amélioration facteur de puissance"""
        if facteur_actuel >= 0.95:
            return "Déjà optimal"
        
        # Calcul simplifié d'économie (en %)
        economie_pct = (0.95 - facteur_actuel) * 100 * 0.5  # Approximation
        return f"~{economie_pct:.1f}% sur la facture électrique"
    
    # =================== ADMINISTRATION DU CACHE ===================
    
    def get_cache_statistics(self):
        """Statistiques du cache AnalyseurTriphase"""
        try:
            if not self.redis:
                return {
                    "success": False,
                    "error": "Redis non disponible",
                    "cache_enabled": False
                }
            
            # Compter les clés par type
            cache_types = [
                'analysis', 'trends', 'quality', 'desequilibres', 
                'batch_analysis', 'alert_dedup', 'critical_events',
                'power_trends'
            ]
            
            cache_stats = {}
            total_keys = 0
            
            for cache_type in cache_types:
                pattern = f"{self.redis_prefix}{cache_type}:*"
                keys = self.redis.keys(pattern)
                count = len(keys)
                cache_stats[cache_type] = count
                total_keys += count
            
            return {
                "success": True,
                "cache_enabled": True,
                "service": "AnalyseurTriphaseService",
                "total_keys": total_keys,
                "keys_by_type": cache_stats,
                "cache_config": self.cache_config,
                "redis_prefix": self.redis_prefix,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erreur stats cache analyseur: {e}")
            return {"success": False, "error": str(e)}
    
    def cleanup_cache(self, cache_type=None):
        """Nettoyer le cache de l'analyseur"""
        try:
            if not self.redis:
                return {"success": False, "error": "Redis non disponible"}
            
            deleted_count = 0
            
            if cache_type:
                # Nettoyage par type
                pattern = f"{self.redis_prefix}{cache_type}:*"
                keys = self.redis.keys(pattern)
                
                if keys:
                    deleted_count = self.redis.delete(*keys)
                
                message = f"Cache {cache_type} nettoyé"
            else:
                # Nettoyage complet
                pattern = f"{self.redis_prefix}*"
                keys = self.redis.keys(pattern)
                
                if keys:
                    deleted_count = self.redis.delete(*keys)
                
                message = "Cache analyseur triphasé nettoyé complètement"
            
            self.logger.info(f"Cache cleanup: {deleted_count} clés supprimées")
            
            return {
                "success": True,
                "message": message,
                "deleted_keys": deleted_count,
                "pattern_used": pattern
            }
            
        except Exception as e:
            self.logger.error(f"Erreur nettoyage cache: {e}")
            return {"success": False, "error": str(e)}
    
    def get_service_info(self):
        """Informations du service pour monitoring"""
        return {
            "service_name": "AnalyseurTriphaseService",
            "version": "2.0.0",  # ✅ MODIFIÉ : Version mise à jour pour intégration AlertService
            "redis_enabled": self.redis is not None,
            "cache_prefix": self.redis_prefix,
            "cache_types": list(self.cache_config.keys()),
            "default_thresholds": self.default_thresholds,
            "status": "operational",
            "integration": "AlertService compatible",  # ✅ NOUVEAU
            "features": [
                "Analyse temps réel triphasé",
                "Cache Redis intelligent", 
                "Détection déséquilibres",
                "Déduplication alertes",
                "Historique tendances",
                "Analyse pure sans création alertes"  # ✅ NOUVEAU
            ]
        }
    
    # =================== MÉTHODES DE MONITORING & DEBUG ===================
    
    def get_cache_health(self):
        """Vérification santé du cache"""
        try:
            health = {
                "service": "AnalyseurTriphaseService",
                "timestamp": datetime.utcnow().isoformat(),
                "cache_enabled": self.redis is not None,
                "status": "unknown"
            }
            
            if not self.redis:
                health["status"] = "disabled"
                health["message"] = "Redis non disponible"
                return {"success": True, "health": health}
            
            # Test Redis
            self.redis.ping()
            
            # Statistiques cache
            cache_stats = self.get_cache_statistics()
            
            if cache_stats.get("success"):
                total_keys = cache_stats.get("total_keys", 0)
                
                if total_keys > 1000:
                    health["status"] = "warning"
                    health["message"] = f"Beaucoup de clés en cache ({total_keys})"
                else:
                    health["status"] = "healthy"
                    health["message"] = f"Cache opérationnel ({total_keys} clés)"
                
                health["cache_stats"] = cache_stats["keys_by_type"]
            else:
                health["status"] = "error"
                health["message"] = "Erreur lecture statistiques cache"
            
            return {"success": True, "health": health}
            
        except Exception as e:
            health["status"] = "error"
            health["message"] = f"Erreur vérification santé: {str(e)}"
            return {"success": False, "health": health}
    
    def debug_device_analysis(self, device_id, show_cache_details=True):
        """Debug complet de l'analyse d'un appareil"""
        try:
            debug_info = {
                "device_id": device_id,
                "timestamp": datetime.utcnow().isoformat(),
                "cache_enabled": self.redis is not None,
                "analysis_cache": {},
                "trends_cache": {},
                "quality_cache": {}
            }
            
            # Vérifier appareil
            appareil = Device.query.get(device_id)
            if not appareil:
                debug_info["error"] = "Appareil non trouvé"
                return {"success": False, "debug": debug_info}
            
            debug_info["device_info"] = {
                "nom": appareil.nom_appareil,
                "type_systeme": appareil.type_systeme,
                "is_triphase": appareil.is_triphase(),
                "actif": appareil.actif
            }
            
            if not appareil.is_triphase():
                debug_info["error"] = "Appareil non triphasé"
                return {"success": False, "debug": debug_info}
            
            if show_cache_details and self.redis:
                # Analyser cache pour cet appareil
                patterns = [
                    f"{self.redis_prefix}analysis:{device_id}:*",
                    f"{self.redis_prefix}trends:{device_id}_*",
                    f"{self.redis_prefix}quality:{device_id}_*"
                ]
                
                for pattern in patterns:
                    keys = self.redis.keys(pattern)
                    pattern_name = pattern.split(':')[1].split('_')[0]
                    
                    debug_info[f"{pattern_name}_cache"]["key_count"] = len(keys)
                    debug_info[f"{pattern_name}_cache"]["keys"] = []
                    
                    for key in keys[:3]:  # Limiter à 3 clés
                        if isinstance(key, bytes):
                            key = key.decode()
                        
                        try:
                            ttl = self.redis.ttl(key)
                            debug_info[f"{pattern_name}_cache"]["keys"].append({
                                "key": key,
                                "ttl_seconds": ttl,
                                "expires_in": f"{ttl // 60}m {ttl % 60}s" if ttl > 0 else "No TTL"
                            })
                        except Exception as e:
                            debug_info[f"{pattern_name}_cache"]["keys"].append({
                                "key": key,
                                "error": str(e)
                            })
            
            # Test analyse temps réel
            derniere_donnee = DeviceData.query.filter_by(
                appareil_id=device_id,
                type_systeme='triphase'
            ).order_by(DeviceData.horodatage.desc()).first()
            
            if derniere_donnee:
                debug_info["last_data"] = {
                    "timestamp": derniere_donnee.horodatage.isoformat(),
                    "has_triphasé_data": all([
                        derniere_donnee.tension_l1 is not None,
                        derniere_donnee.tension_l2 is not None,
                        derniere_donnee.tension_l3 is not None
                    ])
                }
                
                # Test analyse sans cache
                try:
                    alertes = self.analyser_donnees_temps_reel(derniere_donnee, use_cache=False)
                    debug_info["test_analysis"] = {
                        "success": True,
                        "alertes_count": len(alertes) if isinstance(alertes, list) else 0
                    }
                    
                    # ✅ NOUVEAU : Test analyse pure sans création d'alertes
                    analyse_pure = self.analyser_donnees_sans_creation_alertes(derniere_donnee, use_cache=False)
                    debug_info["test_pure_analysis"] = {
                        "success": analyse_pure.get('success', False),
                        "anomalies_count": analyse_pure.get('nb_anomalies', 0),
                        "anomalies": analyse_pure.get('anomalies', [])
                    }
                    
                except Exception as e:
                    debug_info["test_analysis"] = {
                        "success": False,
                        "error": str(e)
                    }
            else:
                debug_info["last_data"] = None
                debug_info["test_analysis"] = {
                    "success": False,
                    "error": "Aucune donnée triphasée trouvée"
                }
            
            return {"success": True, "debug": debug_info}
            
        except Exception as e:
            self.logger.error(f"Erreur debug device analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "debug": {
                    "device_id": device_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
    
    # =================== MÉTHODES SIMPLIFIÉES POUR ALERTSERVICE ===================
    
    def detecter_anomalies_triphase(self, device_data, seuils_personnalises=None):
        """
        ✅ NOUVEAU : Méthode simplifiée pour AlertService
        Détecte les anomalies sans créer d'alertes
        Retourne juste les données d'analyse
        """
        try:
            if not isinstance(device_data, DeviceData) or not device_data.is_triphase():
                return {
                    'success': False,
                    'anomalies': [],
                    'recommandations': []
                }
            
            # Utiliser seuils personnalisés ou par défaut
            seuils = seuils_personnalises or self.default_thresholds
            anomalies = []
            
            # 1. Vérifier déséquilibres
            desequilibre_tension = device_data.calculer_desequilibre_tension()
            if desequilibre_tension and desequilibre_tension > seuils.get('desequilibre_tension_warning', 2.0):
                anomalies.append({
                    'type': 'desequilibre_tension',
                    'valeur': desequilibre_tension,
                    'seuil': seuils.get('desequilibre_tension_warning', 2.0),
                    'gravite': 'critique' if desequilibre_tension > seuils.get('desequilibre_tension_critical', 5.0) else 'warning',
                    'message': f'Déséquilibre de tension de {desequilibre_tension:.1f}%',
                    'recommandation': 'Vérifier équilibrage des charges'
                })
            
            desequilibre_courant = device_data.calculer_desequilibre_courant()
            if desequilibre_courant and desequilibre_courant > seuils.get('desequilibre_courant_warning', 10.0):
                anomalies.append({
                    'type': 'desequilibre_courant',
                    'valeur': desequilibre_courant,
                    'seuil': seuils.get('desequilibre_courant_warning', 10.0),
                    'gravite': 'critique' if desequilibre_courant > seuils.get('desequilibre_courant_critical', 20.0) else 'warning',
                    'message': f'Déséquilibre de courant de {desequilibre_courant:.1f}%',
                    'recommandation': 'Rééquilibrer les charges entre phases'
                })
            
            # 2. Vérifier pertes de phase
            phases_perdues = []
            tensions = {
                'L1': device_data.tension_l1,
                'L2': device_data.tension_l2,
                'L3': device_data.tension_l3
            }
            
            for phase, tension in tensions.items():
                if tension is None or tension < 50:
                    phases_perdues.append(phase)
            
            if phases_perdues:
                anomalies.append({
                    'type': 'perte_phase',
                    'phases_perdues': phases_perdues,
                    'gravite': 'critique',
                    'message': f'Perte de phase(s): {", ".join(phases_perdues)}',
                    'recommandation': 'Vérification urgente de l\'installation'
                })
            
            # 3. Vérifier facteur de puissance
            facteur_moyen = device_data.get_facteur_puissance_moyen()
            if facteur_moyen and facteur_moyen < seuils.get('facteur_puissance_min', 0.85):
                anomalies.append({
                    'type': 'facteur_puissance_faible',
                    'valeur': facteur_moyen,
                    'seuil': seuils.get('facteur_puissance_min', 0.85),
                    'gravite': 'warning',
                    'message': f'Facteur de puissance faible: {facteur_moyen:.3f}',
                    'recommandation': 'Envisager compensation réactive'
                })
            
            # Générer recommandations globales
            recommandations = self._generer_recommandations_simples(anomalies)
            
            return {
                'success': True,
                'device_id': device_data.appareil_id,
                'anomalies': anomalies,
                'nb_anomalies': len(anomalies),
                'nb_critiques': len([a for a in anomalies if a.get('gravite') == 'critique']),
                'recommandations': recommandations,
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erreur détection anomalies: {e}")
            return {
                'success': False,
                'error': str(e),
                'anomalies': [],
                'recommandations': []
            }
    
    def _generer_recommandations_simples(self, anomalies):
        """Générer recommandations simples basées sur les anomalies"""
        recommandations = []
        
        # Collecter toutes les recommandations des anomalies
        for anomalie in anomalies:
            if anomalie.get('recommandation'):
                recommandations.append({
                    'type': anomalie.get('type'),
                    'priorite': 'urgente' if anomalie.get('gravite') == 'critique' else 'normale',
                    'action': anomalie.get('recommandation'),
                    'concerne': anomalie.get('phases_perdues', []) or [anomalie.get('type')]
                })
        
        # Recommandation globale si beaucoup d'anomalies
        if len(anomalies) >= 3:
            recommandations.append({
                'type': 'audit_global',
                'priorite': 'haute',
                'action': 'Audit complet de l\'installation triphasée recommandé',
                'concerne': ['installation_complete']
            })
        
        return recommandations