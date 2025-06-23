#!/usr/bin/env python3
"""
Script de test Redis pour SERTEC IoT
Teste votre configuration Redis avec le mot de passe haadee123!
"""

import os
import redis
import json
from dotenv import load_dotenv

def test_redis_simple():
    """Test simple de Redis avec votre configuration"""
    
    print("🚀 Test Redis SERTEC IoT")
    print("=" * 40)
    
    # Charger .env
    load_dotenv()
    
    # URL Redis depuis votre .env
    redis_url = os.getenv('REDIS_URL', 'redis://:haadee123!@localhost:6379/0')
    print(f"📍 URL Redis: {redis_url}")
    
    try:
        # Connexion
        print("\n🔄 Connexion à Redis...")
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=5
        )
        
        # Test ping
        print("🔄 Test ping...")
        ping_result = client.ping()
        print(f"✅ Ping: {ping_result}")
        
        # Test écriture simple
        print("🔄 Test écriture simple...")
        client.set('sertec_test', 'Hello SERTEC!', ex=30)
        value = client.get('sertec_test')
        print(f"✅ Écriture/lecture: {value}")
        
        # Test JSON (pour vos données IoT)
        print("🔄 Test données JSON...")
        device_data = {
            'device_id': 'test_device_123',
            'timestamp': '2025-01-01T10:00:00Z',
            'values': {
                'tension': 230.5,
                'courant': 2.3,
                'puissance': 529.15,
                'etat_switch': True
            }
        }
        
        client.set('device:test_device_123', json.dumps(device_data), ex=60)
        stored_data = json.loads(client.get('device:test_device_123'))
        print(f"✅ JSON stocké: {stored_data['values']['tension']}V")
        
        # Test hash (pour sessions utilisateur)
        print("🔄 Test hash Redis...")
        session_data = {
            'user_id': 'user123',
            'role': 'admin',
            'client_id': 'client456'
        }
        client.hset('session:user123', mapping=session_data)
        retrieved_session = client.hgetall('session:user123')
        print(f"✅ Session: {retrieved_session['role']}")
        
        # Test TTL
        print("🔄 Test TTL...")
        client.set('temp_key', 'temporary', ex=5)
        ttl = client.ttl('temp_key')
        print(f"✅ TTL: {ttl} secondes")
        
        # Informations serveur
        print("\n📊 Informations Redis:")
        info = client.info('server')
        print(f"   Version: {info.get('redis_version')}")
        print(f"   Uptime: {info.get('uptime_in_seconds')} secondes")
        
        memory_info = client.info('memory')
        print(f"   Mémoire utilisée: {memory_info.get('used_memory_human')}")
        
        # Nettoyage
        print("\n🧹 Nettoyage des clés de test...")
        client.delete('sertec_test', 'device:test_device_123', 'session:user123', 'temp_key')
        
        print("\n✅ Tous les tests Redis réussis!")
        print("🎉 Votre configuration Redis est prête pour SERTEC IoT!")
        
        return True
        
    except redis.ConnectionError:
        print("❌ Erreur de connexion Redis")
        print("💡 Vérifiez que Redis est démarré:")
        print("   redis-server --requirepass haadee123!")
        print("   ou")
        print("   docker run -d -p 6379:6379 redis:7 redis-server --requirepass haadee123!")
        return False
        
    except redis.AuthenticationError:
        print("❌ Erreur d'authentification Redis")
        print("💡 Vérifiez le mot de passe dans REDIS_URL")
        print(f"   Actuel: {redis_url}")
        return False
        
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def test_flask_integration():
    """Test d'intégration avec Flask"""
    print("\n" + "=" * 40)
    print("🔄 Test intégration Flask...")
    
    try:
        # Ajouter le chemin parent pour import depuis app/
        import sys
        import os
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Import votre app
        from app import create_app, get_redis, is_redis_available
        
        # Créer l'app
        app = create_app()
        
        with app.app_context():
            # Test helper functions
            redis_client = get_redis()
            available = is_redis_available()
            
            print(f"✅ get_redis(): {'OK' if redis_client else 'None'}")
            print(f"✅ is_redis_available(): {available}")
            
            if redis_client and available:
                # Test rapide
                redis_client.set('flask_test', 'integration_ok', ex=10)
                value = redis_client.get('flask_test')
                print(f"✅ Test Flask-Redis: {value}")
                redis_client.delete('flask_test')
                
                print("🎉 Intégration Flask-Redis réussie!")
                return True
            else:
                print("⚠️ Redis non disponible dans Flask")
                return False
                
    except ImportError:
        print("⚠️ Impossible d'importer l'app Flask")
        print("💡 Assurez-vous que votre app/__init__.py est correct")
        return False
    except Exception as e:
        print(f"❌ Erreur intégration Flask: {e}")
        return False

if __name__ == "__main__":
    # Test Redis seul
    redis_ok = test_redis_simple()
    
    # Test intégration Flask si Redis OK
    if redis_ok:
        flask_ok = test_flask_integration()
        
        if flask_ok:
            print("\n🎯 RÉSULTAT FINAL:")
            print("✅ Redis configuré et fonctionnel")
            print("✅ Intégration Flask réussie")
            print("🚀 Prêt pour utiliser Redis dans vos services!")
        else:
            print("\n🎯 RÉSULTAT FINAL:")
            print("✅ Redis configuré")
            print("⚠️ Problème intégration Flask")
    else:
        print("\n🎯 RÉSULTAT FINAL:")
        print("❌ Configuration Redis à corriger")
        
    print("\n💡 Prochaines étapes:")
    print("1. python test_redis.py")
    print("2. flask run")
    print("3. Visiter http://127.0.0.1:5000/debug/redis")