# app/utils/fast_cache.py - Cache Redis ultra-rapide

import json
import time
import logging
from datetime import datetime
from app import get_redis, get_redis_pipeline

class FastCache:
    """Cache Redis ultra-optimisé pour votre app"""
    
    def __init__(self):
        self.redis = get_redis()
        self.logger = logging.getLogger(__name__)
        
        # Optimisations
        self._serializer = json.dumps
        self._deserializer = json.loads
        
    def quick_set(self, key, data, ttl=300):
        """Set ultra-rapide sans vérifications lourdes"""
        if not self.redis:
            return False
        
        try:
            # Sérialisation simple
            if isinstance(data, (dict, list)):
                value = self._serializer(data)
            else:
                value = str(data)
            
            # Set direct avec TTL
            return bool(self.redis.setex(key, ttl, value))
            
        except Exception as e:
            # Log minimaliste pour performance
            self.logger.error(f"Cache SET error: {e}")
            return False
    
    def quick_get(self, key, default=None):
        """Get ultra-rapide avec fallback"""
        if not self.redis:
            return default
        
        try:
            value = self.redis.get(key)
            if value is None:
                return default
            
            # Désérialisation intelligente
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            
            # Essayer JSON d'abord (la plupart de vos données)
            if value.startswith(('{', '[', '"')) or value in ('true', 'false', 'null'):
                try:
                    return self._deserializer(value)
                except:
                    pass
            
            return value
            
        except Exception as e:
            self.logger.error(f"Cache GET error: {e}")
            return default
    
    def batch_set(self, data_dict, ttl=300):
        """Set multiple clés en une seule opération"""
        if not self.redis or not data_dict:
            return False
        
        try:
            pipe = get_redis_pipeline()
            if not pipe:
                return False
            
            # Ajouter toutes les opérations au pipeline
            for key, data in data_dict.items():
                if isinstance(data, (dict, list)):
                    value = self._serializer(data)
                else:
                    value = str(data)
                
                pipe.setex(key, ttl, value)
            
            # Exécuter tout d'un coup
            results = pipe.execute()
            return all(results)
            
        except Exception as e:
            self.logger.error(f"Batch SET error: {e}")
            return False
    
    def batch_get(self, keys):
        """Get multiple clés en une seule opération"""
        if not self.redis or not keys:
            return {}
        
        try:
            # Get multiple avec pipeline
            pipe = get_redis_pipeline()
            if not pipe:
                return {}
            
            for key in keys:
                pipe.get(key)
            
            results = pipe.execute()
            
            # Construire dictionnaire résultat
            data = {}
            for i, key in enumerate(keys):
                if i < len(results) and results[i] is not None:
                    value = results[i]
                    
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    
                    # Désérialisation
                    if value.startswith(('{', '[', '"')) or value in ('true', 'false', 'null'):
                        try:
                            data[key] = self._deserializer(value)
                        except:
                            data[key] = value
                    else:
                        data[key] = value
            
            return data
            
        except Exception as e:
            self.logger.error(f"Batch GET error: {e}")
            return {}
    
    def delete_pattern(self, pattern):
        """Suppression rapide par pattern"""
        if not self.redis:
            return 0
        
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            self.logger.error(f"Delete pattern error: {e}")
            return 0
    
    def is_connected(self):
        """Test connexion rapide"""
        if not self.redis:
            return False
        
        try:
            self.redis.ping()
            return True
        except:
            return False
    
    def get_performance_stats(self):
        """Stats performance Redis"""
        if not self.redis:
            return {'connected': False}
        
        try:
            start = time.time()
            self.redis.ping()
            ping_time = (time.time() - start) * 1000
            
            info = self.redis.info()
            
            return {
                'connected': True,
                'ping_ms': round(ping_time, 2),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'hit_rate': round(
                    info.get('keyspace_hits', 0) / 
                    max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100, 
                    1
                )
            }
        except Exception as e:
            return {'connected': False, 'error': str(e)}

# Instance globale
fast_cache = FastCache()