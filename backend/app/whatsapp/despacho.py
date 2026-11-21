"""Worker persistente. Ejecutar desde backend: python -m app.whatsapp.despacho."""
import json
import logging
import os
import time

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from twilio.base.exceptions import TwilioRestException
from twilio.http.http_client import TwilioHttpClient
from twilio.rest import Client

from app.db import SessionLocal
from app.models import AvisoWhatsApp, HistorialEstado
from app.whatsapp.cliente import _destino
from app.whatsapp.config import obtener_config

ESTADOS = {"accepted": "ACEPTADO", "queued": "ACEPTADO", "sending": "ACEPTADO",
           "sent": "ENVIADO", "delivered": "ENTREGADO", "read": "LEIDO",
           "failed": "FALLIDO", "undelivered": "FALLIDO", "canceled": "FALLIDO"}
ORDEN = ["CONCILIAR", "ACEPTADO", "ENVIADO", "FALLIDO", "ENTREGADO", "LEIDO"]


def actualizar(db, intento, sid, estado, error=None):
    aviso = db.scalar(select(AvisoWhatsApp).where(AvisoWhatsApp.intento == intento).with_for_update().execution_options(populate_existing=True))
    if not aviso or (aviso.sid and sid and aviso.sid != sid) or aviso.estado not in ORDEN:
        return
    if ORDEN.index(estado) < ORDEN.index(aviso.estado):
        return
    aviso.sid = sid or aviso.sid
    aviso.estado = estado
    aviso.error = str(error)[:80] if error else None
    db.commit()


def enviar(aviso, cfg):
    if not all((cfg.account_sid, cfg.auth_token, cfg.whatsapp_number, cfg.webhook_public_url)):
        raise ValueError("CONFIGURACION_INCOMPLETA")
    campos = {"from_": _destino(cfg.whatsapp_number), "to": _destino(aviso.telefono),
              "status_callback": f"{cfg.webhook_public_url}/estado/{aviso.intento}"}
    plantilla = os.getenv(f"TWILIO_CONTENT_SID_{aviso.evento}_{aviso.destinatario}")
    if plantilla or (cfg.content_sid and not cfg.content_sin_variables):
        campos.update(content_sid=plantilla or cfg.content_sid,
                      content_variables=json.dumps({"1": aviso.contenido}, ensure_ascii=False))
    else:
        campos["body"] = aviso.contenido
    cliente = Client(cfg.account_sid, cfg.auth_token, http_client=TwilioHttpClient(timeout=12))
    return cliente.messages.create(**campos).sid


def despachar_uno(fabrica=SessionLocal):
    with fabrica() as db:
        aviso = db.scalar(select(AvisoWhatsApp).where(AvisoWhatsApp.estado == "PENDIENTE")
                          .order_by(AvisoWhatsApp.id).limit(1).with_for_update(skip_locked=True))
        if aviso is None:
            return False
        vigente = db.scalar(select(func.max(HistorialEstado.id)).where(
            HistorialEstado.solicitud_id == aviso.solicitud_id))
        if vigente != aviso.historial_id:
            aviso.estado = "SUSTITUIDO"
            db.commit()
            return True
        # Guardar antes del POST. Tras una caída se concilia por callback, sin otro envío.
        aviso.estado = "CONCILIAR"
        intento = aviso.intento
        db.commit()
        try:
            sid = enviar(aviso, obtener_config())
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


if __name__ == "__main__":
    while True:
        try:
            if not despachar_uno():
                time.sleep(2)
        except SQLAlchemyError as exc:
            logging.error("Bandeja de avisos no disponible: %s", type(exc).__name__)
            time.sleep(5)
