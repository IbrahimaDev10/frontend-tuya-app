# device_service_analysis_extension.py - PARTIE 1
# ✅ AJOUTS pour intégrer AlertService + AnalyseurTriphaseService
# ⚠️ IMPORTANT : NE PAS MODIFIER L'EXISTANT - SEULEMENT AJOUTER

from app.services.alert_service import AlertService
from app.services.analyseur_triphase_service import AnalyseurTriphaseService
from datetime import datetime, timedelta
import json
import logging

# =================== EXTENSION DeviceService - PARTIE 1 ===================

class DeviceServiceAnalysisExtension:
    """
    Extension pour DeviceService - Intégration AlertService + AnalyseurTriphaseService
    ✅ À AJOUTER à votre DeviceService existant via héritage ou composition
    """
    
    def __init__(self, device_service_instance):
        """
        Initialiser l'extension avec l'instance DeviceService existante
        
        Args:
            device_service_instance: Votre instance DeviceService existante
        """
        # Référence vers votre DeviceService existant
        self.device_service = device_service_instance
        self.tuya_client = device_service_instance.tuya_client
        self.redis = device_service_instance.redis
        self.logger = logging.getLogger(__name__)
        
        # ✅ NOUVEAUX SERVICES
        self.alert_service = AlertService()
        self.analyseur_triphase = AnalyseurTriphaseService(redis_client=self.redis)
        
        # Configuration cache pour analyse
        self.analysis_cache_config = {
            'device_analysis_ttl': 300,      # 5 min - Résultats analyse
            'alert_summary_ttl': 600,        # 10 min - Résumé alertes
            'anomaly_detection_ttl': 900,    # 15 min - Détection anomalies
            'quality_score_ttl': 1800,       # 30 min - Score qualité
            'recommendations_ttl': 3600      # 1h - Recommandations
        }
        
        self.logger.info("✅ DeviceService Analysis Extension initialisée")
    
    # =================== NOUVELLES MÉTHODES D'ANALYSE ===================
    
    def analyser_device_complete_auto(self, device_data, device, use_cache=True):
        """
        ✅ NOUVELLE : Analyse complète automatique après collecte de données
        
        Args:
            device_data: Instance DeviceData à analyser
            device: Instance Device correspondante
            use_cache: Utiliser le cache Redis
            
        Returns:
            Dict avec résultats d'analyse complète
        """
        try:
            self.logger.info(f"🔍 Analyse automatique complète - Device: {device.id}")
            
            # Clé cache basée sur device + timestamp
            cache_key = f"{device.id}_{int(device_data.horodatage.timestamp()) if device_data.horodatage else int(datetime.utcnow().timestamp())}"
            
            # ✅ Vérifier cache d'abord
            if use_cache:
                cached_result = self._get_cached_complete_analysis(cache_key)
                if cached_result:
                    self.logger.debug(f"📦 Analyse depuis cache pour device {device.id}")
                    return cached_result
            
            # Résultat d'analyse
            analysis_result = {
                'device_id': device.id,
                'device_name': device.nom_appareil,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'type_systeme': device.type_systeme,
                'data_timestamp': device_data.horodatage.isoformat() if device_data.horodatage else None,
                'alertes_creees': [],
                'anomalies_detectees': [],
                'quality_analysis': {},
                'recommendations': [],
                'from_cache': False
            }
            
            # ✅ 1. Analyse via AlertService (automatique mono/triphasé)
            try:
                alert_result = self.alert_service.analyser_et_creer_alertes(
                    device_data, device, config={'use_cache': use_cache}
                )
                
                analysis_result['alertes_creees'] = alert_result.get('alertes_creees', [])
                analysis_result['nb_alertes'] = alert_result.get('nb_alertes', 0)
                analysis_result['nb_alertes_critiques'] = alert_result.get('nb_alertes_critiques', 0)
                analysis_result['type_systeme_detecte'] = alert_result.get('type_systeme_detecte')
                
                self.logger.debug(f"AlertService: {analysis_result['nb_alertes']} alertes créées")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur AlertService pour device {device.id}: {e}")
                analysis_result['alertes_error'] = str(e)
            
            # ✅ 2. Analyse spécialisée triphasé si applicable
            if device.is_triphase() and device_data.is_triphase():
                try:
                    # Analyse pure sans création d'alertes (déjà fait par AlertService)
                    triphase_result = self.analyseur_triphase.analyser_donnees_sans_creation_alertes(
                        device_data, use_cache=use_cache
                    )
                    
                    if triphase_result.get('success'):
                        analysis_result['anomalies_detectees'] = triphase_result.get('anomalies', [])
                        analysis_result['nb_anomalies'] = triphase_result.get('nb_anomalies', 0)
                        analysis_result['recommendations'].extend(triphase_result.get('recommandations', []))
                        
                        # Score qualité réseau
                        quality_score = self._calculate_quality_score_from_anomalies(
                            triphase_result.get('anomalies', [])
                        )
                        analysis_result['quality_analysis'] = {
                            'score': quality_score,
                            'level': self._get_quality_level(quality_score),
                            'anomalies_count': len(triphase_result.get('anomalies', []))
                        }
                        
                        self.logger.debug(f"AnalyseurTriphase: {len(triphase_result.get('anomalies', []))} anomalies détectées")
                    
                except Exception as e:
                    self.logger.error(f"❌ Erreur AnalyseurTriphase pour device {device.id}: {e}")
                    analysis_result['triphase_error'] = str(e)
            
            # ✅ 3. Mettre en cache le résultat
            if use_cache:
                self._cache_complete_analysis(cache_key, analysis_result)
            
            # ✅ 4. Statistiques finales
            analysis_result['analysis_summary'] = {
                'has_alerts': analysis_result['nb_alertes'] > 0,
                'has_critical_alerts': analysis_result['nb_alertes_critiques'] > 0,
                'has_anomalies': len(analysis_result['anomalies_detectees']) > 0,
                'has_recommendations': len(analysis_result['recommendations']) > 0,
                'overall_status': self._determine_overall_status(analysis_result)
            }
            
            self.logger.info(f"✅ Analyse complète terminée - Device: {device.id} - Status: {analysis_result['analysis_summary']['overall_status']}")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse complète device {device.id}: {e}")
            return {
                'device_id': device.id,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'success': False,
                'error': str(e),
                'alertes_creees': [],
                'anomalies_detectees': [],
                'recommendations': []
            }
    
    def get_device_analysis_summary(self, device_id, hours_back=24, use_cache=True):
        """
        ✅ NOUVELLE : Résumé des analyses récentes d'un appareil
        
        Args:
            device_id: ID de l'appareil (UUID ou tuya_device_id)
            hours_back: Période à analyser (heures)
            use_cache: Utiliser le cache
            
        Returns:
            Dict avec résumé des analyses récentes
        """
        try:
            device = self._get_device_by_id(device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            # Cache key
            cache_key = f"{device.id}_{hours_back}h_summary"
            
            if use_cache:
                cached_summary = self._get_cached_analysis_summary(cache_key)
                if cached_summary:
                    return cached_summary
            
            # Période d'analyse
            since = datetime.utcnow() - timedelta(hours=hours_back)
            
            # ✅ 1. Alertes récentes via AlertService
            alertes_result = self.alert_service.get_alertes_recentes(
                device_id=device.id, hours_back=hours_back
            )
            
            # ✅ 2. Données récentes pour analyse tendances
            from app.models.device_data import DeviceData
            recent_data = DeviceData.query.filter(
                DeviceData.appareil_id == device.id,
                DeviceData.horodatage >= since
            ).order_by(DeviceData.horodatage.desc()).limit(100).all()
            
            # ✅ 3. Analyse de tendances si triphasé
            tendances_analysis = {}
            if device.is_triphase() and len(recent_data) >= 10:
                try:
                    tendances_result = self.analyseur_triphase.analyser_tendances_appareil_cached(
                        device.id, hours_back=hours_back, use_cache=use_cache
                    )
                    
                    if tendances_result.get('success'):
                        tendances_analysis = {
                            'tensions': tendances_result.get('tensions', {}),
                            'desequilibres': tendances_result.get('desequilibres', {}),
                            'qualite_reseau': tendances_result.get('qualite_reseau', {}),
                            'recommandations': tendances_result.get('recommandations', [])
                        }
                except Exception as e:
                    self.logger.error(f"Erreur analyse tendances: {e}")
            
            # ✅ 4. Construire le résumé
            summary = {
                'success': True,
                'device_id': device.id,
                'device_name': device.nom_appareil,
                'periode_heures': hours_back,
                'type_systeme': device.type_systeme,
                'summary_timestamp': datetime.utcnow().isoformat(),
                
                # Alertes
                'alertes_summary': {
                    'total': alertes_result.get('statistiques', {}).get('total', 0),
                    'critiques': alertes_result.get('statistiques', {}).get('critiques', 0),
                    'warnings': alertes_result.get('statistiques', {}).get('warnings', 0),
                    'nouvelles': alertes_result.get('statistiques', {}).get('nouvelles', 0)
                },
                
                # Données
                'donnees_summary': {
                    'nb_echantillons': len(recent_data),
                    'derniere_donnee': recent_data[0].horodatage.isoformat() if recent_data else None,
                    'couverture_donnees': self._calculate_data_coverage(recent_data, hours_back)
                },
                
                # Tendances (si triphasé)
                'tendances_analysis': tendances_analysis,
                
                # Statut global
                'status_global': self._determine_device_health_status(
                    alertes_result.get('statistiques', {}),
                    len(recent_data),
                    tendances_analysis
                ),
                
                'from_cache': False
            }
            
            # ✅ 5. Mettre en cache
            if use_cache:
                self._cache_analysis_summary(cache_key, summary)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Erreur résumé analyse device {device_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "device_id": device_id
            }
    
    def get_device_anomalies_recent(self, device_id, hours_back=24, use_cache=True):
        """
        ✅ NOUVELLE : Récupérer les anomalies récentes détectées
        
        Args:
            device_id: ID de l'appareil
            hours_back: Période à analyser
            use_cache: Utiliser le cache
            
        Returns:
            Dict avec anomalies récentes
        """
        try:
            device = self._get_device_by_id(device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            cache_key = f"{device.id}_anomalies_{hours_back}h"
            
            if use_cache:
                cached_anomalies = self._get_cached_anomalies(cache_key)
                if cached_anomalies:
                    return cached_anomalies
            
            # Récupérer données récentes
            since = datetime.utcnow() - timedelta(hours=hours_back)
            from app.models.device_data import DeviceData
            
            recent_data = DeviceData.query.filter(
                DeviceData.appareil_id == device.id,
                DeviceData.horodatage >= since
            ).order_by(DeviceData.horodatage.desc()).all()
            
            anomalies_timeline = []
            
            # ✅ Analyser chaque point de données pour anomalies
            for data_point in recent_data:
                try:
                    if device.is_triphase() and data_point.is_triphase():
                        # Analyse triphasé
                        anomaly_result = self.analyseur_triphase.detecter_anomalies_triphase(
                            data_point, seuils_personnalises=device.get_seuils_actifs()
                        )
                        
                        if anomaly_result.get('success') and anomaly_result.get('anomalies'):
                            anomalies_timeline.append({
                                'timestamp': data_point.horodatage.isoformat(),
                                'type_systeme': 'triphase',
                                'anomalies': anomaly_result['anomalies'],
                                'nb_anomalies': len(anomaly_result['anomalies'])
                            })
                    
                    else:
                        # Analyse monophasé basique
                        anomalies_mono = self._detect_monophase_anomalies(data_point, device)
                        if anomalies_mono:
                            anomalies_timeline.append({
                                'timestamp': data_point.horodatage.isoformat(),
                                'type_systeme': 'monophase',
                                'anomalies': anomalies_mono,
                                'nb_anomalies': len(anomalies_mono)
                            })
                
                except Exception as e:
                    self.logger.error(f"Erreur analyse anomalie pour timestamp {data_point.horodatage}: {e}")
                    continue
            
            # ✅ Statistiques des anomalies
            total_anomalies = sum(item['nb_anomalies'] for item in anomalies_timeline)
            types_anomalies = {}
            for item in anomalies_timeline:
                for anomalie in item['anomalies']:
                    type_anom = anomalie.get('type', 'unknown')
                    types_anomalies[type_anom] = types_anomalies.get(type_anom, 0) + 1
            
            result = {
                'success': True,
                'device_id': device.id,
                'device_name': device.nom_appareil,
                'periode_heures': hours_back,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'total_points_analyses': len(recent_data),
                'points_avec_anomalies': len(anomalies_timeline),
                'total_anomalies': total_anomalies,
                'types_anomalies': types_anomalies,
                'anomalies_timeline': anomalies_timeline,
                'from_cache': False
            }
            
            # ✅ Cache
            if use_cache:
                self._cache_anomalies(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur anomalies récentes device {device_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "device_id": device_id
            }
    
    def get_device_quality_score(self, device_id, use_cache=True):
        """
        ✅ NOUVELLE : Score de qualité réseau pour appareil triphasé
        
        Args:
            device_id: ID de l'appareil
            use_cache: Utiliser le cache
            
        Returns:
            Dict avec score de qualité
        """
        try:
            device = self._get_device_by_id(device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            if not device.is_triphase():
                return {
                    "success": False,
                    "error": "Score de qualité disponible uniquement pour les appareils triphasés"
                }
            
            cache_key = f"{device.id}_quality_score"
            
            if use_cache:
                cached_score = self._get_cached_quality_score(cache_key)
                if cached_score:
                    return cached_score
            
            # ✅ Analyse via AnalyseurTriphase
            quality_result = self.analyseur_triphase.analyser_tendances_appareil_cached(
                device.id, hours_back=24, use_cache=use_cache
            )
            
            if not quality_result.get('success'):
                return {
                    "success": False,
                    "error": "Impossible d'analyser la qualité réseau"
                }
            
            quality_data = quality_result.get('qualite_reseau', {})
            
            result = {
                'success': True,
                'device_id': device.id,
                'device_name': device.nom_appareil,
                'quality_timestamp': datetime.utcnow().isoformat(),
                'quality_score': quality_data.get('score', 0),
                'quality_level': quality_data.get('niveau', 'inconnu'),
                'quality_trend': quality_data.get('tendance', 'stable'),
                'contributing_factors': {
                    'tensions_stability': quality_result.get('tensions', {}),
                    'desequilibres': quality_result.get('desequilibres', {}),
                    'facteur_puissance': quality_result.get('facteur_puissance', {})
                },
                'recommendations': quality_result.get('recommandations', []),
                'from_cache': False
            }
            
            # ✅ Cache
            if use_cache:
                self._cache_quality_score(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur score qualité device {device_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "device_id": device_id
            }
    
    def get_device_recommendations(self, device_id, use_cache=True):
        """
        ✅ NOUVELLE : Recommandations intelligentes pour un appareil
        
        Args:
            device_id: ID de l'appareil
            use_cache: Utiliser le cache
            
        Returns:
            Dict avec recommandations
        """
        try:
            device = self._get_device_by_id(device_id)
            if not device:
                return {"success": False, "error": "Appareil non trouvé"}
            
            cache_key = f"{device.id}_recommendations"
            
            if use_cache:
                cached_reco = self._get_cached_recommendations(cache_key)
                if cached_reco:
                    return cached_reco
            
            recommendations = []
            
            # ✅ 1. Recommandations basées sur alertes récentes
            alertes_result = self.alert_service.get_alertes_recentes(
                device_id=device.id, hours_back=48
            )
            
            if alertes_result.get('success'):
                alertes_stats = alertes_result.get('statistiques', {})
                
                if alertes_stats.get('critiques', 0) > 0:
                    recommendations.append({
                        'type': 'maintenance_urgente',
                        'priorite': 'haute',
                        'message': 'Intervention urgente recommandée suite aux alertes critiques',
                        'action': 'Vérifier installation et connexions',
                        'basé_sur': f"{alertes_stats['critiques']} alertes critiques"
                    })
                
                if alertes_stats.get('warnings', 0) > 5:
                    recommendations.append({
                        'type': 'maintenance_preventive',
                        'priorite': 'moyenne',
                        'message': 'Maintenance préventive recommandée',
                        'action': 'Inspection visuelle et vérification paramètres',
                        'basé_sur': f"{alertes_stats['warnings']} alertes d'avertissement"
                    })
            
            # ✅ 2. Recommandations spécifiques triphasé
            if device.is_triphase():
                try:
                    quality_result = self.get_device_quality_score(device.id, use_cache)
                    if quality_result.get('success'):
                        quality_score = quality_result.get('quality_score', 0)
                        
                        if quality_score < 60:
                            recommendations.append({
                                'type': 'qualite_reseau',
                                'priorite': 'haute',
                                'message': f'Qualité réseau dégradée (score: {quality_score})',
                                'action': 'Audit complet installation triphasée',
                                'basé_sur': 'Analyse qualité réseau'
                            })
                        
                        # Ajouter recommandations spécifiques de l'analyseur
                        quality_reco = quality_result.get('recommendations', [])
                        recommendations.extend(quality_reco)
                
                except Exception as e:
                    self.logger.error(f"Erreur recommandations triphasé: {e}")
            
            # ✅ 3. Recommandations basées sur historique
            history_reco = self._generate_history_based_recommendations(device)
            recommendations.extend(history_reco)
            
            # ✅ 4. Prioriser et limiter
            recommendations = self._prioritize_recommendations(recommendations)
            
            result = {
                'success': True,
                'device_id': device.id,
                'device_name': device.nom_appareil,
                'recommendations_timestamp': datetime.utcnow().isoformat(),
                'total_recommendations': len(recommendations),
                'recommendations': recommendations,
                'from_cache': False
            }
            
            # ✅ Cache
            if use_cache:
                self._cache_recommendations(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur recommandations device {device_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "device_id": device_id
            }
    
    def batch_analyze_devices(self, device_ids, use_cache=True):
        """
        ✅ NOUVELLE : Analyse batch de plusieurs appareils
        
        Args:
            device_ids: Liste des IDs d'appareils
            use_cache: Utiliser le cache
            
        Returns:
            Dict avec résultats d'analyse pour tous les appareils
        """
        try:
            if not isinstance(device_ids, list) or len(device_ids) == 0:
                return {"success": False, "error": "Liste d'IDs appareils requise"}
            
            if len(device_ids) > 50:  # Limite de sécurité
                return {"success": False, "error": "Maximum 50 appareils par analyse batch"}
            
            self.logger.info(f"🔍 Analyse batch de {len(device_ids)} appareils")
            
            results = []
            summary_stats = {
                'total_analyzed': 0,
                'successful_analyses': 0,
                'failed_analyses': 0,
                'total_alerts': 0,
                'total_anomalies': 0,
                'devices_with_issues': 0
            }
            
            for device_id in device_ids:
                try:
                    device = self._get_device_by_id(device_id)
                    if not device:
                        results.append({
                            'device_id': device_id,
                            'success': False,
                            'error': 'Appareil non trouvé'
                        })
                        summary_stats['failed_analyses'] += 1
                        continue
                    
                    # Récupérer dernière donnée pour analyse
                    from app.models.device_data import DeviceData
                    latest_data = DeviceData.query.filter_by(
                        appareil_id=device.id
                    ).order_by(DeviceData.horodatage.desc()).first()
                    
                    if not latest_data:
                        results.append({
                            'device_id': device_id,
                            'device_name': device.nom_appareil,
                            'success': False,
                            'error': 'Aucune donnée disponible'
                        })
                        summary_stats['failed_analyses'] += 1
                        continue
                    
                    # Analyse complète
                    analysis_result = self.analyser_device_complete_auto(
                        latest_data, device, use_cache
                    )
                    
                    if analysis_result.get('success', True):  # Par défaut True si pas spécifié
                        device_summary = {
                            'device_id': device.id,
                            'device_name': device.nom_appareil,
                            'success': True,
                            'type_systeme': device.type_systeme,
                            'nb_alertes': analysis_result.get('nb_alertes', 0),
                            'nb_alertes_critiques': analysis_result.get('nb_alertes_critiques', 0),
                            'nb_anomalies': len(analysis_result.get('anomalies_detectees', [])),
                            'overall_status': analysis_result.get('analysis_summary', {}).get('overall_status', 'unknown'),
                            'last_data_timestamp': latest_data.horodatage.isoformat(),
                            'from_cache': analysis_result.get('from_cache', False)
                        }
                        
                        # Compteurs
                        summary_stats['total_alerts'] += device_summary['nb_alertes']
                        summary_stats['total_anomalies'] += device_summary['nb_anomalies']
                        if device_summary['nb_alertes'] > 0 or device_summary['nb_anomalies'] > 0:
                            summary_stats['devices_with_issues'] += 1
                        
                        summary_stats['successful_analyses'] += 1
                    else:
                        device_summary = {
                            'device_id': device.id,
                            'device_name': device.nom_appareil,
                            'success': False,
                            'error': analysis_result.get('error', 'Erreur analyse')
                        }
                        summary_stats['failed_analyses'] += 1
                    
                    results.append(device_summary)
                    summary_stats['total_analyzed'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Erreur analyse device {device_id}: {e}")
                    results.append({
                        'device_id': device_id,
                        'success': False,
                        'error': str(e)
                    })
                    summary_stats['failed_analyses'] += 1
            
            return {
                'success': True,
                'batch_analysis_timestamp': datetime.utcnow().isoformat(),
                'requested_devices': len(device_ids),
                'summary_statistics': summary_stats,
                'results': results,
                'cache_used': use_cache
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse batch: {e}")
            return {
                "success": False,
                "error": str(e),
                "batch_analysis_timestamp": datetime.utcnow().isoformat()
            }
    
    # =================== MÉTHODES DE CACHE SPÉCIALISÉES ===================
    
    def _get_cached_complete_analysis(self, cache_key):
        """Récupérer analyse complète depuis cache"""
        if not self.redis:
            return None
        
        try:
            key = f"analysis_complete:{cache_key}"
            ttl = self.analysis_cache_config['device_analysis_ttl']
            
            cache_data = {
                **analysis_result,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            self.logger.debug(f"Cache analysis SET: {key} (TTL: {ttl}s)")
            
        except Exception as e:
            self.logger.error(f"Erreur cache analyse: {e}")
    
    def _get_cached_analysis_summary(self, cache_key):
        """Récupérer résumé analyse depuis cache"""
        if not self.redis:
            return None
        
        try:
            key = f"analysis_summary:{cache_key}"
            cached_data = self.redis.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                data['from_cache'] = True
                return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur récupération cache résumé: {e}")
            return None
    
    def _cache_analysis_summary(self, cache_key, summary_result):
        """Mettre en cache résumé analyse"""
        if not self.redis:
            return
        
        try:
            key = f"analysis_summary:{cache_key}"
            ttl = self.analysis_cache_config['alert_summary_ttl']
            
            cache_data = {
                **summary_result,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            
        except Exception as e:
            self.logger.error(f"Erreur cache résumé: {e}")
    
    def _get_cached_anomalies(self, cache_key):
        """Récupérer anomalies depuis cache"""
        if not self.redis:
            return None
        
        try:
            key = f"analysis_anomalies:{cache_key}"
            cached_data = self.redis.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                data['from_cache'] = True
                return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur récupération cache anomalies: {e}")
            return None
    
    def _cache_anomalies(self, cache_key, anomalies_result):
        """Mettre en cache anomalies"""
        if not self.redis:
            return
        
        try:
            key = f"analysis_anomalies:{cache_key}"
            ttl = self.analysis_cache_config['anomaly_detection_ttl']
            
            cache_data = {
                **anomalies_result,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            
        except Exception as e:
            self.logger.error(f"Erreur cache anomalies: {e}")
    
    def _get_cached_quality_score(self, cache_key):
        """Récupérer score qualité depuis cache"""
        if not self.redis:
            return None
        
        try:
            key = f"analysis_quality:{cache_key}"
            cached_data = self.redis.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                data['from_cache'] = True
                return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur récupération cache qualité: {e}")
            return None
    
    def _cache_quality_score(self, cache_key, quality_result):
        """Mettre en cache score qualité"""
        if not self.redis:
            return
        
        try:
            key = f"analysis_quality:{cache_key}"
            ttl = self.analysis_cache_config['quality_score_ttl']
            
            cache_data = {
                **quality_result,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            
        except Exception as e:
            self.logger.error(f"Erreur cache qualité: {e}")
    
    def _get_cached_recommendations(self, cache_key):
        """Récupérer recommandations depuis cache"""
        if not self.redis:
            return None
        
        try:
            key = f"analysis_recommendations:{cache_key}"
            cached_data = self.redis.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                data['from_cache'] = True
                return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur récupération cache recommandations: {e}")
            return None
    
    def _cache_recommendations(self, cache_key, recommendations_result):
        """Mettre en cache recommandations"""
        if not self.redis:
            return
        
        try:
            key = f"analysis_recommendations:{cache_key}"
            ttl = self.analysis_cache_config['recommendations_ttl']
            
            cache_data = {
                **recommendations_result,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            
        except Exception as e:
            self.logger.error(f"Erreur cache recommandations: {e}")
    
    # =================== MÉTHODES UTILITAIRES ===================
    
    def _get_device_by_id(self, device_id):
        """Récupérer appareil par ID (UUID ou tuya_device_id)"""
        try:
            from app.models.device import Device
            
            # Essayer UUID d'abord
            device = Device.query.get(device_id)
            
            if not device:
                # Essayer tuya_device_id
                device = Device.query.filter_by(tuya_device_id=device_id).first()
            
            return device
            
        except Exception as e:
            self.logger.error(f"Erreur récupération device {device_id}: {e}")
            return None
    
    def _calculate_quality_score_from_anomalies(self, anomalies):
        """Calculer score qualité basé sur anomalies"""
        if not anomalies:
            return 95  # Score élevé si pas d'anomalies
        
        score = 100
        
        for anomalie in anomalies:
            gravite = anomalie.get('gravite', 'warning')
            
            if gravite == 'critique':
                score -= 20
            elif gravite == 'warning':
                score -= 10
            else:
                score -= 5
        
        return max(0, score)
    
    def _get_quality_level(self, score):
        """Déterminer niveau qualité basé sur score"""
        if score >= 90:
            return 'excellent'
        elif score >= 75:
            return 'bon'
        elif score >= 60:
            return 'moyen'
        else:
            return 'mauvais'
    
    def _determine_overall_status(self, analysis_result):
        """Déterminer statut global d'analyse"""
        nb_critiques = analysis_result.get('nb_alertes_critiques', 0)
        nb_alertes = analysis_result.get('nb_alertes', 0)
        nb_anomalies = len(analysis_result.get('anomalies_detectees', []))
        
        if nb_critiques > 0:
            return 'critique'
        elif nb_alertes > 0 or nb_anomalies > 2:
            return 'attention'
        elif nb_anomalies > 0:
            return 'surveillance'
        else:
            return 'normal'
    
    def _calculate_data_coverage(self, data_points, hours_back):
        """Calculer couverture des données"""
        if not data_points:
            return 0.0
        
        # Calculer intervalles théoriques vs réels
        expected_points = hours_back * 60 / 5  # Assuming 5-minute intervals
        actual_points = len(data_points)
        
        coverage = min(100.0, (actual_points / expected_points) * 100)
        return round(coverage, 2)
    
    def _determine_device_health_status(self, alertes_stats, nb_donnees, tendances):
        """Déterminer statut santé global appareil"""
        critiques = alertes_stats.get('critiques', 0)
        warnings = alertes_stats.get('warnings', 0)
        
        if critiques > 0:
            return 'critique'
        elif warnings > 3:
            return 'degraded'
        elif nb_donnees < 10:
            return 'insufficient_data'
        else:
            return 'healthy'
    
    def _detect_monophase_anomalies(self, device_data, device):
        """Détecter anomalies simples pour monophasé"""
        anomalies = []
        seuils = device.get_seuils_actifs()
        
        try:
            # Tension
            if device_data.tension:
                if device_data.tension < seuils.get('seuil_tension_min', 200):
                    anomalies.append({
                        'type': 'tension_basse',
                        'valeur': device_data.tension,
                        'seuil': seuils.get('seuil_tension_min'),
                        'gravite': 'warning'
                    })
                elif device_data.tension > seuils.get('seuil_tension_max', 250):
                    anomalies.append({
                        'type': 'tension_haute',
                        'valeur': device_data.tension,
                        'seuil': seuils.get('seuil_tension_max'),
                        'gravite': 'critique'
                    })
            
            # Courant
            if device_data.courant and device_data.courant > seuils.get('seuil_courant_max', 20):
                anomalies.append({
                    'type': 'courant_eleve',
                    'valeur': device_data.courant,
                    'seuil': seuils.get('seuil_courant_max'),
                    'gravite': 'warning'
                })
            
            # Puissance
            if device_data.puissance and device_data.puissance > seuils.get('seuil_puissance_max', 5000):
                anomalies.append({
                    'type': 'puissance_elevee',
                    'valeur': device_data.puissance,
                    'seuil': seuils.get('seuil_puissance_max'),
                    'gravite': 'warning'
                })
            
        except Exception as e:
            self.logger.error(f"Erreur détection anomalies mono: {e}")
        
        return anomalies
    
    def _generate_history_based_recommendations(self, device):
        """Générer recommandations basées sur historique"""
        recommendations = []
        
        try:
            # Vérifier fréquence des données
            from app.models.device_data import DeviceData
            recent_count = DeviceData.query.filter(
                DeviceData.appareil_id == device.id,
                DeviceData.horodatage >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            if recent_count < 50:  # Moins de données que prévu
                recommendations.append({
                    'type': 'connectivity',
                    'priorite': 'moyenne',
                    'message': 'Collecte de données irrégulière détectée',
                    'action': 'Vérifier connectivité et configuration Tuya',
                    'basé_sur': f'Seulement {recent_count} points de données en 24h'
                })
            
            # Vérifier dernière connexion
            if device.derniere_donnee:
                silence_hours = (datetime.utcnow() - device.derniere_donnee).total_seconds() / 3600
                if silence_hours > 2:
                    recommendations.append({
                        'type': 'communication',
                        'priorite': 'haute',
                        'message': f'Appareil silencieux depuis {silence_hours:.1f}h',
                        'action': 'Vérifier état appareil et connexion réseau',
                        'basé_sur': 'Absence de données récentes'
                    })
            
        except Exception as e:
            self.logger.error(f"Erreur recommandations historique: {e}")
        
        return recommendations
    
    def _prioritize_recommendations(self, recommendations):
        """Prioriser et limiter les recommandations"""
        # Tri par priorité
        priority_order = {'urgente': 0, 'haute': 1, 'moyenne': 2, 'basse': 3}
        
        recommendations.sort(key=lambda x: priority_order.get(x.get('priorite', 'basse'), 3))
        
        # Limiter à 10 recommandations max
        return recommendations[:10]
    
    # =================== INTÉGRATION AVEC DeviceService EXISTANT ===================
    
    def enhance_save_device_data(self, device, status_data):
        """
        ✅ NOUVELLE : Méthode d'enhancement pour _save_device_data existant
        
        Cette méthode doit être appelée APRÈS votre _save_device_data existant
        pour ajouter l'analyse automatique
        
        Args:
            device: Instance Device
            status_data: Données de statut récupérées
        """
        try:
            if not status_data.get("success") or not device.is_assigne():
                return
            
            self.logger.debug(f"🔍 Enhancement analyse auto pour device {device.id}")
            
            # Récupérer la dernière DeviceData créée
            from app.models.device_data import DeviceData
            latest_data = DeviceData.query.filter_by(
                appareil_id=device.id
            ).order_by(DeviceData.horodatage.desc()).first()
            
            if latest_data:
                # ✅ Lancer analyse automatique
                analysis_result = self.analyser_device_complete_auto(
                    latest_data, device, use_cache=True
                )
                
                # Log résultat
                if analysis_result.get('nb_alertes', 0) > 0:
                    self.logger.info(f"📊 Analyse auto - Device {device.id}: {analysis_result['nb_alertes']} alertes créées")
                
                return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur enhancement save data device {device.id}: {e}")
            return None
    
    def enhance_get_device_status(self, original_result, device_id):
        """
        ✅ NOUVELLE : Enhancement pour get_device_status existant
        
        Ajoute informations d'analyse au résultat existant
        
        Args:
            original_result: Résultat original de get_device_status
            device_id: ID de l'appareil
            
        Returns:
            Résultat enrichi avec données d'analyse
        """
        try:
            if not original_result.get('success'):
                return original_result
            
            device = self._get_device_by_id(device_id)
            if not device:
                return original_result
            
            # ✅ Ajouter résumé d'analyse récent
            try:
                analysis_summary = self.get_device_analysis_summary(
                    device.id, hours_back=6, use_cache=True
                )
                
                if analysis_summary.get('success'):
                    original_result['analysis_summary'] = {
                        'alertes_recentes': analysis_summary.get('alertes_summary', {}),
                        'status_global': analysis_summary.get('status_global', 'unknown'),
                        'derniere_analyse': analysis_summary.get('summary_timestamp')
                    }
            except Exception as e:
                self.logger.error(f"Erreur ajout analyse summary: {e}")
            
            # ✅ Ajouter score qualité si triphasé
            if device.is_triphase():
                try:
                    quality_result = self.get_device_quality_score(device.id, use_cache=True)
                    if quality_result.get('success'):
                        original_result['quality_score'] = {
                            'score': quality_result.get('quality_score', 0),
                            'level': quality_result.get('quality_level', 'unknown')
                        }
                except Exception as e:
                    self.logger.error(f"Erreur ajout quality score: {e}")
            
            return original_result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur enhancement get_device_status: {e}")
            return original_result
    
    # =================== ADMINISTRATION ET MONITORING ===================
    
    def get_analysis_service_health(self):
        """Vérifier santé des services d'analyse"""
        try:
            health = {
                'service': 'DeviceServiceAnalysisExtension',
                'timestamp': datetime.utcnow().isoformat(),
                'components': {}
            }
            
            # Test AlertService
            try:
                alert_health = self.alert_service.get_service_health()
                health['components']['alert_service'] = {
                    'status': 'healthy' if alert_health.get('success') else 'error',
                    'details': alert_health.get('health', {})
                }
            except Exception as e:
                health['components']['alert_service'] = {
                    'status': 'error',
                    'error': str(e)
                }
            
            # Test AnalyseurTriphaseService
            try:
                analyseur_health = self.analyseur_triphase.get_cache_health()
                health['components']['analyseur_triphase'] = {
                    'status': 'healthy' if analyseur_health.get('success') else 'error',
                    'details': analyseur_health.get('health', {})
                }
            except Exception as e:
                health['components']['analyseur_triphase'] = {
                    'status': 'error',
                    'error': str(e)
                }
            
            # Test Redis cache
            try:
                if self.redis:
                    self.redis.ping()
                    health['components']['redis_cache'] = {
                        'status': 'healthy',
                        'cache_enabled': True
                    }
                else:
                    health['components']['redis_cache'] = {
                        'status': 'disabled',
                        'cache_enabled': False
                    }
            except Exception as e:
                health['components']['redis_cache'] = {
                    'status': 'error',
                    'error': str(e)
                }
            
            # Statut global
            all_healthy = all(
                comp.get('status') in ['healthy', 'disabled']
                for comp in health['components'].values()
            )
            
            health['overall_status'] = 'healthy' if all_healthy else 'degraded'
            
            return {'success': True, 'health': health}
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'health': {
                    'service': 'DeviceServiceAnalysisExtension',
                    'overall_status': 'error',
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
    
    def get_analysis_cache_statistics(self):
        """Statistiques du cache d'analyse"""
        try:
            if not self.redis:
                return {
                    'success': False,
                    'error': 'Redis non disponible',
                    'cache_enabled': False
                }
            
            # Compter clés par type
            cache_types = ['analysis_complete', 'analysis_summary', 'analysis_anomalies', 
                          'analysis_quality', 'analysis_recommendations']
            
            cache_stats = {}
            total_keys = 0
            
            for cache_type in cache_types:
                pattern = f"{cache_type}:*"
                keys = self.redis.keys(pattern)
                count = len(keys)
                cache_stats[cache_type] = count
                total_keys += count
            
            return {
                'success': True,
                'service': 'DeviceServiceAnalysisExtension',
                'cache_enabled': True,
                'total_keys': total_keys,
                'keys_by_type': cache_stats,
                'cache_config': self.analysis_cache_config,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def cleanup_analysis_cache(self, cache_type=None):
        """Nettoyer le cache d'analyse"""
        try:
            if not self.redis:
                return {'success': False, 'error': 'Redis non disponible'}
            
            deleted_count = 0
            
            if cache_type:
                # Nettoyage par type
                pattern = f"analysis_{cache_type}:*"
                keys = self.redis.keys(pattern)
                
                if keys:
                    deleted_count = self.redis.delete(*keys)
                
                message = f"Cache analysis {cache_type} nettoyé"
            else:
                # Nettoyage complet
                patterns = ['analysis_complete:*', 'analysis_summary:*', 'analysis_anomalies:*',
                           'analysis_quality:*', 'analysis_recommendations:*']
                
                for pattern in patterns:
                    keys = self.redis.keys(pattern)
                    if keys:
                        deleted_count += self.redis.delete(*keys)
                
                message = "Cache analysis complet nettoyé"
            
            self.logger.info(f"Cache cleanup analysis: {deleted_count} clés supprimées")
            
            return {
                'success': True,
                'message': message,
                'deleted_keys': deleted_count,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erreur nettoyage cache analysis: {e}")
            return {'success': False, 'error': str(e)}

            cached_data = self.redis.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                data['from_cache'] = True
                return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur récupération cache analyse: {e}")
            return None
    
    def _cache_complete_analysis(self, cache_key, analysis_result):
        """Mettre en cache analyse complète"""
        if not self.redis:
            return
        
        try:
            key = f"analysis_complete:{cache_key}"
            ttl = self.analysis_cache_config['device_analysis_ttl']
            
            cache_data = {
                **analysis_result,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(key, ttl, json.dumps(cache_data))
            self.logger.debug(f"Cache analysis SET: {key} (TTL: {ttl}s)")
            
        except Exception as e:
            self.logger.error(f"Erreur cache analyse: {e}")

    def _get_cached_complete_analysis(self, cache_key):
        """Récupérer analyse complète depuis cache"""
        if not self.redis:
            return None
        
        try:
            key = f"analysis_complete:{cache_key}"
            cached_data = self.redis.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                data['from_cache'] = True
                return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur récupération cache analyse: {e}")
            return None