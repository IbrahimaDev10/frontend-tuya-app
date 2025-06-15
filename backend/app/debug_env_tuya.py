# debug_env_tuya_improved.py - Diagnostic complet amélioré

import os
import sys
from pathlib import Path

def debug_environment():
    """Diagnostic complet de l'environnement"""
    
    print("🔍 DIAGNOSTIC COMPLET ENVIRONNEMENT")
    print("=" * 60)
    
    # 1. Informations système
    print("📍 INFORMATIONS SYSTÈME :")
    print(f"   Python: {sys.version}")
    print(f"   Répertoire actuel: {os.getcwd()}")
    print(f"   Fichier script: {__file__}")
    
    # 2. Recherche fichiers .env
    print("\n📁 RECHERCHE FICHIERS .env :")
    current_dir = Path(os.getcwd())
    env_files = list(current_dir.rglob('.env'))
    
    if env_files:
        for env_file in env_files:
            print(f"   ✅ Trouvé: {env_file}")
            print(f"      Taille: {env_file.stat().st_size} bytes")
    else:
        print("   ❌ Aucun fichier .env trouvé")
    
    # 3. Variables d'environnement système
    print("\n🌍 VARIABLES SYSTÈME (avant load_dotenv) :")
    tuya_vars = ['ACCESS_ID', 'ACCESS_KEY', 'USERNAME', 'TUYA_USERNAME', 'PASSWORD', 'TUYA_ENDPOINT', 'COUNTRY_CODE']
    
    for var in tuya_vars:
        value = os.environ.get(var)
        if value:
            if var in ['ACCESS_KEY', 'PASSWORD']:
                masked = value[:4] + "***" + value[-4:] if len(value) > 8 else "***"
                print(f"   ✅ {var}: {masked}")
            else:
                print(f"   ✅ {var}: {value}")
        else:
            print(f"   ❌ {var}: NON DÉFINI")
    
    # 4. Test avec dotenv
    print("\n📋 TEST AVEC DOTENV :")
    try:
        from dotenv import load_dotenv
        
        # Charger depuis le répertoire actuel
        env_loaded = load_dotenv()
        print(f"   load_dotenv() result: {env_loaded}")
        
        # Charger explicitement
        env_file_path = Path(os.getcwd()) / '.env'
        if env_file_path.exists():
            explicit_loaded = load_dotenv(env_file_path)
            print(f"   load_dotenv(explicit): {explicit_loaded}")
            
            # Lire le contenu du fichier
            print(f"\n📄 CONTENU .env ({env_file_path}) :")
            with open(env_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines[:25], 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if any(sensitive in line for sensitive in ['PASSWORD=', 'ACCESS_KEY=']):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                masked_value = value[:4] + "***" + value[-4:] if len(value) > 8 else "***"
                                print(f"   {i:2d}: {key}={masked_value}")
                        else:
                            print(f"   {i:2d}: {line}")
        
        # Variables après dotenv
        print("\n🔄 VARIABLES APRÈS DOTENV :")
        for var in tuya_vars:
            value = os.getenv(var)
            if value:
                if var in ['ACCESS_KEY', 'PASSWORD']:
                    masked = value[:4] + "***" + value[-4:] if len(value) > 8 else "***"
                    print(f"   ✅ {var}: {masked}")
                else:
                    print(f"   ✅ {var}: {value}")
            else:
                print(f"   ❌ {var}: NON DÉFINI")
                
    except ImportError:
        print("   ❌ Module python-dotenv non installé")
        print("   💡 Installez avec: pip install python-dotenv")
    except Exception as e:
        print(f"   ❌ Erreur dotenv: {e}")

def test_tuya_http_client():
    """Test du TuyaClient HTTP (votre implémentation)"""
    print("\n🔗 TEST TUYA CLIENT HTTP (VOTRE IMPLÉMENTATION)")
    print("=" * 50)
    
    access_id = os.getenv('ACCESS_ID')
    access_key = os.getenv('ACCESS_KEY')
    endpoint = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com')
    
    if not all([access_id, access_key]):
        print("   ❌ ACCESS_ID ou ACCESS_KEY manquants")
        return False
    
    try:
        # Import du TuyaClient HTTP
        import sys
        sys.path.append('app/services')
        from tuya_service import TuyaClient
        
        print(f"   📡 Endpoint: {endpoint}")
        print(f"   🔑 Access ID: {access_id[:10]}...")
        
        client = TuyaClient()
        
        # Test connexion
        print("\n   🔌 Test connexion automatique...")
        connected = client.auto_connect_from_env()
        print(f"   🔗 Connexion: {'✅ OK' if connected else '❌ ÉCHEC'}")
        
        if connected:
            # Informations de connexion
            info = client.get_connection_info()
            print(f"\n   📊 Informations connexion:")
            print(f"      - Connecté: {info.get('is_connected')}")
            print(f"      - Token valide: {info.get('token_valid')}")
            print(f"      - UID: {info.get('uid')}")
            print(f"      - Endpoint: {info.get('endpoint')}")
            
            # Test récupération appareils
            print("\n   📱 Test récupération appareils...")
            devices_result = client.get_devices()
            
            if devices_result.get('success'):
                devices = devices_result.get('result', [])
                print(f"   🎯 SUCCÈS ! {len(devices)} appareils trouvés:")
                
                for i, device in enumerate(devices, 1):
                    name = device.get('name', 'Sans nom')
                    device_id = device.get('id', 'Sans ID')
                    online = "🟢" if device.get('isOnline') else "🔴"
                    category = device.get('category', 'N/A')
                    print(f"      {i:2d}. {online} {name}")
                    print(f"          ID: {device_id}")
                    print(f"          Type: {category}")
                
                # Test statut d'un appareil
                if devices:
                    test_device = devices[0]
                    test_id = test_device.get('id')
                    print(f"\n   🧪 Test statut appareil: {test_device.get('name')}")
                    
                    try:
                        status_result = client.get_device_status(test_id)
                        if status_result.get('success'):
                            status_data = status_result.get('result', [])
                            print(f"      ✅ Statut récupéré: {len(status_data)} données")
                            for status in status_data[:3]:
                                code = status.get('code', 'N/A')
                                value = status.get('value', 'N/A')
                                print(f"         - {code}: {value}")
                        else:
                            print(f"      ⚠️ Statut inaccessible: {status_result.get('error', 'Erreur')}")
                    except Exception as e:
                        print(f"      ❌ Erreur test statut: {e}")
                
                return True
            else:
                print(f"   ❌ Erreur récupération: {devices_result.get('error', 'Inconnue')}")
                return False
        else:
            print("   ❌ Connexion impossible")
            return False
            
    except ImportError as e:
        print(f"   ❌ Import TuyaClient échoué: {e}")
        print("   💡 Vérifiez que app/services/tuya_service.py existe")
        return False
    except Exception as e:
        print(f"   ❌ Erreur TuyaClient: {e}")
        import traceback
        print(f"   📋 Traceback: {traceback.format_exc()}")
        return False

def test_tuya_iot_sdk():
    """Test du SDK tuya-iot (pour comparaison)"""
    print("\n🔗 TEST SDK TUYA-IOT (COMPARAISON)")
    print("=" * 40)
    
    username = os.getenv('TUYA_USERNAME') or os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    access_id = os.getenv('ACCESS_ID')
    access_key = os.getenv('ACCESS_KEY')
    endpoint = os.getenv('TUYA_ENDPOINT', 'https://openapi.tuyaeu.com')
    country_code = os.getenv('COUNTRY_CODE', '221')
    
    if not all([access_id, access_key, username, password]):
        print("   ❌ Variables manquantes pour SDK tuya-iot")
        missing = []
        if not access_id: missing.append('ACCESS_ID')
        if not access_key: missing.append('ACCESS_KEY')
        if not username: missing.append('TUYA_USERNAME/USERNAME')
        if not password: missing.append('PASSWORD')
        print(f"   📋 Manquantes: {', '.join(missing)}")
        return False
    
    try:
        from tuya_iot import TuyaOpenAPI
        
        print(f"   👤 Username: {username}")
        print(f"   🌍 Country: {country_code}")
        
        # Test avec différents schemas
        schemas = ["smart_life", "smartlife", "tuya", "Smart Life"]
        
        for schema in schemas:
            try:
                print(f"\n   🧪 Test schema: {schema}")
                api = TuyaOpenAPI(endpoint, access_id, access_key)
                result = api.connect(username, password, country_code, schema)
                
                if result:
                    print(f"      ✅ CONNEXION RÉUSSIE avec {schema}!")
                    
                    # Test simple
                    try:
                        test_response = api.get("/v2.0/cloud/thing/device?page_size=5")
                        if test_response.get('success'):
                            devices = test_response.get('result', [])
                            print(f"      📱 SDK trouve {len(devices)} appareils")
                        else:
                            print(f"      ⚠️ SDK erreur: {test_response.get('msg', 'Inconnue')}")
                    except Exception as e:
                        print(f"      ❌ Erreur test SDK: {e}")
                    
                    return True
                else:
                    print(f"      ❌ Échec avec {schema}")
                    
            except Exception as e:
                print(f"      ❌ Erreur {schema}: {e}")
                continue
        
        print("   ❌ TOUS LES SCHEMAS ONT ÉCHOUÉ")
        return False
        
    except ImportError:
        print("   ❌ Module tuya-iot non installé")
        print("   💡 Installez avec: pip install tuya-iot")
        return False
    except Exception as e:
        print(f"   ❌ Erreur SDK: {e}")
        return False

def test_flask_integration():
    """Test d'intégration Flask"""
    print("\n🌶️ TEST INTÉGRATION FLASK")
    print("=" * 30)
    
    try:
        import sys
        sys.path.append(os.getcwd())
        
        from app import create_app
        app = create_app()
        
        with app.app_context():
            print("   ✅ App Flask créée")
            
            # Test TuyaClient dans contexte Flask
            try:
                from app.services.tuya_service import TuyaClient
                tuya = TuyaClient()
                
                connected = tuya.auto_connect_from_env()
                print(f"   🔗 TuyaClient Flask: {'✅ OK' if connected else '❌ ÉCHEC'}")
                
                if connected:
                    # Test import rapide
                    devices_result = tuya.get_all_devices_with_details()
                    if devices_result.get('success'):
                        devices = devices_result.get('result', [])
                        print(f"   📱 Appareils disponibles: {len(devices)}")
                        print("   🎯 Prêt pour l'import dans l'application !")
                        return True
                    else:
                        print(f"   ❌ Erreur appareils: {devices_result.get('error')}")
                
            except Exception as e:
                print(f"   ❌ Erreur TuyaClient Flask: {e}")
                
    except Exception as e:
        print(f"   ❌ Erreur Flask: {e}")
    
    return False

def main():
    """Fonction principale de diagnostic"""
    print("🚀 DIAGNOSTIC COMPLET TUYA")
    print("=" * 60)
    
    # 1. Diagnostic environnement
    debug_environment()
    
    # 2. Test TuyaClient HTTP (votre implémentation)
    http_success = test_tuya_http_client()
    
    # 3. Test SDK tuya-iot (comparaison)
    sdk_success = test_tuya_iot_sdk()
    
    # 4. Test intégration Flask
    flask_success = test_flask_integration()
    
    # 5. Résumé final
    print("\n" + "=" * 60)
    print("🎯 RÉSUMÉ FINAL :")
    print(f"{'✅' if http_success else '❌'} TuyaClient HTTP: {'OK' if http_success else 'KO'}")
    print(f"{'✅' if sdk_success else '❌'} SDK tuya-iot: {'OK' if sdk_success else 'KO'}")
    print(f"{'✅' if flask_success else '❌'} Intégration Flask: {'OK' if flask_success else 'KO'}")
    
    if http_success:
        print(f"\n🎉 EXCELLENT ! Votre TuyaClient HTTP fonctionne parfaitement !")
        print(f"🚀 Actions recommandées :")
        print(f"   1. Lancez: python app.py")
        print(f"   2. Testez: POST /api/devices/import-tuya")
        print(f"   3. Importez vos appareils dans l'interface")
    else:
        print(f"\n⚠️ PROBLÈMES DÉTECTÉS")
        print(f"🔧 Actions à faire :")
        print(f"   1. Vérifiez vos variables d'environnement")
        print(f"   2. Remplacez tuya_service.py par la version HTTP")
        print(f"   3. Relancez ce diagnostic")

if __name__ == "__main__":
    main()