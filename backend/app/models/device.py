from app import db
from datetime import datetime
import uuid

class Device(db.Model):
    """Modèle pour les appareils IoT avec support assignation"""
    
    __tablename__ = 'devices'
    
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relations - ✅ MODIFIÉ : Nullable pour support non-assignés
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=True, index=True)
    site_id = db.Column(db.String(36), db.ForeignKey('sites.id'), nullable=True, index=True)
    
    # Lien avec Tuya (IMPORTANT)
    tuya_device_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    
    # Informations appareil
    nom_appareil = db.Column(db.String(255), nullable=False)
    type_appareil = db.Column(db.String(100), nullable=False)  # Ex: 'atorch_argp2ws'
    emplacement = db.Column(db.String(255), nullable=True)  # "Cuisine - Près frigo"
    
    # ✅ NOUVEAU : Statut d'assignation
    statut_assignation = db.Column(db.Enum('non_assigne', 'assigne', name='device_assignment_status'), 
                                  nullable=False, default='non_assigne', index=True)
    
    # Configuration - Seuils par défaut
    seuil_tension_min = db.Column(db.Float, nullable=True, default=200.0)
    seuil_tension_max = db.Column(db.Float, nullable=True, default=250.0)
    seuil_courant_max = db.Column(db.Float, nullable=True, default=20.0)
    seuil_puissance_max = db.Column(db.Float, nullable=True, default=5000.0)
    
    # ✅ NOUVEAU : Informations Tuya supplémentaires
    tuya_nom_original = db.Column(db.String(255), nullable=True)  # Nom dans Tuya
    tuya_modele = db.Column(db.String(100), nullable=True)  # Modèle de l'appareil
    tuya_version_firmware = db.Column(db.String(50), nullable=True)  # Version firmware
    
    # Métadonnées
    date_installation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_assignation = db.Column(db.DateTime, nullable=True)  # ✅ NOUVEAU : Quand assigné
    derniere_donnee = db.Column(db.DateTime, nullable=True)  # Dernière donnée reçue
    actif = db.Column(db.Boolean, default=True, nullable=False, index=True)
    en_ligne = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # Relations
    donnees = db.relationship('DeviceData', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    alertes = db.relationship('Alert', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    acces = db.relationship('DeviceAccess', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Device {self.nom_appareil} ({self.tuya_device_id}) - {self.statut_assignation}>'
    
    # =================== MÉTHODES D'ASSIGNATION ===================
    
    def is_assigne(self):
        """Vérifier si l'appareil est assigné"""
        return self.statut_assignation == 'assigne' and self.client_id is not None
    
    def is_non_assigne(self):
        """Vérifier si l'appareil n'est pas assigné"""
        return self.statut_assignation == 'non_assigne' or self.client_id is None
    
    def assigner_a_client(self, client_id, site_id, utilisateur_assigneur_id=None):
        """Assigner l'appareil à un client et site"""
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
        """Désassigner l'appareil (remettre non-assigné)"""
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
        """Vérifier si un utilisateur peut voir cet appareil"""
        # Superadmin voit tout
        if utilisateur.is_superadmin():
            return True
        
        # Appareil non-assigné : seul superadmin peut voir
        if self.is_non_assigne():
            return False
        
        # Appareil assigné : vérifier client
        return self.client_id == utilisateur.client_id
    
    # =================== MÉTHODES EXISTANTES MODIFIÉES ===================
    
    def update_last_data_time(self):
        """Mettre à jour l'heure de dernière donnée"""
        self.derniere_donnee = datetime.utcnow()
        self.en_ligne = True
        db.session.commit()
    
    def check_offline(self, timeout_minutes=5):
        """Vérifier si l'appareil est hors ligne"""
        if not self.derniere_donnee:
            return True
        
        timeout = datetime.utcnow() - self.derniere_donnee
        if timeout.total_seconds() > (timeout_minutes * 60):
            self.en_ligne = False
            db.session.commit()
            return True
        return False
    
    def update_from_tuya_data(self, tuya_data):
        """Mettre à jour les infos depuis les données Tuya"""
        try:
            # Mettre à jour les informations Tuya
            if tuya_data.get('name'):
                self.tuya_nom_original = tuya_data['name']
            
            if tuya_data.get('model'):
                self.tuya_modele = tuya_data['model']
            
            if tuya_data.get('sw_ver'):
                self.tuya_version_firmware = tuya_data['sw_ver']
            
            # Si pas de nom personnalisé, utiliser le nom Tuya
            if not self.nom_appareil or self.nom_appareil == self.tuya_nom_original:
                self.nom_appareil = tuya_data.get('name', self.tuya_device_id)
            
            # Mettre à jour le statut en ligne
            self.en_ligne = tuya_data.get('online', False)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur mise à jour appareil depuis Tuya: {e}")
            return False
    
    def to_dict(self, include_stats=False, include_tuya_info=False):
        """Convertir en dictionnaire pour l'API"""
        data = {
            'id': self.id,
            'client_id': self.client_id,
            'site_id': self.site_id,
            'tuya_device_id': self.tuya_device_id,
            'nom_appareil': self.nom_appareil,
            'type_appareil': self.type_appareil,
            'emplacement': self.emplacement,
            'statut_assignation': self.statut_assignation,  # ✅ NOUVEAU
            'is_assigne': self.is_assigne(),  # ✅ NOUVEAU
            'date_installation': self.date_installation.isoformat() if self.date_installation else None,
            'date_assignation': self.date_assignation.isoformat() if self.date_assignation else None,  # ✅ NOUVEAU
            'derniere_donnee': self.derniere_donnee.isoformat() if self.derniere_donnee else None,
            'actif': self.actif,
            'en_ligne': self.en_ligne,
            'seuils': {
                'tension_min': float(self.seuil_tension_min) if self.seuil_tension_min else None,
                'tension_max': float(self.seuil_tension_max) if self.seuil_tension_max else None,
                'courant_max': float(self.seuil_courant_max) if self.seuil_courant_max else None,
                'puissance_max': float(self.seuil_puissance_max) if self.seuil_puissance_max else None
            }
        }
        
        # ✅ NOUVEAU : Informations Tuya supplémentaires
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
        
        # Informations client/site si assigné
        if self.is_assigne():
            try:
                if hasattr(self, 'client') and self.client:
                    data['client_nom'] = self.client.nom_entreprise
                if hasattr(self, 'site') and self.site:
                    data['site_nom'] = self.site.nom_site
            except:
                pass  # Ignorer si relations pas chargées
            
        return data
    
    # =================== MÉTHODES DE CLASSE POUR REQUÊTES ===================
    
    @classmethod
    def get_non_assignes(cls):
        """Récupérer tous les appareils non-assignés"""
        return cls.query.filter_by(statut_assignation='non_assigne').all()
    
    @classmethod
    def get_assignes_client(cls, client_id):
        """Récupérer les appareils assignés à un client"""
        return cls.query.filter_by(client_id=client_id, statut_assignation='assigne').all()
    
    @classmethod
    def get_by_tuya_id(cls, tuya_device_id):
        """Récupérer un appareil par son ID Tuya"""
        return cls.query.filter_by(tuya_device_id=tuya_device_id).first()
    
    @classmethod
    def count_by_status(cls):
        """Compter les appareils par statut d'assignation"""
        return {
            'non_assignes': cls.query.filter_by(statut_assignation='non_assigne').count(),
            'assignes': cls.query.filter_by(statut_assignation='assigne').count(),
            'total': cls.query.count()
        }