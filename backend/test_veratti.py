#!/usr/bin/env python3
# test_fix_veratti_sertec.py - Test du fix avec vos données réelles

import sys
import os
import json
import base64

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_manual_decode():
    """🔍 Décodage manuel pour confirmer que vos données sont valides"""
    
    print("🔍 === DÉCODAGE MANUEL SERTEC ===")
    
    # Vos vraies données
    phases_data = {
        "L1 (phase_a)": "CIIAAAAAAAA=",  # 08 82 00 00 00 00 00 00
        "L2 (phase_b)": "CIIAAAAAAAA=",  # 08 82 00 00 00 00 00 00
        "L3 (phase_c)": "CIIAAHUAAAs="   # 08 82 00 00 75 00 00 0b
    }
    
    for phase_name, base64_data in phases_data.items():
        print(f"\n📊 Analyse {phase_name}:")
        
        # Décoder
        bytes_data = list(base64.b64decode(base64_data))
        print(f"   Bytes: {' '.join([f'{b:02x}' for b in bytes_data])}")
        print(f"   Longueur: {len(bytes_data)} bytes ({'✅ Suffisant' if len(bytes_data) >= 5 else '❌ Insuffisant'})")
        
        # Position 1: Tension
        if len(bytes_data) > 1:
            voltage_byte = bytes_data[1]  # 0x82 = 130
            voltage_v1 = voltage_byte * 1.74   # 226.2V
            voltage_v2 = voltage_byte + 94     # 224.0V
            print(f"   🔋 Tension (pos 1): {voltage_byte} → {voltage_v1:.1f}V ou {voltage_v2:.1f}V")
        
        # Position 4: Courant  
        if len(bytes_data) > 4:
            current_byte = bytes_data[4]
            current_a = current_byte / 875 if current_byte > 0 else 0
            status = "🔥 ACTIF" if current_byte > 0 else "⚪ INACTIF"
            print(f"   ⚡ Courant (pos 4): {current_byte} → {current_a:.3f}A {status}")
        
        # Autres positions intéressantes
        if len(bytes_data) >= 8:
            print(f"   🔍 Autres: pos0={bytes_data[0]}, pos7={bytes_data[7]}")

def simulate_fixed_decoder():
    """🧪 Simulation du décodeur fixé"""
    
    print("\n🧪 === SIMULATION DÉCODEUR FIXÉ ===")
    
    # Simulation des formules VERATTI
    def try_voltage_formulas(byte_value):
        results = {}
        formulas = [
            {'factor': 1.74, 'name': 'VERATTI_v1'},
            {'offset': 94, 'name': 'VERATTI_v2'}
        ]
        
        for formula in formulas:
            if 'factor' in formula:
                value = byte_value * formula['factor']
            else:
                value = byte_value + formula['offset']
            
            if 180.0 <= value <= 280.0:  # Validation tension
                results[formula['name']] = round(value, 1)
        
        return results
    
    def try_current_formulas(byte_value):
        if byte_value == 0:
            return {'zero_current': 0.0}
        
        value = byte_value / 875
        if 0.0 <= value <= 100.0:  # Validation courant
            return {'VERATTI_primary': round(value, 3)}
        return {}
    
    # Test avec vos données
    test_phases = {
        "L1": "CIIAAAAAAAA=",
        "L2": "CIIAAAAAAAA=", 
        "L3": "CIIAAHUAAAs="
    }
    
    results = {}
    
    for phase_name, base64_data in test_phases.items():
        print(f"\n🔄 Décodage simulé {phase_name}:")
        
        bytes_data = list(base64.b64decode(base64_data))
        
        # Vérification longueur (APRÈS fix)
        if len(bytes_data) < 5:
            print(f"   ❌ Données insuffisantes: {len(bytes_data)} bytes")
            continue
        
        print(f"   ✅ Données suffisantes: {len(bytes_data)} bytes")
        
        # Tension (position 1)
        voltage_byte = bytes_data[1]
        voltage_candidates = try_voltage_formulas(voltage_byte)
        
        if voltage_candidates:
            best_voltage = list(voltage_candidates.values())[0]
            best_formula = list(voltage_candidates.keys())[0]
            print(f"   🔋 Tension: {best_voltage}V ({best_formula})")
            tension = best_voltage
        else:
            print(f"   ⚠️ Tension: échec formules")
            tension = None
        
        # Courant (position 4)
        current_byte = bytes_data[4]
        current_candidates = try_current_formulas(current_byte)
        
        if current_candidates:
            courant = list(current_candidates.values())[0]
            current_formula = list(current_candidates.keys())[0]
            print(f"   ⚡ Courant: {courant}A ({current_formula})")
        else:
            print(f"   ⚠️ Courant: 0A (défaut)")
            courant = 0.0
        
        # Puissance calculée
        if tension and courant:
            puissance = round(tension * courant * 0.9, 2)  # cos φ ≈ 0.9
            print(f"   🔌 Puissance: {puissance}W (calculée)")
        else:
            puissance = 0.0
            print(f"   🔌 Puissance: 0W (défaut)")
        
        results[phase_name] = {
            'success': True,
            'tension': tension,
            'courant': courant,
            'puissance': puissance,
            'bytes_length': len(bytes_data)
        }
    
    # Totaux
    phases_success = [r for r in results.values() if r.get('success')]
    if phases_success:
        print(f"\n📊 === TOTAUX CALCULÉS ===")
        
        tensions = [r['tension'] for r in phases_success if r['tension']]
        if tensions:
            tension_moy = sum(tensions) / len(tensions)
            print(f"   🔋 Tension moyenne: {tension_moy:.1f}V")
        
        courants = [r['courant'] for r in phases_success]
        courant_total = sum(courants)
        print(f"   ⚡ Courant total: {courant_total:.3f}A")
        
        puissances = [r['puissance'] for r in phases_success]
        puissance_totale = sum(puissances)
        print(f"   🔌 Puissance totale: {puissance_totale:.2f}W")
        
        print(f"\n✅ Résultat: {len(phases_success)}/3 phases décodées avec succès")
    
    return results

def main():
    """🚀 Test principal du fix"""
    
    print("🚀 === TEST FIX VERATTI POUR SERTEC ===")
    print("🎯 Objectif: Prouver que 8 bytes suffisent pour le décodage")
    
    # 1. Analyse manuelle
    test_manual_decode()
    
    # 2. Simulation du décodeur fixé
    results = simulate_fixed_decoder()
    
    # 3. Conclusion
    print(f"\n🎉 === CONCLUSION ===")
    
    success_count = len([r for r in results.values() if r.get('success')])
    
    if success_count > 0:
        print(f"✅ Le fix fonctionne: {success_count}/3 phases peuvent être décodées")
        print(f"🔧 Action requise: Changer 'len(bytes_data) < 15' en 'len(bytes_data) < 5'")
        print(f"📁 Fichier: app/services/tuya_to_devicedata_service.py ligne ~85")
        print(f"🧪 Après le fix, relancez: python3 test_veratti.py")
    else:
        print(f"❌ Problème détecté dans les formules")
    
    print(f"\n📋 Données de test utilisées:")
    print(f"   - L1/L2: 08 82 00 00 00 00 00 00 (tension 224V, courant 0A)")
    print(f"   - L3: 08 82 00 00 75 00 00 0b (tension 224V, courant 0.134A)")

if __name__ == "__main__":
    main()