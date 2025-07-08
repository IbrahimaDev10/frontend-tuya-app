import os
import json
from dotenv import load_dotenv

# Assurez-vous que tuya_service.py est dans le même répertoire ou dans votre PYTHONPATH
# Si tuya_service.py est dans app/services/, vous devrez ajuster l'importation
# Par exemple: from app.services.tuya_service import TuyaClient
# Pour ce test simple, supposons qu'il est accessible directement.
from app.services.tuya_service import TuyaClient

def run_datapoint_test():
    load_dotenv() # Charge les variables d'environnement depuis .env
    
    tuya_client = TuyaClient()
    
    # 1. Tenter de se connecter à Tuya
    print("Tentative de connexion à Tuya...")
    if not tuya_client.auto_connect_from_env():
        print("❌ Échec de la connexion à Tuya. Vérifiez vos ACCESS_ID, ACCESS_KEY et TUYA_ENDPOINT dans .env")
        return
    print("✅ Connecté à Tuya.")
    
    # 2. Récupérer la liste des appareils pour trouver un ID
    print("\nRécupération de la liste des appareils...")
    devices_list_response = tuya_client.get_devices()
    if not devices_list_response.get("success"):
        print(f"❌ Échec de la récupération de la liste des appareils: {devices_list_response.get('error')}")
        return
    
    devices = devices_list_response.get("result", [])
    if not devices:
        print("⚠️ Aucuns appareils trouvés dans votre compte Tuya.")
        return
    
    print(f"Appareils trouvés ({len(devices)}):")
    for i, device in enumerate(devices):
        print(f"  {i+1}. Nom: {device.get('name')}, ID: {device.get('id')}, Statut: {'En ligne' if device.get('isOnline') else 'Hors ligne'}")
    
    # Demander à l'utilisateur de choisir un appareil
    selected_device_id = None
    while selected_device_id is None:
        try:
            choice = input("\nEntrez le numéro de l'appareil à tester (ou 'q' pour quitter): ")
            if choice.lower() == 'q':
                return
            
            idx = int(choice) - 1
            if 0 <= idx < len(devices):
                selected_device_id = devices[idx].get('id')
            else:
                print("Numéro invalide. Veuillez réessayer.")
        except ValueError:
            print("Entrée invalide. Veuillez entrer un numéro.")
    
    print(f"\n--- Test de l'appareil ID: {selected_device_id} ---")
    
    # 3. Appeler get_device_status pour obtenir les datapoints bruts
    print("\nAppel de tuya_client.get_device_status (réponse brute de l'API Tuya)...")
    raw_status_response = tuya_client.get_device_status(selected_device_id)
    print(json.dumps(raw_status_response, indent=2))
    
    if raw_status_response.get("success"):
        status_data = raw_status_response.get("result", [])
        print("\nDatapoints bruts trouvés:")
        found_energy_data = False
        for item in status_data:
            code = item.get("code")
            value = item.get("value")
            print(f"  Code: {code}, Valeur: {value}")
            if code in ["cur_voltage", "cur_current", "cur_power", "add_ele", "temp_current", "temp_power", "temp_voltage"]:
                found_energy_data = True
        
        if not found_energy_data:
            print("\n⚠️ Aucun datapoint de courant, puissance ou énergie (cur_current, cur_power, add_ele, etc.) trouvé pour cet appareil.")
            print("Cela signifie que l'appareil ne rapporte pas ces données via l'API Tuya.")
    else:
        print(f"❌ Échec de la récupération du statut brut: {raw_status_response.get('error')}")
    
    # 4. Appeler get_device_current_values pour voir les valeurs mappées
    print("\nAppel de tuya_client.get_device_current_values (valeurs mappées)...")
    mapped_values_response = tuya_client.get_device_current_values(selected_device_id)
    print(json.dumps(mapped_values_response, indent=2))
    
    if mapped_values_response.get("success"):
        values = mapped_values_response.get("values", {})
        print("\nValeurs mappées:")
        for key, val in values.items():
            print(f"  {key}: {val}")
        
        if "courant" not in values and "puissance" not in values and "energie" not in values:
            print("\n⚠️ Les valeurs 'courant', 'puissance', 'energie' ne sont pas présentes dans les valeurs mappées.")
            print("Ceci est probablement dû à l'absence de ces datapoints bruts de l'appareil.")
    else:
        print(f"❌ Échec de la récupération des valeurs mappées: {mapped_values_response.get('error')}")

if __name__ == "__main__":
    run_datapoint_test()
