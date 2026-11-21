"""Pruebas del adaptador saliente y de medios de Twilio."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import ClassVar, Self

import pytest
from twilio.base.exceptions import TwilioRestException

from app.whatsapp import cliente, media
from app.whatsapp.errores import ConfiguracionIncompleta, MultimediaNoDisponible


class _Mensajes:
    def __init__(self) -> None:
        self.opciones: dict[str, object] = {}

    def create(self, **opciones: object) -> SimpleNamespace:
        self.opciones = opciones
        return SimpleNamespace(sid="SMsalida123")


class _ClienteTwilio:
    instancias: ClassVar[list[_ClienteTwilio]] = []

    def __init__(self, account_sid: str, auth_token: str) -> None:
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.messages = _Mensajes()
        _ClienteTwilio.instancias.append(self)


def test_enviar_texto_usa_numero_twilio_y_devuelve_sid(monkeypatch) -> None:
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
    monkeypatch.delenv("TWILIO_CONTENT_SID", raising=False)
    _ClienteTwilio.instancias.clear()
    monkeypatch.setattr(cliente, "Client", _ClienteTwilio)

    sid = cliente.enviar_texto("+573001112222", "Hola EcoConecta")

    assert sid == "SMsalida123"
    instancia = _ClienteTwilio.instancias[0]
    assert (instancia.account_sid, instancia.auth_token) == ("AC123", "token")
    assert instancia.messages.opciones == {
        "from_": "whatsapp:+14155238886",
        "to": "whatsapp:+573001112222",
        "body": "Hola EcoConecta",
    }


def test_enviar_texto_normaliza_numeros_con_espacios(monkeypatch) -> None:
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_WHATSAPP_NUMBER", "+1 555 123 4567")
    monkeypatch.delenv("TWILIO_CONTENT_SID", raising=False)
    _ClienteTwilio.instancias.clear()
    monkeypatch.setattr(cliente, "Client", _ClienteTwilio)

    cliente.enviar_texto("+57 300 111 2222", "Hola")

    opciones = _ClienteTwilio.instancias[0].messages.opciones
    assert opciones["from_"] == "whatsapp:+15551234567"
    assert opciones["to"] == "whatsapp:+573001112222"


def test_enviar_texto_usa_content_sid_cuando_esta_configurado(monkeypatch) -> None:
    class Mensajes:
        def __init__(self) -> None:
            self.intentos: list[dict[str, object]] = []

        def create(self, **opciones: object) -> SimpleNamespace:
            self.intentos.append(opciones)
            if len(self.intentos) == 1:
                raise TwilioRestException(
                    status=400, uri="/Messages", msg="fuera de ventana", code=63016
                )
            return SimpleNamespace(sid="SMplantilla")

    mensajes = Mensajes()
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")
    monkeypatch.setenv("TWILIO_CONTENT_SID", "HX123")
    monkeypatch.delenv("TWILIO_CONTENT_SIN_VARIABLES", raising=False)
    monkeypatch.setattr(cliente, "Client", lambda *_: SimpleNamespace(messages=mensajes))

    assert cliente.enviar_texto("+573001112222", "Aviso") == "SMplantilla"
    assert mensajes.intentos[0]["body"] == "Aviso"
    opciones = mensajes.intentos[1]
    assert opciones["from_"] == "whatsapp:+14155238886"
    assert opciones["content_sid"] == "HX123"
    assert opciones["content_variables"] == json.dumps(
        {"1": "Aviso"}, ensure_ascii=False
    )
    assert "body" not in opciones


def test_enviar_texto_no_envia_variables_cuando_template_no_las_acepta(
    monkeypatch,
) -> None:
    class Mensajes:
        def __init__(self) -> None:
            self.intentos: list[dict[str, object]] = []

        def create(self, **opciones: object) -> SimpleNamespace:
            self.intentos.append(opciones)
            if len(self.intentos) == 1:
                raise TwilioRestException(
                    status=400, uri="/Messages", msg="fuera de ventana", code=63016
                )
            return SimpleNamespace(sid="SMplantilla")

    mensajes = Mensajes()
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")
    monkeypatch.setenv("TWILIO_CONTENT_SID", "HX123")
    monkeypatch.setenv("TWILIO_CONTENT_SIN_VARIABLES", "true")
    monkeypatch.setattr(cliente, "Client", lambda *_: SimpleNamespace(messages=mensajes))

    cliente.enviar_texto("+573001112222", "Aviso")

    opciones = mensajes.intentos[1]
    assert opciones["content_sid"] == "HX123"
    assert "content_variables" not in opciones
    assert "body" not in opciones


def test_enviar_texto_reintenta_sin_variables_cuando_template_no_las_acepta(
    monkeypatch,
) -> None:
    class Mensajes:
        def __init__(self) -> None:
            self.intentos: list[dict[str, object]] = []

        def create(self, **opciones: object) -> SimpleNamespace:
            self.intentos.append(opciones)
            if len(self.intentos) == 1:
                raise TwilioRestException(
                    status=400, uri="/Messages", msg="fuera de ventana", code=63016
                )
            if len(self.intentos) == 2:
                raise TwilioRestException(
                    status=400, uri="/Messages", msg="invalid", code=21656
                )
            return SimpleNamespace(sid="SMreintento")

    mensajes = Mensajes()
    cliente_twilio = SimpleNamespace(messages=mensajes)
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")
    monkeypatch.setenv("TWILIO_CONTENT_SID", "HX123")
    monkeypatch.delenv("TWILIO_CONTENT_SIN_VARIABLES", raising=False)
    monkeypatch.setattr(cliente, "Client", lambda *_: cliente_twilio)

    assert cliente.enviar_texto("+573001112222", "Aviso\nimportante") == "SMreintento"
    assert mensajes.intentos[0]["body"] == "Aviso\nimportante"
    assert "content_variables" in mensajes.intentos[1]
    assert "content_variables" not in mensajes.intentos[2]
    assert mensajes.intentos[1]["content_variables"] == json.dumps(
        {"1": "Aviso importante"}, ensure_ascii=False
    )


def test_enviar_texto_sin_credenciales_falla(monkeypatch) -> None:
    for variable in (
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_WHATSAPP_NUMBER",
    ):
        monkeypatch.delenv(variable, raising=False)
    with pytest.raises(ConfiguracionIncompleta):
        cliente.enviar_texto("+573001112222", "Hola")


class _Respuesta:
    def __init__(self, contenido: bytes) -> None:
        self.content = contenido

    def raise_for_status(self) -> None:
        return None


class _ClienteHttp:
    ultimo_auth: tuple[str, str] | None = None

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def get(self, url: str, auth: tuple[str, str]) -> _Respuesta:
        _ClienteHttp.ultimo_auth = auth
        return _Respuesta(b"contenido")


def test_descargar_media_autentica_con_twilio(monkeypatch) -> None:
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setattr(media.httpx, "Client", _ClienteHttp)

    archivo = media.descargar_media(
        "https://api.twilio.com/2010-04-01/Accounts/AC123/Messages/SM/Media/ME",
        "image/jpeg",
    )

    assert archivo.datos == b"contenido"
    assert archivo.mime_type == "image/jpeg"
    assert _ClienteHttp.ultimo_auth == ("AC123", "token")


def test_descargar_media_rechaza_otro_host(monkeypatch) -> None:
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setattr(media.httpx, "Client", _ClienteHttp)

    with pytest.raises(MultimediaNoDisponible):
        media.descargar_media("https://ejemplo.com/archivo.jpg", "image/jpeg")
