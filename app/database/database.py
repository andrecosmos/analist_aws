# app/database/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Carrega as variáveis do arquivo .env automaticamente
load_dotenv()

# Busca a URL do banco
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("A variável de ambiente 'DATABASE_URL' não foi encontrada. Verifique seu arquivo .env!")

# Correção caso o Supabase entregue com o prefixo antigo postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# O engine gerencia a conexão física com o banco
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# O sessionmaker cria as sessões de conversação com o banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Esta função será usada pelo FastAPI para injetar o banco nas rotas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
