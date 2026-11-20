"""Rutas de catálogo compartido (reglas de puntos activas)."""

from __future__ import annotations

from fastapi import APIRouter

from app.presenters import construir_regla_response
from app.schemas import ErrorRespuesta, ReglaPuntosResponse
from app.security import SesionDB, UsuarioActual
from app.services.reglas import listar_reglas_activas

router = APIRouter()


@router.get(
    "/reglas-puntos",
    response_model=list[ReglaPuntosResponse],
    summary="Consultar reglas de puntos activas y su nota de parametrización",
    responses={
        401: {"model": ErrorRespuesta, "description": "Token inválido."},
    },
)
def reglas_activas(usuario: UsuarioActual, db: SesionDB) -> list[ReglaPuntosResponse]:
    # El parámetro usuario activa la dependencia de autenticación; no expone datos personales.
    del usuario
    return [construir_regla_response(regla) for regla in listar_reglas_activas(db)]


__all__ = ["router"]
