"""Rutas de autenticación de EcoConecta."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.config import settings
from app.models import Usuario
from app.presenters import construir_usuario_response
from app.schemas import (
    DemoLoginRequest,
    ErrorRespuesta,
    LoginRequest,
    TokenResponse,
    UsuarioResponse,
)
from app.security import SesionDB, UsuarioActual, autenticar, crear_access_token
from app.services.errors import NoEncontrado, PermisoDenegado

router = APIRouter()

RESPUESTAS_AUTH = {
    401: {"model": ErrorRespuesta, "description": "Credenciales o token inválidos."},
    403: {"model": ErrorRespuesta, "description": "Cuenta inactiva."},
}


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión con teléfono y contraseña",
    responses=RESPUESTAS_AUTH,
)
def login(datos: LoginRequest, db: SesionDB) -> TokenResponse:
    usuario = autenticar(db, datos.telefono, datos.password)
    token, segundos = crear_access_token(usuario)
    return TokenResponse(
        access_token=token,
        expira_en_segundos=segundos,
        usuario=construir_usuario_response(usuario),
    )


@router.post(
    "/demo-login",
    response_model=TokenResponse,
    summary="Acceso directo por perfil (solo ENTORNO=development)",
    responses={
        403: {"model": ErrorRespuesta, "description": "Acceso rápido deshabilitado."},
        404: {"model": ErrorRespuesta, "description": "No hay cuenta activa para ese rol."},
    },
)
def demo_login(datos: DemoLoginRequest, db: SesionDB) -> TokenResponse:
    if settings.entorno != "development":
        raise PermisoDenegado(
            "El acceso directo por perfil solo está habilitado en ENTORNO=development.",
            codigo="DEMO_NO_HABILITADO",
        )
    usuario = db.scalar(
        select(Usuario)
        .where(Usuario.rol == datos.rol, Usuario.activo.is_(True))
        .order_by(Usuario.es_piloto.desc(), Usuario.telefono.asc())
    )
    if usuario is None:
        raise NoEncontrado(f"No hay una cuenta activa con rol {datos.rol}.")
    token, segundos = crear_access_token(usuario)
    return TokenResponse(
        access_token=token,
        expira_en_segundos=segundos,
        usuario=construir_usuario_response(usuario),
    )


@router.get(
    "/me",
    response_model=UsuarioResponse,
    summary="Consultar la cuenta autenticada y sus puntos",
    responses={401: {"model": ErrorRespuesta, "description": "Token inválido."}},
)
def me(usuario: UsuarioActual) -> UsuarioResponse:
    return construir_usuario_response(usuario)


__all__ = ["router"]
