"""Transcripción de notas de voz mediante OpenAI o Azure OpenAI."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from app.whatsapp.config import ConfiguracionWhatsApp, obtener_config
from app.whatsapp.errores import ConfiguracionIncompleta, ProveedorNoDisponible
from app.whatsapp.media import ArchivoMedia

_EXTENSIONES = {
    "audio/ogg": "nota.ogg",
    "audio/mpeg": "nota.mp3",
    "audio/mp4": "nota.m4a",
    "audio/webm": "nota.webm",
    "audio/wav": "nota.wav",
    "audio/x-wav": "nota.wav",
}


def _configuracion_transcripcion(
    configuracion: ConfiguracionWhatsApp,
) -> tuple[str, dict[str, str], dict[str, str], str]:
    if configuracion.proveedor_ia == "azure":
        endpoint = configuracion.azure_openai_endpoint.rstrip("/")
        despliegue = (
            configuracion.azure_openai_audio_deployment
            or configuracion.azure_openai_chat_deployment
        )
        if not endpoint or not configuracion.azure_openai_api_key or not despliegue:
            raise ConfiguracionIncompleta(
                "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY y "
                "AZURE_OPENAI_AUDIO_DEPLOYMENT"
            )
        if not endpoint.startswith(("http://", "https://")):
            endpoint = f"https://{endpoint}"
        cabeceras = {"api-key": configuracion.azure_openai_api_key}
        if configuracion.azure_openai_api_mode == "v1" or endpoint.endswith(
            "/openai/v1"
        ):
            return (
                f"{endpoint}/audio/transcriptions",
                cabeceras,
                {"model": despliegue},
                "Azure OpenAI STT",
            )
        version = quote(configuracion.azure_openai_api_version, safe="")
        nombre = quote(despliegue, safe="")
        url = (
            f"{endpoint}/openai/deployments/{nombre}/audio/transcriptions"
            f"?api-version={version}"
        )
        return url, cabeceras, {}, "Azure OpenAI STT"
    if not configuracion.openai_api_key:
        raise ConfiguracionIncompleta("OPENAI_API_KEY")
    return (
        "https://api.openai.com/v1/audio/transcriptions",
        {"Authorization": f"Bearer {configuracion.openai_api_key}"},
        {"model": configuracion.transcripcion_modelo},
        "OpenAI STT",
    )


def transcribir_audio(archivo: ArchivoMedia) -> str:
    configuracion = obtener_config()
    url, cabeceras, datos, proveedor = _configuracion_transcripcion(configuracion)
    nombre = _EXTENSIONES.get(archivo.mime_type, "nota.ogg")
    try:
        with httpx.Client(timeout=45.0) as cliente:
            respuesta = cliente.post(
                url,
                headers=cabeceras,
                data=datos,
                files={
                    "file": (nombre, archivo.datos, archivo.mime_type or "audio/ogg")
                },
            )
            respuesta.raise_for_status()
            texto = respuesta.json().get("text")
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        raise ProveedorNoDisponible(proveedor) from exc
    if not isinstance(texto, str) or not texto.strip():
        raise ProveedorNoDisponible(proveedor)
    return texto.strip()


__all__ = ["transcribir_audio"]
