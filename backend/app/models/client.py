from app import db
from datetime import datetime
import uuid

class Client(db.Model):
    """Modèle pour les clients entreprises de SERTEC"""
    
    __tablename__ = 'clients'
    
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Informations entreprise
    nom_entreprise = db.Column(db.String(255), nullable=False, index=True)
    email_contact = db.Column(db.String(255), nullable=False, unique=True, index=True)
    telephone = db.Column(db.String(20), nullable=True)
    adresse = db.Column(db.Text, nullable=True)
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    actif = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Relations
    utilisateurs = db.relationship('User', backref='client', lazy='dynamic', cascade='all, delete-orphan')
    sites = db.relationship('Site', backref='client', lazy='dynamic', cascade='all, delete-orphan')
    appareils = db.relationship('Device', backref='client', lazy='dynamic', cascade='all, delete-orphan')
    donnees = db.relationship('DeviceData', backref='client', lazy='dynamic')
    alertes = db.relationship('Alert', backref='client', lazy='dynamic')
    
    def __repr__(self):
        return f'<Client {self.nom_entreprise}>'
    
    def to_dict(self):
        """Convertir en dictionnaire pour l'API"""
        return {
            'id': self.id,
            'nom_entreprise': self.nom_entreprise,
            'email_contact': self.email_contact,
            'telephone': self.telephone,
            'adresse': self.adresse,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'actif': self.actif,
            'nb_utilisateurs': self.utilisateurs.count(),
            'nb_sites': self.sites.count(),
            'nb_appareils': self.appareils.count()
        }