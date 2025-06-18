# app/utils/token_manager.py

import secrets
import time
from typing import Optional, Dict, Any

class ActivationTokenManager:
    """Gestionnaire de tokens d'activation temporaires pour les admins"""
    
    # En mémoire pour commencer - en production utilisez Redis
    _tokens = {}
    
    @classmethod
    def generate_token(cls, admin_id: str, email: str = None, expires_in: int = 86400) -> str:
        """
        Génère un token d'activation sécurisé
        
        Args:
            admin_id: ID de l'administrateur (compatible avec user_id)
            email: Email de l'utilisateur (optionnel pour vérification)
            expires_in: Durée de validité en secondes (défaut: 24h)
            
        Returns:
            str: Token généré
        """
        # Générer un token sécurisé de 32 caractères
        token = secrets.token_urlsafe(32)
        
        # Calculer l'heure d'expiration
        expires_at = time.time() + expires_in
        
        # Stocker les données du token avec admin_id (compatible UserService)
        cls._tokens[token] = {
            'admin_id': admin_id,  # ✅ Nom cohérent avec UserService
            'user_id': admin_id,   # ✅ Alias pour compatibilité
            'email': email,
            'expires_at': expires_at,
            'type': 'admin_activation',
            'created_at': time.time()
        }
        
        print(f"🔑 Token généré pour admin {admin_id} ({email}): {token[:10]}...")
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
        
        print(f"✅ Token valide: {token[:10]}...")
        return token_data.copy()  # Retourner une copie pour éviter les modifications
    
    @classmethod
    def use_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        ✅ MÉTHODE ATTENDUE PAR USERSERVICE
        Utilise (consomme) un token d'activation - le supprime après validation
        
        Args:
            token: Token à consommer
            
        Returns:
            Dict avec les données du token si valide, None sinon
        """
        token_data = cls.validate_token(token)
        
        if token_data and token in cls._tokens:
            del cls._tokens[token]
            print(f"🔥 Token consommé: {token[:10]}...")
            return token_data
        
        return None
    
    @classmethod
    def consume_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Alias pour use_token - pour rétrocompatibilité
        """
        return cls.use_token(token)
    
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
        active_tokens = 0
        expired_tokens = 0
        
        for data in cls._tokens.values():
            if current_time > data['expires_at']:
                expired_tokens += 1
            else:
                active_tokens += 1
        
        return {
            'total_tokens': len(cls._tokens),
            'active_tokens': active_tokens,
            'expired_tokens': expired_tokens,
            'tokens_details': [
                {
                    'admin_id': data['admin_id'],
                    'email': data.get('email', 'N/A'),
                    'expires_in_seconds': max(0, int(data['expires_at'] - current_time)),
                    'expired': current_time > data['expires_at']
                }
                for data in cls._tokens.values()
            ]
        }
    
    @classmethod
    def revoke_admin_tokens(cls, admin_id: str) -> int:
        """
        Révoque tous les tokens d'un administrateur
        
        Args:
            admin_id: ID de l'administrateur
            
        Returns:
            int: Nombre de tokens révoqués
        """
        tokens_to_revoke = [
            token for token, data in cls._tokens.items()
            if data.get('admin_id') == admin_id or data.get('user_id') == admin_id
        ]
        
        for token in tokens_to_revoke:
            del cls._tokens[token]
        
        if tokens_to_revoke:
            print(f"🚫 {len(tokens_to_revoke)} tokens révoqués pour admin {admin_id}")
        
        return len(tokens_to_revoke)
    
    @classmethod
    def revoke_user_tokens(cls, user_id: str) -> int:
        """
        Alias pour revoke_admin_tokens - rétrocompatibilité
        """
        return cls.revoke_admin_tokens(user_id)
    
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
            'admin_id': data['admin_id'],
            'email': data.get('email', 'N/A'),
            'created_at': data['created_at'],
            'expires_at': data['expires_at'],
            'expires_in_seconds': max(0, int(data['expires_at'] - current_time)),
            'is_expired': current_time > data['expires_at'],
            'type': data.get('type', 'unknown')
        }
    

    # Ajoutez cette méthode à votre classe ActivationTokenManager

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
            del cls._tokens[token]
            print(f"🗑️ Token invalidé: {token[:10]}...")
            return True
        else:
            print(f"❌ Token à invalider non trouvé: {token[:10] if token else 'None'}...")
            return False

    @classmethod
    def force_add_token_for_debug(cls, admin_id: str, email: str, token: str = None) -> str:
        """
        MÉTHODE DE DEBUG UNIQUEMENT
        Force l'ajout d'un token pour les tests
        """
        if not token:
            token = secrets.token_urlsafe(32)
        
        expires_at = time.time() + 86400  # 24h
        
        cls._tokens[token] = {
            'admin_id': admin_id,
            'user_id': admin_id,
            'email': email,
            'expires_at': expires_at,
            'type': 'admin_activation',
            'created_at': time.time()
        }
        
        print(f"🔧 Token DEBUG ajouté pour {admin_id}: {token[:10]}...")
        return token