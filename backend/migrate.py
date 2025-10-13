#!/usr/bin/env python
# migrate.py - Script de migration sans eventlet
import os
import sys

# Ajouter le répertoire backend au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# IMPORTANT : Configurer matplotlib AVANT tout import
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour serveur sans display

print("🔄 Démarrage des migrations de la base de données...")

# Importer Flask et les extensions SANS eventlet
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade

# Créer une app Flask minimale
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialiser les extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Exécuter les migrations
try:
    with app.app_context():
        print("📊 Exécution de 'flask db upgrade'...")
        upgrade()
        print("✅ Migrations terminées avec succès !")
        
except Exception as e:
    print(f"❌ Erreur lors des migrations : {e}")
    sys.exit(1)
    
finally:
    # Fermer proprement toutes les connexions
    print("🧹 Nettoyage des connexions...")
    db.session.remove()
    db.engine.dispose()
    print("✅ Connexions fermées proprement")

# Sortie propre
sys.exit(0)