from app import create_app, db

def migrate_device_table():
    app = create_app()
    with app.app_context():
        print("🔄 Migration de la table devices...")
        try:
            # Créer toutes les tables selon les modèles actuels
            db.create_all()
            print("✅ Migration terminée")
            
            # Vérifier les colonnes
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('devices')]
            print(f"📋 {len(columns)} colonnes dans la table devices")
            
            return True
        except Exception as e:
            print(f"❌ Erreur migration: {e}")
            return False

if __name__ == "__main__":
    migrate_device_table()