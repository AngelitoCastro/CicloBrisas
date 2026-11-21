"""Pruebas del adaptador de IA para texto, imagen y audio (OpenAI y Azure OpenAI)."""

from __future__ import annotations

import json
from typing import ClassVar, Self

import pytest

from app.whatsapp import transcripcion
from app.whatsapp.errores import ProveedorNoDisponible
from app.whatsapp.ia import client as ia
from app.whatsapp.media import ArchivoMedia


class _Respuesta:
    def __init__(self, contenido: object) -> None:
        self.contenido = contenido

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self.contenido


class _ClienteHttp:
    respuesta: ClassVar[object] = {}
    llamadas: ClassVar[list[dict[str, object]]] = []

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def post(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        json: object = None,
        data: object = None,
        files: object = None,
    ) -> _Respuesta:
        type(self).llamadas.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "data": data,
                "files": files,
            }
        )
        return _Respuesta(type(self).respuesta)


@pytest.fixture(autouse=True)
def proveedor_openai_por_defecto(monkeypatch) -> None:
    monkeypatch.setenv("IA_PROVEEDOR", "openai")
    monkeypatch.delenv("AZURE_OPENAI_API_MODE", raising=False)


def _clasificacion_json() -> dict[str, object]:
    return {
        "intencion": "SOLICITUD_RECOLECCION",
        "flujo_sugerido": "ORGANICO",
        "disponibilidad_texto": "viernes",
        "respuesta_usuario": "Anotado.",
    }


def test_clasificar_texto_llama_chat_completions(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-pruebas")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    _ClienteHttp.llamadas.clear()
    _ClienteHttp.respuesta = {
        "choices": [{"message": {"content": json.dumps(_clasificacion_json())}}]
    }
    monkeypatch.setattr(ia.httpx, "Client", _ClienteHttp)

    resultado = ia.clasificar_texto("Recojo orgánicos el viernes")

    assert resultado.flujo_sugerido == "ORGANICO"
    llamada = _ClienteHttp.llamadas[0]
    assert llamada["url"] == "https://api.openai.com/v1/chat/completions"
    assert llamada["headers"] == {"Authorization": "Bearer sk-pruebas"}
    cuerpo = llamada["json"]
    assert isinstance(cuerpo, dict)
    assert cuerpo["model"] == "gpt-4o-mini"
    assert cuerpo["response_format"] == {"type": "json_object"}


def test_clasificacion_normaliza_flujo_en_minusculas(monkeypatch) -> None:
    datos = _clasificacion_json()
    datos["flujo_sugerido"] = "reciclable"
    monkeypatch.setattr(ia, "_consultar", lambda *_args, **_kwargs: json.dumps(datos))

    resultado = ia.clasificar_texto("Recojo cartón el viernes")

    assert resultado.flujo_sugerido == "RECICLABLE"


def test_clasificacion_normaliza_alias_de_flujo(monkeypatch) -> None:
    datos = _clasificacion_json()
    datos["flujo_sugerido"] = "recoleccion_organico"
    monkeypatch.setattr(ia, "_consultar", lambda *_args, **_kwargs: json.dumps(datos))

    resultado = ia.clasificar_texto("Recojo cáscaras el viernes")

    assert resultado.flujo_sugerido == "ORGANICO"


def test_clasificacion_normaliza_flujo_con_acento(monkeypatch) -> None:
    datos = _clasificacion_json()
    datos["flujo_sugerido"] = "orgánico"
    monkeypatch.setattr(ia, "_consultar", lambda *_args, **_kwargs: json.dumps(datos))

    resultado = ia.clasificar_texto("Recojo cáscaras el viernes")

    assert resultado.flujo_sugerido == "ORGANICO"


def test_clasificar_imagen_envia_data_uri(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-pruebas")
    _ClienteHttp.llamadas.clear()
    _ClienteHttp.respuesta = {
        "choices": [{"message": {"content": json.dumps(_clasificacion_json())}}]
    }
    monkeypatch.setattr(ia.httpx, "Client", _ClienteHttp)

    ia.clasificar_imagen(ArchivoMedia(b"imagen", "image/jpeg", "ME1"))

    cuerpo = _ClienteHttp.llamadas[0]["json"]
    assert isinstance(cuerpo, dict)
    mensajes = cuerpo["messages"]
    assert isinstance(mensajes, list)
    contenido = mensajes[1]["content"]
    assert contenido[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_transcribir_audio_envia_multipart(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-pruebas")
    monkeypatch.setenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-transcribe")
    _ClienteHttp.llamadas.clear()
    _ClienteHttp.respuesta = {"text": "Reciclo latas el lunes"}
    monkeypatch.setattr(transcripcion.httpx, "Client", _ClienteHttp)

    texto = transcripcion.transcribir_audio(ArchivoMedia(b"audio", "audio/ogg", "ME2"))

    assert texto == "Reciclo latas el lunes"
    llamada = _ClienteHttp.llamadas[0]
    assert llamada["url"] == "https://api.openai.com/v1/audio/transcriptions"
    assert llamada["data"] == {"model": "gpt-transcribe"}
    assert llamada["files"] is not None


def test_redactar_sin_api_key_devuelve_plantilla(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert ia.redactar("Hola {nombre}") == "Hola {nombre}"


def test_clasificar_texto_sin_api_key_falla(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ProveedorNoDisponible):
        ia.clasificar_texto("hola")


def _configurar_azure(monkeypatch, modo: str = "classic") -> None:
    monkeypatch.setenv("IA_PROVEEDOR", "azure")
    endpoint = (
        "https://recurso.openai.azure.com/openai/v1"
        if modo == "v1"
        else "https://recurso.openai.azure.com/"
    )
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", endpoint)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "clave-azure-pruebas")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "despliegue-chat")
    monkeypatch.setenv("AZURE_OPENAI_AUDIO_DEPLOYMENT", "despliegue-audio")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    if modo == "v1":
        monkeypatch.setenv("AZURE_OPENAI_API_MODE", "v1")


def test_clasificar_texto_usa_azure_despliegue_clasico(monkeypatch) -> None:
    _configurar_azure(monkeypatch)
    _ClienteHttp.llamadas.clear()
    _ClienteHttp.respuesta = {
        "choices": [{"message": {"content": json.dumps(_clasificacion_json())}}]
    }
    monkeypatch.setattr(ia.httpx, "Client", _ClienteHttp)

    resultado = ia.clasificar_texto("Recojo orgánicos el viernes")

    assert resultado.flujo_sugerido == "ORGANICO"
    llamada = _ClienteHttp.llamadas[0]
    assert llamada["url"] == (
        "https://recurso.openai.azure.com/openai/deployments/despliegue-chat/"
        "chat/completions?api-version=2024-10-21"
    )
    assert llamada["headers"] == {"api-key": "clave-azure-pruebas"}
    cuerpo = llamada["json"]
    assert isinstance(cuerpo, dict)
    assert "model" not in cuerpo
    assert cuerpo["max_completion_tokens"] == 2000
    assert "max_tokens" not in cuerpo
    assert "temperature" not in cuerpo
    assert cuerpo["response_format"] == {"type": "json_object"}


def test_clasificar_texto_usa_azure_v1(monkeypatch) -> None:
    _configurar_azure(monkeypatch, modo="v1")
    _ClienteHttp.llamadas.clear()
    _ClienteHttp.respuesta = {
        "choices": [{"message": {"content": json.dumps(_clasificacion_json())}}]
    }
    monkeypatch.setattr(ia.httpx, "Client", _ClienteHttp)

    ia.clasificar_texto("Recojo orgánicos el viernes")

    llamada = _ClienteHttp.llamadas[0]
    assert (
        llamada["url"] == "https://recurso.openai.azure.com/openai/v1/chat/completions"
    )
    assert llamada["headers"] == {"api-key": "clave-azure-pruebas"}
    cuerpo = llamada["json"]
    assert isinstance(cuerpo, dict)
    assert cuerpo["model"] == "despliegue-chat"
    assert cuerpo["max_completion_tokens"] == 2000
    assert "max_tokens" not in cuerpo
    assert "temperature" not in cuerpo


def test_transcribir_audio_usa_azure(monkeypatch) -> None:
    _configurar_azure(monkeypatch)
    _ClienteHttp.llamadas.clear()
    _ClienteHttp.respuesta = {"text": "Reciclo latas el lunes"}
    monkeypatch.setattr(transcripcion.httpx, "Client", _ClienteHttp)

    texto = transcripcion.transcribir_audio(ArchivoMedia(b"audio", "audio/ogg", "ME3"))

    assert texto == "Reciclo latas el lunes"
    llamada = _ClienteHttp.llamadas[0]
    assert llamada["url"] == (
        "https://recurso.openai.azure.com/openai/deployments/despliegue-audio/"
        "audio/transcriptions?api-version=2024-10-21"
    )
    assert llamada["headers"] == {"api-key": "clave-azure-pruebas"}
    assert llamada["data"] == {}


def test_azure_incompleto_falla_sin_llamada(monkeypatch) -> None:
    monkeypatch.setenv("IA_PROVEEDOR", "azure")
    for clave in (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_KEY",
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
    ):
        monkeypatch.delenv(clave, raising=False)
    _ClienteHttp.llamadas.clear()
    monkeypatch.setattr(ia.httpx, "Client", _ClienteHttp)

    with pytest.raises(ProveedorNoDisponible):
        ia.clasificar_texto("hola")

    assert _ClienteHttp.llamadas == []


def test_redactar_azure_incompleto_devuelve_plantilla(monkeypatch) -> None:
    monkeypatch.setenv("IA_PROVEEDOR", "azure")
    for clave in (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_KEY",
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
    ):
        monkeypatch.delenv(clave, raising=False)

    assert ia.redactar("Hola {nombre}") == "Hola {nombre}"


def test_clasificar_texto_envia_historial_y_perfil(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-pruebas")
    _ClienteHttp.llamadas.clear()
    _ClienteHttp.respuesta = {
        "choices": [{"message": {"content": json.dumps(_clasificacion_json())}}]
    }
    monkeypatch.setattr(ia.httpx, "Client", _ClienteHttp)

    ia.clasificar_texto(
        "¿Y ahora?",
        historial=[
            {"role": "user", "content": "Quiero reciclar"},
            {"role": "assistant", "content": "¿Qué material es?"},
        ],
        perfil="Rol registrado: HOGAR. EcoPuntos acumulados: 12.00.",
    )

    cuerpo = _ClienteHttp.llamadas[0]["json"]
    assert isinstance(cuerpo, dict)
    mensajes = cuerpo["messages"]
    assert mensajes[0]["role"] == "system"
    assert "Rol registrado: HOGAR" in mensajes[0]["content"]
    assert "EcoPuntos acumulados: 12.00" in mensajes[0]["content"]
    assert mensajes[1:3] == [
        {"role": "user", "content": "Quiero reciclar"},
        {"role": "assistant", "content": "¿Qué material es?"},
    ]
    assert mensajes[-1] == {"role": "user", "content": "¿Y ahora?"}


def test_prompt_incluye_reglas_personalizadas() -> None:
    from app.whatsapp.ia.prompt import prompt_sistema

    sistema = prompt_sistema("Rol registrado: HOGAR.")
    assert "aceite usado" in sistema
    assert "Rol registrado: HOGAR." in sistema
    assert "{REGLAS_PERSONALIZADAS}" not in sistema
