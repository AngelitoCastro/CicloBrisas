"""Configuración de conexión y sesiones síncronas SQLAlchemy 2 con psycopg 3."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_BACKEND_DIR = Path(__file__).resolve().parent.parent
for _candidate_env in (_BACKEND_DIR / ".env", _BACKEND_DIR.parent / ".env"):
    if _candidate_env.exists():
        load_dotenv(_candidate_env, override=False)

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa compartida para los modelos ORM de EcoConecta."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def normalize_database_url(url: str) -> str:
    """Garantiza el dialecto psycopg 3 para URLs PostgreSQL estándar."""
    cleaned = url.strip()
    if cleaned.startswith("postgres://"):
        return "postgresql+psycopg://" + cleaned[len("postgres://") :]
    if cleaned.startswith("postgresql://"):
        return "postgresql+psycopg://" + cleaned[len("postgresql://") :]
    return cleaned


def get_database_url() -> str:
    """Resuelve DATABASE_URL desde el entorno o a partir de variables POSTGRES_*."""
    env_url = os.getenv("DATABASE_URL")
    if env_url and env_url.strip():
        return normalize_database_url(env_url)

    user = quote_plus(os.getenv("POSTGRES_USER", "ecoconecta"))
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = quote_plus(os.getenv("POSTGRES_DB", "ecoconecta"))

    auth = f"{user}:{password}" if password else user
    return f"postgresql+psycopg://{auth}@{host}:{port}/{db_name}"


def create_db_engine(database_url: str | None = None) -> Engine:
    """Crea un Engine síncrono de SQLAlchemy 2."""
    url = normalize_database_url(database_url) if database_url else get_database_url()
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


DATABASE_URL: str = get_database_url()
engine: Engine = create_db_engine(DATABASE_URL)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI que entrega una sesión síncrona SQLAlchemy por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    "DATABASE_URL",
    "NAMING_CONVENTION",
    "Base",
    "SessionLocal",
    "create_db_engine",
    "engine",
    "get_database_url",
    "get_db",
    "normalize_database_url",
]
