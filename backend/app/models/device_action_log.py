# app/models/device_action_log.py

from app import db
from datetime import datetime
import uuid
import json

class DeviceActionLog(db.Model):
    """Modèle pour logger les actions sur les appareils"""
    
    __tablename__ = 'device_action_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = db.Column(db.String(36), db.ForeignKey('devices.id'), nullable=False)
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=True)
    
    # Informations sur l'action
    action_type = db.Column(db.String(50), nullable=False)
    action_subtype = db.Column(db.String(50), nullable=True)
    
    # Résultat de l'action
    result = db.Column(db.String(20), nullable=False, default='pending')
    error_message = db.Column(db.Text, nullable=True)
    
    # Détails de l'action
    action_details = db.Column(db.JSON, nullable=True)
    
    # Métadonnées
    triggered_by_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    executed_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # ✅ RELATIONS CORRIGÉES - PAS DE back_populates ici
    # La relation est définie côté Device avec backref
    # device sera créé automatiquement par le backref du modèle Device
    
    # Relations avec User (si le modèle existe)
    user = db.relationship('User', backref='device_actions', lazy=True)
    
    def __repr__(self):
        return f'<DeviceActionLog {self.id}: {self.action_type} on {self.device_id}>'
    
    @staticmethod
    def log_action(device_id, client_id=None, action_type='manual_control', 
                   action_subtype=None, result='success', details=None, 
                   user_id=None, ip_address=None, user_agent=None):
        """Créer un log d'action"""
        try:
            log_entry = DeviceActionLog(
                device_id=device_id,
                client_id=client_id,
                action_type=action_type,
                action_subtype=action_subtype,
                result=result,
                action_details=details or {},
                triggered_by_user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                executed_at=datetime.utcnow() if result != 'pending' else None,
                completed_at=datetime.utcnow() if result in ['success', 'failed'] else None
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
            return log_entry
            
        except Exception as e:
            print(f"Erreur création log action: {e}")
            db.session.rollback()
            return None
    
    def mark_as_executed(self, result='success', error_message=None):
        """Marquer l'action comme exécutée"""
        self.result = result
        self.executed_at = datetime.utcnow()
        self.completed_at = datetime.utcnow()
        
        if error_message:
            self.error_message = error_message
        
        db.session.commit()
    
    def to_dict(self):
        """Convertir en dictionnaire"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'client_id': self.client_id,
            'action_type': self.action_type,
            'action_subtype': self.action_subtype,
            'result': self.result,
            'error_message': self.error_message,
            'action_details': self.action_details,
            'triggered_by_user_id': self.triggered_by_user_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
