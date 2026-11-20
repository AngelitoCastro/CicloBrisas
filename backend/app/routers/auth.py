"""Rutas de autenticación de EcoConecta."""

from __future__ import annotations

from fastapi import APIRouter

from app.presenters import construir_usuario_response
from app.schemas import (
    ErrorRespuesta,
    LoginRequest,
    TokenResponse,
    UsuarioResponse,
)
from app.security import SesionDB, UsuarioActual, autenticar, crear_access_token

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


@router.get(
    "/me",
    response_model=UsuarioResponse,
    summary="Consultar la cuenta autenticada y sus puntos",
    responses={401: {"model": ErrorRespuesta, "description": "Token inválido."}},
)
def me(usuario: UsuarioActual) -> UsuarioResponse:
    return construir_usuario_response(usuario)


__all__ = ["router"]
