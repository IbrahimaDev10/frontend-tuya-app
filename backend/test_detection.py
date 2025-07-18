# test_detection.py - VERSION CORRIGÉE
from app import create_app
from app.services.tuya_service import TuyaClient

def test_detection_simple():
    """Test simple de détection avec contexte Flask"""
    
    # ✅ CORRECTION : Créer le contexte Flask
    app = create_app()
    
    with app.app_context():
        try:
            # Import dans le contexte
            from app.services.triphase_detection_service import TriphaseDetectionService
            
            # 1. Connexion Tuya
            tuya_client = TuyaClient()
            if not tuya_client.auto_connect_from_env():
                print("❌ Connexion Tuya impossible")
                return
            
            # 2. Service de détection
            detector = TriphaseDetectionService(tuya_client)
            
            # 3. RAPPORT SANS MODIFICATION (sécurisé)
            print("📋 Génération rapport de détection...")
            report = detector.get_detection_report()
            
            if report.get("success"):
                print(f"✅ RÉSULTATS DÉTECTION:")
                print(f"   Total appareils: {report['summary']['total_devices']}")
                print(f"   Triphasés détectés: {report['summary']['triphase_detected']}")
                print(f"   Monophasés: {report['summary']['monophase_detected']}")
                print(f"   Taux détection: {report['summary']['detection_rate']}%")
                
                # Afficher les triphasés trouvés
                if report['triphase_devices']:
                    print(f"\n🔌 APPAREILS TRIPHASÉS DÉTECTÉS:")
                    for device in report['triphase_devices']:
                        print(f"   📱 {device['name']}")
                        print(f"      Confiance: {device['confidence']}%")
                        print(f"      Indicateurs: {', '.join(device['key_indicators'][:3])}")
                        print()
                else:
                    print("\nℹ️ Aucun appareil triphasé détecté")
                
                print("✅ Ce rapport ne modifie RIEN dans votre base de données")
                
            else:
                print(f"❌ Erreur: {report.get('error')}")
                
        except Exception as e:
            print(f"❌ Erreur dans le contexte: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_detection_simple()