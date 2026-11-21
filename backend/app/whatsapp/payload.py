"""Verificación de firma y normalización del payload entrante de Twilio."""

from __future__ import annotations

import re
from collections.abc import Iterable

from twilio.request_validator import RequestValidator

from app.schemas_whatsapp import MensajeNormalizado, PayloadTwilio
from app.whatsapp.errores import FirmaInvalida


def verificar_firma_twilio(
    url: str | Iterable[str],
    parametros: dict[str, str],
    cabecera: str | None,
    auth_token: str,
) -> None:
    if not auth_token or not cabecera:
        raise FirmaInvalida()
    urls = [url] if isinstance(url, str) else list(url)
    validador = RequestValidator(auth_token)
    if not any(validador.validate(candidata, parametros, cabecera) for candidata in urls):
        raise FirmaInvalida()


def normalizar_telefono(valor: str) -> str:
    limpio = re.sub(r"(?i)^whatsapp:", "", (valor or "").strip())
    digitos = re.sub(r"\D", "", limpio)
    if len(digitos) == 10:
        return f"+57{digitos}"
    if len(digitos) == 12 and digitos.startswith("57"):
        return f"+{digitos}"
    if digitos:
        return f"+{digitos}"
    return limpio


def extraer_mensajes(payload: PayloadTwilio) -> list[MensajeNormalizado]:
    if payload.es_actualizacion_estado:
        return []
    telefono = normalizar_telefono(payload.from_telefono)
    mime = (payload.media_content_type0 or "").strip().lower()
    if payload.num_media > 0 and payload.media_url0:
        if mime.startswith("image/"):
            return [
                MensajeNormalizado(
                    id=payload.message_sid,
                    telefono=telefono,
                    tipo="image",
                    texto=payload.body or None,
                    media_id=payload.media_url0,
                    media_mime=payload.media_content_type0,
                )
            ]
        if mime.startswith("audio/"):
            return [
                MensajeNormalizado(
                    id=payload.message_sid,
                    telefono=telefono,
                    tipo="audio",
                    texto=payload.body or None,
                    media_id=payload.media_url0,
                    media_mime=payload.media_content_type0,
                    es_voz=True,
                )
            ]
        return [
            MensajeNormalizado(
                id=payload.message_sid,
                telefono=telefono,
                tipo="text",
                texto="Adjunto un archivo que todavía no puedo leer.",
            )
        ]
    return [
        MensajeNormalizado(
            id=payload.message_sid,
            telefono=telefono,
            tipo="text",
            texto=payload.body or None,
        )
    ]


__all__ = ["extraer_mensajes", "normalizar_telefono", "verificar_firma_twilio"]
