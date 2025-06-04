from app import db
from datetime import datetime
import uuid

class DeviceAccess(db.Model):
    """Modèle pour gérer les permissions d'accès aux appareils"""
    
    __tablename__ = 'device_access'
    
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relations
    utilisateur_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    appareil_id = db.Column(db.String(36), db.ForeignKey('devices.id'), nullable=False, index=True)
    
    # Permissions
    peut_voir = db.Column(db.Boolean, default=True, nullable=False)  # Voir les données
    peut_controler = db.Column(db.Boolean, default=False, nullable=False)  # Allumer/éteindre
    peut_configurer = db.Column(db.Boolean, default=False, nullable=False)  # Modifier config
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    actif = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Index unique pour éviter les doublons
    __table_args__ = (
        db.UniqueConstraint('utilisateur_id', 'appareil_id', name='unique_user_device_access'),
    )
    
    def __repr__(self):
        return f'<DeviceAccess User:{self.utilisateur_id} Device:{self.appareil_id}>'
    
    def to_dict(self):
        """Convertir en dictionnaire pour l'API"""
        return {
            'id': self.id,
            'utilisateur_id': self.utilisateur_id,
            'appareil_id': self.appareil_id,
            'peut_voir': self.peut_voir,
            'peut_controler': self.peut_controler,
            'peut_configurer': self.peut_configurer,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'actif' : self.actif
        }   