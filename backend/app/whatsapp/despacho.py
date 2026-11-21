"""Worker persistente. Ejecutar desde backend: python -m app.whatsapp.despacho."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from twilio.base.exceptions import TwilioRestException
from twilio.http.http_client import TwilioHttpClient
from twilio.rest import Client

from app.db import SessionLocal
from app.models import AvisoWhatsApp, HistorialEstado
from app.whatsapp.cliente import _destino
from app.whatsapp.config import obtener_config, proveedor_whatsapp_activo
from app.whatsapp.errores import ErrorMetaDefinitivo, ErrorMetaIncierto
from app.whatsapp.meta import enviar_aviso_meta, procesar_entrante_meta_uno
from app.whatsapp.notificaciones import (
    ESTADO_SIN_CONSENTIMIENTO,
    tiene_consentimiento_para_aviso,
)

ESTADOS = {
    "accepted": "ACEPTADO",
    "queued": "ACEPTADO",
    "sending": "ACEPTADO",
    "sent": "ENVIADO",
    "delivered": "ENTREGADO",
    "read": "LEIDO",
    "failed": "FALLIDO",
    "undelivered": "FALLIDO",
    "canceled": "FALLIDO",
}
ORDEN = ["CONCILIAR", "ACEPTADO", "ENVIADO", "FALLIDO", "ENTREGADO", "LEIDO"]


def _aplicar_estado(
    aviso: AvisoWhatsApp,
    sid: str | None,
    estado: str,
    error: str | None = None,
) -> bool:
    if (aviso.sid and sid and aviso.sid != sid) or aviso.estado not in ORDEN:
        return False
    if estado not in ORDEN:
        return False
    if ORDEN.index(estado) < ORDEN.index(aviso.estado):
        return False
    aviso.sid = sid or aviso.sid
    aviso.estado = estado
    aviso.error = str(error)[:80] if error else None
    aviso.actualizado_en = datetime.now(UTC)
    return True


def actualizar(db, intento, sid, estado, error=None):
    aviso = db.scalar(
        select(AvisoWhatsApp)
        .where(AvisoWhatsApp.intento == intento)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not aviso:
        return
    if _aplicar_estado(aviso, sid, estado, error):
        db.commit()


def actualizar_por_meta(
    db,
    *,
    wamid: str,
    intento: str | None,
    estado: str,
    error: str | None = None,
    commit: bool = True,
) -> bool:
    """Concilia eventos de estado de Meta buscando por sid (wamid) o biz_opaque_callback_data."""
    aviso = None
    if wamid:
        aviso = db.scalar(
            select(AvisoWhatsApp)
            .where(AvisoWhatsApp.sid == wamid)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    if aviso is None and intento:
        aviso = db.scalar(
            select(AvisoWhatsApp)
            .where(AvisoWhatsApp.intento == intento)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    if aviso is None:
        return False
    actualizado = _aplicar_estado(aviso, wamid or None, estado, error)
    if actualizado and commit:
        db.commit()
    return actualizado


def enviar_twilio(aviso: AvisoWhatsApp, cfg) -> str:
    if not all((cfg.account_sid, cfg.auth_token, cfg.whatsapp_number, cfg.webhook_public_url)):
        raise ValueError("CONFIGURACION_INCOMPLETA")
    campos = {
        "from_": _destino(cfg.whatsapp_number),
        "to": _destino(aviso.telefono),
        "status_callback": f"{cfg.webhook_public_url}/estado/{aviso.intento}",
    }
    plantilla = os.getenv(f"TWILIO_CONTENT_SID_{aviso.evento}_{aviso.destinatario}")
    if plantilla or (cfg.content_sid and not cfg.content_sin_variables):
        campos.update(
            content_sid=plantilla or cfg.content_sid,
            content_variables=json.dumps({"1": aviso.contenido}, ensure_ascii=False),
        )
    else:
        campos["body"] = aviso.contenido
    cliente = Client(
        cfg.account_sid, cfg.auth_token, http_client=TwilioHttpClient(timeout=12)
    )
    return cliente.messages.create(**campos).sid


def enviar(aviso: AvisoWhatsApp, cfg) -> str:
    proveedor = (aviso.proveedor or "AUTO").upper()
    if proveedor == "META" or (
        proveedor == "AUTO" and proveedor_whatsapp_activo(cfg) == "meta"
    ):
        return enviar_aviso_meta(aviso, cfg)
    return enviar_twilio(aviso, cfg)


def despachar_uno(fabrica=SessionLocal) -> bool:
    with fabrica() as db:
        aviso = db.scalar(
            select(AvisoWhatsApp)
            .where(AvisoWhatsApp.estado == "PENDIENTE")
            .order_by(AvisoWhatsApp.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if aviso is None:
            return False
        vigente = db.scalar(
            select(func.max(HistorialEstado.id)).where(
                HistorialEstado.solicitud_id == aviso.solicitud_id
            )
        )
        if vigente != aviso.historial_id:
            aviso.estado = "SUSTITUIDO"
            aviso.actualizado_en = datetime.now(UTC)
            db.commit()
            return True
        if not tiene_consentimiento_para_aviso(db, aviso):
            aviso.estado = ESTADO_SIN_CONSENTIMIENTO
            aviso.error = ESTADO_SIN_CONSENTIMIENTO
            aviso.actualizado_en = datetime.now(UTC)
            db.commit()
            return True
        # Guardar antes del POST. Tras una caída se concilia por webhook/callback, sin reenviar.
        aviso.estado = "CONCILIAR"
        aviso.actualizado_en = datetime.now(UTC)
        intento = aviso.intento
        db.commit()
        try:
            sid = enviar(aviso, obtener_config())
        except ErrorMetaDefinitivo as exc:
            actualizar(db, intento, None, "FALLIDO", exc.codigo)
        except ErrorMetaIncierto as exc:
            actualizar(db, intento, None, "CONCILIAR", exc.codigo)
        except TwilioRestException as exc:
            estado = "FALLIDO" if 400 <= exc.status < 500 else "CONCILIAR"
            actualizar(db, intento, None, estado, exc.code or exc.status)
        except ValueError:
            actualizar(db, intento, None, "FALLIDO", "CONFIGURACION_INVALIDA")
        except Exception as exc:
            actualizar(db, intento, None, "CONCILIAR", type(exc).__name__)
        else:
            actualizar(db, intento, sid, "ACEPTADO")
        return True


def ejecutar_ciclo(fabrica=SessionLocal) -> bool:
    """Procesa un elemento pendiente de entrada Meta y/o un aviso saliente."""
    hizo_entrante = procesar_entrante_meta_uno(fabrica)
    hizo_saliente = despachar_uno(fabrica)
    return hizo_entrante or hizo_saliente


if __name__ == "__main__":
    while True:
        try:
            if not ejecutar_ciclo():
                time.sleep(2)
        except SQLAlchemyError as exc:
            logging.error("Bandeja de mensajería no disponible: %s", type(exc).__name__)
            time.sleep(5)
