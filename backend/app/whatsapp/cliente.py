"""Cliente de Twilio WhatsApp para mensajes salientes."""

from __future__ import annotations

import json

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.whatsapp.config import obtener_config
from app.whatsapp.errores import ConfiguracionIncompleta, ErrorWhatsApp


def _destino(telefono: str) -> str:
    valor = "".join(telefono.strip().split())
    if valor.lower().startswith("whatsapp:"):
        valor = valor.split(":", 1)[1]
    return f"whatsapp:{valor}"


def _fallo(exc: Exception) -> ErrorWhatsApp:
    return ErrorWhatsApp(
        f"TWILIO_{exc.code}" if isinstance(exc, TwilioRestException) and exc.code else "WHATSAPP_ENVIO_FALLIDO",
        "No fue posible entregar el mensaje de WhatsApp.",
    )


def enviar_texto(telefono: str, texto: str) -> str:
    configuracion = obtener_config()
    if (
        not configuracion.account_sid
        or not configuracion.auth_token
        or not configuracion.whatsapp_number
    ):
        raise ConfiguracionIncompleta(
            "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN y TWILIO_WHATSAPP_NUMBER"
        )

    base: dict[str, object] = {
        "from_": _destino(configuracion.whatsapp_number),
        "to": _destino(telefono),
    }
    cliente = Client(configuracion.account_sid, configuracion.auth_token)

    libre = {**base, "body": texto[:4000]}
    try:
        return str(cliente.messages.create(**libre).sid)
    except (TwilioRestException, ValueError, TypeError) as exc:
        if not configuracion.content_sid:
            raise _fallo(exc) from exc

    plantilla: dict[str, object] = {
        **base,
        "content_sid": configuracion.content_sid,
    }
    if not configuracion.content_sin_variables:
        plantilla["content_variables"] = json.dumps(
            {"1": " ".join(texto.split())[:1024]}, ensure_ascii=False
        )
        try:
            return str(cliente.messages.create(**plantilla).sid)
        except (TwilioRestException, ValueError, TypeError):
            plantilla.pop("content_variables", None)

    try:
        return str(cliente.messages.create(**plantilla).sid)
    except (TwilioRestException, ValueError, TypeError) as exc:
        raise _fallo(exc) from exc


__all__ = ["enviar_texto"]
