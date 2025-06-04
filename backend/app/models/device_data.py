from app import db
from datetime import datetime
import uuid

class DeviceData(db.Model):
    """Modèle pour les données temps réel des appareils"""
    
    __tablename__ = 'device_data'
    
    # Clé primaire (auto-increment pour performance)
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    
    # Relations
    appareil_id = db.Column(db.String(36), db.ForeignKey('devices.id'), nullable=False, index=True)
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=False, index=True)  # Pour filtrage rapide
    
    # Horodatage
    horodatage = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Données électriques - ✅ Correction: utilisation de db.Float au lieu de db.Decimal
    tension = db.Column(db.Float, nullable=True)  # Volts (ex: 230.50)
    courant = db.Column(db.Float, nullable=True)  # Ampères (ex: 2.350)
    puissance = db.Column(db.Float, nullable=True)  # Watts (ex: 1250.75)
    energie = db.Column(db.Float, nullable=True)  # kWh (ex: 15.250)
    
    # Données environnementales - ✅ Correction: utilisation de db.Float au lieu de db.Decimal
    temperature = db.Column(db.Float, nullable=True)  # Celsius (ex: 25.50)
    humidite = db.Column(db.Float, nullable=True)  # % (ex: 65.25)
    
    # État de l'appareil
    etat_switch = db.Column(db.Boolean, nullable=True)  # Allumé/Éteint
    
    # Données brutes JSON (pour flexibilité)
    donnees_brutes = db.Column(db.JSON, nullable=True)
    
    # Index composé pour performance
    __table_args__ = (
        db.Index('idx_device_data_time', 'appareil_id', 'horodatage'),
        db.Index('idx_client_data_time', 'client_id', 'horodatage'),
    )
    
    def __repr__(self):
        return f'<DeviceData {self.appareil_id} @ {self.horodatage}>'
    
    def to_dict(self):
        """Convertir en dictionnaire pour l'API"""
        return {
            'id': self.id,
            'appareil_id': self.appareil_id,
            'horodatage': self.horodatage.isoformat() if self.horodatage else None,
            'tension': float(self.tension) if self.tension else None,
            'courant': float(self.courant) if self.courant else None,
            'puissance': float(self.puissance) if self.puissance else None,
            'energie': float(self.energie) if self.energie else None,
            'temperature': float(self.temperature) if self.temperature else None,
            'humidite': float(self.humidite) if self.humidite else None,
            'etat_switch': self.etat_switch,
            'donnees_brutes': self.donnees_brutes
        }