from app import db
from datetime import datetime, timedelta
import uuid
import json

class ScheduledAction(db.Model):
    """Modèle pour les actions programmées des appareils (allumage/extinction automatique)"""
    
    __tablename__ = 'scheduled_actions'
    
    # Clé primaire
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relations
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=False, index=True)
    appareil_id = db.Column(db.String(36), db.ForeignKey('devices.id'), nullable=False, index=True)
    
    # Type d'action
    action_type = db.Column(db.Enum(
        'turn_on', 'turn_off', 'toggle', 'custom_command', 
        'restart', 'standby', 'protection_mode',
        name='scheduled_action_types'
    ), nullable=False, default='turn_on', index=True)
    
    # Commande personnalisée (pour custom_command)
    custom_command = db.Column(db.JSON, nullable=True)
    
    # Programmation temporelle
    heure_execution = db.Column(db.Time, nullable=False, index=True)  # Heure d'exécution (HH:MM)
    jours_semaine = db.Column(db.String(20), nullable=False, default='1,2,3,4,5,6,7')  # Jours séparés par virgules
    # Format: "1,2,3,4,5" pour Lundi-Vendredi, "1,2,3,4,5,6,7" pour tous les jours
    
    # Période d'activité (optionnel)
    date_debut = db.Column(db.Date, nullable=True)
    date_fin = db.Column(db.Date, nullable=True)
    
    # Configuration avancée
    timezone = db.Column(db.String(50), nullable=False, default='Africa/Dakar')
    actif = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Mode d'exécution
    mode_execution = db.Column(db.Enum(
        'once', 'daily', 'weekly', 'custom',
        name='execution_modes'
    ), nullable=False, default='daily')
    
    # Prochaine exécution calculée
    prochaine_execution = db.Column(db.DateTime, nullable=True, index=True)
    
    # Historique de la dernière exécution
    derniere_execution = db.Column(db.DateTime, nullable=True)
    derniere_execution_success = db.Column(db.Boolean, nullable=True)
    derniere_execution_error = db.Column(db.Text, nullable=True)
    
    # Compteurs
    executions_totales = db.Column(db.Integer, default=0, nullable=False)
    executions_reussies = db.Column(db.Integer, default=0, nullable=False)
    executions_echouees = db.Column(db.Integer, default=0, nullable=False)
    
    # Métadonnées
    nom_action = db.Column(db.String(255), nullable=True)  # Nom personnalisé pour l'action
    description = db.Column(db.Text, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    cree_par = db.Column(db.String(36), nullable=True)  # ID utilisateur créateur
    
    # Configuration de retry en cas d'échec
    retry_enabled = db.Column(db.Boolean, default=True, nullable=False)
    retry_attempts = db.Column(db.Integer, default=3, nullable=False)
    retry_delay_minutes = db.Column(db.Integer, default=5, nullable=False)
    
    # Mode priorité (désactive temporairement d'autres actions)
    priorite = db.Column(db.Integer, default=5, nullable=False)  # 1-10, 10 = priorité max
    
    def __repr__(self):
        return f'<ScheduledAction {self.action_type} @ {self.heure_execution} - Device:{self.appareil_id}>'
    
    # =================== MÉTHODES DE GESTION DES JOURS ===================
    
    def set_jours_semaine(self, jours_list):
        """Définir les jours de la semaine (1=Lundi, 7=Dimanche)"""
        if isinstance(jours_list, list):
            # Valider que tous les jours sont entre 1 et 7
            jours_valides = [str(j) for j in jours_list if 1 <= j <= 7]
            self.jours_semaine = ','.join(jours_valides)
        elif isinstance(jours_list, str):
            self.jours_semaine = jours_list
    
    def get_jours_semaine_list(self):
        """Récupérer les jours sous forme de liste d'entiers"""
        if not self.jours_semaine:
            return []
        return [int(j) for j in self.jours_semaine.split(',') if j.isdigit()]
    
    def get_jours_semaine_noms(self):
        """Récupérer les noms des jours en français"""
        noms_jours = {
            1: 'Lundi', 2: 'Mardi', 3: 'Mercredi', 4: 'Jeudi',
            5: 'Vendredi', 6: 'Samedi', 7: 'Dimanche'
        }
        jours = self.get_jours_semaine_list()
        return [noms_jours.get(j, f'Jour {j}') for j in jours]
    
    def is_jour_actif(self, jour_semaine):
        """Vérifier si l'action est active pour un jour donné (1=Lundi, 7=Dimanche)"""
        return jour_semaine in self.get_jours_semaine_list()
    
    # =================== CALCUL PROCHAINE EXÉCUTION ===================
    
    def calculer_prochaine_execution(self):
        """Calculer la prochaine date/heure d'exécution - VERSION CORRIGÉE"""
        if not self.actif or not self.heure_execution:
            self.prochaine_execution = None
            return
        
        try:
            from datetime import datetime, timedelta, time, date
            import pytz
            
            # Timezone
            try:
                tz = pytz.timezone(self.timezone)
                now = datetime.now(tz)
            except:
                now = datetime.utcnow()
            
            # Jours actifs
            jours_actifs = self.get_jours_semaine_list()
            if not jours_actifs:
                self.prochaine_execution = None
                return
            
            # ✅ CORRECTION : Chercher la prochaine occurrence
            for i in range(8):  # Chercher sur les 8 prochains jours
                check_date = now.date() + timedelta(days=i)
                check_datetime = datetime.combine(check_date, self.heure_execution)
                
                # ✅ CORRECTION : Conversion correcte du jour de la semaine
                # Python weekday() : 0=Lundi, 6=Dimanche
                # Votre format : 1=Lundi, 7=Dimanche
                weekday_python = check_date.weekday()  # 0-6
                weekday_votre_format = weekday_python + 1  # 1-7
                if weekday_votre_format == 7:  # Dimanche
                    weekday_votre_format = 7
                
                # Ajouter timezone si nécessaire
                if hasattr(now, 'tzinfo') and now.tzinfo:
                    check_datetime = tz.localize(check_datetime)
                
                # Vérifier les conditions
                conditions = [
                    weekday_votre_format in jours_actifs,
                    check_datetime > now,
                    self._is_date_in_range(check_date)
                ]
                
                if all(conditions):
                    # ✅ CORRECTION : Retirer timezone pour stockage en DB
                    if hasattr(check_datetime, 'tzinfo') and check_datetime.tzinfo:
                        check_datetime = check_datetime.replace(tzinfo=None)
                    
                    self.prochaine_execution = check_datetime
                    print(f"✅ Prochaine exécution calculée: {check_datetime} pour {self.nom_action}")
                    return
            
            # Aucune prochaine exécution trouvée
            self.prochaine_execution = None
            print(f"⚠️ Aucune prochaine exécution trouvée pour {self.nom_action}")
            
        except Exception as e:
            print(f"❌ Erreur calcul prochaine exécution: {e}")
            self.prochaine_execution = None
    
    def _is_date_in_range(self, check_date):
        """Vérifier si la date est dans la plage autorisée"""
        if self.date_debut and check_date < self.date_debut:
            return False
        if self.date_fin and check_date > self.date_fin:
            return False
        return True
    
    # =================== EXÉCUTION ET HISTORIQUE ===================
    
    def marquer_execution(self, success=True, error_message=None):
        """Marquer une exécution dans l'historique"""
        try:
            self.derniere_execution = datetime.utcnow()
            self.derniere_execution_success = success
            self.derniere_execution_error = error_message
            self.executions_totales += 1
            
            if success:
                self.executions_reussies += 1
            else:
                self.executions_echouees += 1
            
            # Recalculer la prochaine exécution
            self.calculer_prochaine_execution()
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur marquage exécution: {e}")
            return False
    
    def get_taux_reussite(self):
        """Calculer le taux de réussite en pourcentage"""
        if self.executions_totales == 0:
            return 0
        return round((self.executions_reussies / self.executions_totales) * 100, 2)
    
    def is_due_for_execution(self, tolerance_minutes=2):
        """Vérifier si l'action doit être exécutée maintenant"""
        if not self.actif or not self.prochaine_execution:
            return False
        
        now = datetime.utcnow()
        tolerance = timedelta(minutes=tolerance_minutes)
        
        return (self.prochaine_execution - tolerance) <= now <= (self.prochaine_execution + tolerance)
    
    def should_retry(self):
        """Vérifier si l'action doit être retentée après un échec"""
        if not self.retry_enabled or not self.derniere_execution:
            return False
        
        # Vérifier si la dernière exécution a échoué
        if self.derniere_execution_success:
            return False
        
        # Vérifier le délai depuis la dernière tentative
        now = datetime.utcnow()
        retry_time = self.derniere_execution + timedelta(minutes=self.retry_delay_minutes)
        
        return now >= retry_time
    
    # =================== CONFIGURATION ET VALIDATION ===================
    
    def valider_configuration(self):
        """Valider la configuration de l'action programmée"""
        erreurs = []
        
        # Vérifier l'heure
        if not self.heure_execution:
            erreurs.append("Heure d'exécution requise")
        
        # Vérifier les jours
        jours = self.get_jours_semaine_list()
        if not jours:
            erreurs.append("Au moins un jour de la semaine requis")
        elif any(j < 1 or j > 7 for j in jours):
            erreurs.append("Jours de semaine invalides (1-7)")
        
        # Vérifier les dates
        if self.date_debut and self.date_fin and self.date_debut > self.date_fin:
            erreurs.append("Date de début doit être antérieure à la date de fin")
        
        # Vérifier les paramètres de retry
        if self.retry_attempts < 0 or self.retry_attempts > 10:
            erreurs.append("Nombre de tentatives doit être entre 0 et 10")
        
        if self.retry_delay_minutes < 1 or self.retry_delay_minutes > 60:
            erreurs.append("Délai de retry doit être entre 1 et 60 minutes")
        
        return erreurs
    
    def activer(self):
        """Activer l'action programmée"""
        erreurs = self.valider_configuration()
        if erreurs:
            return False, erreurs
        
        self.actif = True
        self.calculer_prochaine_execution()
        db.session.commit()
        return True, []
    
    def desactiver(self):
        """Désactiver l'action programmée"""
        self.actif = False
        self.prochaine_execution = None
        db.session.commit()
        return True
    
    # =================== SÉRIALISATION ===================
    
    def to_dict(self, include_stats=False, include_history=False):
        """Convertir en dictionnaire pour l'API"""
        data = {
            'id': self.id,
            'client_id': self.client_id,
            'appareil_id': self.appareil_id,
            'action_type': self.action_type,
            'custom_command': self.custom_command,
            'heure_execution': self.heure_execution.strftime('%H:%M') if self.heure_execution else None,
            'jours_semaine': self.jours_semaine,
            'jours_semaine_noms': self.get_jours_semaine_noms(),
            'date_debut': self.date_debut.isoformat() if self.date_debut else None,
            'date_fin': self.date_fin.isoformat() if self.date_fin else None,
            'timezone': self.timezone,
            'actif': self.actif,
            'mode_execution': self.mode_execution,
            'prochaine_execution': self.prochaine_execution.isoformat() if self.prochaine_execution else None,
            'nom_action': self.nom_action,
            'description': self.description,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'cree_par': self.cree_par,
            'retry_enabled': self.retry_enabled,
            'retry_attempts': self.retry_attempts,
            'retry_delay_minutes': self.retry_delay_minutes,
            'priorite': self.priorite
        }
        
        if include_stats:
            data['stats'] = {
                'executions_totales': self.executions_totales,
                'executions_reussies': self.executions_reussies,
                'executions_echouees': self.executions_echouees,
                'taux_reussite': self.get_taux_reussite()
            }
        
        if include_history:
            data['derniere_execution'] = {
                'timestamp': self.derniere_execution.isoformat() if self.derniere_execution else None,
                'success': self.derniere_execution_success,
                'error': self.derniere_execution_error
            }
        
        return data
    
    # =================== MÉTHODES DE CLASSE ===================
    
    @classmethod
    def creer_action_simple(cls, client_id, appareil_id, action_type, heure, jours=None, 
                           nom_action=None, user_id=None):
        """Créer une action programmée simple"""
        if jours is None:
            jours = [1, 2, 3, 4, 5, 6, 7]  # Tous les jours par défaut
        
        try:
            from datetime import time
            
            # Parser l'heure si c'est une string
            if isinstance(heure, str):
                hour, minute = map(int, heure.split(':'))
                heure = time(hour, minute)
            
            action = cls(
                client_id=client_id,
                appareil_id=appareil_id,
                action_type=action_type,
                heure_execution=heure,
                nom_action=nom_action or f"{action_type.replace('_', ' ').title()} automatique",
                cree_par=user_id
            )
            
            action.set_jours_semaine(jours)
            action.calculer_prochaine_execution()
            
            db.session.add(action)
            db.session.commit()
            return action
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur création action programmée: {e}")
            return None
    
    @classmethod
    def get_actions_dues(cls, tolerance_minutes=2):
        """Récupérer toutes les actions qui doivent être exécutées"""
        now = datetime.utcnow()
        tolerance = timedelta(minutes=tolerance_minutes)
        
        return cls.query.filter(
            cls.actif == True,
            cls.prochaine_execution.isnot(None),
            cls.prochaine_execution >= (now - tolerance),
            cls.prochaine_execution <= (now + tolerance)
        ).order_by(cls.priorite.desc(), cls.prochaine_execution.asc()).all()
    
    @classmethod
    def get_actions_by_device(cls, appareil_id):
        """Récupérer toutes les actions programmées d'un appareil"""
        return cls.query.filter_by(appareil_id=appareil_id)\
                       .order_by(cls.actif.desc(), cls.heure_execution.asc()).all()
    
    @classmethod
    def get_prochaines_actions(cls, client_id=None, limit=10):
        """Récupérer les prochaines actions à exécuter"""
        query = cls.query.filter(
            cls.actif == True,
            cls.prochaine_execution.isnot(None)
        )
        
        if client_id:
            query = query.filter_by(client_id=client_id)
        
        return query.order_by(cls.prochaine_execution.asc()).limit(limit).all()
    
    @classmethod
    def recalculer_toutes_prochaines_executions(cls):
        """Recalculer les prochaines exécutions pour toutes les actions actives"""
        actions = cls.query.filter_by(actif=True).all()
        count = 0
        
        for action in actions:
            try:
                action.calculer_prochaine_execution()
                count += 1
            except Exception as e:
                print(f"Erreur recalcul action {action.id}: {e}")
        
        return count
    
    @classmethod
    def get_statistiques_globales(cls, client_id=None):
        """Statistiques globales des actions programmées"""
        query = cls.query
        if client_id:
            query = query.filter_by(client_id=client_id)
        
        actions = query.all()
        
        stats = {
            'total_actions': len(actions),
            'actions_actives': sum(1 for a in actions if a.actif),
            'actions_inactives': sum(1 for a in actions if not a.actif),
            'par_type': {},
            'executions_totales': sum(a.executions_totales for a in actions),
            'executions_reussies': sum(a.executions_reussies for a in actions),
            'taux_reussite_global': 0,
            'actions_avec_erreurs': sum(1 for a in actions if a.executions_echouees > 0),
            'prochaines_24h': 0
        }
        
        # Statistiques par type
        for action in actions:
            if action.action_type not in stats['par_type']:
                stats['par_type'][action.action_type] = 0
            stats['par_type'][action.action_type] += 1
        
        # Taux de réussite global
        if stats['executions_totales'] > 0:
            stats['taux_reussite_global'] = round(
                (stats['executions_reussies'] / stats['executions_totales']) * 100, 2
            )
        
        # Actions dans les prochaines 24h
        dans_24h = datetime.utcnow() + timedelta(hours=24)
        stats['prochaines_24h'] = sum(
            1 for a in actions 
            if a.prochaine_execution and a.prochaine_execution <= dans_24h
        )
        
        return stats
    
    @classmethod
    def nettoyer_actions_expirees(cls):
        """Supprimer les actions expirées (date_fin dépassée)"""
        from datetime import date
        
        today = date.today()
        
        try:
            count = cls.query.filter(
                cls.date_fin.isnot(None),
                cls.date_fin < today
            ).count()
            
            cls.query.filter(
                cls.date_fin.isnot(None),
                cls.date_fin < today
            ).delete()
            
            db.session.commit()
            return count
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur nettoyage actions expirées: {e}")
            return 0