"""Pruebas del webhook de Twilio con proveedores sustituidos."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from twilio.request_validator import RequestValidator

from app.models import AvisoWhatsApp, MensajeWhatsapp, Solicitud, Usuario
from app.schemas_whatsapp import ClasificacionIA, IntencionIA
from app.whatsapp.errores import ProveedorNoDisponible
from app.whatsapp.media import ArchivoMedia
from tests.conftest import fecha_futura, usuario_por_rol

CUENTA = "ACtwilio pruebas 1234567890"
TOKEN = "token-twilio-pruebas"
REMITENTE = "whatsapp:+14155238886"
URL = "http://testserver/api/webhooks/whatsapp"
URL_PUBLICA = "https://webhook.publico/api/webhooks/whatsapp"


@pytest.fixture()
def proveedores(monkeypatch, session_factory):
    enviados: list[tuple[str, str]] = []

    def falso_enviar(telefono: str, texto: str) -> str:
        enviados.append((telefono, texto))
        return f"SMsaliente-{len(enviados)}"

    monkeypatch.setenv("TWILIO_ACCOUNT_SID", CUENTA)
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("TWILIO_WHATSAPP_NUMBER", REMITENTE)
    monkeypatch.delenv("WEBHOOK_PUBLIC_URL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-pruebas")
    monkeypatch.setattr("app.whatsapp.webhook_service.SessionLocal", session_factory)
    monkeypatch.setattr("app.whatsapp.webhook_service.enviar_texto", falso_enviar)
    monkeypatch.setattr("app.whatsapp.estado.redactar", lambda plantilla: plantilla)
    return enviados


def _firmar(parametros: dict[str, str], token: str = TOKEN, url: str = URL) -> str:
    return RequestValidator(token).compute_signature(url, parametros)


def _publicar(
    client,
    mensajes: list[dict[str, str]],
    *,
    cuenta: str = CUENTA,
    token: str = TOKEN,
    firma: str | None = None,
    url: str = URL,
    cabeceras: dict[str, str] | None = None,
):
    mensaje = mensajes[0]
    parametros = {
        "AccountSid": cuenta,
        "To": REMITENTE,
        **mensaje,
    }
    cabecera = firma if firma is not None else _firmar(parametros, token, url)
    headers = {"X-Twilio-Signature": cabecera}
    if cabeceras:
        headers.update(cabeceras)
    return client.post(
        "/api/webhooks/whatsapp",
        data=parametros,
        headers=headers,
    )


def _texto(identificador: str, telefono: str, texto: str) -> dict[str, str]:
    return {
        "MessageSid": identificador,
        "From": f"whatsapp:{telefono}",
        "Body": texto,
        "NumMedia": "0",
    }


def _media(
    identificador: str,
    telefono: str,
    url: str,
    mime: str,
) -> dict[str, str]:
    return {
        "MessageSid": identificador,
        "From": f"whatsapp:{telefono}",
        "Body": "",
        "NumMedia": "1",
        "MediaUrl0": url,
        "MediaContentType0": mime,
    }


def _ia_texto(monkeypatch, respuestas: list[ClasificacionIA]) -> list[str]:
    vistos: list[str] = []
    resultados: Iterator[ClasificacionIA] = iter(respuestas)

    def falso_clasificar(
        texto: str,
        contexto: str | None = None,
        historial: list[dict[str, str]] | None = None,
        perfil: str | None = None,
    ) -> ClasificacionIA:
        vistos.append(texto)
        return next(resultados)

    monkeypatch.setattr(
        "app.whatsapp.webhook_service.ia.clasificar_texto", falso_clasificar
    )
    return vistos


def _solicitud_creada(
    clasificacion: ClasificacionIA,
    respuesta: str = "Listo.",
) -> ClasificacionIA:
    return clasificacion.model_copy(update={"respuesta_usuario": respuesta})


def test_firma_invalida_no_procesa(client, proveedores) -> None:
    respuesta = _publicar(
        client,
        [_texto("SMfirma", "+573001112222", "hola")],
        firma="invalida",
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["codigo"] == "WEBHOOK_FIRMA_INVALIDA"


def test_cuenta_invalida_no_procesa(client, proveedores) -> None:
    respuesta = _publicar(
        client,
        [_texto("SMcuenta", "+573001112222", "hola")],
        cuenta="ACotra",
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["codigo"] == "WEBHOOK_CUENTA_INVALIDA"


def test_firma_valida_con_url_publica_configurada(
    client, monkeypatch, proveedores
) -> None:
    monkeypatch.setenv("WEBHOOK_PUBLIC_URL", URL_PUBLICA)
    respuesta = _publicar(
        client, [_texto("SMurlpublica", "+573001112222", "hola")], url=URL_PUBLICA
    )
    assert respuesta.status_code == 200


def test_firma_valida_con_barra_final(client, monkeypatch, proveedores) -> None:
    monkeypatch.setenv("WEBHOOK_PUBLIC_URL", URL_PUBLICA)
    respuesta = _publicar(
        client,
        [_texto("SMbarra", "+573001112222", "hola")],
        url=f"{URL_PUBLICA}/",
    )
    assert respuesta.status_code == 200


def test_firma_valida_con_cabeceras_de_proxy(client, monkeypatch, proveedores) -> None:
    monkeypatch.delenv("WEBHOOK_PUBLIC_URL", raising=False)
    respuesta = _publicar(
        client,
        [_texto("SMproxy", "+573001112222", "hola")],
        url=URL_PUBLICA,
        cabeceras={
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "webhook.publico",
        },
    )
    assert respuesta.status_code == 200


def test_mensaje_entrante_con_sms_status_recibido_se_procesa(
    client, db, proveedores
) -> None:
    mensaje = {
        **_texto("SMsmsstatus", "+573001112222", "hola"),
        "SmsStatus": "received",
    }
    assert _publicar(client, [mensaje]).status_code == 200
    assert db.scalar(select(func.count()).select_from(MensajeWhatsapp)) == 2


def test_actualizacion_de_estado_no_procesa(client, db, proveedores) -> None:
    parametros = {
        "AccountSid": CUENTA,
        "To": REMITENTE,
        "MessageSid": "SMestado",
        "MessageStatus": "delivered",
    }
    respuesta = client.post(
        "/api/webhooks/whatsapp",
        data=parametros,
        headers={"X-Twilio-Signature": _firmar(parametros)},
    )
    assert respuesta.status_code == 200
    assert "<Response/>" in respuesta.text
    assert db.scalar(select(func.count()).select_from(MensajeWhatsapp)) == 0


def test_metodo_get_no_disponible(client, proveedores) -> None:
    assert client.get("/api/webhooks/whatsapp").status_code == 405


def test_texto_crea_solicitud_con_preferencia_y_dedupe(
    client, db, monkeypatch, proveedores, telefono
) -> None:
    clasificacion = _solicitud_creada(
        ClasificacionIA(
            intencion=IntencionIA.SOLICITUD_RECOLECCION,
            flujo_sugerido="ORGANICO",
            subtipo_material="Cáscaras de frutas",
            disponibilidad_texto="viernes",
            respuesta_usuario="Anotado.",
        )
    )
    _ia_texto(monkeypatch, [clasificacion])
    mensaje = _texto("SMcrear1", telefono["HOGAR"], "Recojo orgánicos el viernes")

    assert _publicar(client, [mensaje]).status_code == 200
    db.expire_all()
    hogar = usuario_por_rol(db, "HOGAR", telefono["HOGAR"])
    solicitudes = db.scalars(
        select(Solicitud).where(Solicitud.solicitante_id == hogar.id)
    ).all()
    assert len(solicitudes) == 1
    solicitud = solicitudes[0]
    assert solicitud.estado == "RECIBIDA"
    assert solicitud.disponibilidad_usuario == "viernes"
    assert solicitud.recolector_id is None
    assert solicitud.fecha_programada is None
    assert solicitud.hora_programada is None

    mensajes_db = db.scalars(select(MensajeWhatsapp)).all()
    assert any(
        mensaje.direccion == "ENTRANTE"
        and mensaje.wa_message_id == "SMcrear1"
        and mensaje.solicitud_id == solicitud.id
        for mensaje in mensajes_db
    )
    assert any(
        mensaje.direccion == "SALIENTE"
        and solicitud.codigo_publico in mensaje.contenido
        for mensaje in mensajes_db
    )

    assert _publicar(client, [mensaje]).status_code == 200
    db.expire_all()
    total = db.scalar(select(func.count()).select_from(Solicitud))
    assert total == 1
    total_mensajes = db.scalar(select(func.count()).select_from(MensajeWhatsapp))
    assert total_mensajes == len(mensajes_db)


def test_flujo_ambiguo_pregunta_y_luego_crea(
    client, db, monkeypatch, proveedores, telefono
) -> None:
    _ia_texto(
        monkeypatch,
        [
            ClasificacionIA(
                intencion=IntencionIA.SOLICITUD_RECOLECCION,
                flujo_sugerido=None,
                disponibilidad_texto="viernes",
                respuesta_usuario="¿Son orgánicos o reciclables?",
            ),
            ClasificacionIA(
                intencion=IntencionIA.SOLICITUD_RECOLECCION,
                flujo_sugerido="ORGANICO",
                disponibilidad_texto="viernes",
                respuesta_usuario="Perfecto.",
            ),
        ],
    )
    numero = telefono["HOGAR"]
    assert (
        _publicar(
            client, [_texto("SMambiguo1", numero, "Quiero que recojan esto")]
        ).status_code
        == 200
    )
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Solicitud)) == 0
    pendiente = db.scalar(
        select(MensajeWhatsapp).where(
            MensajeWhatsapp.estado_conversacion == "ACLARACION_PENDIENTE"
        )
    )
    assert pendiente is not None
    assert "viernes" in (pendiente.borrador_json or "")

    assert (
        _publicar(client, [_texto("SMambiguo2", numero, "Son orgánicos")]).status_code
        == 200
    )
    db.expire_all()
    solicitudes = db.scalars(select(Solicitud)).all()
    assert len(solicitudes) == 1
    assert solicitudes[0].flujo == "ORGANICO"
    assert solicitudes[0].disponibilidad_usuario == "viernes"


def test_numero_nuevo_se_registra_con_paso_previo(
    client, db, monkeypatch, proveedores
) -> None:
    numero = "+573001112222"
    assert _publicar(client, [_texto("SMregistro1", numero, "hola")]).status_code == 200
    db.expire_all()
    assert db.scalar(select(Usuario).where(Usuario.telefono == numero)) is None

    _ia_texto(
        monkeypatch,
        [
            ClasificacionIA(
                intencion=IntencionIA.OTRO,
                respuesta_usuario="Gracias, ya te tengo registrado.",
            )
        ],
    )
    assert (
        _publicar(
            client,
            [
                _texto(
                    "SMregistro2",
                    numero,
                    "Nombre: Ana Pérez, Dirección: Calle 1 # 2",
                )
            ],
        ).status_code
        == 200
    )
    db.expire_all()
    usuario = db.scalar(select(Usuario).where(Usuario.telefono == numero))
    assert usuario is not None
    assert usuario.nombre == "Ana Pérez"
    assert usuario.rol == "HOGAR"
    assert usuario.es_piloto is True
    assert usuario.password_hash


def test_foto_crea_solicitud(client, db, monkeypatch, proveedores, telefono) -> None:
    url = "https://api.twilio.com/2010-04-01/Accounts/AC/Message/SM/Media/MEfoto"
    monkeypatch.setattr(
        "app.whatsapp.webhook_service.descargar_media",
        lambda media_id, mime_type=None: ArchivoMedia(
            b"imagen", "image/jpeg", media_id
        ),
    )
    monkeypatch.setattr(
        "app.whatsapp.webhook_service.preparar_imagen", lambda archivo: archivo
    )
    monkeypatch.setattr(
        "app.whatsapp.webhook_service.ia.clasificar_imagen",
        lambda archivo, texto_usuario=None, **kwargs: ClasificacionIA(
            intencion=IntencionIA.SOLICITUD_RECOLECCION,
            flujo_sugerido="RECICLABLE",
            subtipo_material="Botellas PET y latas",
            descripcion_material="Bolsa con botellas y latas limpias",
            disponibilidad_texto="lunes",
            respuesta_usuario="Vi botellas y latas.",
        ),
    )
    mensaje = _media("SMfoto", telefono["HOGAR"], url, "image/jpeg")
    assert _publicar(client, [mensaje]).status_code == 200
    db.expire_all()
    solicitud = db.scalar(select(Solicitud))
    assert solicitud is not None
    assert solicitud.flujo == "RECICLABLE"
    assert solicitud.subtipo_material == "Botellas PET y latas"
    registro = db.scalar(
        select(MensajeWhatsapp).where(MensajeWhatsapp.wa_message_id == "SMfoto")
    )
    assert registro is not None
    assert registro.media_id == url


def test_audio_se_transcribe_y_trata_como_texto(
    client, db, monkeypatch, proveedores, telefono
) -> None:
    url = "https://api.twilio.com/2010-04-01/Accounts/AC/Message/SM/Media/MEaudio"
    monkeypatch.setattr(
        "app.whatsapp.webhook_service.descargar_media",
        lambda media_id, mime_type=None: ArchivoMedia(b"audio", "audio/ogg", media_id),
    )
    monkeypatch.setattr(
        "app.whatsapp.webhook_service.transcribir_audio",
        lambda archivo: "Reciclo latas el lunes",
    )
    vistos = _ia_texto(
        monkeypatch,
        [
            ClasificacionIA(
                intencion=IntencionIA.SOLICITUD_RECOLECCION,
                flujo_sugerido="RECICLABLE",
                disponibilidad_texto="lunes",
                respuesta_usuario="Entendido.",
            )
        ],
    )
    mensaje = _media("SMaudio", telefono["HOGAR"], url, "audio/ogg")
    assert _publicar(client, [mensaje]).status_code == 200
    assert vistos == ["Reciclo latas el lunes"]
    db.expire_all()
    registro = db.scalar(
        select(MensajeWhatsapp).where(MensajeWhatsapp.wa_message_id == "SMaudio")
    )
    assert registro is not None
    assert registro.texto_extraido == "Reciclo latas el lunes"
    solicitud = db.scalar(select(Solicitud))
    assert solicitud is not None
    assert solicitud.flujo == "RECICLABLE"


def test_asignar_no_notifica_y_programar_notifica_una_vez(
    client, db, login, proveedores, telefono
) -> None:
    creada = client.post(
        "/api/solicitudes",
        json={"flujo": "ORGANICO", "disponibilidad_usuario": "Mañana"},
        headers=login(telefono["HOGAR"]),
    ).json()
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])
    coordinador = login(telefono["COORD_HUERTEROS"])

    asignada = client.post(
        f"/api/solicitudes/{creada['id']}/asignar",
        json={"recolector_id": str(huertero.id)},
        headers=coordinador,
    )
    assert asignada.status_code == 200
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(MensajeWhatsapp)) == 0

    programada = client.patch(
        f"/api/solicitudes/{creada['id']}/programar",
        json={
            "recolector_id": str(huertero.id),
            "fecha_programada": fecha_futura().isoformat(),
            "hora_programada": "09:30",
        },
        headers=coordinador,
    )
    assert programada.status_code == 200
    db.expire_all()
    avisos = db.scalars(select(AvisoWhatsApp)).all()
    assert {a.destinatario for a in avisos} == {"SOLICITANTE", "RECOLECTOR"}
    orden = next(a for a in avisos if a.destinatario == "RECOLECTOR")
    assert orden.telefono == huertero.telefono
    assert creada["codigo_publico"] in orden.contenido and "09:30" in orden.contenido



def test_cierre_por_whatsapp_es_idempotente(
    client, db, login, monkeypatch, proveedores, telefono
) -> None:
    creada = client.post(
        "/api/solicitudes",
        json={"flujo": "ORGANICO", "disponibilidad_usuario": "Mañana"},
        headers=login(telefono["HOGAR"]),
    ).json()
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])
    coordinador = login(telefono["COORD_HUERTEROS"])
    assert (
        client.patch(
            f"/api/solicitudes/{creada['id']}/programar",
            json={
                "recolector_id": str(huertero.id),
                "fecha_programada": fecha_futura().isoformat(),
                "hora_programada": "10:00",
            },
            headers=coordinador,
        ).status_code
        == 200
    )

    _ia_texto(monkeypatch, [])
    assert (
        _publicar(
            client,
            [_texto("SMcierre1", telefono["HUERTERO"], f"LISTO {creada['codigo_publico']} 8")],
        ).status_code
        == 200
    )
    db.expire_all()
    hogar = usuario_por_rol(db, "HOGAR", telefono["HOGAR"])
    puntos = db.get(Usuario, hogar.id).puntos_acumulados
    assert puntos == Decimal("50.00")

    assert (
        _publicar(
            client,
            [_texto("SMcierre2", telefono["HUERTERO"], f"LISTO {creada['codigo_publico']} 8")],
        ).status_code
        == 200
    )
    db.expire_all()
    assert db.get(Usuario, hogar.id).puntos_acumulados == puntos
    solicitud = db.get(Solicitud, creada["id"])
    assert solicitud is not None
    assert solicitud.estado == "RECOLECTADA"


def test_salida_ia_invalida_y_proveedor_caido_no_crean_solicitud(
    client, db, monkeypatch, proveedores, telefono
) -> None:
    monkeypatch.setattr(
        "app.whatsapp.ia.client._consultar",
        lambda sistema, usuario, **kwargs: "esto no es JSON",
    )
    numero = telefono["HOGAR"]
    assert (
        _publicar(client, [_texto("SMiaInvalida", numero, "hola")]).status_code == 200
    )
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Solicitud)) == 0
    respuesta = db.scalar(
        select(MensajeWhatsapp).where(MensajeWhatsapp.wa_message_id == "SMiaInvalida")
    )
    assert respuesta is not None
    assert respuesta.intencion_ia == "OTRO"

    def fallar(
        texto: str,
        contexto: str | None = None,
        historial: list[dict[str, str]] | None = None,
        perfil: str | None = None,
    ) -> ClasificacionIA:
        raise ProveedorNoDisponible("OpenAI")

    monkeypatch.setattr("app.whatsapp.webhook_service.ia.clasificar_texto", fallar)
    assert _publicar(client, [_texto("SMiaCaida", numero, "hola")]).status_code == 200
    db.expire_all()
    fallido = db.scalar(
        select(MensajeWhatsapp).where(MensajeWhatsapp.wa_message_id == "SMiaCaida")
    )
    assert fallido is not None
    assert fallido.error == "ProveedorNoDisponible"
    assert db.scalar(select(func.count()).select_from(Solicitud)) == 0


def test_despacho_independiente_y_callback(client, db, login, proveedores, telefono, monkeypatch, session_factory):
    from app.whatsapp.despacho import despachar_uno
    from twilio.base.exceptions import TwilioRestException

    hogar = login(telefono["HOGAR"])
    coord = login(telefono["COORD_RECICLADORES"])
    creada = client.post("/api/solicitudes", headers=hogar, json={
        "flujo": "RECICLABLE", "disponibilidad_usuario": "Mañana"}).json()
    ruta = f"/api/solicitudes/{creada['id']}"
    persona = usuario_por_rol(db, "RECICLADOR", telefono["RECICLADOR"])
    datos = {"recolector_id": str(persona.id), "fecha_programada": fecha_futura().isoformat(), "hora_programada": "09:30"}
    for _ in range(2):
        assert client.patch(ruta + "/programar", headers=coord, json=datos).status_code == 200

    def proveedor(aviso, cfg):
        if aviso.destinatario == "SOLICITANTE":
            raise TwilioRestException(400, "/Messages", code=63016)
        return "SMconfirmado"

    monkeypatch.setattr("app.whatsapp.despacho.enviar", proveedor)
    assert despachar_uno(session_factory) and despachar_uno(session_factory)
    assert not despachar_uno(session_factory)
    orden, fallo = db.scalars(select(AvisoWhatsApp).order_by(AvisoWhatsApp.id)).all()
    assert (orden.estado, fallo.estado, fallo.error) == ("ACEPTADO", "FALLIDO", "63016")
    callback = f"/api/webhooks/whatsapp/estado/{orden.intento}"
    for estado in ("delivered", "sent", "delivered"):
        campos = {"AccountSid": CUENTA, "MessageSid": "SMconfirmado", "MessageStatus": estado}
        assert client.post(callback, data=campos).status_code == 403
        firma = _firmar(campos, url="http://testserver" + callback)
        assert client.post(callback, data=campos, headers={"X-Twilio-Signature": firma}).status_code == 204
    assert client.get(ruta + "/avisos", headers=hogar).status_code == 403
    estados = client.get(ruta + "/avisos", headers=coord).json()
    assert {a["estado"] for a in estados} == {"ENTREGADO", "FALLIDO"}
    retry = ruta + f"/avisos/{fallo.id}/reintentar"
    assert client.post(retry, headers=coord).status_code == 202
    assert client.post(retry, headers=coord).status_code == 409
    def timeout(aviso, cfg):
        raise TimeoutError()
    monkeypatch.setattr("app.whatsapp.despacho.enviar", timeout)
    assert despachar_uno(session_factory)
    assert not despachar_uno(session_factory)
    assert client.post(retry, headers=coord).status_code == 409
