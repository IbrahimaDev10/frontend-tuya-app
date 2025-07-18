# workflow_complet.py - IMPORT + DÉTECTION + CORRECTION AUTOMATIQUE
# ✅ Script intégré qui fait tout dans l'ordre optimal

from app import create_app
from app.services.device_service import DeviceService
from app.services.tuya_service import TuyaClient
from app.services.triphase_detection_service import TriphaseDetectionService
from app.models.device import Device
from app import db
import json
from datetime import datetime

def workflow_complet_detection_triphase(force_import=True, auto_correct=True):
    """
    Workflow complet :
    1. Import/Sync des appareils depuis Tuya
    2. Détection des appareils triphasés
    3. Correction automatique des types
    """
    
    app = create_app()
    with app.app_context():
        try:
            print("🚀 === WORKFLOW COMPLET DÉTECTION TRIPHASÉ ===")
            print(f"📥 Import forcé: {'✅' if force_import else '❌'}")
            print(f"🔧 Correction auto: {'✅' if auto_correct else '❌'}")
            
            resultats = {
                'import_success': False,
                'detection_success': False,
                'correction_success': False,
                'statistiques': {}
            }
            
            # =================== ÉTAPE 1: IMPORT/SYNC ===================
            print(f"\n📥 === ÉTAPE 1: IMPORT ET SYNCHRONISATION ===")
            
            device_service = DeviceService()
            
            if force_import:
                print("🔄 Import complet depuis Tuya...")
                import_result = device_service.import_tuya_devices(use_cache=False, force_refresh=True)
                
                if import_result.get("success"):
                    stats_import = import_result.get("statistiques", {})
                    print(f"✅ Import réussi:")
                    print(f"   📊 Importés: {stats_import.get('appareils_importes', 0)}")
                    print(f"   🔄 Mis à jour: {stats_import.get('appareils_mis_a_jour', 0)}")
                    print(f"   🟢 En ligne: {stats_import.get('online_count', 0)}")
                    print(f"   🔴 Hors ligne: {stats_import.get('offline_count', 0)}")
                    
                    resultats['import_success'] = True
                    resultats['statistiques']['import'] = stats_import
                else:
                    print(f"❌ Erreur import: {import_result.get('error')}")
                    return resultats
            else:
                print("⏭️ Import ignoré - utilisation données existantes")
                resultats['import_success'] = True
            
            # Sync complète pour s'assurer que tout est à jour
            print("\n🔄 Synchronisation complète...")
            sync_result = device_service.sync_all_devices(force_refresh=True)
            
            if sync_result.get("success"):
                final_stats = sync_result.get("final_stats", {})
                print(f"✅ Sync réussie:")
                print(f"   📊 Total actifs: {final_stats.get('total', 0)}")
                print(f"   🟢 En ligne: {final_stats.get('online', 0)}")
                print(f"   🔴 Hors ligne: {final_stats.get('offline', 0)}")
                
                resultats['statistiques']['sync'] = final_stats
            else:
                print(f"⚠️ Sync partiellement échouée: {sync_result.get('error')}")
            
            # =================== ÉTAPE 2: DÉTECTION TRIPHASÉ ===================
            print(f"\n🔍 === ÉTAPE 2: DÉTECTION APPAREILS TRIPHASÉS ===")
            
            # Créer client Tuya pour détection
            tuya_client = TuyaClient()
            if not tuya_client.auto_connect_from_env():
                print("❌ Connexion TuyaClient pour détection impossible")
                return resultats
            
            # Service de détection
            detection_service = TriphaseDetectionService(tuya_client)
            
            # Générer rapport complet
            print("📊 Analyse de tous les appareils...")
            rapport_detection = detection_service.get_detection_report(save_to_db=False)
            
            if not rapport_detection.get("success"):
                print(f"❌ Erreur détection: {rapport_detection.get('error')}")
                return resultats
            
            resultats['detection_success'] = True
            
            # Extraire résultats
            summary = rapport_detection.get("summary", {})
            triphase_devices = rapport_detection.get("triphase_devices", [])
            
            print(f"✅ Détection terminée:")
            print(f"   📊 Appareils analysés: {summary.get('total_devices', 0)}")
            print(f"   ⚡ Triphasés détectés: {summary.get('triphase_detected', 0)}")
            print(f"   🔌 Monophasés: {summary.get('monophase_detected', 0)}")
            print(f"   📈 Taux détection: {summary.get('detection_rate', 0)}%")
            
            resultats['statistiques']['detection'] = summary
            
            # Filtrer appareils nécessitant correction
            devices_to_correct = [d for d in triphase_devices if d.get('needs_update', False)]
            high_confidence = [d for d in devices_to_correct if d.get('confidence', 0) >= 70]
            
            print(f"\n🔧 Appareils à corriger:")
            print(f"   📊 Total nécessitant correction: {len(devices_to_correct)}")
            print(f"   🎯 Haute confiance (≥70%): {len(high_confidence)}")
            
            if not devices_to_correct:
                print("✅ Aucune correction nécessaire - Tous les appareils sont bien classés !")
                resultats['correction_success'] = True
                return resultats
            
            # Afficher détails des appareils à corriger
            if devices_to_correct:
                print(f"\n📋 === APPAREILS À CORRIGER ===")
                for i, device in enumerate(devices_to_correct[:5], 1):  # Top 5
                    name = device.get('name', 'Inconnu')[:40]
                    confidence = device.get('confidence', 0)
                    current_type = device.get('current_db_type', 'unknown')
                    
                    confidence_emoji = "🎯" if confidence >= 80 else "⚠️"
                    
                    print(f"   {confidence_emoji} [{i}] {name}")
                    print(f"        Confiance: {confidence}% | Actuel: {current_type} → triphase")
                
                if len(devices_to_correct) > 5:
                    print(f"   ... et {len(devices_to_correct) - 5} autres")
            
            # =================== ÉTAPE 3: CORRECTION ===================
            if auto_correct and devices_to_correct:
                print(f"\n🔧 === ÉTAPE 3: CORRECTION AUTOMATIQUE ===")
                
                corrections_effectuees = 0
                erreurs_correction = 0
                
                # Corriger seulement les appareils haute confiance
                for device_info in high_confidence:
                    device_id = device_info.get('device_id')
                    device_name = device_info.get('name', 'Inconnu')
                    confidence = device_info.get('confidence', 0)
                    
                    try:
                        print(f"🔧 Correction: {device_name[:30]}... ({confidence}%)")
                        
                        # Récupérer appareil
                        device = Device.get_by_tuya_id(device_id)
                        if not device:
                            print(f"   ❌ Appareil non trouvé en base")
                            erreurs_correction += 1
                            continue
                        
                        # Effectuer correction
                        old_type = device.type_systeme
                        device.type_systeme = 'triphase'
                        
                        # Configurer seuils triphasés complets
                        device.seuil_tension_l1_min = 200.0
                        device.seuil_tension_l1_max = 250.0
                        device.seuil_tension_l2_min = 200.0
                        device.seuil_tension_l2_max = 250.0
                        device.seuil_tension_l3_min = 200.0
                        device.seuil_tension_l3_max = 250.0
                        
                        device.seuil_courant_l1_max = 20.0
                        device.seuil_courant_l2_max = 20.0
                        device.seuil_courant_l3_max = 20.0
                        
                        device.seuil_desequilibre_tension = 2.0
                        device.seuil_desequilibre_courant = 10.0
                        device.seuil_facteur_puissance_min = 0.85
                        
                        # Sauvegarder
                        db.session.commit()
                        
                        print(f"   ✅ {old_type} → triphase")
                        corrections_effectuees += 1
                        
                    except Exception as e:
                        print(f"   ❌ Erreur: {e}")
                        db.session.rollback()
                        erreurs_correction += 1
                
                print(f"\n📊 === RÉSULTATS CORRECTION ===")
                print(f"   ✅ Corrections réussies: {corrections_effectuees}")
                print(f"   ❌ Erreurs: {erreurs_correction}")
                
                if corrections_effectuees > 0:
                    resultats['correction_success'] = True
                    resultats['statistiques']['correction'] = {
                        'corrections_effectuees': corrections_effectuees,
                        'erreurs': erreurs_correction,
                        'taux_succes': round(corrections_effectuees / (corrections_effectuees + erreurs_correction) * 100, 1) if (corrections_effectuees + erreurs_correction) > 0 else 0
                    }
            elif auto_correct:
                print(f"\n✅ === AUCUNE CORRECTION NÉCESSAIRE ===")
                resultats['correction_success'] = True
            else:
                print(f"\n⏭️ === CORRECTION DÉSACTIVÉE ===")
                print(f"   🔍 {len(devices_to_correct)} appareils pourraient être corrigés")
                print(f"   💡 Utilisez auto_correct=True pour les corriger")
            
            # =================== ÉTAPE 4: VÉRIFICATION FINALE ===================
            print(f"\n📊 === VÉRIFICATION FINALE ===")
            
            # Recompter après corrections
            total_final = Device.query.filter_by(actif=True).count()
            monophase_final = Device.query.filter_by(type_systeme='monophase', actif=True).count()
            triphase_final = Device.query.filter_by(type_systeme='triphase', actif=True).count()
            
            print(f"   📈 État final:")
            print(f"     📊 Total actifs: {total_final}")
            print(f"     🔌 Monophasés: {monophase_final} ({(monophase_final/total_final*100):.1f}%)" if total_final > 0 else "     🔌 Monophasés: 0")
            print(f"     ⚡ Triphasés: {triphase_final} ({(triphase_final/total_final*100):.1f}%)" if total_final > 0 else "     ⚡ Triphasés: 0")
            
            resultats['statistiques']['final'] = {
                'total': total_final,
                'monophase': monophase_final,
                'triphase': triphase_final
            }
            
            # =================== RÉSUMÉ GLOBAL ===================
            print(f"\n🎯 === RÉSUMÉ GLOBAL ===")
            print(f"   📥 Import: {'✅ OK' if resultats['import_success'] else '❌ ERREUR'}")
            print(f"   🔍 Détection: {'✅ OK' if resultats['detection_success'] else '❌ ERREUR'}")
            print(f"   🔧 Correction: {'✅ OK' if resultats['correction_success'] else '❌ ERREUR'}")
            
            if all([resultats['import_success'], resultats['detection_success'], resultats['correction_success']]):
                print(f"\n🎉 === WORKFLOW TERMINÉ AVEC SUCCÈS ===")
                print(f"   ⚡ {triphase_final} appareils triphasés configurés")
                print(f"   📊 Base de données mise à jour")
                print(f"   🚀 Système prêt pour analyse triphasée")
            else:
                print(f"\n⚠️ === WORKFLOW PARTIELLEMENT RÉUSSI ===")
                print(f"   🔍 Vérifiez les étapes en erreur ci-dessus")
            
            return resultats
            
        except Exception as e:
            print(f"❌ Erreur workflow global: {e}")
            import traceback
            traceback.print_exc()
            return resultats

def verification_post_workflow():
    """Vérifier l'état après le workflow"""
    
    app = create_app()
    with app.app_context():
        try:
            print("🔍 === VÉRIFICATION POST-WORKFLOW ===")
            
            # Statistiques générales
            total = Device.query.filter_by(actif=True).count()
            assignes = Device.query.filter_by(statut_assignation='assigne', actif=True).count()
            en_ligne = Device.query.filter_by(en_ligne=True, actif=True).count()
            
            monophase = Device.query.filter_by(type_systeme='monophase', actif=True).count()
            triphase = Device.query.filter_by(type_systeme='triphase', actif=True).count()
            
            print(f"\n📊 État général:")
            print(f"   📱 Total appareils actifs: {total}")
            print(f"   ✅ Assignés: {assignes} ({(assignes/total*100):.1f}%)" if total > 0 else "   ✅ Assignés: 0")
            print(f"   🟢 En ligne: {en_ligne} ({(en_ligne/total*100):.1f}%)" if total > 0 else "   🟢 En ligne: 0")
            
            print(f"\n⚡ Répartition par type:")
            print(f"   🔌 Monophasés: {monophase} ({(monophase/total*100):.1f}%)" if total > 0 else "   🔌 Monophasés: 0")
            print(f"   ⚡ Triphasés: {triphase} ({(triphase/total*100):.1f}%)" if total > 0 else "   ⚡ Triphasés: 0")
            
            # Détails appareils triphasés
            if triphase > 0:
                devices_triphase = Device.query.filter_by(type_systeme='triphase', actif=True).all()
                print(f"\n⚡ === APPAREILS TRIPHASÉS CONFIGURÉS ===")
                
                for i, device in enumerate(devices_triphase, 1):
                    status = "✅" if device.statut_assignation == 'assigne' else "⚪"
                    online = "🟢" if device.en_ligne else "🔴"
                    seuils_ok = "🔧" if device.seuil_tension_l1_min else "❌"
                    
                    print(f"   [{i:2d}] {device.nom_appareil[:35]}")
                    print(f"        {status} {online} {seuils_ok} | ID: {device.tuya_device_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur vérification: {e}")
            return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        action = sys.argv[1]
        
        if action == "complet":
            # Workflow complet avec import et correction
            workflow_complet_detection_triphase(force_import=True, auto_correct=True)
            
        elif action == "sans-import":
            # Sans import (utilise données existantes)
            workflow_complet_detection_triphase(force_import=False, auto_correct=True)
            
        elif action == "detection-seule":
            # Détection sans correction
            workflow_complet_detection_triphase(force_import=True, auto_correct=False)
            
        elif action == "verification":
            # Vérification post-workflow
            verification_post_workflow()
            
        else:
            print("Usage:")
            print("  python workflow_complet.py complet          # Import + Détection + Correction")
            print("  python workflow_complet.py sans-import      # Détection + Correction (sans import)")
            print("  python workflow_complet.py detection-seule  # Import + Détection seule")
            print("  python workflow_complet.py verification     # Vérifier état final")
            
    else:
        print("🚀 === WORKFLOW COMPLET PAR DÉFAUT ===")
        print("Exécution: Import + Détection + Correction")
        
        # Workflow complet par défaut
        workflow_complet_detection_triphase(force_import=True, auto_correct=True)
        
        print("\n" + "="*60 + "\n")
        
        # Vérification finale
        verification_post_workflow()