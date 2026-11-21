"""Cliente de IA con salida estructurada validada (OpenAI o Azure OpenAI)."""

from __future__ import annotations

import base64
import json
import re
import unicodedata
from urllib.parse import quote

import httpx

from app.schemas_whatsapp import ClasificacionIA, IntencionIA
from app.whatsapp.anonimizacion import anonimizar
from app.whatsapp.config import ConfiguracionWhatsApp, obtener_config
from app.whatsapp.errores import ProveedorNoDisponible
from app.whatsapp.ia.prompt import (
    PROMPT_REDACCION,
    RESPUESTA_FALLBACK,
    prompt_sistema,
)
from app.whatsapp.media import ArchivoMedia


def _fallback() -> ClasificacionIA:
    return ClasificacionIA(
        intencion=IntencionIA.OTRO,
        respuesta_usuario=RESPUESTA_FALLBACK,
    )


def _parsear_clasificacion(contenido: str | None) -> ClasificacionIA:
    texto = contenido or ""
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio < 0 or fin <= inicio:
        return _fallback()
    try:
        datos = json.loads(texto[inicio : fin + 1])
        flujo = datos.get("flujo_sugerido")
        if isinstance(flujo, str):
            normalizado = (
                unicodedata.normalize("NFKD", flujo)
                .encode("ascii", "ignore")
                .decode()
                .strip()
                .upper()
            )
            if "ORGAN" in normalizado:
                datos["flujo_sugerido"] = "ORGANICO"
            elif "RECICL" in normalizado:
                datos["flujo_sugerido"] = "RECICLABLE"
            else:
                datos["flujo_sugerido"] = normalizado
        return ClasificacionIA.model_validate(datos)
    except (ValueError, TypeError):
        return _fallback()


def _parsear_redaccion(contenido: str | None, plantilla: str) -> str:
    texto = contenido or ""
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio < 0 or fin <= inicio:
        return plantilla
    try:
        resultado = json.loads(texto[inicio : fin + 1])
        texto_final = str(resultado["texto"]).strip()
    except (ValueError, TypeError, KeyError):
        return plantilla
    marcadores = re.findall(r"\{[^{}]+\}", plantilla)
    if any(marcador not in texto_final for marcador in marcadores):
        return plantilla
    return texto_final or plantilla


def _configuracion_chat_azure(
    configuracion: ConfiguracionWhatsApp,
) -> tuple[str, dict[str, str], str | None]:
    endpoint = configuracion.azure_openai_endpoint.rstrip("/")
    clave = configuracion.azure_openai_api_key
    despliegue = configuracion.azure_openai_chat_deployment
    if not endpoint or not clave or not despliegue:
        raise ProveedorNoDisponible("Azure OpenAI")
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"
    if configuracion.azure_openai_api_mode == "v1" or endpoint.endswith("/openai/v1"):
        return f"{endpoint}/chat/completions", {"api-key": clave}, despliegue
    version = quote(configuracion.azure_openai_api_version, safe="")
    nombre = quote(despliegue, safe="")
    url = (
        f"{endpoint}/openai/deployments/{nombre}/chat/completions?api-version={version}"
    )
    return url, {"api-key": clave}, None


def _verificar_proveedor(configuracion: ConfiguracionWhatsApp) -> None:
    if configuracion.proveedor_ia == "azure":
        _configuracion_chat_azure(configuracion)
        return
    if not configuracion.openai_api_key:
        raise ProveedorNoDisponible("OpenAI")


def _consultar(
    sistema: str,
    usuario: object,
    historial: list[dict[str, str]] | None = None,
) -> str:
    configuracion = obtener_config()
    mensajes: list[dict[str, object]] = [{"role": "system", "content": sistema}]
    if historial:
        mensajes.extend(historial)
    mensajes.append({"role": "user", "content": usuario})
    cuerpo: dict[str, object] = {
        "messages": mensajes,
        "response_format": {"type": "json_object"},
    }
    if configuracion.proveedor_ia == "azure":
        url, cabeceras, modelo = _configuracion_chat_azure(configuracion)
        if modelo is not None:
            cuerpo["model"] = modelo
        cuerpo["max_completion_tokens"] = 2000
        proveedor = "Azure OpenAI"
    else:
        if not configuracion.openai_api_key:
            raise ProveedorNoDisponible("OpenAI")
        url = "https://api.openai.com/v1/chat/completions"
        cabeceras = {"Authorization": f"Bearer {configuracion.openai_api_key}"}
        cuerpo["model"] = configuracion.openai_model
        cuerpo["temperature"] = 0.3
        cuerpo["max_tokens"] = 700
        proveedor = "OpenAI"
    try:
        with httpx.Client(timeout=30.0) as cliente:
            respuesta = cliente.post(url, headers=cabeceras, json=cuerpo)
            respuesta.raise_for_status()
            return str(respuesta.json()["choices"][0]["message"]["content"])
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise ProveedorNoDisponible(proveedor) from exc


def clasificar_texto(
    texto: str,
    contexto: str | None = None,
    historial: list[dict[str, str]] | None = None,
    perfil: str | None = None,
) -> ClasificacionIA:
    limpio = anonimizar(texto)
    usuario = (
        f"Contexto: {anonimizar(contexto)}\nMensaje: {limpio}" if contexto else limpio
    )
    return _parsear_clasificacion(
        _consultar(prompt_sistema(perfil), usuario, historial=historial)
    )


def clasificar_imagen(
    archivo: ArchivoMedia,
    texto_usuario: str | None = None,
    historial: list[dict[str, str]] | None = None,
    perfil: str | None = None,
) -> ClasificacionIA:
    configuracion = obtener_config()
    mime = archivo.mime_type if archivo.mime_type.startswith("image/") else "image/jpeg"
    codificada = base64.b64encode(archivo.datos).decode("ascii")
    instruccion = (
        f"La persona envió esta foto de residuos. {anonimizar(texto_usuario)}"
        if texto_usuario
        else "La persona envió esta foto de residuos. Identifica el material y qué recolección solicita."
    )
    usuario: object = [
        {"type": "text", "text": instruccion},
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{codificada}"},
        },
    ]
    _verificar_proveedor(configuracion)
    return _parsear_clasificacion(
        _consultar(prompt_sistema(perfil), usuario, historial=historial)
    )


def redactar(plantilla: str) -> str:
    try:
        contenido = _consultar(PROMPT_REDACCION, plantilla)
    except ProveedorNoDisponible:
        return plantilla
    return _parsear_redaccion(contenido, plantilla)


__all__ = ["clasificar_imagen", "clasificar_texto", "redactar"]
