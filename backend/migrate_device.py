from app import create_app, db

def migrate_device_table():
    app = create_app()
    with app.app_context():
        print("🔄 Migration de la table devices...")
        try:
            # Créer toutes les tables selon les modèles actuels
            db.create_all()
            print("✅ Migration terminée")
            return True
        except Exception as e:
            print(f"❌ Erreur migration: {e}")
            return False

if __name__ == "__main__":
    migrate_device_table()