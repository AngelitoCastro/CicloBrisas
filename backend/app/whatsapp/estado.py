"""Redacción de respuestas de consulta de estado."""

from __future__ import annotations

from app.models import Solicitud
from app.whatsapp.ia.client import redactar

PLANTILLA_ESTADO = (
    "Tu solicitud {codigo} está {estado}. {detalle} "
    "Si tienes otra duda, escríbenos por aquí."
)


def texto_estado(solicitud: Solicitud) -> str:
    if solicitud.estado == "PROGRAMADA" and solicitud.fecha_programada:
        detalle = (
            f"{solicitud.recolector.nombre if solicitud.recolector else 'El recolector'} "
            f"pasa el {solicitud.fecha_programada.isoformat()} a las "
            f"{solicitud.hora_programada.strftime('%H:%M') if solicitud.hora_programada else 'la hora acordada'}."
        )
    elif solicitud.disponibilidad_usuario:
        detalle = f"Tu preferencia registrada fue: {solicitud.disponibilidad_usuario}."
    else:
        detalle = "El coordinador la está revisando."
    texto = redactar(PLANTILLA_ESTADO)
    return (
        texto.replace("{codigo}", solicitud.codigo_publico)
        .replace("{estado}", solicitud.estado.lower())
        .replace("{detalle}", detalle)
    )


__all__ = ["texto_estado"]
