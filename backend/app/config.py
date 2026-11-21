"""Configuracion central de la API.

Carga los archivos .env locales antes de construir los ajustes usados por
FastAPI y la autenticacion JWT.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


_BACKEND_DIR = Path(__file__).resolve().parent.parent
for _candidate_env in (_BACKEND_DIR / ".env", _BACKEND_DIR.parent / ".env"):
    if _candidate_env.exists():
        load_dotenv(_candidate_env, override=False)


@dataclass(frozen=True)
class Settings:
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
            "Configurala en el archivo .env antes de iniciar la API."
        )
    if len(secret_key) < 32:
        raise RuntimeError(
            "SECRET_KEY debe tener al menos 32 caracteres. "
            "Usa una cadena larga y aleatoria."
        )

    try:
        access_token_expire_minutes = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        )
    except ValueError as exc:
        raise RuntimeError(
            "ACCESS_TOKEN_EXPIRE_MINUTES debe ser un numero entero."
        ) from exc
    if access_token_expire_minutes <= 0:
        raise RuntimeError(
            "ACCESS_TOKEN_EXPIRE_MINUTES debe ser mayor que cero."
        )

    cors_origins = tuple(
        origen.strip()
        for origen in (os.getenv("CORS_ORIGINS") or "").split(",")
        if origen.strip()
    )

    return Settings(
        secret_key=secret_key,
        algorithm=(os.getenv("ALGORITHM") or "HS256").strip(),
        access_token_expire_minutes=access_token_expire_minutes,
        cors_origins=cors_origins,
        entorno=(os.getenv("ENTORNO") or "development").strip(),
    )


settings = _cargar_settings()

__all__ = ["Settings", "settings"]
