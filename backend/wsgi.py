# run.py (ou le nom de votre fichier de démarrage)

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# --- IMPORTER create_app ET socketio ---
from app import create_app, socketio

# Créer l'application Flask
app = create_app()

if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print("🚀 Démarrage du serveur SERTEC IoT API (avec support WebSocket)")
    print(f"   Serveur: http://{host}:{port}" )
    print(f"   Mode debug: {debug}")
    print(f"   Environnement: {os.getenv('FLASK_ENV', 'development')}")
    
    # -- UTILISER socketio.run() AU LIEU DE app.run() ---
    # C'est ce qui permet au serveur de gérer à la fois les requêtes HTTP classiques
    # et les connexions WebSocket.
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True # Nécessaire pour le reloader de debug avec SocketIO
    )
