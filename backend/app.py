import os
from app import create_app

# Créer l'application Flask
app = create_app()

if __name__ == '__main__':
    # Configuration du serveur - On garde le meme style que le code qui exister
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
