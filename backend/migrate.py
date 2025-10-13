#!/usr/bin/env python
# migrate.py - Script de migration sans eventlet
import os
import sys

# Ajouter le répertoire backend au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🔄 Démarrage des migrations de la base de données...")

# Importer Flask et les extensions SANS eventlet
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade

# Créer une app Flask minimale
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialiser les extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Exécuter les migrations
with app.app_context():
    print("📊 Exécution de 'flask db upgrade'...")
    upgrade()
    print("✅ Migrations terminées avec succès !")