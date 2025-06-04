from app import db
from datetime import datetime
import uuid

class Device(db.Model):
    """Modèle pour les appareils IoT"""
    
    __tablename__ = 'devices'
    
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relations
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=False, index=True)
    site_id = db.Column(db.String(36), db.ForeignKey('sites.id'), nullable=False, index=True)
    
    # Lien avec Tuya (IMPORTANT)
    tuya_device_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    
    # Informations appareil
    nom_appareil = db.Column(db.String(255), nullable=False)
    type_appareil = db.Column(db.String(100), nullable=False)  # Ex: 'atorch_argp2ws'
    emplacement = db.Column(db.String(255), nullable=True)  # "Cuisine - Près frigo"
    
    # Configuration - ✅ Correction: utilisation de db.Float au lieu de db.Decimal
    seuil_tension_min = db.Column(db.Float, nullable=True, default=200.0)
    seuil_tension_max = db.Column(db.Float, nullable=True, default=250.0)
    seuil_courant_max = db.Column(db.Float, nullable=True, default=20.0)
    seuil_puissance_max = db.Column(db.Float, nullable=True, default=5000.0)
    
    # Métadonnées
    date_installation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    derniere_donnee = db.Column(db.DateTime, nullable=True)  # Dernière donnée reçue
    actif = db.Column(db.Boolean, default=True, nullable=False, index=True)
    en_ligne = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # Relations
    donnees = db.relationship('DeviceData', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    alertes = db.relationship('Alert', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    acces = db.relationship('DeviceAccess', backref='appareil', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Device {self.nom_appareil} ({self.tuya_device_id})>'
    
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
    
    def to_dict(self, include_stats=False):
        """Convertir en dictionnaire pour l'API"""
        data = {
            'id': self.id,
            'client_id': self.client_id,
            'site_id': self.site_id,
            'tuya_device_id': self.tuya_device_id,
            'nom_appareil': self.nom_appareil,
            'type_appareil': self.type_appareil,
            'emplacement': self.emplacement,
            'date_installation': self.date_installation.isoformat() if self.date_installation else None,
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
        
        if include_stats:
            data['nb_donnees'] = self.donnees.count()
            data['nb_alertes'] = self.alertes.filter_by(statut='nouvelle').count()
            
        return data