"""Extractor estructurado de solicitudes WhatsApp con Gemini (google-genai)."""

from __future__ import annotations

import httpx
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import ValidationError

from app.schemas_whatsapp import ExtraccionSolicitudMeta
from app.whatsapp.config import obtener_config
from app.whatsapp.errores import (
    ConfiguracionIncompleta,
    ErrorTransitorioIA,
    ErrorWhatsApp,
    SalidaIAInvalida,
)

_CODIGOS_TRANSITORIOS = frozenset({408, 429, 500, 502, 503, 504})

PROMPT_EXTRACCION_META = """Eres el extractor estructurado de solicitudes de recolección comunitaria de EcoConecta (Villas de San Pablo).
Tu única función es interpretar un mensaje ya anonimizado y devolver un JSON estricto con:
- flujo: "ORGANICO" (cáscaras, restos de comida, frutas, verduras, borra de café, poda/hojas), "RECICLABLE" (cartón, papel, plástico, PET, botellas, latas, vidrio, chatarra/metal), o "AMBIGUO" si mezcla flujos, es vago o no permite distinguir de forma inequívoca.
- material: nombre breve del material sin inventar ni incluir datos personales.
- cantidad: número positivo si se mencionó una cantidad; null si no se indicó.
- unidad: "KG", "G", "BOLSAS", "CAJAS", "BOTELLAS", "UNIDADES", "OTRA" o null. Usa "G" para gramos y "KG" para kilos/kilogramos.
- referencia_general: disponibilidad horaria o referencia general (ej. "mañana en la tarde", "portería") sin datos personales exactos; null si no hay.
- notas: detalles operativos útiles sin datos personales; null si no hay.
- es_solicitud: true si el remitente pide recolección de residuos; false si solo saluda, pregunta o no solicita recolección.

Reglas estrictas:
- Nunca asignes personas ni horarios confirmados.
- Si el flujo no es inequívoco, usa flujo="AMBIGUO".
- No inventes cantidades ni unidades que no estén en el texto.
"""


def _crear_cliente(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def extraer_solicitud_gemini(texto_anonimo: str) -> ExtraccionSolicitudMeta:
    """Llama a Gemini con salida estructurada y valida el esquema Pydantic."""
    cfg = obtener_config()
    if not cfg.gemini_api_key:
        raise ConfiguracionIncompleta("GEMINI_API_KEY")

    cliente = _crear_cliente(cfg.gemini_api_key)
    try:
        respuesta = cliente.models.generate_content(
            model=cfg.gemini_model,
            contents=texto_anonimo,
            config=types.GenerateContentConfig(
                system_instruction=PROMPT_EXTRACCION_META,
                response_mime_type="application/json",
                response_schema=ExtraccionSolicitudMeta,
                temperature=0.1,
            ),
        )
    except APIError as exc:
        codigo = getattr(exc, "code", None)
        if codigo in _CODIGOS_TRANSITORIOS or codigo is None:
            raise ErrorTransitorioIA("Gemini", str(codigo or "API")) from exc
        raise ErrorWhatsApp(
            f"GEMINI_HTTP_{codigo}",
            "Gemini rechazó la petición de extracción.",
            status_code=502,
        ) from exc
    except (httpx.HTTPError, TimeoutError, ConnectionError, OSError) as exc:
        raise ErrorTransitorioIA("Gemini", type(exc).__name__) from exc
    except Exception as exc:
        raise ErrorTransitorioIA("Gemini", type(exc).__name__) from exc

    parsed = getattr(respuesta, "parsed", None)
    try:
        if isinstance(parsed, ExtraccionSolicitudMeta):
            return parsed
        if isinstance(parsed, dict):
            return ExtraccionSolicitudMeta.model_validate(parsed)
        texto = getattr(respuesta, "text", None)
        if isinstance(texto, str) and texto.strip():
            return ExtraccionSolicitudMeta.model_validate_json(texto)
    except (ValidationError, ValueError, TypeError) as exc:
        raise SalidaIAInvalida() from exc

    raise SalidaIAInvalida()


__all__ = ["PROMPT_EXTRACCION_META", "extraer_solicitud_gemini"]
