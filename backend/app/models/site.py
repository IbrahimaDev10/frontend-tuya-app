from app import db
from datetime import datetime
import uuid
import requests
from sqlalchemy.types import DECIMAL

class Site(db.Model):
    """Modèle pour les sites d'installation des appareils"""
    
    __tablename__ = 'sites'
    
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relation client
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=False, index=True)
    
    # Informations site
    nom_site = db.Column(db.String(255), nullable=False)
    adresse = db.Column(db.Text, nullable=False)
    
    # Coordonnées GPS (OPTIONNELLES - peuvent être NULL)
    latitude = db.Column(DECIMAL(10, 8), nullable=True)  # ✅ Correction ici
    longitude = db.Column(DECIMAL(11, 8), nullable=True)  # ✅ Correction ici
    
    # Informations géographiques alternatives
    ville = db.Column(db.String(100), nullable=True)
    quartier = db.Column(db.String(100), nullable=True)
    code_postal = db.Column(db.String(10), nullable=True)
    pays = db.Column(db.String(50), nullable=True, default='Sénégal')
    
    # Coordonnées trouvées automatiquement
    coordonnees_auto = db.Column(db.Boolean, default=False, nullable=False)  # Si trouvées par géocodage
    precision_gps = db.Column(db.Enum('exacte', 'approximative', 'inconnue', name='gps_precision'), 
                             default='inconnue', nullable=False)
    
    # Contact sur site
    contact_site = db.Column(db.String(255), nullable=True)
    telephone_site = db.Column(db.String(20), nullable=True)
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    actif = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Relations
    appareils = db.relationship('Device', backref='site', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Site {self.nom_site} - {self.ville or "Position inconnue"}>'
    
    def get_adresse_complete(self):
        """Retourne l'adresse complète formatée"""
        parts = [self.adresse]
        if self.quartier:
            parts.append(self.quartier)
        if self.ville:
            parts.append(self.ville)
        if self.code_postal:
            parts.append(self.code_postal)
        if self.pays:
            parts.append(self.pays)
        
        return ', '.join(filter(None, parts))
    
    def try_geocode_address(self):
        """Essayer de trouver les coordonnées automatiquement"""
        if self.latitude and self.longitude:
            return True  # Déjà renseignées
        
        try:
            # Option 1: Service de géocodage gratuit (Nominatim)
            address = self.get_adresse_complete()
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'sn'  # Limiter au Sénégal
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data:
                    self.latitude = float(data[0]['lat'])
                    self.longitude = float(data[0]['lon'])
                    self.coordonnees_auto = True
                    self.precision_gps = 'approximative'
                    db.session.commit()
                    return True
            
        except Exception as e:
            print(f"Erreur géocodage pour {self.nom_site}: {e}")
        
        return False
    
    def set_manual_coordinates(self, lat, lon, precision='exacte'):
        """Définir manuellement les coordonnées"""
        self.latitude = lat
        self.longitude = lon
        self.coordonnees_auto = False
        self.precision_gps = precision
        db.session.commit()
    
    def has_coordinates(self):
        """Vérifier si le site a des coordonnées"""
        return self.latitude is not None and self.longitude is not None
    
    def get_map_link(self):
        """Générer un lien Google Maps"""
        if self.has_coordinates():
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        else:
            # Utiliser l'adresse
            address = self.get_adresse_complete().replace(' ', '+')
            return f"https://www.google.com/maps/search/{address}"
    
    def to_dict(self, include_map_link=False):
        """Convertir en dictionnaire pour l'API"""
        data = {
            'id': self.id,
            'client_id': self.client_id,
            'nom_site': self.nom_site,
            'adresse': self.adresse,
            'adresse_complete': self.get_adresse_complete(),
            'ville': self.ville,
            'quartier': self.quartier,
            'code_postal': self.code_postal,
            'pays': self.pays,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'has_coordinates': self.has_coordinates(),
            'coordonnees_auto': self.coordonnees_auto,
            'precision_gps': self.precision_gps,
            'contact_site': self.contact_site,
            'telephone_site': self.telephone_site,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'actif': self.actif,
            'nb_appareils': self.appareils.count()
        }
        
        if include_map_link:
            data['map_link'] = self.get_map_link()
            
        return data