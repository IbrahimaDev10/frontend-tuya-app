from app import db
from datetime import datetime
import uuid

class Device(db.Model):
    """Modèle pour les appareils IoT avec support monophasé/triphasé"""
    
    __tablename__ = 'devices'
    
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relations
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=True, index=True)
    site_id = db.Column(db.String(36), db.ForeignKey('sites.id'), nullable=True, index=True)
    
    # Lien avec Tuya
    tuya_device_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    
    # Informations appareil
    nom_appareil = db.Column(db.String(255), nullable=False)
    type_appareil = db.Column(db.String(100), nullable=False)
    emplacement = db.Column(db.String(255), nullable=True)
    
    # ✅ NOUVEAU : TYPE DE SYSTÈME ÉLECTRIQUE
    type_systeme = db.Column(db.Enum('monophase', 'triphase', name='electrical_system_type'), 
                           nullable=False, default='monophase', index=True)
    
    # Statut d'assignation
    statut_assignation = db.Column(db.Enum('non_assigne', 'assigne', name='device_assignment_status'), 
                                  nullable=False, default='non_assigne', index=True)
    
    # =================== SEUILS MONOPHASÉS (existants) ===================
    seuil_tension_min = db.Column(db.Float, nullable=True, default=200.0)
    seuil_tension_max = db.Column(db.Float, nullable=True, default=250.0)
    seuil_courant_max = db.Column(db.Float, nullable=True, default=20.0)
    seuil_puissance_max = db.Column(db.Float, nullable=True, default=5000.0)
    
    # =================== NOUVEAUX SEUILS TRIPHASÉS ===================
    
    # Seuils par phase (si différents)
    seuil_tension_l1_min = db.Column(db.Float, nullable=True)
    seuil_tension_l1_max = db.Column(db.Float, nullable=True)
    seuil_tension_l2_min = db.Column(db.Float, nullable=True)
    seuil_tension_l2_max = db.Column(db.Float, nullable=True)
    seuil_tension_l3_min = db.Column(db.Float, nullable=True)
    seuil_tension_l3_max = db.Column(db.Float, nullable=True)
    
    seuil_courant_l1_max = db.Column(db.Float, nullable=True)
    seuil_courant_l2_max = db.Column(db.Float, nullable=True)
    seuil_courant_l3_max = db.Column(db.Float, nullable=True)
    
    # Seuils spécifiques triphasé
    seuil_desequilibre_tension = db.Column(db.Float, nullable=True, default=2.0)  # % max de déséquilibre
    seuil_desequilibre_courant = db.Column(db.Float, nullable=True, default=10.0)  # % max de déséquilibre
    seuil_facteur_puissance_min = db.Column(db.Float, nullable=True, default=0.85)  # Facteur de puissance minimum
    
    # Informations Tuya
    tuya_nom_original = db.Column(db.String(255), nullable=True)
    tuya_modele = db.Column(db.String(100), nullable=True)
    tuya_version_firmware = db.Column(db.String(50), nullable=True)
    
    # Métadonnées
    date_installation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_assignation = db.Column(db.DateTime, nullable=True)
    derniere_donnee = db.Column(db.DateTime, nullable=True)
    actif = db.Column(db.Boolean, default=True, nullable=False, index=True)
    en_ligne = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # Relations
    donnees = db.relationship('DeviceData', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    alertes = db.relationship('Alert', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    acces = db.relationship('DeviceAccess', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Device {self.nom_appareil} ({self.type_systeme}) - {self.statut_assignation}>'
    
    # =================== MÉTHODES SYSTÈME ÉLECTRIQUE ===================
    
    def is_monophase(self):
        """Vérifier si l'appareil est monophasé"""
        return self.type_systeme == 'monophase'
    
    def is_triphase(self):
        """Vérifier si l'appareil est triphasé"""
        return self.type_systeme == 'triphase'
    
    def set_as_monophase(self):
        """Configurer comme monophasé"""
        self.type_systeme = 'monophase'
        # Réinitialiser les seuils triphasés
        self._reset_triphasé_seuils()
    
    def set_as_triphase(self):
        """Configurer comme triphasé"""
        self.type_systeme = 'triphase'
        # Initialiser les seuils triphasés basés sur les monophasés
        self._init_triphasé_seuils()
    
    def _reset_triphasé_seuils(self):
        """Réinitialiser les seuils triphasés"""
        fields = [
            'seuil_tension_l1_min', 'seuil_tension_l1_max',
            'seuil_tension_l2_min', 'seuil_tension_l2_max', 
            'seuil_tension_l3_min', 'seuil_tension_l3_max',
            'seuil_courant_l1_max', 'seuil_courant_l2_max', 'seuil_courant_l3_max'
        ]
        for field in fields:
            setattr(self, field, None)
    
    def _init_triphasé_seuils(self):
        """Initialiser les seuils triphasés basés sur les seuils monophasés"""
        if self.seuil_tension_min:
            self.seuil_tension_l1_min = self.seuil_tension_l2_min = self.seuil_tension_l3_min = self.seuil_tension_min
        if self.seuil_tension_max:
            self.seuil_tension_l1_max = self.seuil_tension_l2_max = self.seuil_tension_l3_max = self.seuil_tension_max
        if self.seuil_courant_max:
            self.seuil_courant_l1_max = self.seuil_courant_l2_max = self.seuil_courant_l3_max = self.seuil_courant_max
    
    # =================== GESTION DES SEUILS INTELLIGENTE ===================
    
    def get_seuils_actifs(self):
        """Retourner les seuils actifs selon le type de système"""
        if self.is_monophase():
            return {
                'tension_min': self.seuil_tension_min,
                'tension_max': self.seuil_tension_max,
                'courant_max': self.seuil_courant_max,
                'puissance_max': self.seuil_puissance_max
            }
        else:  # Triphasé
            return {
                'tension_l1_min': self.seuil_tension_l1_min,
                'tension_l1_max': self.seuil_tension_l1_max,
                'tension_l2_min': self.seuil_tension_l2_min,
                'tension_l2_max': self.seuil_tension_l2_max,
                'tension_l3_min': self.seuil_tension_l3_min,
                'tension_l3_max': self.seuil_tension_l3_max,
                'courant_l1_max': self.seuil_courant_l1_max,
                'courant_l2_max': self.seuil_courant_l2_max,
                'courant_l3_max': self.seuil_courant_l3_max,
                'desequilibre_tension': self.seuil_desequilibre_tension,
                'desequilibre_courant': self.seuil_desequilibre_courant,
                'facteur_puissance_min': self.seuil_facteur_puissance_min
            }
    
    def set_seuils_uniformes_triphase(self, tension_min, tension_max, courant_max):
        """Définir les mêmes seuils pour les 3 phases"""
        if not self.is_triphase():
            return False, "L'appareil n'est pas configuré en triphasé"
        
        # Tensions
        self.seuil_tension_l1_min = self.seuil_tension_l2_min = self.seuil_tension_l3_min = tension_min
        self.seuil_tension_l1_max = self.seuil_tension_l2_max = self.seuil_tension_l3_max = tension_max
        
        # Courants
        self.seuil_courant_l1_max = self.seuil_courant_l2_max = self.seuil_courant_l3_max = courant_max
        
        return True, "Seuils triphasés uniformes définis"
    
    # =================== MÉTHODES D'ASSIGNATION (existantes) ===================
    
    def is_assigne(self):
        return self.statut_assignation == 'assigne' and self.client_id is not None
    
    def is_non_assigne(self):
        return self.statut_assignation == 'non_assigne' or self.client_id is None
    
    def assigner_a_client(self, client_id, site_id, utilisateur_assigneur_id=None):
        try:
            self.client_id = client_id
            self.site_id = site_id
            self.statut_assignation = 'assigne'
            self.date_assignation = datetime.utcnow()
            
            db.session.commit()
            return True, f"Appareil {self.nom_appareil} assigné avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de l'assignation: {str(e)}"
    
    def desassigner(self):
        try:
            self.client_id = None
            self.site_id = None
            self.statut_assignation = 'non_assigne'
            self.date_assignation = None
            
            db.session.commit()
            return True, f"Appareil {self.nom_appareil} désassigné avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de la désassignation: {str(e)}"
    
    def peut_etre_vu_par_utilisateur(self, utilisateur):
        if utilisateur.is_superadmin():
            return True
        if self.is_non_assigne():
            return False
        return self.client_id == utilisateur.client_id
    
    # =================== MÉTHODES EXISTANTES ===================
    
    def update_last_data_time(self):
        self.derniere_donnee = datetime.utcnow()
        self.en_ligne = True
        db.session.commit()
    
    def check_offline(self, timeout_minutes=5):
        if not self.derniere_donnee:
            return True
        
        timeout = datetime.utcnow() - self.derniere_donnee
        if timeout.total_seconds() > (timeout_minutes * 60):
            self.en_ligne = False
            db.session.commit()
            return True
        return False
    
    def update_from_tuya_data(self, tuya_data):
        try:
            if tuya_data.get('name'):
                self.tuya_nom_original = tuya_data['name']
            if tuya_data.get('model'):
                self.tuya_modele = tuya_data['model']
            if tuya_data.get('sw_ver'):
                self.tuya_version_firmware = tuya_data['sw_ver']
            
            if not self.nom_appareil or self.nom_appareil == self.tuya_nom_original:
                self.nom_appareil = tuya_data.get('name', self.tuya_device_id)
            
            self.en_ligne = tuya_data.get('online', False)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur mise à jour appareil depuis Tuya: {e}")
            return False
    
    def to_dict(self, include_stats=False, include_tuya_info=False, include_seuils_detail=False):
        """Convertir en dictionnaire pour l'API"""
        data = {
            'id': self.id,
            'client_id': self.client_id,
            'site_id': self.site_id,
            'tuya_device_id': self.tuya_device_id,
            'nom_appareil': self.nom_appareil,
            'type_appareil': self.type_appareil,
            'type_systeme': self.type_systeme,  # ✅ NOUVEAU
            'emplacement': self.emplacement,
            'statut_assignation': self.statut_assignation,
            'is_assigne': self.is_assigne(),
            'date_installation': self.date_installation.isoformat() if self.date_installation else None,
            'date_assignation': self.date_assignation.isoformat() if self.date_assignation else None,
            'derniere_donnee': self.derniere_donnee.isoformat() if self.derniere_donnee else None,
            'actif': self.actif,
            'en_ligne': self.en_ligne
        }
        
        # Seuils selon le type
        if include_seuils_detail:
            data['seuils'] = self.get_seuils_actifs()
        else:
            # Seuils de base pour compatibilité
            data['seuils'] = {
                'tension_min': float(self.seuil_tension_min) if self.seuil_tension_min else None,
                'tension_max': float(self.seuil_tension_max) if self.seuil_tension_max else None,
                'courant_max': float(self.seuil_courant_max) if self.seuil_courant_max else None,
                'puissance_max': float(self.seuil_puissance_max) if self.seuil_puissance_max else None
            }
        
        # Informations Tuya
        if include_tuya_info:
            data['tuya_info'] = {
                'nom_original': self.tuya_nom_original,
                'modele': self.tuya_modele,
                'version_firmware': self.tuya_version_firmware
            }
        
        # Statistiques
        if include_stats and self.is_assigne():
            data['nb_donnees'] = self.donnees.count()
            data['nb_alertes'] = self.alertes.filter_by(statut='nouvelle').count()
        
        # Informations client/site
        if self.is_assigne():
            try:
                if hasattr(self, 'client') and self.client:
                    data['client_nom'] = self.client.nom_entreprise
                if hasattr(self, 'site') and self.site:
                    data['site_nom'] = self.site.nom_site
            except:
                pass
            
        return data
    
    # =================== MÉTHODES DE CLASSE ===================
    
    @classmethod
    def get_non_assignes(cls):
        return cls.query.filter_by(statut_assignation='non_assigne').all()
    
    @classmethod
    def get_assignes_client(cls, client_id):
        return cls.query.filter_by(client_id=client_id, statut_assignation='assigne').all()
    
    @classmethod
    def get_by_tuya_id(cls, tuya_device_id):
        return cls.query.filter_by(tuya_device_id=tuya_device_id).first()
    
    @classmethod
    def count_by_status(cls):
        return {
            'non_assignes': cls.query.filter_by(statut_assignation='non_assigne').count(),
            'assignes': cls.query.filter_by(statut_assignation='assigne').count(),
            'total': cls.query.count()
        }
    
    @classmethod
    def count_by_system_type(cls):
        """✅ NOUVEAU : Statistiques par type de système"""
        return {
            'monophase': cls.query.filter_by(type_systeme='monophase').count(),
            'triphase': cls.query.filter_by(type_systeme='triphase').count(),
            'total': cls.query.count()
        }