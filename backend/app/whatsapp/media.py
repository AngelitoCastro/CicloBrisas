"""Descarga y preparación de imágenes y audios recibidos por Twilio."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from urllib.parse import urlparse

import httpx

from app.whatsapp.config import obtener_config
from app.whatsapp.errores import ConfiguracionIncompleta, MultimediaNoDisponible

MAX_BYTES = 16 * 1024 * 1024
HOST_PERMITIDO = "api.twilio.com"


@dataclass(frozen=True)
class ArchivoMedia:
    datos: bytes
    mime_type: str
    media_id: str


def descargar_media(url: str, mime_type: str | None = None) -> ArchivoMedia:
    configuracion = obtener_config()
    if not configuracion.account_sid or not configuracion.auth_token:
        raise ConfiguracionIncompleta("TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN")
    if urlparse(url).hostname != HOST_PERMITIDO:
        raise MultimediaNoDisponible()
    try:
        with httpx.Client(timeout=15.0) as cliente:
            respuesta = cliente.get(
                url,
                auth=(configuracion.account_sid, configuracion.auth_token),
            )
            respuesta.raise_for_status()
    except (httpx.HTTPError, ValueError) as exc:
        raise MultimediaNoDisponible() from exc

    datos = respuesta.content
    if not datos or len(datos) > MAX_BYTES:
        raise MultimediaNoDisponible()
    return ArchivoMedia(datos, mime_type or "application/octet-stream", url)


def preparar_imagen(archivo: ArchivoMedia) -> ArchivoMedia:
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return archivo
    try:
        with Image.open(BytesIO(archivo.datos)) as imagen:
            normalizada = ImageOps.exif_transpose(imagen).convert("RGB")
            normalizada.thumbnail((1024, 1024))
            destino = BytesIO()
            normalizada.save(destino, format="JPEG", quality=85)
            return ArchivoMedia(destino.getvalue(), "image/jpeg", archivo.media_id)
    except OSError:
        return archivo


__all__ = ["ArchivoMedia", "descargar_media", "preparar_imagen"]
