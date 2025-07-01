from app import db
from datetime import datetime
import uuid

class ProtectionEvent(db.Model):
    """Modèle pour l'historique des événements de protection automatique"""
    
    __tablename__ = 'protection_events'
    
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relations
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=False, index=True)
    appareil_id = db.Column(db.String(36), db.ForeignKey('devices.id'), nullable=False, index=True)
    
    # Type d'événement de protection
    type_protection = db.Column(db.Enum(
        'courant_depasse', 'puissance_depassee', 'temperature_haute', 
        'tension_anormale', 'desequilibre_tension', 'desequilibre_courant',
        'perte_phase', 'facteur_puissance_faible', 'autre',
        name='protection_event_types'
    ), nullable=False, index=True)
    
    # Type de système concerné
    type_systeme = db.Column(db.Enum('monophase', 'triphase', name='system_type_protection'), 
                           nullable=False, default='monophase', index=True)
    
    # Phase concernée (pour triphasé)
    phase_concernee = db.Column(db.Enum('L1', 'L2', 'L3', 'neutre', 'toutes', name='phase_protection'), 
                               nullable=True)
    
    # Action effectuée
    action_effectuee = db.Column(db.Enum(
        'arret_appareil', 'reduction_puissance', 'alerte_envoyee', 
        'redemarrage_auto', 'mode_securite', 'aucune_action',
        name='protection_actions'
    ), nullable=False, default='alerte_envoyee')
    
    # État avant/après
    etat_avant = db.Column(db.String(20), nullable=True)  # 'on', 'off', 'standby'
    etat_apres = db.Column(db.String(20), nullable=True)
    
    # Valeurs mesurées au moment du déclenchement
    valeur_declenchement = db.Column(db.Float, nullable=True)
    valeur_seuil = db.Column(db.Float, nullable=True)
    unite_mesure = db.Column(db.String(10), nullable=True)  # A, V, W, °C, %
    
    # Valeurs triphasées au moment du déclenchement (JSON)
    valeurs_phases = db.Column(db.JSON, nullable=True)
    # Structure: {
    #   "tensions": {"L1": 230, "L2": 225, "L3": 235},
    #   "courants": {"L1": 15.5, "L2": 16.2, "L3": 14.8},
    #   "puissances": {"L1": 3565, "L2": 3645, "L3": 3478}
    # }
    
    # Métadonnées
    timestamp_declenchement = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    timestamp_resolution = db.Column(db.DateTime, nullable=True)
    
    # Statut de l'événement
    statut = db.Column(db.Enum(
        'en_cours', 'resolu_auto', 'resolu_manuel', 'ignore', 'erreur',
        name='protection_event_status'
    ), nullable=False, default='en_cours', index=True)
    
    # Résolution
    resolu_par = db.Column(db.String(36), nullable=True)  # ID utilisateur si résolution manuelle
    methode_resolution = db.Column(db.String(100), nullable=True)  # 'auto_restart', 'manual_intervention', etc.
    
    # Durée de l'événement (calculée)
    duree_minutes = db.Column(db.Float, nullable=True)
    
    # Configuration de protection active au moment du déclenchement
    config_protection = db.Column(db.JSON, nullable=True)
    
    # Notes et détails supplémentaires
    description = db.Column(db.Text, nullable=True)
    details_techniques = db.Column(db.JSON, nullable=True)
    
    # Compteur de récurrence (si même type d'événement se répète)
    occurrence_count = db.Column(db.Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f'<ProtectionEvent {self.type_protection} ({self.type_systeme}) @ {self.timestamp_declenchement}>'
    
    # =================== MÉTHODES SPÉCIFIQUES ===================
    
    def marquer_resolu(self, methode='auto_restart', user_id=None, description_resolution=None):
        """Marquer l'événement comme résolu"""
        try:
            self.timestamp_resolution = datetime.utcnow()
            self.statut = 'resolu_auto' if not user_id else 'resolu_manuel'
            self.methode_resolution = methode
            self.resolu_par = user_id
            
            # Calculer la durée
            if self.timestamp_declenchement:
                duree = self.timestamp_resolution - self.timestamp_declenchement
                self.duree_minutes = round(duree.total_seconds() / 60, 2)
            
            if description_resolution:
                self.description = (self.description or '') + f"\nRésolution: {description_resolution}"
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur marquage résolu: {e}")
            return False
    
    def incrementer_occurrence(self):
        """Incrémenter le compteur d'occurrence pour événements répétitifs"""
        try:
            self.occurrence_count += 1
            self.timestamp_declenchement = datetime.utcnow()  # Mettre à jour le timestamp
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    def get_gravite(self):
        """Déterminer la gravité selon le type de protection"""
        gravites_critiques = [
            'perte_phase', 'temperature_haute', 'courant_depasse'
        ]
        gravites_warning = [
            'desequilibre_tension', 'desequilibre_courant', 'facteur_puissance_faible'
        ]
        
        if self.type_protection in gravites_critiques:
            return 'critique'
        elif self.type_protection in gravites_warning:
            return 'warning'
        else:
            return 'info'
    
    def get_message_descriptif(self):
        """Générer un message descriptif de l'événement"""
        base_messages = {
            'courant_depasse': f"Courant de {self.valeur_declenchement}{self.unite_mesure} dépasse le seuil de {self.valeur_seuil}{self.unite_mesure}",
            'puissance_depassee': f"Puissance de {self.valeur_declenchement}{self.unite_mesure} dépasse le seuil de {self.valeur_seuil}{self.unite_mesure}",
            'temperature_haute': f"Température de {self.valeur_declenchement}°C dépasse le seuil de {self.valeur_seuil}°C",
            'desequilibre_tension': f"Déséquilibre de tension de {self.valeur_declenchement}% dépasse le seuil de {self.valeur_seuil}%",
            'desequilibre_courant': f"Déséquilibre de courant de {self.valeur_declenchement}% dépasse le seuil de {self.valeur_seuil}%",
            'perte_phase': f"Perte de phase détectée sur {self.phase_concernee}",
            'facteur_puissance_faible': f"Facteur de puissance de {self.valeur_declenchement} inférieur au seuil de {self.valeur_seuil}"
        }
        
        message = base_messages.get(self.type_protection, f"Événement de protection: {self.type_protection}")
        
        if self.occurrence_count > 1:
            message += f" (Occurrence #{self.occurrence_count})"
        
        if self.action_effectuee != 'aucune_action':
            message += f". Action: {self.action_effectuee.replace('_', ' ')}"
        
        return message
    
    def to_dict(self, include_details=False):
        """Convertir en dictionnaire pour l'API"""
        data = {
            'id': self.id,
            'client_id': self.client_id,
            'appareil_id': self.appareil_id,
            'type_protection': self.type_protection,
            'type_systeme': self.type_systeme,
            'phase_concernee': self.phase_concernee,
            'action_effectuee': self.action_effectuee,
            'etat_avant': self.etat_avant,
            'etat_apres': self.etat_apres,
            'valeur_declenchement': float(self.valeur_declenchement) if self.valeur_declenchement else None,
            'valeur_seuil': float(self.valeur_seuil) if self.valeur_seuil else None,
            'unite_mesure': self.unite_mesure,
            'timestamp_declenchement': self.timestamp_declenchement.isoformat() if self.timestamp_declenchement else None,
            'timestamp_resolution': self.timestamp_resolution.isoformat() if self.timestamp_resolution else None,
            'statut': self.statut,
            'resolu_par': self.resolu_par,
            'methode_resolution': self.methode_resolution,
            'duree_minutes': self.duree_minutes,
            'occurrence_count': self.occurrence_count,
            'gravite': self.get_gravite(),
            'message_descriptif': self.get_message_descriptif()
        }
        
        if include_details:
            data.update({
                'valeurs_phases': self.valeurs_phases,
                'config_protection': self.config_protection,
                'description': self.description,
                'details_techniques': self.details_techniques
            })
        
        return data
    
    # =================== MÉTHODES DE CLASSE ===================
    
    @classmethod
    def creer_evenement_protection(cls, client_id, appareil_id, type_protection, action_effectuee,
                                  valeur_declenchement=None, valeur_seuil=None, unite_mesure=None,
                                  type_systeme='monophase', phase_concernee=None, valeurs_phases=None,
                                  etat_avant=None, etat_apres=None, config_protection=None):
        """Créer un nouvel événement de protection"""
        try:
            # Vérifier s'il y a un événement similaire récent non résolu
            recent_event = cls.query.filter(
                cls.appareil_id == appareil_id,
                cls.type_protection == type_protection,
                cls.statut == 'en_cours',
                cls.timestamp_declenchement >= datetime.utcnow() - timedelta(minutes=5)
            ).first()
            
            if recent_event:
                # Incrémenter l'occurrence au lieu de créer un nouvel événement
                recent_event.incrementer_occurrence()
                return recent_event
            
            # Créer un nouvel événement
            event = cls(
                client_id=client_id,
                appareil_id=appareil_id,
                type_protection=type_protection,
                type_systeme=type_systeme,
                phase_concernee=phase_concernee,
                action_effectuee=action_effectuee,
                etat_avant=etat_avant,
                etat_apres=etat_apres,
                valeur_declenchement=valeur_declenchement,
                valeur_seuil=valeur_seuil,
                unite_mesure=unite_mesure,
                valeurs_phases=valeurs_phases,
                config_protection=config_protection
            )
            
            db.session.add(event)
            db.session.commit()
            return event
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur création événement protection: {e}")
            return None
    
    @classmethod
    def get_evenements_actifs(cls, client_id=None, appareil_id=None):
        """Récupérer les événements de protection en cours"""
        query = cls.query.filter_by(statut='en_cours')
        
        if client_id:
            query = query.filter_by(client_id=client_id)
        if appareil_id:
            query = query.filter_by(appareil_id=appareil_id)
        
        return query.order_by(cls.timestamp_declenchement.desc()).all()
    
    @classmethod
    def get_historique_appareil(cls, appareil_id, limit=50):
        """Récupérer l'historique des événements de protection d'un appareil"""
        return cls.query.filter_by(appareil_id=appareil_id)\
                       .order_by(cls.timestamp_declenchement.desc())\
                       .limit(limit).all()
    
    @classmethod
    def get_statistiques_protection(cls, client_id=None, days_back=30):
        """Statistiques des événements de protection"""
        from datetime import timedelta
        
        since = datetime.utcnow() - timedelta(days=days_back)
        query = cls.query.filter(cls.timestamp_declenchement >= since)
        
        if client_id:
            query = query.filter_by(client_id=client_id)
        
        events = query.all()
        
        stats = {
            'total_evenements': len(events),
            'par_type': {},
            'par_statut': {},
            'par_systeme': {'monophase': 0, 'triphase': 0},
            'duree_moyenne_resolution': 0,
            'evenements_critiques': 0,
            'appareils_concernes': set()
        }
        
        durees_resolution = []
        
        for event in events:
            # Par type
            if event.type_protection not in stats['par_type']:
                stats['par_type'][event.type_protection] = 0
            stats['par_type'][event.type_protection] += 1
            
            # Par statut
            if event.statut not in stats['par_statut']:
                stats['par_statut'][event.statut] = 0
            stats['par_statut'][event.statut] += 1
            
            # Par système
            stats['par_systeme'][event.type_systeme] += 1
            
            # Gravité
            if event.get_gravite() == 'critique':
                stats['evenements_critiques'] += 1
            
            # Appareils concernés
            stats['appareils_concernes'].add(event.appareil_id)
            
            # Durée de résolution
            if event.duree_minutes:
                durees_resolution.append(event.duree_minutes)
        
        if durees_resolution:
            stats['duree_moyenne_resolution'] = round(sum(durees_resolution) / len(durees_resolution), 2)
        
        stats['appareils_concernes'] = len(stats['appareils_concernes'])
        
        return stats
    
    @classmethod
    def nettoyer_anciens_evenements(cls, days_to_keep=180):
        """Nettoyer les anciens événements résolus"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        try:
            count = cls.query.filter(
                cls.statut.in_(['resolu_auto', 'resolu_manuel']),
                cls.timestamp_resolution < cutoff_date
            ).count()
            
            cls.query.filter(
                cls.statut.in_(['resolu_auto', 'resolu_manuel']),
                cls.timestamp_resolution < cutoff_date
            ).delete()
            
            db.session.commit()
            return count
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur nettoyage événements protection: {e}")
            return 0