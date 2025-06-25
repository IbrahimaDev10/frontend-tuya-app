# app/utils/token_manager.py

import secrets
import time
from typing import Optional, Dict, Any

class ActivationTokenManager:
    """Gestionnaire de tokens d'activation temporaires pour tous les utilisateurs"""
    
    # En mémoire pour commencer - en production utilisez Redis
    _tokens = {}
    
    @classmethod
    def generate_token(cls, user_id: str, email: str = None, expires_in: int = 86400, user_type: str = 'user') -> str:
        """
        Génère un token d'activation sécurisé
        
        Args:
            user_id: ID de l'utilisateur (admin, user, etc.)
            email: Email de l'utilisateur (optionnel pour vérification)
            expires_in: Durée de validité en secondes (défaut: 24h)
            user_type: Type d'utilisateur ('admin', 'user', 'superadmin')
            
        Returns:
            str: Token généré
        """
        # Générer un token sécurisé de 32 caractères
        token = secrets.token_urlsafe(32)
        
        # Calculer l'heure d'expiration
        expires_at = time.time() + expires_in
        
        # Déterminer le type d'activation selon le type d'utilisateur
        activation_type = f"{user_type}_activation"
        
        # Stocker les données du token
        cls._tokens[token] = {
            'user_id': user_id,
            'admin_id': user_id,   # ✅ Alias pour rétrocompatibilité
            'email': email,
            'expires_at': expires_at,
            'user_type': user_type,  # ✅ NOUVEAU: Type d'utilisateur
            'type': activation_type,  # ✅ Type d'activation dynamique
            'created_at': time.time()
        }
        
        print(f"🔑 Token généré pour {user_type} {user_id} ({email}): {token[:10]}...")
        return token
    
    @classmethod
    def validate_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Valide un token sans le consommer
        
        Args:
            token: Token à valider
            
        Returns:
            Dict avec les données du token si valide, None sinon
        """
        if not token or token not in cls._tokens:
            print(f"❌ Token non trouvé: {token[:10] if token else 'None'}...")
            return None
        
        token_data = cls._tokens[token]
        
        # Vérifier expiration
        if time.time() > token_data['expires_at']:
            print(f"⏰ Token expiré: {token[:10]}...")
            del cls._tokens[token]
            return None
        
        print(f"✅ Token valide pour {token_data.get('user_type', 'unknown')}: {token[:10]}...")
        return token_data.copy()  # Retourner une copie pour éviter les modifications
    
    @classmethod
    def use_token(cls, token: str, expected_user_type: str = None) -> Optional[Dict[str, Any]]:
        """
        ✅ MÉTHODE MISE À JOUR
        Utilise (consomme) un token d'activation - le supprime après validation
        
        Args:
            token: Token à consommer
            expected_user_type: Type d'utilisateur attendu (optionnel pour validation)
            
        Returns:
            Dict avec les données du token si valide, None sinon
        """
        token_data = cls.validate_token(token)
        
        if not token_data:
            return None
        
        # Vérifier le type d'utilisateur si spécifié
        if expected_user_type and token_data.get('user_type') != expected_user_type:
            print(f"❌ Type d'utilisateur incorrect. Attendu: {expected_user_type}, Trouvé: {token_data.get('user_type')}")
            return None
        
        if token in cls._tokens:
            del cls._tokens[token]
            print(f"🔥 Token {token_data.get('user_type', 'unknown')} consommé: {token[:10]}...")
            return token_data
        
        return None
    
    @classmethod
    def consume_token(cls, token: str, expected_user_type: str = None) -> Optional[Dict[str, Any]]:
        """
        Alias pour use_token - pour rétrocompatibilité
        """
        return cls.use_token(token, expected_user_type)
    
    @classmethod
    def generate_admin_token(cls, admin_id: str, email: str = None, expires_in: int = 86400) -> str:
        """
        ✅ MÉTHODE SPÉCIALISÉE pour les admins (rétrocompatibilité)
        """
        return cls.generate_token(admin_id, email, expires_in, 'admin')
    
    @classmethod
    def generate_user_token(cls, user_id: str, email: str = None, expires_in: int = 86400) -> str:
        """
        ✅ NOUVELLE MÉTHODE pour les utilisateurs standards
        """
        return cls.generate_token(user_id, email, expires_in, 'user')
    
    @classmethod
    def generate_superadmin_token(cls, superadmin_id: str, email: str = None, expires_in: int = 86400) -> str:
        """
        ✅ NOUVELLE MÉTHODE pour les superadmins
        """
        return cls.generate_token(superadmin_id, email, expires_in, 'superadmin')
    
    @classmethod
    def cleanup_expired(cls) -> int:
        """
        Nettoie les tokens expirés
        
        Returns:
            int: Nombre de tokens supprimés
        """
        current_time = time.time()
        expired_tokens = [
            token for token, data in cls._tokens.items()
            if current_time > data['expires_at']
        ]
        
        for token in expired_tokens:
            del cls._tokens[token]
        
        if expired_tokens:
            print(f"🧹 {len(expired_tokens)} tokens expirés nettoyés")
        
        return len(expired_tokens)
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """
        Retourne des statistiques sur les tokens
        Utile pour le debug
        """
        current_time = time.time()
        stats_by_type = {}
        
        for data in cls._tokens.values():
            user_type = data.get('user_type', 'unknown')
            if user_type not in stats_by_type:
                stats_by_type[user_type] = {'active': 0, 'expired': 0}
            
            if current_time > data['expires_at']:
                stats_by_type[user_type]['expired'] += 1
            else:
                stats_by_type[user_type]['active'] += 1
        
        return {
            'total_tokens': len(cls._tokens),
            'stats_by_type': stats_by_type,
            'tokens_details': [
                {
                    'user_id': data['user_id'],
                    'user_type': data.get('user_type', 'unknown'),
                    'email': data.get('email', 'N/A'),
                    'expires_in_seconds': max(0, int(data['expires_at'] - current_time)),
                    'expired': current_time > data['expires_at']
                }
                for data in cls._tokens.values()
            ]
        }
    
    @classmethod
    def revoke_user_tokens(cls, user_id: str, user_type: str = None) -> int:
        """
        ✅ MÉTHODE MISE À JOUR
        Révoque tous les tokens d'un utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            user_type: Type d'utilisateur spécifique (optionnel)
            
        Returns:
            int: Nombre de tokens révoqués
        """
        tokens_to_revoke = []
        
        for token, data in cls._tokens.items():
            # Vérifier l'ID utilisateur
            if data.get('user_id') == user_id or data.get('admin_id') == user_id:
                # Si un type spécifique est demandé, le vérifier
                if user_type is None or data.get('user_type') == user_type:
                    tokens_to_revoke.append(token)
        
        for token in tokens_to_revoke:
            del cls._tokens[token]
        
        if tokens_to_revoke:
            type_info = f" de type {user_type}" if user_type else ""
            print(f"🚫 {len(tokens_to_revoke)} tokens révoqués pour utilisateur {user_id}{type_info}")
        
        return len(tokens_to_revoke)
    
    @classmethod
    def revoke_admin_tokens(cls, admin_id: str) -> int:
        """
        Alias spécialisé pour les admins (rétrocompatibilité)
        """
        return cls.revoke_user_tokens(admin_id, 'admin')
    
    @classmethod
    def get_token_info(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Obtenir des informations détaillées sur un token (debug)
        """
        if token not in cls._tokens:
            return None
        
        data = cls._tokens[token]
        current_time = time.time()
        
        return {
            'token': token[:10] + "...",
            'user_id': data['user_id'],
            'user_type': data.get('user_type', 'unknown'),
            'email': data.get('email', 'N/A'),
            'created_at': data['created_at'],
            'expires_at': data['expires_at'],
            'expires_in_seconds': max(0, int(data['expires_at'] - current_time)),
            'is_expired': current_time > data['expires_at'],
            'type': data.get('type', 'unknown')
        }
    
    @classmethod
    def invalidate_token(cls, token: str) -> bool:
        """
        Invalide (supprime) un token spécifique
        
        Args:
            token: Token à invalider
            
        Returns:
            bool: True si le token a été supprimé, False s'il n'existait pas
        """
        if token in cls._tokens:
            token_data = cls._tokens[token]
            user_type = token_data.get('user_type', 'unknown')
            del cls._tokens[token]
            print(f"🗑️ Token {user_type} invalidé: {token[:10]}...")
            return True
        else:
            print(f"❌ Token à invalider non trouvé: {token[:10] if token else 'None'}...")
            return False

    @classmethod
    def force_add_token_for_debug(cls, user_id: str, email: str, user_type: str = 'user', token: str = None) -> str:
        """
        ✅ MÉTHODE DE DEBUG MISE À JOUR
        Force l'ajout d'un token pour les tests
        """
        if not token:
            token = secrets.token_urlsafe(32)
        
        expires_at = time.time() + 86400  # 24h
        
        cls._tokens[token] = {
            'user_id': user_id,
            'admin_id': user_id,  # Alias
            'email': email,
            'expires_at': expires_at,
            'user_type': user_type,
            'type': f'{user_type}_activation',
            'created_at': time.time()
        }
        
        print(f"🔧 Token DEBUG {user_type} ajouté pour {user_id}: {token[:10]}...")
        return token