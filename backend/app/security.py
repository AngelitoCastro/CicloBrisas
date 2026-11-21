"""Autenticación con bcrypt, emisión/validación de JWT y permisos por rol."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Usuario
from app.services.errors import (
    NoAutenticado,
    PermisoDenegado,
    TokenExpirado,
    TokenInvalido,
)

# Hash de relleno para reducir diferencias de tiempo cuando el teléfono no existe.
_DUMMY_PASSWORD_HASH = b"$2b$12$vDyfT/M4ApqWNaMBrM0KK.rvftGIUfdI.ZBdQoVPd/JqbcwfhWr16"

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="JWT",
    description="Token Bearer emitido por POST /api/auth/login.",
)


def hash_password(plain_password: str) -> str:
    """Genera un hash bcrypt (nunca se almacena la contraseña en texto claro)."""
    if not plain_password:
        raise ValueError("La contraseña no puede estar vacía.")
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("La contraseña supera el límite de 72 bytes de bcrypt.")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verificar_password(plain_password: str, password_hash: str) -> bool:
    """Compara una contraseña con su hash bcrypt sin propagar errores de formato."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def _verificar_hash_relleno(plain_password: str) -> None:
    try:
        bcrypt.checkpw(plain_password.encode("utf-8"), _DUMMY_PASSWORD_HASH)
    except (ValueError, TypeError):
        pass


def crear_access_token(usuario: Usuario) -> tuple[str, int]:
    """Emite un JWT de acceso y devuelve (token, segundos_de_vigencia)."""
    ahora = datetime.now(UTC)
    expira = ahora + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(usuario.id),
        "rol": usuario.rol,
        "tipo": "access",
        "iat": ahora,
        "exp": expira,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, settings.access_token_expire_minutes * 60


def decodificar_token(token: str) -> dict[str, object]:
    """Valida firma y expiración del JWT y devuelve sus claims."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpirado() from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalido() from exc

    if payload.get("tipo") != "access":
        raise TokenInvalido()
    if not isinstance(payload.get("sub"), str):
        raise TokenInvalido()
    return payload


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Dependencia FastAPI que resuelve el usuario autenticado y activo."""
    if credentials is None or not credentials.credentials.strip():
        raise NoAutenticado("Falta el token Bearer en la cabecera Authorization.")

    payload = decodificar_token(credentials.credentials)
    try:
        usuario_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError, TypeError) as exc:
        raise TokenInvalido() from exc

    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id))
    if usuario is None or not usuario.activo:
        raise NoAutenticado("La cuenta no existe o está inactiva.")
    return usuario


UsuarioActual = Annotated[Usuario, Depends(get_current_user)]
SesionDB = Annotated[Session, Depends(get_db)]


def require_roles(*roles: str) -> Callable[..., Usuario]:
    """Construye una dependencia que exige uno de los roles indicados."""
    roles_permitidos = frozenset(roles)

    def dependency(usuario: UsuarioActual) -> Usuario:
        if usuario.rol not in roles_permitidos:
            raise PermisoDenegado(
                "Tu rol no está autorizado para esta operación.",
                codigo="ROL_NO_AUTORIZADO",
            )
        return usuario

    return dependency


def autenticar(db: Session, telefono: str, password: str) -> Usuario:
    """Valida credenciales y devuelve el usuario activo o lanza un error genérico."""
    usuario = db.scalar(select(Usuario).where(Usuario.telefono == telefono))
    if usuario is None:
        _verificar_hash_relleno(password)
        raise NoAutenticado("Teléfono o contraseña incorrectos.")
    if not verificar_password(password, usuario.password_hash):
        raise NoAutenticado("Teléfono o contraseña incorrectos.")
    if not usuario.activo:
        raise PermisoDenegado(
            "La cuenta está inactiva. Contacta a la administración comunitaria.",
            codigo="USUARIO_INACTIVO",
        )
    return usuario


__all__ = [
    "SesionDB",
    "UsuarioActual",
    "autenticar",
    "bearer_scheme",
    "crear_access_token",
    "decodificar_token",
    "get_current_user",
    "hash_password",
    "require_roles",
    "verificar_password",
]
