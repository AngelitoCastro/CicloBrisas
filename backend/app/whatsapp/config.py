"""Configuración diferida de WhatsApp (Meta y Twilio) e IA, sin validación al importar."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _es_verdadero(valor: str | None) -> bool:
    return (valor or "").strip().lower() in {"1", "true", "yes", "si", "sí"}


def _entero(nombre: str, defecto: int, minimo: int = 0) -> int:
    bruto = (os.getenv(nombre) or "").strip()
    if not bruto:
        return defecto
    try:
        valor = int(bruto)
    except ValueError:
        return defecto
    return max(minimo, valor)


@dataclass(frozen=True)
class ConfiguracionWhatsApp:
    account_sid: str = ""
    auth_token: str = ""
    whatsapp_number: str = ""
    content_sid: str = ""
    content_sin_variables: bool = False
    webhook_public_url: str = ""
    whatsapp_proveedor: str = "auto"
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_graph_version: str = "v25.0"
    whatsapp_template_lang: str = "es"
    whatsapp_template_sin_variables: bool = False
    whatsapp_exigir_consentimiento_explicito: bool = False
    proveedor_ia: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    transcripcion_modelo: str = "gpt-transcribe"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_max_intentos: int = 3
    gemini_backoff_base_segundos: int = 15
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_deployment: str = ""
    azure_openai_audio_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_api_mode: str = "classic"


def obtener_config() -> ConfiguracionWhatsApp:
    verify_token = (
        os.getenv("WHATSAPP_VERIFY_TOKEN")
        or os.getenv("VERIFY_TOKEN")
        or ""
    ).strip()

    return ConfiguracionWhatsApp(
        account_sid=(os.getenv("TWILIO_ACCOUNT_SID") or "").strip(),
        auth_token=(os.getenv("TWILIO_AUTH_TOKEN") or "").strip(),
        whatsapp_number=(os.getenv("TWILIO_WHATSAPP_NUMBER") or "").strip(),
        content_sid=(os.getenv("TWILIO_CONTENT_SID") or "").strip(),
        content_sin_variables=_es_verdadero(os.getenv("TWILIO_CONTENT_SIN_VARIABLES")),
        webhook_public_url=(os.getenv("WEBHOOK_PUBLIC_URL") or "").strip().rstrip("/"),
        whatsapp_proveedor=(os.getenv("WHATSAPP_PROVEEDOR") or "auto").strip().lower(),
        whatsapp_verify_token=verify_token,
        whatsapp_app_secret=(os.getenv("WHATSAPP_APP_SECRET") or "").strip(),
        whatsapp_access_token=(
            os.getenv("WHATSAPP_ACCESS_TOKEN") or os.getenv("WHATSAPP_TOKEN") or ""
        ).strip(),
        whatsapp_phone_number_id=(
            os.getenv("WHATSAPP_PHONE_NUMBER_ID") or os.getenv("PHONE_NUMBER_ID") or ""
        ).strip(),
        whatsapp_graph_version=(
            os.getenv("WHATSAPP_GRAPH_VERSION") or "v25.0"
        ).strip(),
        whatsapp_template_lang=(os.getenv("WHATSAPP_TEMPLATE_LANG") or "es").strip(),
        whatsapp_template_sin_variables=_es_verdadero(
            os.getenv("WHATSAPP_TEMPLATE_SIN_VARIABLES")
        ),
        whatsapp_exigir_consentimiento_explicito=_es_verdadero(
            os.getenv("WHATSAPP_EXIGIR_CONSENTIMIENTO_EXPLICITO")
        ),
        proveedor_ia=(os.getenv("IA_PROVEEDOR") or "openai").strip().lower(),
        openai_api_key=(os.getenv("OPENAI_API_KEY") or "").strip(),
        openai_model=(os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip(),
        transcripcion_modelo=(
            os.getenv("OPENAI_TRANSCRIPTION_MODEL") or "gpt-transcribe"
        ).strip(),
        gemini_api_key=(os.getenv("GEMINI_API_KEY") or "").strip(),
        gemini_model=(os.getenv("GEMINI_MODEL") or "gemini-3.5-flash-lite").strip(),
        gemini_max_intentos=_entero("GEMINI_MAX_INTENTOS", 3, minimo=1),
        gemini_backoff_base_segundos=_entero(
            "GEMINI_BACKOFF_BASE_SEGUNDOS", 15, minimo=0
        ),
        azure_openai_endpoint=(os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip(),
        azure_openai_api_key=(
            os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY") or ""
        ).strip(),
        azure_openai_chat_deployment=(
            os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
            or ""
        ).strip(),
        azure_openai_audio_deployment=(
            os.getenv("AZURE_OPENAI_AUDIO_DEPLOYMENT") or ""
        ).strip(),
        azure_openai_api_version=(
            os.getenv("AZURE_OPENAI_API_VERSION")
            or os.getenv("OPENAI_API_VERSION")
            or "2024-10-21"
        ).strip(),
        azure_openai_api_mode=(os.getenv("AZURE_OPENAI_API_MODE") or "classic")
        .strip()
        .lower(),
    )


def proveedor_whatsapp_activo(cfg: ConfiguracionWhatsApp) -> str:
    """Determina si el envío saliente usa Meta Cloud API o Twilio."""
    if cfg.whatsapp_proveedor in {"meta", "twilio"}:
        return cfg.whatsapp_proveedor
    if cfg.whatsapp_access_token and cfg.whatsapp_phone_number_id:
        return "meta"
    return "twilio"


def plantilla_meta_para(evento: str, destinatario: str) -> str:
    """Resuelve el nombre de la plantilla aprobada de Meta para evento y destinatario."""
    especifica = (
        os.getenv(f"WHATSAPP_TEMPLATE_{evento.upper()}_{destinatario.upper()}") or ""
    ).strip()
    if especifica:
        return especifica
    return (os.getenv("WHATSAPP_TEMPLATE_DEFAULT") or "").strip()


__all__ = [
    "ConfiguracionWhatsApp",
    "obtener_config",
    "plantilla_meta_para",
    "proveedor_whatsapp_activo",
]
