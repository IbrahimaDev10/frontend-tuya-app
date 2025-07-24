# diagnose_with_client.py


import os
from dotenv import load_dotenv

# Importer votre nouveau TuyaClient
from app.services.tuya_service import TuyaClient, test_tuya_complete
import json

def analyze_device_for_phase_type(device_id, client):
    """
    Analyse un appareil en utilisant TuyaClient pour déterminer s'il est 
    monophasé ou triphasé.
    """
    print(f"\n🔬 Lancement de l'analyse pour l'appareil : {device_id}")
    
    # 1. Utiliser la méthode existante pour récupérer les valeurs
    response = client.get_device_current_values(device_id)
    
    if not response.get("success"):
        print(f"   ❌ Erreur lors de la récupération des données : {response.get('error')}")
        return

    # 2. Extraire les données brutes et les valeurs mappées
    raw_status = response.get("raw_status", [])
    mapped_values = response.get("values", {})
    
    print("\n--------------- DONNÉES BRUTES DE L'APPAREIL ---------------")
    # Affiche les données brutes pour un contrôle manuel
    for status in raw_status:
        code = status.get('code')
        value = status.get('value')
        print(f"   - Code: {code:<25} | Valeur: {value}")
    print("----------------------------------------------------------")

    # 3. Logique de diagnostic
    # On recherche les clés spécifiques au triphasé que votre client mappe déjà.
    three_phase_keys = ['power_a', 'power_b', 'power_c']
    
    # On peut aussi chercher des codes qui contiennent des indicateurs de phase
    # comme "voltage_a", "current_b", etc.
    three_phase_indicators = ['_a', '_b', '_c', '_1', '_2', '_3']
    
    found_three_phase_evidence = []

    # Vérifier dans les clés mappées par votre client
    for key in three_phase_keys:
        if key in mapped_values:
            found_three_phase_evidence.append(key)

    # Vérifier dans tous les codes bruts pour être exhaustif
    all_codes = mapped_values.keys()
    for code in all_codes:
        for indicator in three_phase_indicators:
            if code.endswith(indicator):
                if code not in found_three_phase_evidence:
                    found_three_phase_evidence.append(code)

    print("\n================== DIAGNOSTIC DU SYSTÈME ==================")
    if found_three_phase_evidence:
        print("📊 Conclusion : L'appareil est très probablement **TRIPHASÉ**.")
        print("\n   Raison : Les codes de statut suivants, indiquant une mesure")
        print("   par phase, ont été détectés :")
        for evidence in set(found_three_phase_evidence): # 'set' pour éviter les doublons
            print(f"     - {evidence}")
    else:
        print("📊 Conclusion : L'appareil semble être **MONOPHASÉ**.")
        print("\n   Raison : Aucun des codes de statut ne suggère une mesure")
        print("   distincte pour plusieurs phases (ex: 'phase_a', 'voltage_b').")
    print("==========================================================")


def main():
    """
    Fonction principale pour lancer le diagnostic.
    """
    print("==========================================================")
    print("=   Diagnostic de Phase avec TuyaClient (Basé sur votre service)   =")
    print("==========================================================\n")

    # Initialisation de votre client
    client = TuyaClient()
    if not client.auto_connect_from_env():
        print("❌ La connexion initiale via TuyaClient a échoué. Vérifiez vos identifiants.")
        return

    # Récupération des appareils via votre client
    devices_response = client.get_all_devices_with_details()
    if not devices_response.get("success"):
        print("❌ Impossible de récupérer la liste des appareils.")
        return
        
    devices = devices_response.get("result", [])
    if not devices:
        print("ℹ️ Aucun appareil n'a été trouvé sur votre compte.")
        return

    print("\n👤 Veuillez choisir l'appareil à diagnostiquer :\n")
    for i, device in enumerate(devices):
        online_status = "🟢 En ligne" if device.get('online_status') == "Online" else "🔴 Hors ligne"
        print(f"   [{i}] - {device.get('name', 'Nom inconnu')} ({online_status})")

    try:
        choice_index = int(input("\n   Entrez le numéro de l'appareil : "))
        if not 0 <= choice_index < len(devices):
            print("❌ Choix invalide.")
            return
        chosen_device = devices[choice_index]
    except (ValueError, IndexError):
        print("❌ Entrée invalide. Veuillez entrer un numéro de la liste.")
        return

    device_id = chosen_device.get('id')
    
    # Lancer l'analyse sur l'appareil choisi
    analyze_device_for_phase_type(device_id, client)


if __name__ == "__main__":
    main()
