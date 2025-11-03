# wsgi.py
import eventlet
eventlet.monkey_patch() 

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    # ✅ En mode debug avec eventlet, il vaut mieux ne pas utiliser debug=True
    print("🚀 Démarrage du serveur SERTEC IoT API (avec support WebSocket)")
    print(f"   Serveur: http://{host}:{port}")
    print(f"   Environnement: {os.getenv('FLASK_ENV', 'development')}")
    
    socketio.run(
        app,
        host=host,
        port=port,
        debug=False,  # ← Désactiver le mode debug Flask
        use_reloader=False,
        log_output=True
    )