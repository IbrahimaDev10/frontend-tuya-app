from app import db
from datetime import datetime
import uuid
import math

class DeviceData(db.Model):
    """Modèle pour les données temps réel des appareils (monophasé et triphasé)"""
    
    __tablename__ = 'device_data'
    
    # Clé primaire (auto-increment pour performance)
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    
    # Relations
    appareil_id = db.Column(db.String(36), db.ForeignKey('devices.id'), nullable=False, index=True)
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=False, index=True)
    
    # Horodatage
    horodatage = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # =================== TYPE DE SYSTÈME ===================
    type_systeme = db.Column(db.Enum('monophase', 'triphase', name='system_type'), 
                            nullable=False, default='monophase', index=True)
    
    # =================== DONNÉES MONOPHASÉES (compatibilité existante) ===================
    tension = db.Column(db.Float, nullable=True)  # Volts (ex: 230.50)
    courant = db.Column(db.Float, nullable=True)  # Ampères (ex: 2.350)
    puissance = db.Column(db.Float, nullable=True)  # Watts (ex: 1250.75)
    energie = db.Column(db.Float, nullable=True)  # kWh (ex: 15.250)
    
    # =================== NOUVELLES DONNÉES TRIPHASÉES ===================
    
    # Tensions par phase (Line to Neutral) - V
    tension_l1 = db.Column(db.Float, nullable=True)  # Phase 1 vers Neutre
    tension_l2 = db.Column(db.Float, nullable=True)  # Phase 2 vers Neutre
    tension_l3 = db.Column(db.Float, nullable=True)  # Phase 3 vers Neutre
    
    # Tensions composées (Line to Line) - V
    tension_l1_l2 = db.Column(db.Float, nullable=True)  # Phase 1 vers Phase 2
    tension_l2_l3 = db.Column(db.Float, nullable=True)  # Phase 2 vers Phase 3
    tension_l3_l1 = db.Column(db.Float, nullable=True)  # Phase 3 vers Phase 1
    
    # Courants par phase - A
    courant_l1 = db.Column(db.Float, nullable=True)  # Courant Phase 1
    courant_l2 = db.Column(db.Float, nullable=True)  # Courant Phase 2
    courant_l3 = db.Column(db.Float, nullable=True)  # Courant Phase 3
    courant_neutre = db.Column(db.Float, nullable=True)  # Courant Neutre
    
    # Puissances par phase - W
    puissance_l1 = db.Column(db.Float, nullable=True)  # Puissance active Phase 1
    puissance_l2 = db.Column(db.Float, nullable=True)  # Puissance active Phase 2
    puissance_l3 = db.Column(db.Float, nullable=True)  # Puissance active Phase 3
    puissance_totale = db.Column(db.Float, nullable=True)  # Puissance active totale
    
    # Puissances réactives par phase - VAR
    puissance_reactive_l1 = db.Column(db.Float, nullable=True)
    puissance_reactive_l2 = db.Column(db.Float, nullable=True)
    puissance_reactive_l3 = db.Column(db.Float, nullable=True)
    puissance_reactive_totale = db.Column(db.Float, nullable=True)
    
    # Puissances apparentes par phase - VA
    puissance_apparente_l1 = db.Column(db.Float, nullable=True)
    puissance_apparente_l2 = db.Column(db.Float, nullable=True)
    puissance_apparente_l3 = db.Column(db.Float, nullable=True)
    puissance_apparente_totale = db.Column(db.Float, nullable=True)
    
    # Facteurs de puissance par phase
    facteur_puissance_l1 = db.Column(db.Float, nullable=True)  # cos φ Phase 1
    facteur_puissance_l2 = db.Column(db.Float, nullable=True)  # cos φ Phase 2
    facteur_puissance_l3 = db.Column(db.Float, nullable=True)  # cos φ Phase 3
    facteur_puissance_total = db.Column(db.Float, nullable=True)  # cos φ total
    
    # Fréquence du réseau - Hz
    frequence = db.Column(db.Float, nullable=True, default=50.0)
    
    # Énergies cumulées par phase - kWh
    energie_l1 = db.Column(db.Float, nullable=True)
    energie_l2 = db.Column(db.Float, nullable=True)
    energie_l3 = db.Column(db.Float, nullable=True)
    energie_totale = db.Column(db.Float, nullable=True)
    
    # =================== DONNÉES ENVIRONNEMENTALES (existantes) ===================
    temperature = db.Column(db.Float, nullable=True)  # Celsius
    humidite = db.Column(db.Float, nullable=True)  # %
    
    # État de l'appareil (existant)
    etat_switch = db.Column(db.Boolean, nullable=True)
    
    # Données brutes JSON (existant)
    donnees_brutes = db.Column(db.JSON, nullable=True)
    
    # Index composé pour performance
    __table_args__ = (
        db.Index('idx_device_data_time', 'appareil_id', 'horodatage'),
        db.Index('idx_client_data_time', 'client_id', 'horodatage'),
        db.Index('idx_system_type_time', 'type_systeme', 'horodatage'),  # ✅ NOUVEAU
    )
    
    def __repr__(self):
        return f'<DeviceData {self.appareil_id} ({self.type_systeme}) @ {self.horodatage}>'
    
    # =================== MÉTHODES D'ANALYSE TRIPHASÉE ===================
    
    def is_monophase(self):
        """Vérifier si les données sont monophasées"""
        return self.type_systeme == 'monophase'
    
    def is_triphase(self) -> bool:
        return all([
            self.tension_l1 and self.tension_l1 > 50,
            self.tension_l2 and self.tension_l2 > 50,
            self.tension_l3 and self.tension_l3 > 50
        ])

    
    def get_tension_moyenne(self):
        """Calculer la tension moyenne selon le type"""
        if self.is_monophase():
            return self.tension
        else:
            tensions = [self.tension_l1, self.tension_l2, self.tension_l3]
            tensions_valides = [t for t in tensions if t is not None]
            return sum(tensions_valides) / len(tensions_valides) if tensions_valides else None
    
    def get_courant_total(self):
        """Calculer le courant total selon le type"""
        if self.is_monophase():
            return self.courant
        else:
            courants = [self.courant_l1, self.courant_l2, self.courant_l3]
            courants_valides = [c for c in courants if c is not None]
            return sum(courants_valides) if courants_valides else None
    
    def get_puissance_totale_calculee(self):
        """Calculer la puissance totale selon le type"""
        if self.is_monophase():
            return self.puissance
        else:
            return self.puissance_totale or self._calculer_puissance_totale()
    
    def _calculer_puissance_totale(self):
        """Calculer la puissance totale à partir des phases"""
        puissances = [self.puissance_l1, self.puissance_l2, self.puissance_l3]
        puissances_valides = [p for p in puissances if p is not None]
        return sum(puissances_valides) if puissances_valides else None
    
    # =================== CALCULS DE DÉSÉQUILIBRE ===================
    
    def calculer_desequilibre_tension(self):
        """Calculer le déséquilibre de tension en %"""
        if not self.is_triphase():
            return None
        
        tensions = [self.tension_l1, self.tension_l2, self.tension_l3]
        tensions_valides = [t for t in tensions if t is not None]
        
        if len(tensions_valides) < 3:
            return None
        
        tension_moyenne = sum(tensions_valides) / len(tensions_valides)
        if tension_moyenne == 0:
            return None
        
        # Déséquilibre = (écart max / moyenne) * 100
        ecart_max = max([abs(t - tension_moyenne) for t in tensions_valides])
        return round((ecart_max / tension_moyenne) * 100, 2)
    
    def calculer_desequilibre_courant(self):
        """Calculer le déséquilibre de courant en %"""
        if not self.is_triphase():
            return None
        
        courants = [self.courant_l1, self.courant_l2, self.courant_l3]
        courants_valides = [c for c in courants if c is not None]
        
        if len(courants_valides) < 3:
            return None
        
        courant_moyen = sum(courants_valides) / len(courants_valides)
        if courant_moyen == 0:
            return None
        
        ecart_max = max([abs(c - courant_moyen) for c in courants_valides])
        return round((ecart_max / courant_moyen) * 100, 2)
    
    def get_facteur_puissance_moyen(self):
        """Calculer le facteur de puissance moyen"""
        if self.is_monophase():
            # Pour monophasé, calculer à partir de P et S si disponibles
            if self.puissance and self.tension and self.courant:
                s_apparent = self.tension * self.courant
                return round(self.puissance / s_apparent, 3) if s_apparent > 0 else None
            return None
        else:
            # Pour triphasé, utiliser le facteur total ou calculer la moyenne
            if self.facteur_puissance_total:
                return self.facteur_puissance_total
            
            facteurs = [self.facteur_puissance_l1, self.facteur_puissance_l2, self.facteur_puissance_l3]
            facteurs_valides = [f for f in facteurs if f is not None]
            return round(sum(facteurs_valides) / len(facteurs_valides), 3) if facteurs_valides else None
    
    # =================== DÉTECTION D'ANOMALIES ===================
    
    def detecter_anomalies(self, seuils_appareil=None):
        """Détecter les anomalies selon le type de système"""
        anomalies = []
        
        if not seuils_appareil:
            return anomalies
        
        if self.is_monophase():
            anomalies.extend(self._detecter_anomalies_monophase(seuils_appareil))
        else:
            anomalies.extend(self._detecter_anomalies_triphase(seuils_appareil))
        
        return anomalies
    
    def _detecter_anomalies_monophase(self, seuils):
        """Détecter anomalies pour système monophasé"""
        anomalies = []
        
        # Vérification tension
        if self.tension:
            if seuils.get('seuil_tension_min') and self.tension < seuils['seuil_tension_min']:
                anomalies.append({
                    'type': 'seuil_depasse',
                    'gravite': 'warning',
                    'message': f'Tension trop basse: {self.tension}V',
                    'valeur': self.tension,
                    'seuil': seuils['seuil_tension_min'],
                    'unite': 'V'
                })
            if seuils.get('seuil_tension_max') and self.tension > seuils['seuil_tension_max']:
                anomalies.append({
                    'type': 'seuil_depasse',
                    'gravite': 'critique',
                    'message': f'Tension trop élevée: {self.tension}V',
                    'valeur': self.tension,
                    'seuil': seuils['seuil_tension_max'],
                    'unite': 'V'
                })
        
        # Vérification courant
        if self.courant and seuils.get('seuil_courant_max'):
            if self.courant > seuils['seuil_courant_max']:
                anomalies.append({
                    'type': 'seuil_depasse',
                    'gravite': 'critique',
                    'message': f'Courant trop élevé: {self.courant}A',
                    'valeur': self.courant,
                    'seuil': seuils['seuil_courant_max'],
                    'unite': 'A'
                })
        
        # Vérification puissance
        if self.puissance and seuils.get('seuil_puissance_max'):
            if self.puissance > seuils['seuil_puissance_max']:
                anomalies.append({
                    'type': 'seuil_depasse',
                    'gravite': 'warning',
                    'message': f'Puissance élevée: {self.puissance}W',
                    'valeur': self.puissance,
                    'seuil': seuils['seuil_puissance_max'],
                    'unite': 'W'
                })
        
        return anomalies
    
    def _detecter_anomalies_triphase(self, seuils):
        """Détecter anomalies pour système triphasé"""
        anomalies = []
        
        # Vérification tensions par phase
        tensions = [
            ('L1', self.tension_l1, seuils.get('seuil_tension_l1_min'), seuils.get('seuil_tension_l1_max')),
            ('L2', self.tension_l2, seuils.get('seuil_tension_l2_min'), seuils.get('seuil_tension_l2_max')),
            ('L3', self.tension_l3, seuils.get('seuil_tension_l3_min'), seuils.get('seuil_tension_l3_max'))
        ]
        
        for phase, tension, seuil_min, seuil_max in tensions:
            if tension:
                if seuil_min and tension < seuil_min:
                    anomalies.append({
                        'type': 'seuil_depasse',
                        'gravite': 'warning',
                        'message': f'Tension {phase} trop basse: {tension}V',
                        'valeur': tension,
                        'seuil': seuil_min,
                        'unite': 'V',
                        'phase': phase
                    })
                if seuil_max and tension > seuil_max:
                    anomalies.append({
                        'type': 'seuil_depasse',
                        'gravite': 'critique',
                        'message': f'Tension {phase} trop élevée: {tension}V',
                        'valeur': tension,
                        'seuil': seuil_max,
                        'unite': 'V',
                        'phase': phase
                    })
        
        # Vérification courants par phase
        courants = [
            ('L1', self.courant_l1, seuils.get('seuil_courant_l1_max')),
            ('L2', self.courant_l2, seuils.get('seuil_courant_l2_max')),
            ('L3', self.courant_l3, seuils.get('seuil_courant_l3_max'))
        ]
        
        for phase, courant, seuil_max in courants:
            if courant and seuil_max and courant > seuil_max:
                anomalies.append({
                    'type': 'seuil_depasse',
                    'gravite': 'critique',
                    'message': f'Courant {phase} trop élevé: {courant}A',
                    'valeur': courant,
                    'seuil': seuil_max,
                    'unite': 'A',
                    'phase': phase
                })
        
        # Vérification déséquilibre tension
        desequilibre_tension = self.calculer_desequilibre_tension()
        if desequilibre_tension and seuils.get('seuil_desequilibre_tension'):
            if desequilibre_tension > seuils['seuil_desequilibre_tension']:
                anomalies.append({
                    'type': 'desequilibre',
                    'gravite': 'warning',
                    'message': f'Déséquilibre tension: {desequilibre_tension}%',
                    'valeur': desequilibre_tension,
                    'seuil': seuils['seuil_desequilibre_tension'],
                    'unite': '%'
                })
        
        # Vérification déséquilibre courant
        desequilibre_courant = self.calculer_desequilibre_courant()
        if desequilibre_courant and seuils.get('seuil_desequilibre_courant'):
            if desequilibre_courant > seuils['seuil_desequilibre_courant']:
                anomalies.append({
                    'type': 'desequilibre',
                    'gravite': 'warning',
                    'message': f'Déséquilibre courant: {desequilibre_courant}%',
                    'valeur': desequilibre_courant,
                    'seuil': seuils['seuil_desequilibre_courant'],
                    'unite': '%'
                })
        
        # Vérification facteur de puissance
        facteur_puissance = self.get_facteur_puissance_moyen()
        if facteur_puissance and seuils.get('seuil_facteur_puissance_min'):
            if facteur_puissance < seuils['seuil_facteur_puissance_min']:
                anomalies.append({
                    'type': 'facteur_puissance',
                    'gravite': 'info',
                    'message': f'Facteur de puissance faible: {facteur_puissance}',
                    'valeur': facteur_puissance,
                    'seuil': seuils['seuil_facteur_puissance_min'],
                    'unite': ''
                })
        
        return anomalies
    
    # =================== MÉTHODES DE COMPATIBILITÉ ===================
    
    def migrer_vers_triphase(self, tension_l1, tension_l2, tension_l3, courant_l1, courant_l2, courant_l3):
        """Migrer des données monophasées vers triphasées"""
        if self.is_triphase():
            return False, "Les données sont déjà triphasées"
        
        self.type_systeme = 'triphase'
        self.tension_l1 = tension_l1
        self.tension_l2 = tension_l2
        self.tension_l3 = tension_l3
        self.courant_l1 = courant_l1
        self.courant_l2 = courant_l2
        self.courant_l3 = courant_l3
        
        # Calculer puissances si tension/courant disponibles
        if tension_l1 and courant_l1:
            self.puissance_l1 = tension_l1 * courant_l1 * (self.facteur_puissance_l1 or 0.9)
        if tension_l2 and courant_l2:
            self.puissance_l2 = tension_l2 * courant_l2 * (self.facteur_puissance_l2 or 0.9)
        if tension_l3 and courant_l3:
            self.puissance_l3 = tension_l3 * courant_l3 * (self.facteur_puissance_l3 or 0.9)
        
        self.puissance_totale = self._calculer_puissance_totale()
        
        return True, "Migration vers triphasé réussie"
    
    def get_resume_donnees(self):
        """Résumé intelligent des données selon le type"""
        if self.is_monophase():
            return {
                'type': 'monophase',
                'tension': self.tension,
                'courant': self.courant,
                'puissance': self.puissance,
                'energie': self.energie,
                'facteur_puissance': self.get_facteur_puissance_moyen()
            }
        else:
            return {
                'type': 'triphase',
                'tensions': {
                    'L1': self.tension_l1,
                    'L2': self.tension_l2,
                    'L3': self.tension_l3,
                    'moyenne': self.get_tension_moyenne()
                },
                'courants': {
                    'L1': self.courant_l1,
                    'L2': self.courant_l2,
                    'L3': self.courant_l3,
                    'total': self.get_courant_total()
                },
                'puissances': {
                    'L1': self.puissance_l1,
                    'L2': self.puissance_l2,
                    'L3': self.puissance_l3,
                    'totale': self.puissance_totale
                },
                'desequilibres': {
                    'tension': self.calculer_desequilibre_tension(),
                    'courant': self.calculer_desequilibre_courant()
                },
                'facteur_puissance': {
                    'L1': self.facteur_puissance_l1,
                    'L2': self.facteur_puissance_l2,
                    'L3': self.facteur_puissance_l3,
                    'moyen': self.get_facteur_puissance_moyen()
                },
                'frequence': self.frequence
            }
    
    def to_dict(self, include_calculs=False, include_anomalies=False, seuils_appareil=None):
        """Convertir en dictionnaire pour l'API"""
        data = {
            'id': self.id,
            'appareil_id': self.appareil_id,
            'horodatage': self.horodatage.isoformat() if self.horodatage else None,
            'type_systeme': self.type_systeme,  # ✅ NOUVEAU
            
            # Données de base (compatibilité)
            'tension': float(self.tension) if self.tension else None,
            'courant': float(self.courant) if self.courant else None,
            'puissance': float(self.puissance) if self.puissance else None,
            'energie': float(self.energie) if self.energie else None,
            
            # Données environnementales
            'temperature': float(self.temperature) if self.temperature else None,
            'humidite': float(self.humidite) if self.humidite else None,
            'etat_switch': self.etat_switch,
            'donnees_brutes': self.donnees_brutes
        }
        
        # Ajouter données triphasées si applicable
        if self.is_triphase():
            data['donnees_triphase'] = {
                'tensions': {
                    'L1': float(self.tension_l1) if self.tension_l1 else None,
                    'L2': float(self.tension_l2) if self.tension_l2 else None,
                    'L3': float(self.tension_l3) if self.tension_l3 else None,
                    'L1_L2': float(self.tension_l1_l2) if self.tension_l1_l2 else None,
                    'L2_L3': float(self.tension_l2_l3) if self.tension_l2_l3 else None,
                    'L3_L1': float(self.tension_l3_l1) if self.tension_l3_l1 else None,
                },
                'courants': {
                    'L1': float(self.courant_l1) if self.courant_l1 else None,
                    'L2': float(self.courant_l2) if self.courant_l2 else None,
                    'L3': float(self.courant_l3) if self.courant_l3 else None,
                    'neutre': float(self.courant_neutre) if self.courant_neutre else None,
                },
                'puissances': {
                    'active': {
                        'L1': float(self.puissance_l1) if self.puissance_l1 else None,
                        'L2': float(self.puissance_l2) if self.puissance_l2 else None,
                        'L3': float(self.puissance_l3) if self.puissance_l3 else None,
                        'totale': float(self.puissance_totale) if self.puissance_totale else None,
                    },
                    'reactive': {
                        'L1': float(self.puissance_reactive_l1) if self.puissance_reactive_l1 else None,
                        'L2': float(self.puissance_reactive_l2) if self.puissance_reactive_l2 else None,
                        'L3': float(self.puissance_reactive_l3) if self.puissance_reactive_l3 else None,
                        'totale': float(self.puissance_reactive_totale) if self.puissance_reactive_totale else None,
                    },
                    'apparente': {
                        'L1': float(self.puissance_apparente_l1) if self.puissance_apparente_l1 else None,
                        'L2': float(self.puissance_apparente_l2) if self.puissance_apparente_l2 else None,
                        'L3': float(self.puissance_apparente_l3) if self.puissance_apparente_l3 else None,
                        'totale': float(self.puissance_apparente_totale) if self.puissance_apparente_totale else None,
                    }
                },
                'facteurs_puissance': {
                    'L1': float(self.facteur_puissance_l1) if self.facteur_puissance_l1 else None,
                    'L2': float(self.facteur_puissance_l2) if self.facteur_puissance_l2 else None,
                    'L3': float(self.facteur_puissance_l3) if self.facteur_puissance_l3 else None,
                    'total': float(self.facteur_puissance_total) if self.facteur_puissance_total else None,
                },
                'energies': {
                    'L1': float(self.energie_l1) if self.energie_l1 else None,
                    'L2': float(self.energie_l2) if self.energie_l2 else None,
                    'L3': float(self.energie_l3) if self.energie_l3 else None,
                    'totale': float(self.energie_totale) if self.energie_totale else None,
                },
                'frequence': float(self.frequence) if self.frequence else None
            }
        
        # Ajouter calculs si demandés
        if include_calculs:
            data['calculs'] = {
                'tension_moyenne': self.get_tension_moyenne(),
                'courant_total': self.get_courant_total(),
                'puissance_totale_calculee': self.get_puissance_totale_calculee(),
                'facteur_puissance_moyen': self.get_facteur_puissance_moyen()
            }
            
            if self.is_triphase():
                data['calculs']['desequilibre_tension'] = self.calculer_desequilibre_tension()
                data['calculs']['desequilibre_courant'] = self.calculer_desequilibre_courant()
        
        # Ajouter anomalies si demandées
        if include_anomalies and seuils_appareil:
            data['anomalies'] = self.detecter_anomalies(seuils_appareil)
        
        return data
    
    # =================== MÉTHODES DE CLASSE ===================
    
    @classmethod
    def get_latest_by_device(cls, device_id, count=1):
        """Récupérer les dernières données d'un appareil"""
        return cls.query.filter_by(appareil_id=device_id)\
                       .order_by(cls.horodatage.desc())\
                       .limit(count).all()
    
    @classmethod
    def get_by_timerange(cls, device_id, start_time, end_time):
        """Récupérer les données dans une plage de temps"""
        return cls.query.filter(
            cls.appareil_id == device_id,
            cls.horodatage >= start_time,
            cls.horodatage <= end_time
        ).order_by(cls.horodatage.asc()).all()
    
    @classmethod
    def count_by_system_type(cls, client_id=None):
        """Compter les données par type de système"""
        query = cls.query
        if client_id:
            query = query.filter_by(client_id=client_id)
        
        return {
            'monophase': query.filter_by(type_systeme='monophase').count(),
            'triphase': query.filter_by(type_systeme='triphase').count(),
            'total': query.count()
        }