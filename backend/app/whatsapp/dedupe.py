"""Dedupe persistente de mensajes entrantes por identificador de Twilio."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import MensajeWhatsapp


def registrar_entrante(
    db: Session,
    *,
    wa_message_id: str,
    telefono: str,
    contenido: str,
    media_id: str | None = None,
    media_tipo: str | None = None,
    media_mime: str | None = None,
) -> MensajeWhatsapp | None:
    registro = MensajeWhatsapp(
        wa_message_id=wa_message_id,
        telefono_remitente=telefono,
        direccion="ENTRANTE",
        contenido=(contenido or "[multimedia]").strip() or "[multimedia]",
        media_id=media_id,
        media_tipo=media_tipo,
        media_mime=media_mime,
        estado_envio="PENDIENTE",
        intentos=0,
    )
    db.add(registro)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    db.refresh(registro)
    return registro


def marcar_procesado(
    db: Session,
    registro: MensajeWhatsapp,
    *,
    intencion: str | None = None,
    solicitud_id: int | None = None,
    texto_extraido: str | None = None,
    estado_conversacion: str | None = None,
    borrador_json: str | None = None,
    error: str | None = None,
) -> None:
    registro.intencion_ia = intencion
    registro.solicitud_id = solicitud_id
    registro.texto_extraido = texto_extraido
    registro.estado_conversacion = estado_conversacion
    registro.borrador_json = borrador_json
    registro.procesado_por_ia = intencion is not None
    registro.procesado_en = datetime.now(UTC)
    registro.error = error
    registro.estado_envio = "FALLIDO" if error else "ENVIADO"
    db.commit()
    db.refresh(registro)


def tiene_intencion(registro: MensajeWhatsapp, intencion: str) -> bool:
    return (registro.intencion_ia or "").upper() == intencion


def peso_como_decimal(valor: Decimal | float | None) -> Decimal | None:
    if valor is None:
        return None
    return Decimal(str(valor))


__all__ = [
    "marcar_procesado",
    "peso_como_decimal",
    "registrar_entrante",
    "tiene_intencion",
]
