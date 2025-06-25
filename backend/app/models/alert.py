from app import db
from datetime import datetime
import uuid

class Alert(db.Model):
    """Modèle pour les alertes et notifications (monophasé et triphasé)"""
    
    __tablename__ = 'alerts'
    
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relations
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=False, index=True)
    appareil_id = db.Column(db.String(36), db.ForeignKey('devices.id'), nullable=False, index=True)
    
    # ✅ NOUVEAU : Type de système concerné
    type_systeme = db.Column(db.Enum('monophase', 'triphase', name='system_type_alert'), 
                           nullable=False, default='monophase', index=True)
    
    # Type d'alerte étendu pour le triphasé
    type_alerte = db.Column(db.Enum(
        # Alertes communes
        'seuil_depasse', 'hors_ligne', 'erreur_communication', 
        'consommation_anormale', 'temperature_haute', 'autre',
        # ✅ NOUVELLES ALERTES TRIPHASÉES
        'desequilibre_tension', 'desequilibre_courant', 'facteur_puissance_faible',
        'perte_phase', 'inversion_phase', 'harmoniques_elevees',
        'surtension_composee', 'defaut_neutre',
        name='alert_types_extended'
    ), nullable=False, index=True)
    
    # Gravité
    gravite = db.Column(db.Enum('info', 'warning', 'critique', name='alert_severity'), 
                       nullable=False, default='info', index=True)
    
    # Contenu
    titre = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # ✅ NOUVEAU : Phase concernée (pour alertes triphasées)
    phase_concernee = db.Column(db.Enum('L1', 'L2', 'L3', 'neutre', 'toutes', name='phase_type'), 
                               nullable=True, index=True)
    
    # Valeurs pour contexte
    valeur_mesuree = db.Column(db.Float, nullable=True)
    valeur_seuil = db.Column(db.Float, nullable=True)
    unite = db.Column(db.String(10), nullable=True)  # V, A, W, °C, %, etc.
    
    # ✅ NOUVEAUX : Valeurs triphasées pour contexte complet
    valeurs_phases = db.Column(db.JSON, nullable=True)  # {'L1': 230, 'L2': 225, 'L3': 235}
    seuils_phases = db.Column(db.JSON, nullable=True)   # {'L1_max': 240, 'L2_max': 240, 'L3_max': 240}
    
    # État
    statut = db.Column(db.Enum('nouvelle', 'vue', 'resolue', name='alert_status'), 
                      nullable=False, default='nouvelle', index=True)
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    date_resolution = db.Column(db.DateTime, nullable=True)
    resolu_par = db.Column(db.String(36), nullable=True)  # ID utilisateur
    
    # ✅ NOUVEAU : Priorité pour tri intelligent
    priorite = db.Column(db.Integer, nullable=False, default=1, index=True)  # 1-10, 10 = urgent
    
    def __repr__(self):
        return f'<Alert {self.type_alerte} ({self.type_systeme}) - {self.gravite}>'
    
    # =================== MÉTHODES SPÉCIFIQUES TRIPHASÉ ===================
    
    def is_alerte_triphase(self):
        """Vérifier si c'est une alerte spécifique au triphasé"""
        alertes_triphase = [
            'desequilibre_tension', 'desequilibre_courant', 'facteur_puissance_faible',
            'perte_phase', 'inversion_phase', 'harmoniques_elevees',
            'surtension_composee', 'defaut_neutre'
        ]
        return self.type_alerte in alertes_triphase
    
    def set_valeurs_triphase(self, valeurs_l1_l2_l3, seuils=None):
        """Définir les valeurs des 3 phases"""
        if isinstance(valeurs_l1_l2_l3, (list, tuple)) and len(valeurs_l1_l2_l3) == 3:
            self.valeurs_phases = {
                'L1': valeurs_l1_l2_l3[0],
                'L2': valeurs_l1_l2_l3[1],
                'L3': valeurs_l1_l2_l3[2]
            }
        elif isinstance(valeurs_l1_l2_l3, dict):
            self.valeurs_phases = valeurs_l1_l2_l3
        
        if seuils:
            self.seuils_phases = seuils
    
    def get_message_detaille(self):
        """Générer un message détaillé selon le type d'alerte"""
        if not self.is_alerte_triphase() or not self.valeurs_phases:
            return self.message
        
        base_msg = self.message
        
        if self.type_alerte == 'desequilibre_tension':
            return f"{base_msg}. Tensions: L1={self.valeurs_phases.get('L1')}V, L2={self.valeurs_phases.get('L2')}V, L3={self.valeurs_phases.get('L3')}V"
        
        elif self.type_alerte == 'desequilibre_courant':
            return f"{base_msg}. Courants: L1={self.valeurs_phases.get('L1')}A, L2={self.valeurs_phases.get('L2')}A, L3={self.valeurs_phases.get('L3')}A"
        
        elif self.type_alerte == 'perte_phase':
            phases_perdues = [p for p, v in self.valeurs_phases.items() if v is None or v == 0]
            return f"{base_msg}. Phase(s) perdue(s): {', '.join(phases_perdues)}"
        
        return base_msg
    
    def calculer_priorite_auto(self):
        """Calculer automatiquement la priorité selon le type et la gravité"""
        priorite_base = {
            'info': 1,
            'warning': 5,
            'critique': 8
        }.get(self.gravite, 1)
        
        # Bonus pour certains types d'alertes critiques
        bonus_type = {
            'perte_phase': +2,
            'surtension_composee': +2,
            'defaut_neutre': +1,
            'hors_ligne': +1,
            'desequilibre_tension': +1 if self.valeur_mesuree and self.valeur_mesuree > 5 else 0,
            'desequilibre_courant': +1 if self.valeur_mesuree and self.valeur_mesuree > 15 else 0
        }.get(self.type_alerte, 0)
        
        self.priorite = min(10, priorite_base + bonus_type)
    
    # =================== MÉTHODES EXISTANTES AMÉLIORÉES ===================
    
    def mark_as_seen(self):
        """Marquer l'alerte comme vue"""
        if self.statut == 'nouvelle':
            self.statut = 'vue'
            db.session.commit()
    
    def resolve(self, user_id=None):
        """Résoudre l'alerte"""
        self.statut = 'resolue'
        self.date_resolution = datetime.utcnow()
        if user_id:
            self.resolu_par = user_id
        db.session.commit()
    
    def to_dict(self, include_details=False):
        """Convertir en dictionnaire pour l'API"""
        data = {
            'id': self.id,
            'client_id': self.client_id,
            'appareil_id': self.appareil_id,
            'type_systeme': self.type_systeme,  # ✅ NOUVEAU
            'type_alerte': self.type_alerte,
            'gravite': self.gravite,
            'titre': self.titre,
            'message': self.message,
            'phase_concernee': self.phase_concernee,  # ✅ NOUVEAU
            'valeur_mesuree': float(self.valeur_mesuree) if self.valeur_mesuree else None,
            'valeur_seuil': float(self.valeur_seuil) if self.valeur_seuil else None,
            'unite': self.unite,
            'statut': self.statut,
            'priorite': self.priorite,  # ✅ NOUVEAU
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'date_resolution': self.date_resolution.isoformat() if self.date_resolution else None,
            'resolu_par': self.resolu_par,
            'is_alerte_triphase': self.is_alerte_triphase()  # ✅ NOUVEAU
        }
        
        # Détails supplémentaires si demandés
        if include_details:
            data['message_detaille'] = self.get_message_detaille()
            data['valeurs_phases'] = self.valeurs_phases
            data['seuils_phases'] = self.seuils_phases
        
        return data
    
    # =================== MÉTHODES DE CLASSE ÉTENDUES ===================
    
    @classmethod
    def create_alerte_monophase(cls, client_id, appareil_id, type_alerte, gravite, titre, message, 
                               valeur=None, seuil=None, unite=None):
        """Créer une alerte monophasée"""
        alerte = cls(
            client_id=client_id,
            appareil_id=appareil_id,
            type_systeme='monophase',
            type_alerte=type_alerte,
            gravite=gravite,
            titre=titre,
            message=message,
            valeur_mesuree=valeur,
            valeur_seuil=seuil,
            unite=unite
        )
        alerte.calculer_priorite_auto()
        
        try:
            db.session.add(alerte)
            db.session.commit()
            return alerte
        except Exception as e:
            db.session.rollback()
            print(f"Erreur création alerte monophasé: {e}")
            return None
    
    @classmethod
    def create_alerte_triphase(cls, client_id, appareil_id, type_alerte, gravite, titre, message,
                              phase_concernee=None, valeurs_phases=None, seuils_phases=None, 
                              valeur_principale=None, seuil_principal=None, unite=None):
        """Créer une alerte triphasée"""
        alerte = cls(
            client_id=client_id,
            appareil_id=appareil_id,
            type_systeme='triphase',
            type_alerte=type_alerte,
            gravite=gravite,
            titre=titre,
            message=message,
            phase_concernee=phase_concernee,
            valeur_mesuree=valeur_principale,
            valeur_seuil=seuil_principal,
            unite=unite,
            valeurs_phases=valeurs_phases,
            seuils_phases=seuils_phases
        )
        alerte.calculer_priorite_auto()
        
        try:
            db.session.add(alerte)
            db.session.commit()
            return alerte
        except Exception as e:
            db.session.rollback()
            print(f"Erreur création alerte triphasé: {e}")
            return None
    
    @classmethod
    def create_alerte_desequilibre_tension(cls, client_id, appareil_id, pourcentage_desequilibre, 
                                          seuil_max, tensions_phases):
        """Créer une alerte spécifique de déséquilibre de tension"""
        gravite = 'critique' if pourcentage_desequilibre > 5 else 'warning'
        
        return cls.create_alerte_triphase(
            client_id=client_id,
            appareil_id=appareil_id,
            type_alerte='desequilibre_tension',
            gravite=gravite,
            titre=f'Déséquilibre de tension détecté',
            message=f'Déséquilibre de {pourcentage_desequilibre}% dépasse le seuil de {seuil_max}%',
            phase_concernee='toutes',
            valeurs_phases=tensions_phases,
            valeur_principale=pourcentage_desequilibre,
            seuil_principal=seuil_max,
            unite='%'
        )
    
    @classmethod
    def create_alerte_desequilibre_courant(cls, client_id, appareil_id, pourcentage_desequilibre, 
                                          seuil_max, courants_phases):
        """Créer une alerte spécifique de déséquilibre de courant"""
        gravite = 'critique' if pourcentage_desequilibre > 20 else 'warning'
        
        return cls.create_alerte_triphase(
            client_id=client_id,
            appareil_id=appareil_id,
            type_alerte='desequilibre_courant',
            gravite=gravite,
            titre=f'Déséquilibre de courant détecté',
            message=f'Déséquilibre de {pourcentage_desequilibre}% dépasse le seuil de {seuil_max}%',
            phase_concernee='toutes',
            valeurs_phases=courants_phases,
            valeur_principale=pourcentage_desequilibre,
            seuil_principal=seuil_max,
            unite='%'
        )
    
    @classmethod
    def create_alerte_perte_phase(cls, client_id, appareil_id, phase_perdue, tensions_phases):
        """Créer une alerte de perte de phase"""
        return cls.create_alerte_triphase(
            client_id=client_id,
            appareil_id=appareil_id,
            type_alerte='perte_phase',
            gravite='critique',
            titre=f'Perte de phase {phase_perdue}',
            message=f'La phase {phase_perdue} a été perdue ou présente une tension nulle',
            phase_concernee=phase_perdue,
            valeurs_phases=tensions_phases
        )
    
    @classmethod
    def create_alerte_facteur_puissance(cls, client_id, appareil_id, facteur_puissance, 
                                       seuil_min, phase_concernee=None):
        """Créer une alerte de facteur de puissance faible"""
        return cls.create_alerte_triphase(
            client_id=client_id,
            appareil_id=appareil_id,
            type_alerte='facteur_puissance_faible',
            gravite='info',
            titre=f'Facteur de puissance faible',
            message=f'Facteur de puissance de {facteur_puissance} inférieur au seuil de {seuil_min}',
            phase_concernee=phase_concernee or 'toutes',
            valeur_principale=facteur_puissance,
            seuil_principal=seuil_min
        )
    
    @classmethod
    def get_alertes_actives(cls, client_id=None, appareil_id=None, type_systeme=None):
        """Récupérer les alertes actives avec filtres"""
        query = cls.query.filter(cls.statut.in_(['nouvelle', 'vue']))
        
        if client_id:
            query = query.filter_by(client_id=client_id)
        if appareil_id:
            query = query.filter_by(appareil_id=appareil_id)
        if type_systeme:
            query = query.filter_by(type_systeme=type_systeme)
        
        return query.order_by(cls.priorite.desc(), cls.date_creation.desc()).all()
    
    @classmethod
    def get_alertes_critiques(cls, client_id=None, hours_back=24):
        """Récupérer les alertes critiques récentes"""
        from datetime import timedelta
        
        since = datetime.utcnow() - timedelta(hours=hours_back)
        query = cls.query.filter(
            cls.gravite == 'critique',
            cls.date_creation >= since
        )
        
        if client_id:
            query = query.filter_by(client_id=client_id)
        
        return query.order_by(cls.priorite.desc(), cls.date_creation.desc()).all()
    
    @classmethod
    def get_statistiques_alertes(cls, client_id=None, days_back=30):
        """Statistiques des alertes par type et gravité"""
        from datetime import timedelta
        
        since = datetime.utcnow() - timedelta(days=days_back)
        query = cls.query.filter(cls.date_creation >= since)
        
        if client_id:
            query = query.filter_by(client_id=client_id)
        
        alertes = query.all()
        
        stats = {
            'total': len(alertes),
            'par_gravite': {'info': 0, 'warning': 0, 'critique': 0},
            'par_type_systeme': {'monophase': 0, 'triphase': 0},
            'par_statut': {'nouvelle': 0, 'vue': 0, 'resolue': 0},
            'types_plus_frequents': {},
            'alertes_triphase_specifiques': 0
        }
        
        for alerte in alertes:
            # Par gravité
            stats['par_gravite'][alerte.gravite] += 1
            
            # Par type de système
            stats['par_type_systeme'][alerte.type_systeme] += 1
            
            # Par statut
            stats['par_statut'][alerte.statut] += 1
            
            # Types les plus fréquents
            if alerte.type_alerte not in stats['types_plus_frequents']:
                stats['types_plus_frequents'][alerte.type_alerte] = 0
            stats['types_plus_frequents'][alerte.type_alerte] += 1
            
            # Alertes spécifiques triphasé
            if alerte.is_alerte_triphase():
                stats['alertes_triphase_specifiques'] += 1
        
        # Trier les types par fréquence
        stats['types_plus_frequents'] = dict(
            sorted(stats['types_plus_frequents'].items(), 
                  key=lambda x: x[1], reverse=True)
        )
        
        return stats
    
    @classmethod
    def nettoyer_alertes_anciennes(cls, days_to_keep=90):
        """Nettoyer les alertes résolues anciennes"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        try:
            alertes_supprimees = cls.query.filter(
                cls.statut == 'resolue',
                cls.date_resolution < cutoff_date
            ).count()
            
            cls.query.filter(
                cls.statut == 'resolue',
                cls.date_resolution < cutoff_date
            ).delete()
            
            db.session.commit()
            return alertes_supprimees
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur nettoyage alertes: {e}")
            return 0
    
    @classmethod
    def count_by_priority(cls, client_id=None):
        """Compter les alertes par priorité"""
        query = cls.query.filter(cls.statut.in_(['nouvelle', 'vue']))
        
        if client_id:
            query = query.filter_by(client_id=client_id)
        
        return {
            'urgent': query.filter(cls.priorite >= 8).count(),
            'elevee': query.filter(cls.priorite.between(5, 7)).count(),
            'normale': query.filter(cls.priorite.between(1, 4)).count(),
            'total': query.count()
        }