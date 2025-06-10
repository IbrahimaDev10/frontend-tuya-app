import sys
import os

# ✅ AJOUT CRITIQUE : Ajouter le répertoire racine au Python path
# Cela permet à app/__init__.py de trouver le module 'routes'
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app import create_app

# Créer l'application Flask
app = create_app()

if __name__ == '__main__':
    # Configuration du serveur - On garde le même style que le code qui existe
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(" Démarrage du serveur SERTEC IoT API")
    print(f" Serveur: http://{host}:{port}")
    print(f" Mode debug: {debug}")
    print(f" Environnement: {os.getenv('FLASK_ENV', 'development')}")
    
    # Garder ton style existant
    app.run(
        host=host,
        port=port,
        debug=debug
    )