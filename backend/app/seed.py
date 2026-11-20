"""Semilla repetible (idempotente) de usuarios piloto, reglas de puntos y contenidos.

Uso desde backend/:
    SEED_DEFAULT_PASSWORD=<clave-local> python -m app.seed
    SEED_DEFAULT_PASSWORD=<clave-local> python app/seed.py
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# Permite ejecutar tanto `python -m app.seed` como `python app/seed.py` desde `backend/`.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import bcrypt
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.fixtures import (
    CONTENIDOS_EDUCATIVOS_INICIALES,
    REGLAS_PUNTOS_INICIALES,
    USUARIOS_PILOTO,
)
from app.models import ContenidoEducativo, ReglaPuntos, Usuario


@dataclass(frozen=True)
class SeedSummary:
    usuarios_creados: int = 0
    usuarios_actualizados: int = 0
    reglas_creadas: int = 0
    reglas_existentes: int = 0
    contenidos_creados: int = 0
    contenidos_actualizados: int = 0


def hash_password(plain_password: str) -> str:
    """Genera un hash bcrypt en formato UTF-8."""
    if not plain_password:
        raise ValueError("La contraseña no puede estar vacía.")
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def _resolve_password(
    env_key: str,
    env: Mapping[str, str],
    default_password: str | None,
) -> str:
    specific = (env.get(env_key) or "").strip()
    if specific:
        return specific
    fallback = (default_password if default_password is not None else env.get("SEED_DEFAULT_PASSWORD", "")).strip()
    if fallback:
        return fallback
    raise RuntimeError(
        "Falta configurar la contraseña para la semilla. "
        f"Define SEED_DEFAULT_PASSWORD o {env_key} en el entorno o en .env."
    )


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "si", "sí"}


def run_seed(
    session: Session,
    *,
    default_password: str | None = None,
    reset_passwords: bool | None = None,
    env: Mapping[str, str] | None = None,
) -> SeedSummary:
    """Carga actores piloto, reglas de puntos y contenidos de forma idempotente."""
    environ = env if env is not None else os.environ
    should_reset_passwords = (
        reset_passwords
        if reset_passwords is not None
        else _is_truthy(environ.get("SEED_RESET_PASSWORDS"))
    )

    usuarios_creados = 0
    usuarios_actualizados = 0
    reglas_creadas = 0
    reglas_existentes = 0
    contenidos_creados = 0
    contenidos_actualizados = 0

    for item in USUARIOS_PILOTO:
        existing = session.scalar(select(Usuario).where(Usuario.telefono == item["telefono"]))
        if existing is None:
            raw_password = _resolve_password(item["password_env"], environ, default_password)
            session.add(
                Usuario(
                    nombre=item["nombre"],
                    telefono=item["telefono"],
                    password_hash=hash_password(raw_password),
                    rol=item["rol"],
                    direccion=item["direccion"],
                    sector_manzana=item["sector_manzana"],
                    es_piloto=item["es_piloto"],
                    activo=item["activo"],
                )
            )
            usuarios_creados += 1
        else:
            existing.nombre = item["nombre"]
            existing.rol = item["rol"]
            existing.direccion = item["direccion"]
            existing.sector_manzana = item["sector_manzana"]
            existing.es_piloto = item["es_piloto"]
            existing.activo = item["activo"]
            if should_reset_passwords:
                raw_password = _resolve_password(item["password_env"], environ, default_password)
                existing.password_hash = hash_password(raw_password)
            usuarios_actualizados += 1

    for regla in REGLAS_PUNTOS_INICIALES:
        existing_rule = session.scalar(
            select(ReglaPuntos).where(
                ReglaPuntos.flujo == regla["flujo"],
                ReglaPuntos.tipo_generador == regla["tipo_generador"],
                ReglaPuntos.activa.is_(True),
            )
        )
        if existing_rule is None:
            session.add(
                ReglaPuntos(
                    flujo=regla["flujo"],
                    tipo_generador=regla["tipo_generador"],
                    puntos_base_solicitud=regla["puntos_base_solicitud"],
                    puntos_por_kg=regla["puntos_por_kg"],
                    valor_referencia_kg_cop=regla["valor_referencia_kg_cop"],
                    descripcion_regla=regla["descripcion_regla"],
                    activa=regla["activa"],
                )
            )
            reglas_creadas += 1
        else:
            reglas_existentes += 1

    for contenido in CONTENIDOS_EDUCATIVOS_INICIALES:
        existing_content = session.scalar(
            select(ContenidoEducativo).where(
                ContenidoEducativo.categoria == contenido["categoria"],
                ContenidoEducativo.titulo == contenido["titulo"],
            )
        )
        if existing_content is None:
            session.add(
                ContenidoEducativo(
                    titulo=contenido["titulo"],
                    categoria=contenido["categoria"],
                    resumen=contenido["resumen"],
                    que_si_va=contenido["que_si_va"],
                    que_no_va=contenido["que_no_va"],
                    orden=contenido["orden"],
                    publicado=contenido["publicado"],
                )
            )
            contenidos_creados += 1
        else:
            existing_content.resumen = contenido["resumen"]
            existing_content.que_si_va = contenido["que_si_va"]
            existing_content.que_no_va = contenido["que_no_va"]
            existing_content.orden = contenido["orden"]
            existing_content.publicado = contenido["publicado"]
            contenidos_actualizados += 1

    session.commit()

    return SeedSummary(
        usuarios_creados=usuarios_creados,
        usuarios_actualizados=usuarios_actualizados,
        reglas_creadas=reglas_creadas,
        reglas_existentes=reglas_existentes,
        contenidos_creados=contenidos_creados,
        contenidos_actualizados=contenidos_actualizados,
    )


def main() -> int:
    """Punto de entrada CLI para cargar datos semilla."""
    root_env = _BACKEND_DIR.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=False)
    local_env = _BACKEND_DIR / ".env"
    if local_env.exists():
        load_dotenv(local_env, override=False)

    with SessionLocal() as session:
        summary = run_seed(session)

    print(
        "Semilla EcoConecta completada: "
        f"usuarios(creados={summary.usuarios_creados}, actualizados={summary.usuarios_actualizados}), "
        f"reglas_puntos(creadas={summary.reglas_creadas}, existentes={summary.reglas_existentes}), "
        f"contenidos(creados={summary.contenidos_creados}, actualizados={summary.contenidos_actualizados})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
