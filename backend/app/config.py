"""Configuración de la API EcoConecta leída desde variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

MIN_SECRET_KEY_LENGTH = 32

# Carga temprana del .env para que `uvicorn app.main:app` funcione desde backend/
# sin exportar manualmente las variables. No sobrescribe el entorno del proceso.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
for _candidate_env in (_BACKEND_DIR / ".env", _BACKEND_DIR.parent / ".env"):
    if _candidate_env.exists():
        load_dotenv(_candidate_env, override=False)


def _entero_positivo(nombre: str, valor_por_defecto: int) -> int:
    crudo = (os.getenv(nombre) or "").strip()
    if not crudo:
        return valor_por_defecto
    try:
        valor = int(crudo)
    except ValueError as exc:
        raise RuntimeError(f"{nombre} debe ser un número entero.") from exc
    if valor <= 0:
        raise RuntimeError(f"{nombre} debe ser mayor que cero.")
    return valor


@dataclass(frozen=True)
class Settings:
    """Valores de configuración inmutables de la API."""

    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    cors_origins: tuple[str, ...]
    entorno: str


def _cargar_settings() -> Settings:
    secret_key = (os.getenv("SECRET_KEY") or "").strip()
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY es obligatoria para firmar los JWT. "
            "Configúrala en el archivo .env antes de iniciar la API."
        )
    if len(secret_key) < MIN_SECRET_KEY_LENGTH:
        raise RuntimeError(
            f"SECRET_KEY debe tener al menos {MIN_SECRET_KEY_LENGTH} caracteres."
        )

    algorithm = (os.getenv("ALGORITHM") or "HS256").strip().upper()
    if algorithm != "HS256":
        raise RuntimeError("ALGORITHM debe ser HS256 para esta API.")

    origenes_crudos = (
        os.getenv("CORS_ORIGINS") or "http://localhost:3000,http://127.0.0.1:3000"
    )
    origenes = tuple(
        origen.strip().rstrip("/")
        for origen in origenes_crudos.split(",")
        if origen.strip()
    )
    if not origenes:
        origenes = ("http://localhost:3000",)

    return Settings(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=_entero_positivo("ACCESS_TOKEN_EXPIRE_MINUTES", 60),
        cors_origins=origenes,
        entorno=(os.getenv("ENTORNO") or "development").strip().lower(),
    )


settings = _cargar_settings()

__all__ = ["MIN_SECRET_KEY_LENGTH", "Settings", "settings"]
