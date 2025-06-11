from app import db
from datetime import datetime
import uuid
import requests
from math import radians, sin, cos, sqrt, atan2

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
    
    # Coordonnées GPS - ✅ CORRIGÉ : Utilisation de db.Numeric
    latitude = db.Column(db.Numeric(10, 8), nullable=True)   # -90.00000000 à 90.00000000
    longitude = db.Column(db.Numeric(11, 8), nullable=True)  # -180.00000000 à 180.00000000
    
    # Informations géographiques alternatives
    ville = db.Column(db.String(100), nullable=True)
    quartier = db.Column(db.String(100), nullable=True)
    code_postal = db.Column(db.String(10), nullable=True)
    pays = db.Column(db.String(50), nullable=True, default='Sénégal')
    
    # Coordonnées trouvées automatiquement
    coordonnees_auto = db.Column(db.Boolean, default=False, nullable=False)
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
    
    def set_coordinates(self, lat, lon, precision='exacte'):
        """Valider et définir les coordonnées avec vérifications complètes"""
        try:
            lat_float = float(lat)
            lon_float = float(lon)
            
            # Validation des limites géographiques mondiales
            if not (-90 <= lat_float <= 90):
                raise ValueError("Latitude doit être entre -90 et 90")
            if not (-180 <= lon_float <= 180):
                raise ValueError("Longitude doit être entre -180 et 180")
            
            # Validation spécifique Sénégal (alerte si en dehors)
            if not (12.0 <= lat_float <= 16.5 and -17.5 <= lon_float <= -11.0):
                print(f"⚠️ Coordonnées en dehors du Sénégal: {lat_float}, {lon_float}")
            
            self.latitude = lat_float
            self.longitude = lon_float
            self.precision_gps = precision
            self.coordonnees_auto = False  # Définies manuellement
            
            return True
            
        except (ValueError, TypeError) as e:
            print(f"Erreur coordonnées pour {self.nom_site}: {e}")
            return False
    
    def try_geocode_address(self):
        """Géocodage amélioré avec gestion d'erreurs robuste"""
        if self.has_coordinates():
            return True  # Déjà renseignées
        
        try:
            address = self.get_adresse_complete()
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'sn',  # Limiter au Sénégal
                'addressdetails': 1
            }
            
            # Headers pour être respectueux de l'API
            headers = {
                'User-Agent': 'SERTEC-IoT-Platform/1.0 (commercial@sertecingenierie.com)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    if self.set_coordinates(result['lat'], result['lon'], 'approximative'):
                        self.coordonnees_auto = True
                        db.session.commit()
                        print(f"✅ Géocodage réussi pour {self.nom_site}: {result['lat']}, {result['lon']}")
                        return True
            
            print(f"❌ Géocodage échoué pour {self.nom_site}: aucun résultat")
            return False
            
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout géocodage pour {self.nom_site}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"🌐 Erreur réseau géocodage pour {self.nom_site}: {e}")
            return False
        except Exception as e:
            print(f"💥 Erreur inattendue géocodage pour {self.nom_site}: {e}")
            return False
    
    def has_coordinates(self):
        """Vérifier si le site a des coordonnées valides"""
        return self.latitude is not None and self.longitude is not None
    
    def get_map_link(self):
        """Générer un lien Google Maps optimisé"""
        if self.has_coordinates():
            # Lien direct avec coordonnées
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}&z=16"
        else:
            # Recherche par adresse
            address = self.get_adresse_complete().replace(' ', '+').replace(',', '%2C')
            return f"https://www.google.com/maps/search/{address}"
    
    def distance_to(self, other_site):
        """Calculer la distance en km vers un autre site (formule de Haversine)"""
        if not (self.has_coordinates() and other_site.has_coordinates()):
            return None
        
        try:
            # Rayon de la Terre en km
            R = 6371
            
            # Conversion en radians
            lat1, lon1 = radians(float(self.latitude)), radians(float(self.longitude))
            lat2, lon2 = radians(float(other_site.latitude)), radians(float(other_site.longitude))
            
            # Différences
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            # Formule de Haversine
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            
            distance = R * c
            return round(distance, 2)  # Arrondi à 2 décimales
            
        except Exception as e:
            print(f"Erreur calcul distance: {e}")
            return None
    
    @classmethod
    def find_nearby_sites(cls, latitude, longitude, radius_km=10, client_id=None):
        """Trouver les sites dans un rayon donné (approximation simple)"""
        try:
            # Approximation : 1 degré ≈ 111 km
            lat_delta = radius_km / 111.0
            lon_delta = radius_km / (111.0 * cos(radians(float(latitude))))
            
            query = cls.query.filter(
                cls.latitude.between(latitude - lat_delta, latitude + lat_delta),
                cls.longitude.between(longitude - lon_delta, longitude + lon_delta),
                cls.actif == True,
                cls.latitude.isnot(None),
                cls.longitude.isnot(None)
            )
            
            if client_id:
                query = query.filter(cls.client_id == client_id)
            
            return query.all()
            
        except Exception as e:
            print(f"Erreur recherche sites proches: {e}")
            return []
    
    def get_stats(self):
        """Statistiques complètes du site"""
        try:
            stats = {
                'nb_appareils_total': self.appareils.count(),
                'nb_appareils_actifs': self.appareils.filter_by(actif=True).count(),
                'nb_appareils_en_ligne': self.appareils.filter_by(actif=True, en_ligne=True).count(),
                'types_appareils': {},
                'derniere_activite': None,
                'taux_disponibilite': 0
            }
            
            # Types d'appareils
            for device in self.appareils.filter_by(actif=True):
                device_type = device.type_appareil
                stats['types_appareils'][device_type] = stats['types_appareils'].get(device_type, 0) + 1
            
            # Dernière activité - Import Device évité avec self.appareils
            from app.models.device import Device
            latest_device = self.appareils.filter(
                Device.derniere_donnee.isnot(None),
                Device.actif == True
            ).order_by(Device.derniere_donnee.desc()).first()
            
            if latest_device and latest_device.derniere_donnee:
                stats['derniere_activite'] = latest_device.derniere_donnee.isoformat()
            
            # Taux de disponibilité
            if stats['nb_appareils_actifs'] > 0:
                stats['taux_disponibilite'] = round(
                    (stats['nb_appareils_en_ligne'] / stats['nb_appareils_actifs']) * 100, 2
                )
            
            return stats
            
        except Exception as e:
            print(f"Erreur calcul statistiques site {self.nom_site}: {e}")
            return {
                'nb_appareils_total': 0,
                'nb_appareils_actifs': 0,
                'nb_appareils_en_ligne': 0,
                'types_appareils': {},
                'derniere_activite': None,
                'taux_disponibilite': 0
            }
    
    def to_dict(self, include_map_link=False, include_stats=False, include_devices=False):
        """Convertir en dictionnaire pour l'API avec options flexibles"""
        try:
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
            
            # Ajout conditionnel du lien carte
            if include_map_link:
                data['map_link'] = self.get_map_link()
            
            # Ajout conditionnel des statistiques
            if include_stats:
                data['stats'] = self.get_stats()
            
            # Ajout conditionnel des appareils
            if include_devices:
                data['appareils'] = [device.to_dict() for device in self.appareils.filter_by(actif=True)]
            
            # Ajouter le nom du client si disponible
            try:
                if hasattr(self, 'client') and self.client:
                    data['client_nom'] = self.client.nom_entreprise
            except:
                pass  # Ignorer si pas de relation client chargée
            
            return data
            
        except Exception as e:
            print(f"Erreur to_dict pour site {self.nom_site}: {e}")
            # Retourner au minimum les données de base
            return {
                'id': self.id,
                'client_id': self.client_id,
                'nom_site': self.nom_site,
                'adresse': self.adresse,
                'actif': self.actif,
                'error': f"Erreur génération données: {str(e)}"
            }