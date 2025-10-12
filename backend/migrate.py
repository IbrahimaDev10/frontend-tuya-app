# migrate.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Créer une app Flask minimale SANS eventlet
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

if __name__ == '__main__':
    print("🔄 Exécution des migrations...")
    from flask_migrate import upgrade
    with app.app_context():
        upgrade()
    print("✅ Migrations terminées !")