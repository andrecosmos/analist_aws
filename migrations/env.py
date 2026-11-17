import sys
from pathlib import Path
from logging.config import fileConfig

# Injeta a raiz do projeto no PATH do Python
RAIZ_DO_PROJETO = Path(__file__).resolve().parent.parent
if str(RAIZ_DO_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_DO_PROJETO))

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# 🌟 CONFIRME ESTE IMPORT: apontando para o arquivo correto dentro de app/models/models.py
from app.models.models import Base 
import os
from dotenv import load_dotenv

load_dotenv()


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 🌟 CONFIRME ESTA LINHA: Ela entrega as tabelas para o Alembic ler
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    
    # Captura a URL da variável de ambiente carregada
    url_do_banco = os.getenv("DATABASE_URL")
    
    if not url_do_banco:
        raise ValueError("A variável de ambiente 'DATABASE_URL' não foi encontrada. Verifique seu arquivo .env!")
        
    # Correção automática do prefixo do Supabase para o SQLAlchemy aceitar
    if url_do_banco.startswith("postgres://"):
        url_do_banco = url_do_banco.replace("postgres://", "postgresql://", 1)

    # Injeta a URL correta dinamicamente na configuração do Alembic
    config_section = config.get_section(config.config_ini_section, {})
    config_section["sqlalchemy.url"] = url_do_banco

    connectable = engine_from_config(
        config_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

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
