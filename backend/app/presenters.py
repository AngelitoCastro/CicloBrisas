"""Serializadores de respuesta con control de datos personales (RN-07)."""

from __future__ import annotations

from app.models import HistorialEstado, ReglaPuntos, Solicitud, Usuario
from app.schemas import (
    CalculoPuntosResponse,
    CierreSolicitudResponse,
    ContactoSolicitante,
    HistorialEstadoResponse,
    ReglaPuntosResponse,
    SolicitudPublicaResponse,
    UsuarioResponse,
    UsuarioResumen,
)
from app.services.solicitudes import COORDINADOR_POR_FLUJO, ResultadoCierre


def _resumen(usuario: Usuario | None) -> UsuarioResumen | None:
    if usuario is None:
        return None
    return UsuarioResumen(id=usuario.id, nombre=usuario.nombre, rol=usuario.rol)


def _contacto_solicitante(
    solicitud: Solicitud,
    *,
    incluir_contacto: bool,
) -> ContactoSolicitante:
    solicitante = solicitud.solicitante
    return ContactoSolicitante(
        id=solicitante.id,
        nombre=solicitante.nombre,
        rol=solicitante.rol,
        telefono=solicitante.telefono if incluir_contacto else None,
        direccion=solicitante.direccion if incluir_contacto else None,
        sector_manzana=solicitante.sector_manzana if incluir_contacto else None,
    )


def construir_solicitud_response(
    solicitud: Solicitud,
    observador: Usuario,
    *,
    ocultar_contacto: bool = False,
) -> SolicitudPublicaResponse:
    """Construye la respuesta ocultando teléfono y dirección a quien no los necesita.

    RN-07: el propietario ve sus datos; el coordinador del flujo, el recolector
    asignado y el administrador ven los datos operativos. Cualquier otro perfil
    no recibe contacto; además, las rutas impiden que consulte la solicitud.
    """
    es_admin = observador.rol == "ADMIN"
    es_propietario = solicitud.solicitante_id == observador.id
    es_coordinador = observador.rol == COORDINADOR_POR_FLUJO.get(solicitud.flujo)
    es_recolector_asignado = (
        solicitud.recolector_id is not None and solicitud.recolector_id == observador.id
    )
    incluir_contacto = not ocultar_contacto and (
        es_admin or es_propietario or es_coordinador or es_recolector_asignado
    )

    return SolicitudPublicaResponse(
        id=solicitud.id,
        codigo_publico=solicitud.codigo_publico,
        flujo=solicitud.flujo,
        subtipo_material=solicitud.subtipo_material,
        cantidad_estimada_kg=solicitud.cantidad_estimada_kg,
        cantidad_real_kg=solicitud.cantidad_real_kg,
        disponibilidad_usuario=solicitud.disponibilidad_usuario,
        observaciones=solicitud.observaciones,
        estado=solicitud.estado,
        solicitante=_contacto_solicitante(
            solicitud,
            incluir_contacto=incluir_contacto,
        ),
        coordinador=_resumen(solicitud.coordinador),
        recolector=_resumen(solicitud.recolector),
        fecha_programada=solicitud.fecha_programada,
        hora_programada=solicitud.hora_programada,
        puntos_otorgados=solicitud.puntos_otorgados,
        regla_puntos_id=solicitud.regla_puntos_id,
        creado_en=solicitud.creado_en,
        actualizado_en=solicitud.actualizado_en,
    )


def construir_cierre_response(
    resultado: ResultadoCierre,
    observador: Usuario,
) -> CierreSolicitudResponse:
    base = construir_solicitud_response(resultado.solicitud, observador)
    calculo = CalculoPuntosResponse(
        regla_puntos_id=resultado.regla_puntos_id,
        flujo=resultado.flujo,
        tipo_generador=resultado.tipo_generador,
        puntos_base_solicitud=resultado.puntos_base_solicitud,
        puntos_por_kg=resultado.puntos_por_kg,
        cantidad_real_kg=resultado.cantidad_real_kg,
        puntos_otorgados=resultado.puntos_otorgados,
        formula=resultado.formula,
    )
    return CierreSolicitudResponse(**base.model_dump(), calculo_puntos=calculo)


def construir_historial_response(registro: HistorialEstado) -> HistorialEstadoResponse:
    return HistorialEstadoResponse(
        id=registro.id,
        estado_anterior=registro.estado_anterior,
        estado_nuevo=registro.estado_nuevo,
        actor=_resumen(registro.actor),
        nota_operativa=registro.nota_operativa,
        fecha_cambio=registro.fecha_cambio,
    )


def construir_regla_response(regla: ReglaPuntos) -> ReglaPuntosResponse:
    return ReglaPuntosResponse.model_validate(regla)


def construir_usuario_response(usuario: Usuario) -> UsuarioResponse:
    return UsuarioResponse.model_validate(usuario)


__all__ = [
    "construir_cierre_response",
    "construir_historial_response",
    "construir_regla_response",
    "construir_solicitud_response",
    "construir_usuario_response",
]
