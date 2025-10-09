# backend/migrations/env.py - NOUVEAU CONTENU COMPLET

from logging.config import fileConfig
from alembic import context
from app import create_app, db  # Importer notre factory et notre objet db

# Créer une instance de l'application pour ce contexte de migration.
# C'est cette ligne qui va forcer l'importation des modèles.
app = create_app()

# Configurer Alembic
config = context.config
fileConfig(config.config_file_name)

# Définir la cible des métadonnées. Maintenant, db.metadata n'est plus vide !
target_metadata = db.metadata

def run_migrations_offline():
    """Exécution hors ligne (non utilisée ici, mais gardée pour la complétude)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Exécution en ligne."""
    # Utiliser le moteur de base de données de notre application
    with app.app_context():
        connectable = db.engine
        with connectable.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata
            )
            with context.begin_transaction():
                context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()