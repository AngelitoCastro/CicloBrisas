"""Rutas de administración: reglas de puntos adaptables y modo piloto."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query

from app.models import Usuario
from app.presenters import (
    construir_regla_response,
    construir_usuario_response,
)
from app.schemas import (
    ErrorRespuesta,
    FlujoResiduo,
    PilotoUpdate,
    ReglaPuntosActualizar,
    ReglaPuntosCrear,
    ReglaPuntosResponse,
    RolUsuario,
    TipoGenerador,
    UsuarioListResponse,
    UsuarioResponse,
)
from app.security import SesionDB, require_roles
from app.services.reglas import (
    actualizar_regla,
    crear_regla,
    listar_reglas_admin,
)
from app.services.usuarios import cambiar_modo_piloto, listar_usuarios_admin

router = APIRouter()

AdminActual = Annotated[Usuario, Depends(require_roles("ADMIN"))]
FlujoFiltro = Annotated[FlujoResiduo | None, Query()]
TipoGeneradorFiltro = Annotated[TipoGenerador | None, Query()]
RolFiltro = Annotated[RolUsuario | None, Query()]
BooleanoFiltro = Annotated[bool | None, Query()]

RESPUESTAS_ADMIN = {
    401: {
        "model": ErrorRespuesta,
        "description": "Token ausente, inválido o expirado.",
    },
    403: {"model": ErrorRespuesta, "description": "Se requiere rol ADMIN."},
    404: {"model": ErrorRespuesta, "description": "Recurso inexistente."},
    409: {"model": ErrorRespuesta, "description": "Conflicto con una regla activa."},
    422: {"model": ErrorRespuesta, "description": "Datos de entrada inválidos."},
}


@router.get(
    "/reglas-puntos",
    response_model=list[ReglaPuntosResponse],
    summary="Listar reglas de puntos (incluye históricas inactivas)",
    responses=RESPUESTAS_ADMIN,
)
def listar_reglas(
    admin: AdminActual,
    db: SesionDB,
    flujo: FlujoFiltro = None,
    tipo_generador: TipoGeneradorFiltro = None,
    activa: BooleanoFiltro = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ReglaPuntosResponse]:
    reglas, _ = listar_reglas_admin(
        db,
        admin,
        flujo=flujo,
        tipo_generador=tipo_generador,
        activa=activa,
        limit=limit,
        offset=offset,
    )
    return [construir_regla_response(regla) for regla in reglas]


@router.post(
    "/reglas-puntos",
    response_model=ReglaPuntosResponse,
    summary="Crear una regla de puntos; si se activa, reemplaza la vigente del mismo par",
    responses=RESPUESTAS_ADMIN,
)
def crear_regla_puntos(
    datos: ReglaPuntosCrear,
    admin: AdminActual,
    db: SesionDB,
) -> ReglaPuntosResponse:
    regla = crear_regla(db, admin, datos)
    return construir_regla_response(regla)


@router.patch(
    "/reglas-puntos/{regla_id}",
    response_model=ReglaPuntosResponse,
    summary="Actualizar parámetros o activar/desactivar una regla",
    responses=RESPUESTAS_ADMIN,
)
def actualizar_regla_puntos(
    regla_id: Annotated[int, Path(ge=1)],
    datos: ReglaPuntosActualizar,
    admin: AdminActual,
    db: SesionDB,
) -> ReglaPuntosResponse:
    regla = actualizar_regla(db, admin, regla_id, datos)
    return construir_regla_response(regla)


@router.get(
    "/usuarios",
    response_model=UsuarioListResponse,
    summary="Listar cuentas para operación administrativa",
    responses=RESPUESTAS_ADMIN,
)
def listar_usuarios(
    admin: AdminActual,
    db: SesionDB,
    rol: RolFiltro = None,
    es_piloto: BooleanoFiltro = None,
    activo: BooleanoFiltro = None,
    q: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UsuarioListResponse:
    usuarios, total = listar_usuarios_admin(
        db,
        admin,
        rol=rol,
        es_piloto=es_piloto,
        activo=activo,
        q=q,
        limit=limit,
        offset=offset,
    )
    return UsuarioListResponse(
        items=[construir_usuario_response(usuario) for usuario in usuarios],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/usuarios/{usuario_id}/piloto",
    response_model=UsuarioResponse,
    summary="Activar o desactivar la etiqueta piloto de hogares y unidades productivas (RN-08)",
    responses=RESPUESTAS_ADMIN,
)
def actualizar_piloto(
    usuario_id: UUID,
    datos: PilotoUpdate,
    admin: AdminActual,
    db: SesionDB,
) -> UsuarioResponse:
    usuario = cambiar_modo_piloto(db, admin, usuario_id, datos.es_piloto)
    return construir_usuario_response(usuario)


__all__ = ["router"]
