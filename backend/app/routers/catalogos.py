"""Rutas de catálogo compartido (reglas de puntos activas, recolectores y educación)."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.models import ContenidoEducativo
from app.presenters import (
    construir_contenido_response,
    construir_recolector_response,
    construir_regla_response,
)
from app.schemas import (
    CategoriaContenido,
    ContenidoEducativoResponse,
    ErrorRespuesta,
    FlujoResiduo,
    RecolectorCatalogoResponse,
    ReglaPuntosResponse,
)
from app.security import SesionDB, UsuarioActual
from app.services.reglas import listar_reglas_activas
from app.services.usuarios import listar_recolectores_activos

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


@router.get(
    "/recolectores",
    response_model=list[RecolectorCatalogoResponse],
    summary="Listar recolectores activos disponibles para el flujo autorizado",
    responses={
        401: {"model": ErrorRespuesta, "description": "Token inválido."},
        403: {"model": ErrorRespuesta, "description": "Rol o flujo no autorizado."},
    },
)
def listar_recolectores(
    usuario: UsuarioActual,
    db: SesionDB,
    flujo: FlujoResiduo | None = Query(default=None),
) -> list[RecolectorCatalogoResponse]:
    recolectores = listar_recolectores_activos(db, usuario, flujo=flujo)
    return [construir_recolector_response(r) for r in recolectores]


@router.get(
    "/contenidos-educativos",
    response_model=list[ContenidoEducativoResponse],
    summary="Consultar guía de separación y contenidos educativos publicados",
    responses={
        401: {"model": ErrorRespuesta, "description": "Token inválido."},
    },
)
def contenidos_educativos(
    usuario: UsuarioActual,
    db: SesionDB,
    categoria: CategoriaContenido | None = Query(default=None),
) -> list[ContenidoEducativoResponse]:
    del usuario
    stmt = (
        select(ContenidoEducativo)
        .where(ContenidoEducativo.publicado.is_(True))
        .order_by(ContenidoEducativo.orden.asc(), ContenidoEducativo.id.asc())
    )
    if categoria is not None:
        stmt = stmt.where(ContenidoEducativo.categoria == categoria)
    contenidos = list(db.scalars(stmt).all())
    return [construir_contenido_response(item) for item in contenidos]


__all__ = ["router"]
