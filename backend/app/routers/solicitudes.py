"""Rutas HTTP de solicitudes de recolección."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.presenters import (
    construir_cierre_response,
    construir_historial_response,
    construir_solicitud_response,
)
from app.schemas import (
    AsignarSolicitud,
    CancelarSolicitud,
    CerrarSolicitud,
    CierreSolicitudResponse,
    ErrorRespuesta,
    EstadoSolicitud,
    FlujoResiduo,
    HistorialEstadoResponse,
    ProgramarSolicitud,
    RevisarSolicitud,
    SolicitudCrear,
    SolicitudListResponse,
    SolicitudPublicaResponse,
)
from app.security import SesionDB, UsuarioActual
from app.services.solicitudes import (
    asignar_solicitud,
    cancelar_solicitud,
    cerrar_solicitud,
    crear_solicitud,
    listar_solicitudes,
    obtener_historial,
    obtener_solicitud,
    programar_solicitud,
    revisar_solicitud,
)

router = APIRouter()

RESPUESTAS_COMUNES = {
    401: {"model": ErrorRespuesta, "description": "Token ausente, inválido o expirado."},
    403: {"model": ErrorRespuesta, "description": "Rol o flujo no autorizado."},
    404: {"model": ErrorRespuesta, "description": "Solicitud no visible o inexistente."},
    409: {"model": ErrorRespuesta, "description": "Conflicto de estado o de datos."},
    422: {"model": ErrorRespuesta, "description": "Datos de entrada inválidos."},
}

SolicitudId = Annotated[int, Path(ge=1, description="Identificador interno de la solicitud.")]


@router.post(
    "",
    response_model=SolicitudPublicaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una solicitud de recolección (hogar o unidad productiva)",
    responses=RESPUESTAS_COMUNES,
)
def crear(
    datos: SolicitudCrear,
    usuario: UsuarioActual,
    db: SesionDB,
) -> SolicitudPublicaResponse:
    solicitud = crear_solicitud(db, usuario, datos)
    return construir_solicitud_response(solicitud, usuario)


@router.get(
    "",
    response_model=SolicitudListResponse,
    summary="Listar solicitudes visibles para el usuario autenticado",
    responses=RESPUESTAS_COMUNES,
)
def listar(
    usuario: UsuarioActual,
    db: SesionDB,
    flujo: FlujoResiduo | None = Query(default=None),
    estado: EstadoSolicitud | None = Query(default=None),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SolicitudListResponse:
    solicitudes, total = listar_solicitudes(
        db,
        usuario,
        flujo=flujo,
        estado=estado,
        limit=limit,
        offset=offset,
    )
    return SolicitudListResponse(
        items=[
            construir_solicitud_response(solicitud, usuario)
            for solicitud in solicitudes
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{solicitud_id}",
    response_model=SolicitudPublicaResponse,
    summary="Consultar una solicitud por su identificador",
    responses=RESPUESTAS_COMUNES,
)
def detalle(
    solicitud_id: SolicitudId,
    usuario: UsuarioActual,
    db: SesionDB,
) -> SolicitudPublicaResponse:
    solicitud = obtener_solicitud(db, usuario, solicitud_id)
    return construir_solicitud_response(solicitud, usuario)


@router.get(
    "/{solicitud_id}/historial",
    response_model=list[HistorialEstadoResponse],
    summary="Consultar el historial auditable de estados (RN-04)",
    responses=RESPUESTAS_COMUNES,
)
def historial(
    solicitud_id: SolicitudId,
    usuario: UsuarioActual,
    db: SesionDB,
) -> list[HistorialEstadoResponse]:
    registros = obtener_historial(db, usuario, solicitud_id)
    return [construir_historial_response(registro) for registro in registros]


@router.post(
    "/{solicitud_id}/revisar",
    response_model=SolicitudPublicaResponse,
    summary="Tomar una solicitud RECIBIDA para revisión (coordinador del flujo)",
    responses=RESPUESTAS_COMUNES,
)
def revisar(
    solicitud_id: SolicitudId,
    datos: RevisarSolicitud,
    usuario: UsuarioActual,
    db: SesionDB,
) -> SolicitudPublicaResponse:
    solicitud = revisar_solicitud(db, usuario, solicitud_id, datos)
    return construir_solicitud_response(solicitud, usuario)


@router.post(
    "/{solicitud_id}/asignar",
    response_model=SolicitudPublicaResponse,
    summary="Asignar recolector compatible y registrar coordinador (RN-03)",
    responses=RESPUESTAS_COMUNES,
)
def asignar(
    solicitud_id: SolicitudId,
    datos: AsignarSolicitud,
    usuario: UsuarioActual,
    db: SesionDB,
) -> SolicitudPublicaResponse:
    solicitud = asignar_solicitud(db, usuario, solicitud_id, datos)
    return construir_solicitud_response(solicitud, usuario)


@router.patch(
    "/{solicitud_id}/programar",
    response_model=SolicitudPublicaResponse,
    summary="Programar día, hora y recolector (RN-02; solo coordinador humano)",
    responses=RESPUESTAS_COMUNES,
)
def programar(
    solicitud_id: SolicitudId,
    datos: ProgramarSolicitud,
    usuario: UsuarioActual,
    db: SesionDB,
) -> SolicitudPublicaResponse:
    solicitud = programar_solicitud(db, usuario, solicitud_id, datos)
    return construir_solicitud_response(solicitud, usuario)


@router.post(
    "/{solicitud_id}/cerrar",
    response_model=CierreSolicitudResponse,
    summary="Cerrar con peso real y acreditar puntos en una sola transacción (RN-05/RN-06)",
    responses=RESPUESTAS_COMUNES,
)
def cerrar(
    solicitud_id: SolicitudId,
    datos: CerrarSolicitud,
    usuario: UsuarioActual,
    db: SesionDB,
) -> CierreSolicitudResponse:
    resultado = cerrar_solicitud(db, usuario, solicitud_id, datos)
    return construir_cierre_response(resultado, usuario)


@router.post(
    "/{solicitud_id}/cancelar",
    response_model=SolicitudPublicaResponse,
    summary="Cancelar una solicitud sin acreditar puntos",
    responses=RESPUESTAS_COMUNES,
)
def cancelar(
    solicitud_id: SolicitudId,
    datos: CancelarSolicitud,
    usuario: UsuarioActual,
    db: SesionDB,
) -> SolicitudPublicaResponse:
    solicitud = cancelar_solicitud(db, usuario, solicitud_id, datos)
    return construir_solicitud_response(solicitud, usuario)


__all__ = ["router"]
