from app import db
from datetime import datetime
import uuid
import bcrypt

class User(db.Model):
    """Modèle pour les utilisateurs (3 niveaux : superadmin, admin, user)"""
    
    __tablename__ = 'users'
    
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relation client (NULL pour superadmin)
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=True, index=True)
    
    # Informations utilisateur - SIMPLIFIÉ avec prénom/nom
    prenom = db.Column(db.String(100), nullable=False, index=True)
    nom = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    mot_de_passe_hash = db.Column(db.String(255), nullable=False)
    
    # Informations complémentaires
    telephone = db.Column(db.String(20), nullable=True)
    
    # Rôle : superadmin, admin, user
    role = db.Column(db.Enum('superadmin', 'admin', 'user', name='user_roles'),
                     nullable=False, default='user', index=True)
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    derniere_connexion = db.Column(db.DateTime, nullable=True)
    actif = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # ✅ CORRECTION : Utiliser back_populates au lieu de backref
    client = db.relationship('Client', back_populates='utilisateurs', lazy='select')
    
    # Relations autres
    acces_appareils = db.relationship('DeviceAccess', backref='utilisateur', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.prenom} {self.nom} ({self.role})>'
    
    @property
    def nom_complet(self):
        """Retourne le nom complet"""
        return f"{self.prenom} {self.nom}"
    
    def set_password(self, password):
        """Hacher et sauvegarder le mot de passe"""
        salt = bcrypt.gensalt()
        self.mot_de_passe_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        """Vérifier le mot de passe"""
        return bcrypt.checkpw(password.encode('utf-8'), self.mot_de_passe_hash.encode('utf-8'))
    
    def is_superadmin(self):
        """Vérifier si l'utilisateur est superadmin"""
        return self.role == 'superadmin'
    
    def is_admin(self):
        """Vérifier si l'utilisateur est admin ou superadmin"""
        return self.role in ['admin', 'superadmin']
    
    def can_access_client(self, client_id):
        """Vérifier si l'utilisateur peut accéder à un client"""
        if self.is_superadmin():
            return True
        return self.client_id == client_id
    
    def update_last_login(self):
        """Mettre à jour l'heure de dernière connexion"""
        self.derniere_connexion = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self, include_sensitive=False):
        """Convertir en dictionnaire pour l'API"""
        data = {
            'id': self.id,
            'prenom': self.prenom,
            'nom': self.nom,
            'nom_complet': self.nom_complet,
            'email': self.email,
            'telephone': self.telephone,
            'role': self.role,
            'client_id': self.client_id,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'derniere_connexion': self.derniere_connexion.isoformat() if self.derniere_connexion else None,
            'actif': self.actif
        }
        
        # Vérification sécurisée du client
        if include_sensitive and self.client_id:
            data['client_nom'] = self.client.nom_entreprise if self.client else None
        
        return data