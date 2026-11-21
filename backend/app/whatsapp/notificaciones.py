"""Notificaciones salientes disparadas por eventos de dominio."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import SessionLocal
from app.models import MensajeWhatsapp, Solicitud
from app.services.errors import ErrorDominio
from app.whatsapp.cliente import enviar_texto
from app.whatsapp.config import obtener_config
from app.whatsapp.ia.client import redactar

PLANTILLA_PROGRAMACION = (
    "Hola {nombre}, tu solicitud {codigo} ya tiene recolección. "
    "{recolector} pasa el {fecha} a las {hora}. "
    "Si cambias algo, escríbenos por aquí."
)
PLANTILLA_CIERRE = (
    "Hola {nombre}, confirmamos la recolección de {codigo}: {peso} kg y "
    "{puntos} EcoPuntos. Gracias por cuidar Villas de San Pablo."
)


def _registrar_saliente(
    db: Session,
    solicitud: Solicitud,
    texto: str,
    wa_message_id: str | None,
    error: str | None = None,
) -> None:
    registro = MensajeWhatsapp(
        solicitud_id=solicitud.id,
        telefono_remitente=solicitud.solicitante.telefono,
        direccion="SALIENTE",
        contenido=texto,
        intencion_ia="NOTIFICACION",
        procesado_por_ia=True,
        procesado_en=datetime.now(UTC),
        estado_envio="ENVIADO" if wa_message_id else "FALLIDO",
        wa_message_id=wa_message_id,
        error=error,
    )
    db.add(registro)
    db.commit()


def _enviar(
    db: Session,
    solicitud: Solicitud,
    plantilla: str,
    valores: dict[str, str],
) -> None:
    texto = redactar(plantilla)
    for clave, valor in valores.items():
        texto = texto.replace(clave, valor)
    try:
        wa_message_id = enviar_texto(solicitud.solicitante.telefono, texto)
        error = None
    except ErrorDominio as exc:
        wa_message_id = None
        error = exc.codigo
    _registrar_saliente(db, solicitud, texto, wa_message_id, error)


def notificar_programacion(solicitud: Solicitud, db: Session) -> None:
    recolector = (
        solicitud.recolector.nombre if solicitud.recolector else "el recolector"
    )
    valores = {
        "{nombre}": solicitud.solicitante.nombre.split()[0],
        "{codigo}": solicitud.codigo_publico,
        "{recolector}": recolector,
        "{fecha}": solicitud.fecha_programada.isoformat()
        if solicitud.fecha_programada
        else "la fecha acordada",
        "{hora}": solicitud.hora_programada.strftime("%H:%M")
        if solicitud.hora_programada
        else "la hora acordada",
    }
    _enviar(db, solicitud, PLANTILLA_PROGRAMACION, valores)


def notificar_cierre(solicitud: Solicitud, db: Session) -> None:
    puntos = solicitud.puntos_otorgados or 0
    valores = {
        "{nombre}": solicitud.solicitante.nombre.split()[0],
        "{codigo}": solicitud.codigo_publico,
        "{peso}": f"{solicitud.cantidad_real_kg:.2f}"
        if solicitud.cantidad_real_kg is not None
        else "0.00",
        "{puntos}": f"{puntos:.2f}",
    }
    _enviar(db, solicitud, PLANTILLA_CIERRE, valores)


def manejar_evento(evento: str, carga: object) -> None:
    configuracion = obtener_config()
    if (
        not configuracion.account_sid
        or not configuracion.auth_token
        or not configuracion.whatsapp_number
    ):
        return
    if evento not in {"solicitud_programada", "solicitud_cerrada"}:
        return
    if not isinstance(carga, int):
        return
    with SessionLocal() as db:
        solicitud = db.scalar(
            select(Solicitud)
            .where(Solicitud.id == carga)
            .options(
                selectinload(Solicitud.solicitante),
                selectinload(Solicitud.recolector),
            )
        )
        if solicitud is None:
            return
        if evento == "solicitud_programada":
            notificar_programacion(solicitud, db)
        else:
            notificar_cierre(solicitud, db)


__all__ = ["manejar_evento", "notificar_cierre", "notificar_programacion"]
