"""Configuración diferida de WhatsApp, OpenAI y Azure OpenAI, sin validación al importar."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfiguracionWhatsApp:
    account_sid: str = ""
    auth_token: str = ""
    whatsapp_number: str = ""
    content_sid: str = ""
    content_sin_variables: bool = False
    webhook_public_url: str = ""
    proveedor_ia: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    transcripcion_modelo: str = "gpt-transcribe"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_deployment: str = ""
    azure_openai_audio_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_api_mode: str = "classic"


def obtener_config() -> ConfiguracionWhatsApp:
    return ConfiguracionWhatsApp(
        account_sid=(os.getenv("TWILIO_ACCOUNT_SID") or "").strip(),
        auth_token=(os.getenv("TWILIO_AUTH_TOKEN") or "").strip(),
        whatsapp_number=(os.getenv("TWILIO_WHATSAPP_NUMBER") or "").strip(),
        content_sid=(os.getenv("TWILIO_CONTENT_SID") or "").strip(),
        content_sin_variables=(os.getenv("TWILIO_CONTENT_SIN_VARIABLES") or "")
        .strip()
        .lower()
        in {"1", "true", "yes"},
        webhook_public_url=(os.getenv("WEBHOOK_PUBLIC_URL") or "").strip().rstrip("/"),
        proveedor_ia=(os.getenv("IA_PROVEEDOR") or "openai").strip().lower(),
        openai_api_key=(os.getenv("OPENAI_API_KEY") or "").strip(),
        openai_model=(os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip(),
        transcripcion_modelo=(
            os.getenv("OPENAI_TRANSCRIPTION_MODEL") or "gpt-transcribe"
        ).strip(),
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


__all__ = ["ConfiguracionWhatsApp", "obtener_config"]
