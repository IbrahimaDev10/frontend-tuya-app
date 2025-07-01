from app import create_app, db
import sqlalchemy as sa

def complete_migration():
    """Migration complète pour finaliser la table devices"""
    
    app = create_app()
    with app.app_context():
        print("🔄 Migration finale de la table devices...")
        
        try:
            connection = db.engine.connect()
            
            # Liste des colonnes encore manquantes d'après l'erreur SQL
            missing_columns = [
                # Ces colonnes manquent dans votre table actuelle
                "ALTER TABLE devices ADD COLUMN protection_tension_config JSON NULL",
                "ALTER TABLE devices ADD COLUMN protection_desequilibre_config JSON NULL",
                
                # Vérifier si ces colonnes manquent aussi
                "ALTER TABLE devices ADD COLUMN seuil_temperature_max FLOAT NULL DEFAULT 60.0",
            ]
            
            success_count = 0
            
            for sql_statement in missing_columns:
                column_name = sql_statement.split("ADD COLUMN")[1].split()[0]
                
                try:
                    connection.execute(sa.text(sql_statement))
                    print(f"  ✅ Ajouté: {column_name}")
                    success_count += 1
                    
                except Exception as e:
                    if "Duplicate column name" in str(e) or "already exists" in str(e):
                        print(f"  ℹ️ Existe déjà: {column_name}")
                    else:
                        print(f"  ❌ Erreur {column_name}: {e}")
            
            connection.close()
            
            print(f"\n📊 Migration terminée: {success_count} colonnes ajoutées")
            
            # Vérifier que tout fonctionne maintenant
            print("\n🧪 Test du modèle Device...")
            
            from app.models.device import Device
            
            # Test simple query
            device = Device.get_by_tuya_id('bf64f01f2b7e204bbczvq6')
            if device:
                print(f"  ✅ Device trouvé: {device.nom_appareil}")
            else:
                print("  ℹ️ Aucun device avec cet ID trouvé")
            
            # Test count
            count = Device.query.count()
            print(f"  ✅ Total devices: {count}")
            
            print("\n🎉 Migration réussie ! L'import Tuya devrait maintenant fonctionner.")
            return True
            
        except Exception as e:
            print(f"❌ Erreur migration: {e}")
            return False

def verify_table_structure():
    """Vérifier la structure finale de la table"""
    
    app = create_app()
    with app.app_context():
        print("🔍 Vérification structure table devices...")
        
        try:
            inspector = db.inspect(db.engine)
            columns = inspector.get_columns('devices')
            
            print(f"📋 Total colonnes: {len(columns)}")
            
            # Colonnes critiques à vérifier
            critical_columns = [
                'protection_automatique_active',
                'protection_courant_config', 
                'protection_puissance_config',
                'protection_temperature_config',
                'protection_tension_config',  # ← Cette colonne cause l'erreur
                'protection_desequilibre_config',
                'programmation_active',
                'type_systeme'
            ]
            
            column_names = [col['name'] for col in columns]
            
            print("\n🔍 Vérification colonnes critiques:")
            missing_critical = []
            
            for col in critical_columns:
                if col in column_names:
                    print(f"  ✅ {col}")
                else:
                    print(f"  ❌ {col} MANQUANTE")
                    missing_critical.append(col)
            
            if missing_critical:
                print(f"\n⚠️ Colonnes manquantes: {missing_critical}")
                return False
            else:
                print("\n✅ Toutes les colonnes critiques sont présentes")
                return True
                
        except Exception as e:
            print(f"❌ Erreur vérification: {e}")
            return False

def fix_enum_columns():
    """Corriger les colonnes ENUM si nécessaire"""
    
    app = create_app()
    with app.app_context():
        print("🔄 Vérification et correction des colonnes ENUM...")
        
        try:
            connection = db.engine.connect()
            
            # Vérifier et corriger les colonnes ENUM
            enum_fixes = [
                # Statut assignation - convertir en ENUM si nécessaire
                "ALTER TABLE devices MODIFY COLUMN statut_assignation ENUM('non_assigne', 'assigne') NOT NULL DEFAULT 'non_assigne'",
                
                # Type système - convertir en ENUM si nécessaire  
                "ALTER TABLE devices MODIFY COLUMN type_systeme ENUM('monophase', 'triphase') NOT NULL DEFAULT 'monophase'",
                
                # Protection status - convertir en ENUM si nécessaire
                "ALTER TABLE devices MODIFY COLUMN protection_status ENUM('normal', 'protected', 'error') NOT NULL DEFAULT 'normal'",
            ]
            
            for sql_statement in enum_fixes:
                try:
                    connection.execute(sa.text(sql_statement))
                    column_name = sql_statement.split("COLUMN")[1].split()[0]
                    print(f"  ✅ ENUM corrigé: {column_name}")
                    
                except Exception as e:
                    # Les erreurs ENUM sont souvent normales si déjà correct
                    column_name = sql_statement.split("COLUMN")[1].split()[0]
                    print(f"  ℹ️ {column_name}: {e}")
            
            connection.close()
            print("✅ Correction ENUM terminée")
            return True
            
        except Exception as e:
            print(f"❌ Erreur correction ENUM: {e}")
            return False

def reset_sqlalchemy_cache():
    """Forcer SQLAlchemy à recharger le schéma"""
    
    app = create_app()
    with app.app_context():
        print("🔄 Reset cache SQLAlchemy...")
        
        try:
            # Forcer la réinitialisation des métadonnées
            db.engine.dispose()
            
            # Recréer la connexion
            db.create_all()
            
            print("✅ Cache SQLAlchemy réinitialisé")
            return True
            
        except Exception as e:
            print(f"❌ Erreur reset cache: {e}")
            return False

if __name__ == "__main__":
    print("🚀 Migration finale table devices")
    print("=" * 50)
    
    # 1. Vérifier structure actuelle
    print("\n1️⃣ VÉRIFICATION STRUCTURE ACTUELLE")
    structure_ok = verify_table_structure()
    
    # 2. Migration des colonnes manquantes
    print("\n2️⃣ AJOUT COLONNES MANQUANTES")
    migration_ok = complete_migration()
    
    # 3. Correction des ENUM
    print("\n3️⃣ CORRECTION COLONNES ENUM")
    enum_ok = fix_enum_columns()
    
    # 4. Reset cache SQLAlchemy
    print("\n4️⃣ RESET CACHE SQLALCHEMY")
    cache_ok = reset_sqlalchemy_cache()
    
    # 5. Vérification finale
    print("\n5️⃣ VÉRIFICATION FINALE")
    final_check = verify_table_structure()
    
    if migration_ok and final_check:
        print("\n🎉 MIGRATION RÉUSSIE!")
        print("\nVous pouvez maintenant:")
        print("  1. Redémarrer votre application: python app.py")
        print("  2. Tester l'import Tuya dans Postman")
        print("     POST /api/devices/import-tuya")
    else:
        print("\n❌ Migration échouée - Vérifiez les erreurs ci-dessus")