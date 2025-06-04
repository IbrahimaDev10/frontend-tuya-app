from app import db
from datetime import datetime
import uuid

class Alert(db.Model):
    """Modèle pour les alertes et notifications"""
    
    __tablename__ = 'alerts'
    
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relations
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=False, index=True)
    appareil_id = db.Column(db.String(36), db.ForeignKey('devices.id'), nullable=False, index=True)
    
    # Type d'alerte
    type_alerte = db.Column(db.Enum(
        'seuil_depasse', 'hors_ligne', 'erreur_communication', 
        'consommation_anormale', 'temperature_haute', 'autre',
        name='alert_types'
    ), nullable=False, index=True)
    
    # Gravité
    gravite = db.Column(db.Enum('info', 'warning', 'critique', name='alert_severity'), 
                       nullable=False, default='info', index=True)
    
    # Contenu
    titre = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Valeurs pour contexte - ✅ Correction: utilisation de db.Float au lieu de db.Decimal
    valeur_mesuree = db.Column(db.Float, nullable=True)
    valeur_seuil = db.Column(db.Float, nullable=True)
    unite = db.Column(db.String(10), nullable=True)  # V, A, W, °C, etc.
    
    # État
    statut = db.Column(db.Enum('nouvelle', 'vue', 'resolue', name='alert_status'), 
                      nullable=False, default='nouvelle', index=True)
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    date_resolution = db.Column(db.DateTime, nullable=True)
    resolu_par = db.Column(db.String(36), nullable=True)  # ID utilisateur
    
    def __repr__(self):
        return f'<Alert {self.type_alerte} - {self.gravite}>'
    
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
    
    def to_dict(self):
        """Convertir en dictionnaire pour l'API"""
        return {
            'id': self.id,
            'client_id': self.client_id,
            'appareil_id': self.appareil_id,
            'type_alerte': self.type_alerte,
            'gravite': self.gravite,
            'titre': self.titre,
            'message': self.message,
            'valeur_mesuree': float(self.valeur_mesuree) if self.valeur_mesuree else None,
            'valeur_seuil': float(self.valeur_seuil) if self.valeur_seuil else None,
            'unite': self.unite,
            'statut': self.statut,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'date_resolution': self.date_resolution.isoformat() if self.date_resolution else None,
            'resolu_par': self.resolu_par
        }