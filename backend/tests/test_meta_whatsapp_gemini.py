"""Pruebas del flujo Meta WhatsApp Cloud API (Graph API v25.0) + Gemini + paneles."""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import func, select

from app.models import (
    AvisoWhatsApp,
    ConsentimientoWhatsApp,
    HistorialEstado,
    MensajeWhatsapp,
    Solicitud,
    Usuario,
)
from app.schemas_whatsapp import ExtraccionSolicitudMeta, convertir_peso_a_kg
from app.whatsapp.config import obtener_config
from app.whatsapp.despacho import despachar_uno, ejecutar_ciclo
from app.whatsapp.errores import ErrorTransitorioIA, SalidaIAInvalida
from app.whatsapp.ia import gemini as modulo_gemini
from app.whatsapp.meta import procesar_entrante_meta_uno
from app.whatsapp.notificaciones import (
    ESTADO_SIN_CONSENTIMIENTO,
    actualizar_consentimiento_whatsapp,
)
from tests.conftest import fecha_futura, usuario_por_rol

META_APP_SECRET = "secreto-meta-pruebas-2026"
META_PHONE_ID = "109876543210"
META_TOKEN = "EAAG-token-meta-pruebas"
META_VERIFY = "token-verificacion-explicito-2026"


def _firmar_meta(cuerpo: bytes, secret: str = META_APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), cuerpo, hashlib.sha256).hexdigest()


def _payload_meta(
    *,
    phone_number_id: str = META_PHONE_ID,
    messages: list[dict] | None = None,
    statuses: list[dict] | None = None,
) -> dict:
    value: dict = {
        "messaging_product": "whatsapp",
        "metadata": {
            "display_phone_number": "573000000000",
            "phone_number_id": phone_number_id,
        },
    }
    if messages is not None:
        value["messages"] = messages
    if statuses is not None:
        value["statuses"] = statuses
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA-123",
                "changes": [{"field": "messages", "value": value}],
            }
        ],
    }


def _post_meta(
    client,
    payload: dict,
    *,
    firma: str | None = None,
    secret: str = META_APP_SECRET,
):
    cuerpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    cabecera = firma if firma is not None else _firmar_meta(cuerpo, secret)
    headers = {"Content-Type": "application/json"}
    if cabecera:
        headers["X-Hub-Signature-256"] = cabecera
    return client.post("/api/webhooks/whatsapp", content=cuerpo, headers=headers)


@pytest.fixture()
def entorno_meta(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVEEDOR", "meta")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", META_VERIFY)
    monkeypatch.setenv("WHATSAPP_APP_SECRET", META_APP_SECRET)
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", META_TOKEN)
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", META_PHONE_ID)
    monkeypatch.setenv("WHATSAPP_GRAPH_VERSION", "v25.0")
    monkeypatch.setenv("WHATSAPP_TEMPLATE_LANG", "es")
    monkeypatch.setenv(
        "WHATSAPP_TEMPLATE_PROGRAMADA_RECOLECTOR", "ecoconecta_asignacion_recolector"
    )
    monkeypatch.setenv(
        "WHATSAPP_TEMPLATE_PROGRAMADA_SOLICITANTE", "ecoconecta_cita_solicitante"
    )
    monkeypatch.setenv(
        "WHATSAPP_TEMPLATE_RECOLECTADA_RECOLECTOR", "ecoconecta_cierre_recolector"
    )
    monkeypatch.setenv(
        "WHATSAPP_TEMPLATE_RECOLECTADA_SOLICITANTE", "ecoconecta_cierre_solicitante"
    )
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-pruebas-gemini")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_MAX_INTENTOS", "3")
    monkeypatch.setenv("GEMINI_BACKOFF_BASE_SEGUNDOS", "0")
    monkeypatch.delenv("WHATSAPP_EXIGIR_CONSENTIMIENTO_EXPLICITO", raising=False)


def test_get_meta_exige_token_explicito_sin_valor_por_defecto(client, monkeypatch):
    monkeypatch.delenv("WHATSAPP_VERIFY_TOKEN", raising=False)
    monkeypatch.delenv("VERIFY_TOKEN", raising=False)

    sin_config = client.get(
        "/api/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "EcoConect",
            "hub.challenge": "98765",
        },
    )
    assert sin_config.status_code == 403

    vacio = client.get(
        "/api/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "",
            "hub.challenge": "98765",
        },
    )
    assert vacio.status_code == 403

    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", META_VERIFY)
    ok = client.get(
        "/api/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": META_VERIFY,
            "hub.challenge": "reto-ok-2026",
        },
    )
    assert ok.status_code == 200
    assert ok.text == "reto-ok-2026"


def test_meta_firma_invalida_y_numero_invalido_rechazados(
    client, db, entorno_meta, telefono
):
    payload = _payload_meta(
        messages=[
            {
                "id": "wamid.firma01",
                "from": telefono["HOGAR"].lstrip("+"),
                "type": "text",
                "text": {"body": "Tengo 2 kg de cartón"},
            }
        ]
    )

    sin_firma = _post_meta(client, payload, firma="")
    assert sin_firma.status_code == 403
    assert sin_firma.json()["detail"]["codigo"] == "WEBHOOK_FIRMA_INVALIDA"

    firma_mala = _post_meta(client, payload, firma="sha256=deadbeef")
    assert firma_mala.status_code == 403
    assert firma_mala.json()["detail"]["codigo"] == "WEBHOOK_FIRMA_INVALIDA"

    numero_ajeno = _post_meta(
        client,
        _payload_meta(
            phone_number_id="999999999999",
            messages=[
                {
                    "id": "wamid.num01",
                    "from": telefono["HOGAR"].lstrip("+"),
                    "type": "text",
                    "text": {"body": "Tengo cartón"},
                }
            ],
        ),
    )
    assert numero_ajeno.status_code == 403
    assert numero_ajeno.json()["detail"]["codigo"] == "WEBHOOK_NUMERO_INVALIDO"
    assert db.scalar(select(func.count()).select_from(MensajeWhatsapp)) == 0


def test_meta_lote_mixto_guarda_textos_deduplica_y_procesa_estados(
    client, db, login, entorno_meta, telefono
):
    # Preparar una solicitud programada y un aviso aceptado para probar el status en el mismo lote
    creada = client.post(
        "/api/solicitudes",
        headers=login(telefono["HOGAR"]),
        json={"flujo": "ORGANICO", "disponibilidad_usuario": "Mañana"},
    ).json()
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])
    assert (
        client.patch(
            f"/api/solicitudes/{creada['id']}/programar",
            headers=login(telefono["COORD_HUERTEROS"]),
            json={
                "recolector_id": str(huertero.id),
                "fecha_programada": fecha_futura().isoformat(),
                "hora_programada": "09:30",
            },
        ).status_code
        == 200
    )
    aviso = db.scalar(
        select(AvisoWhatsApp).where(
            AvisoWhatsApp.solicitud_id == creada["id"],
            AvisoWhatsApp.destinatario == "RECOLECTOR",
        )
    )
    assert aviso is not None
    aviso.estado = "ACEPTADO"
    aviso.sid = "wamid.aviso.rec.1"
    db.commit()

    lote = _payload_meta(
        messages=[
            {
                "id": "wamid.mix.1",
                "from": telefono["HOGAR"].lstrip("+"),
                "type": "text",
                "text": {"body": "Tengo 3 kg de cartón limpio"},
            },
            {
                "id": "wamid.mix.1",  # duplicado dentro del mismo lote
                "from": telefono["HOGAR"].lstrip("+"),
                "type": "text",
                "text": {"body": "Tengo 3 kg de cartón limpio"},
            },
            {
                "id": "wamid.mix.img",  # no-texto: debe ignorarse sin fallar el lote
                "from": telefono["HOGAR"].lstrip("+"),
                "type": "image",
                "image": {"id": "media-1"},
            },
        ],
        statuses=[
            {
                "id": "wamid.aviso.rec.1",
                "status": "delivered",
                "recipient_id": telefono["HUERTERO"].lstrip("+"),
            }
        ],
    )

    resp = _post_meta(client, lote)
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["mensajes_guardados"] == 1
    assert cuerpo["mensajes_duplicados"] == 1
    assert cuerpo["estados_procesados"] == 1

    db.expire_all()
    mensajes = db.scalars(select(MensajeWhatsapp)).all()
    assert len(mensajes) == 1
    assert mensajes[0].wa_message_id == "wamid.mix.1"
    assert mensajes[0].proveedor == "META"
    assert mensajes[0].estado_envio == "PENDIENTE"
    assert mensajes[0].solicitud_id is None  # No bloquea el POST esperando Gemini

    aviso_db = db.get(AvisoWhatsApp, aviso.id)
    assert aviso_db is not None
    assert aviso_db.estado == "ENTREGADO"


def test_gemini_config_por_defecto_y_conversion_unidades():
    cfg = obtener_config()
    assert cfg.gemini_model == "gemini-3.5-flash-lite"

    assert convertir_peso_a_kg(1500, "G") == Decimal("1.50")
    assert convertir_peso_a_kg(250, "G") == Decimal("0.25")
    assert convertir_peso_a_kg(4.25, "KG") == Decimal("4.25")
    assert convertir_peso_a_kg(3, "BOLSAS") is None
    assert convertir_peso_a_kg(None, "KG") is None
    assert convertir_peso_a_kg(5, None) is None


def test_worker_meta_anonimiza_convierte_gramos_y_crea_solicitud_atomica(
    client, db, session_factory, monkeypatch, entorno_meta, telefono
):
    vistos: list[str] = []

    def falso_gemini(texto_anonimo: str) -> ExtraccionSolicitudMeta:
        vistos.append(texto_anonimo)
        return ExtraccionSolicitudMeta(
            flujo="ORGANICO",
            material="Cáscaras de frutas y café",
            cantidad=1500,
            unidad="G",
            referencia_general="Mañana en la mañana",
            notas="En balde tapado",
            es_solicitud=True,
        )

    monkeypatch.setattr("app.whatsapp.meta.extraer_solicitud_gemini", falso_gemini)

    hogar = usuario_por_rol(db, "HOGAR", telefono["HOGAR"])
    texto_con_pii = (
        f"Hola soy {hogar.nombre}, mi número es {hogar.telefono} y vivo en {hogar.direccion}. "
        "Tengo 1500 gramos de cáscaras de frutas y café para mañana en la mañana, en balde tapado."
    )
    resp = _post_meta(
        client,
        _payload_meta(
            messages=[
                {
                    "id": "wamid.org.1",
                    "from": telefono["HOGAR"].lstrip("+"),
                    "type": "text",
                    "text": {"body": texto_con_pii},
                }
            ]
        ),
    )
    assert resp.status_code == 200

    assert procesar_entrante_meta_uno(session_factory) is True
    assert procesar_entrante_meta_uno(session_factory) is False

    # Verificar anonimización antes de Gemini
    assert len(vistos) == 1
    assert hogar.nombre not in vistos[0]
    assert hogar.telefono not in vistos[0]
    assert (hogar.direccion or "") not in vistos[0]

    db.expire_all()
    solicitudes = db.scalars(select(Solicitud)).all()
    assert len(solicitudes) == 1
    sol = solicitudes[0]
    assert sol.estado == "RECIBIDA"
    assert sol.flujo == "ORGANICO"
    assert sol.subtipo_material == "Cáscaras de frutas y café"
    assert sol.cantidad_estimada_kg == Decimal("1.50")
    assert sol.disponibilidad_usuario == "Mañana en la mañana"
    assert sol.observaciones == "En balde tapado"

    msg = db.scalar(
        select(MensajeWhatsapp).where(MensajeWhatsapp.wa_message_id == "wamid.org.1")
    )
    assert msg is not None
    assert msg.solicitud_id == sol.id
    assert msg.estado_envio == "PROCESADO"
    assert msg.procesado_por_ia is True

    # Un mensaje entrante común NO debe crear consentimiento implícito
    assert db.get(ConsentimientoWhatsApp, hogar.id) is None


def test_worker_meta_peso_pendiente_ambiguo_desconocido_y_reintentos_gemini(
    client, db, session_factory, monkeypatch, entorno_meta, telefono
):
    # 1. Remitente desconocido no llama a Gemini ni crea usuario/solicitud
    llamadas = {"n": 0}

    def contar_gemini(_texto: str) -> ExtraccionSolicitudMeta:
        llamadas["n"] += 1
        return ExtraccionSolicitudMeta(flujo="RECICLABLE", es_solicitud=True)

    monkeypatch.setattr("app.whatsapp.meta.extraer_solicitud_gemini", contar_gemini)
    assert (
        _post_meta(
            client,
            _payload_meta(
                messages=[
                    {
                        "id": "wamid.desc.1",
                        "from": "573999888777",
                        "type": "text",
                        "text": {"body": "Tengo 5 kg de cartón"},
                    }
                ]
            ),
        ).status_code
        == 200
    )
    assert procesar_entrante_meta_uno(session_factory) is True
    assert llamadas["n"] == 0
    db.expire_all()
    msg_desc = db.scalar(
        select(MensajeWhatsapp).where(MensajeWhatsapp.wa_message_id == "wamid.desc.1")
    )
    assert msg_desc is not None
    assert msg_desc.estado_conversacion == "REMITENTE_DESCONOCIDO"
    assert db.scalar(select(func.count()).select_from(Solicitud)) == 0

    # 2. Unidad no de peso (bolsas) deja cantidad_estimada_kg en None
    monkeypatch.setattr(
        "app.whatsapp.meta.extraer_solicitud_gemini",
        lambda _t: ExtraccionSolicitudMeta(
            flujo="RECICLABLE",
            material="Botellas PET",
            cantidad=3,
            unidad="BOLSAS",
            referencia_general="Portería en la tarde",
            notas="Limpias y aplastadas",
            es_solicitud=True,
        ),
    )
    assert (
        _post_meta(
            client,
            _payload_meta(
                messages=[
                    {
                        "id": "wamid.bolsas.1",
                        "from": telefono["HOGAR"].lstrip("+"),
                        "type": "text",
                        "text": {"body": "Tengo 3 bolsas de botellas PET"},
                    }
                ]
            ),
        ).status_code
        == 200
    )
    assert procesar_entrante_meta_uno(session_factory) is True
    db.expire_all()
    sol_bolsas = db.scalar(select(Solicitud))
    assert sol_bolsas is not None
    assert sol_bolsas.flujo == "RECICLABLE"
    assert sol_bolsas.cantidad_estimada_kg is None
    assert "3 bolsas" in (sol_bolsas.observaciones or "").lower()

    # 3. Mensaje ambiguo queda pendiente de aclaración sin crear solicitud
    monkeypatch.setattr(
        "app.whatsapp.meta.extraer_solicitud_gemini",
        lambda _t: ExtraccionSolicitudMeta(
            flujo="AMBIGUO",
            material="Residuos variados",
            es_solicitud=True,
        ),
    )
    assert (
        _post_meta(
            client,
            _payload_meta(
                messages=[
                    {
                        "id": "wamid.amb.1",
                        "from": telefono["HOGAR"].lstrip("+"),
                        "type": "text",
                        "text": {"body": "Pasen por unas cosas que separé"},
                    }
                ]
            ),
        ).status_code
        == 200
    )
    assert procesar_entrante_meta_uno(session_factory) is True
    db.expire_all()
    msg_amb = db.scalar(
        select(MensajeWhatsapp).where(MensajeWhatsapp.wa_message_id == "wamid.amb.1")
    )
    assert msg_amb is not None
    assert msg_amb.estado_conversacion == "ACLARACION_PENDIENTE"
    assert msg_amb.solicitud_id is None
    assert db.scalar(select(func.count()).select_from(Solicitud)) == 1

    # 4. Fallo transitorio de Gemini reintenta y luego crea en el segundo intento
    intentos = {"n": 0}

    def gemini_con_reintento(_t: str) -> ExtraccionSolicitudMeta:
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise ErrorTransitorioIA("Gemini", "503")
        return ExtraccionSolicitudMeta(
            flujo="ORGANICO",
            material="Restos de verduras",
            cantidad=4,
            unidad="KG",
            referencia_general="Hoy tarde",
            es_solicitud=True,
        )

    monkeypatch.setattr(
        "app.whatsapp.meta.extraer_solicitud_gemini", gemini_con_reintento
    )
    assert (
        _post_meta(
            client,
            _payload_meta(
                messages=[
                    {
                        "id": "wamid.retry.1",
                        "from": telefono["UNIDAD_PRODUCTIVA"].lstrip("+"),
                        "type": "text",
                        "text": {"body": "4 kg de verduras"},
                    }
                ]
            ),
        ).status_code
        == 200
    )
    assert procesar_entrante_meta_uno(session_factory) is True
    db.expire_all()
    msg_retry = db.scalar(
        select(MensajeWhatsapp).where(MensajeWhatsapp.wa_message_id == "wamid.retry.1")
    )
    assert msg_retry is not None
    assert msg_retry.estado_envio == "PENDIENTE"
    assert msg_retry.intentos == 1
    assert msg_retry.solicitud_id is None

    # Segundo intento exitoso
    assert procesar_entrante_meta_uno(session_factory) is True
    db.expire_all()
    msg_retry = db.scalar(
        select(MensajeWhatsapp).where(MensajeWhatsapp.wa_message_id == "wamid.retry.1")
    )
    assert msg_retry is not None
    assert msg_retry.estado_envio == "PROCESADO"
    assert msg_retry.solicitud_id is not None

    # 5. Agotar reintentos en salida inválida marca FALLIDO sin crear solicitud
    monkeypatch.setattr(
        "app.whatsapp.meta.extraer_solicitud_gemini",
        lambda _t: (_ for _ in ()).throw(SalidaIAInvalida()),
    )
    assert (
        _post_meta(
            client,
            _payload_meta(
                messages=[
                    {
                        "id": "wamid.fail.1",
                        "from": telefono["HOGAR"].lstrip("+"),
                        "type": "text",
                        "text": {"body": "Cartón"},
                    }
                ]
            ),
        ).status_code
        == 200
    )
    for _ in range(3):
        assert procesar_entrante_meta_uno(session_factory) is True
    db.expire_all()
    msg_fail = db.scalar(
        select(MensajeWhatsapp).where(MensajeWhatsapp.wa_message_id == "wamid.fail.1")
    )
    assert msg_fail is not None
    assert msg_fail.estado_envio == "FALLIDO"
    assert msg_fail.intentos == 3
    assert msg_fail.solicitud_id is None


def test_adaptador_google_genai_parsea_y_clasifica_errores(monkeypatch, entorno_meta):
    llamada_args: dict = {}

    class _FakeModels:
        def generate_content(self, *, model, contents, config):
            llamada_args["model"] = model
            llamada_args["contents"] = contents
            llamada_args["schema"] = config.response_schema
            return SimpleNamespace(
                parsed=ExtraccionSolicitudMeta(
                    flujo="RECICLABLE",
                    material="Cartón",
                    cantidad=5,
                    unidad="KG",
                    es_solicitud=True,
                )
            )

    monkeypatch.setattr(
        modulo_gemini,
        "_crear_cliente",
        lambda api_key: SimpleNamespace(models=_FakeModels()),
    )

    resultado = modulo_gemini.extraer_solicitud_gemini("5 kg de cartón")
    assert resultado.flujo == "RECICLABLE"
    assert llamada_args["model"] == "gemini-3.5-flash-lite"
    assert llamada_args["schema"] is ExtraccionSolicitudMeta

    class _TimeoutModels:
        def generate_content(self, **kwargs):
            raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(
        modulo_gemini,
        "_crear_cliente",
        lambda api_key: SimpleNamespace(models=_TimeoutModels()),
    )
    with pytest.raises(ErrorTransitorioIA):
        modulo_gemini.extraer_solicitud_gemini("5 kg de cartón")


def test_revisar_programar_graph_v25_conciliar_y_cierre_manual_ambos_paneles(
    client, db, login, session_factory, monkeypatch, entorno_meta, telefono
):
    # 1. Ingresar una solicitud orgánica (Unidad Productiva) y una reciclable (Hogar) vía Meta
    respuestas = iter(
        [
            ExtraccionSolicitudMeta(
                flujo="ORGANICO",
                material="Restos vegetales",
                cantidad=None,
                unidad=None,
                referencia_general="Mañanas",
                notas="Bolsas verdes",
                es_solicitud=True,
            ),
            ExtraccionSolicitudMeta(
                flujo="RECICLABLE",
                material="Cartón",
                cantidad=2000,
                unidad="G",
                referencia_general="Tardes",
                es_solicitud=True,
            ),
        ]
    )
    monkeypatch.setattr(
        "app.whatsapp.meta.extraer_solicitud_gemini", lambda _t: next(respuestas)
    )
    assert (
        _post_meta(
            client,
            _payload_meta(
                messages=[
                    {
                        "id": "wamid.flow.org",
                        "from": telefono["UNIDAD_PRODUCTIVA"].lstrip("+"),
                        "type": "text",
                        "text": {"body": "Tenemos restos vegetales en la mañana"},
                    },
                    {
                        "id": "wamid.flow.rec",
                        "from": telefono["HOGAR"].lstrip("+"),
                        "type": "text",
                        "text": {"body": "2000 g de cartón en la tarde"},
                    },
                ]
            ),
        ).status_code
        == 200
    )
    assert procesar_entrante_meta_uno(session_factory) is True
    assert procesar_entrante_meta_uno(session_factory) is True

    # 2. Verificar aislamiento entre ambos paneles
    coord_h = login(telefono["COORD_HUERTEROS"])
    coord_r = login(telefono["COORD_RECICLADORES"])

    lista_h = client.get("/api/solicitudes", headers=coord_h).json()["items"]
    lista_r = client.get("/api/solicitudes", headers=coord_r).json()["items"]
    assert len(lista_h) == 1 and lista_h[0]["flujo"] == "ORGANICO"
    assert lista_h[0]["origen_canal"] == "WHATSAPP"
    assert lista_h[0]["cantidad_estimada_kg"] is None
    assert len(lista_r) == 1 and lista_r[0]["flujo"] == "RECICLABLE"
    assert lista_r[0]["origen_canal"] == "WHATSAPP"
    assert lista_r[0]["cantidad_estimada_kg"] == 2.0

    # Permisos entre flujos bloqueados
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])
    reciclador = usuario_por_rol(db, "RECICLADOR", telefono["RECICLADOR"])
    sol_org_id = lista_h[0]["id"]
    sol_rec_id = lista_r[0]["id"]

    assert (
        client.patch(
            f"/api/solicitudes/{sol_org_id}/programar",
            headers=coord_r,
            json={
                "recolector_id": str(reciclador.id),
                "fecha_programada": fecha_futura().isoformat(),
                "hora_programada": "09:30",
            },
        ).status_code
        == 403
    )

    # 3. Otorgar consentimiento explícito a solicitante y recolector orgánicos para envío por Meta
    admin = login(telefono["ADMIN"])
    unidad = usuario_por_rol(db, "UNIDAD_PRODUCTIVA", telefono["UNIDAD_PRODUCTIVA"])
    for destinatario in (unidad, huertero):
        resp_cons = client.patch(
            f"/api/admin/usuarios/{destinatario.id}/consentimiento-whatsapp",
            headers=admin,
            json={"aceptado": True, "origen": "PILOTO_EXPLICITO"},
        )
        assert resp_cons.status_code == 200, resp_cons.text
        assert resp_cons.json()["aceptado"] is True

    # Programar orgánica editando material, peso estimado, referencia y notas
    payload_prog_org = {
        "recolector_id": str(huertero.id),
        "fecha_programada": fecha_futura().isoformat(),
        "hora_programada": "09:30",
        "subtipo_material": "Cáscaras vegetales seleccionadas",
        "cantidad_estimada_kg": 6.5,
        "disponibilidad_usuario": "Portería local 3 · 9:00 a.m.",
        "observaciones": "Llevar dos baldes adicionales",
    }
    prog_org = client.patch(
        f"/api/solicitudes/{sol_org_id}/programar",
        headers=coord_h,
        json=payload_prog_org,
    )
    assert prog_org.status_code == 200, prog_org.text
    datos_org = prog_org.json()
    assert datos_org["estado"] == "PROGRAMADA"
    assert datos_org["subtipo_material"] == "Cáscaras vegetales seleccionadas"
    assert datos_org["cantidad_estimada_kg"] == 6.5
    assert datos_org["disponibilidad_usuario"] == "Portería local 3 · 9:00 a.m."
    assert datos_org["observaciones"] == "Llevar dos baldes adicionales"

    # Repetir programación idéntica NO duplica historial ni avisos
    assert (
        client.patch(
            f"/api/solicitudes/{sol_org_id}/programar",
            headers=coord_h,
            json=payload_prog_org,
        ).status_code
        == 200
    )
    db.expire_all()
    avisos_org = db.scalars(
        select(AvisoWhatsApp)
        .where(AvisoWhatsApp.solicitud_id == sol_org_id)
        .order_by(AvisoWhatsApp.id)
    ).all()
    assert len(avisos_org) == 2
    assert {a.destinatario for a in avisos_org} == {"RECOLECTOR", "SOLICITANTE"}
    assert all(a.proveedor == "META" for a in avisos_org)

    # 4. Enviar por Graph API v25.0: recolector aceptado, solicitante con 400 (FALLIDO reintentable)
    peticiones_graph: list[tuple[str, dict]] = []

    class _RespHttp:
        def __init__(self, status_code: int, body: dict):
            self.status_code = status_code
            self._body = body

        def json(self) -> dict:
            return self._body

    class _FakeHttpxClient:
        def __init__(self, timeout: float = 12.0):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url: str, headers: dict, json: dict):
            peticiones_graph.append((url, json))
            if json["template"]["name"] == "ecoconecta_asignacion_recolector":
                return _RespHttp(
                    200,
                    {
                        "messaging_product": "whatsapp",
                        "messages": [
                            {"id": "wamid.out.rec.1", "message_status": "accepted"}
                        ],
                    },
                )
            if len(peticiones_graph) == 2:
                return _RespHttp(
                    400,
                    {"error": {"code": 131026, "message": "Recipient unavailable"}},
                )
            # En el reintento simulamos timeout -> queda en CONCILIAR
            raise httpx.ReadTimeout("timeout de red")

    monkeypatch.setattr("app.whatsapp.meta.httpx.Client", _FakeHttpxClient)

    assert despachar_uno(session_factory) is True
    assert despachar_uno(session_factory) is True
    assert despachar_uno(session_factory) is False

    assert peticiones_graph[0][0] == f"https://graph.facebook.com/v25.0/{META_PHONE_ID}/messages"
    assert peticiones_graph[0][1]["type"] == "template"
    assert peticiones_graph[0][1]["biz_opaque_callback_data"] == avisos_org[0].intento

    db.expire_all()
    aviso_rec = db.get(AvisoWhatsApp, avisos_org[0].id)
    aviso_sol = db.get(AvisoWhatsApp, avisos_org[1].id)
    assert aviso_rec is not None and aviso_sol is not None
    assert (aviso_rec.estado, aviso_rec.sid) == ("ACEPTADO", "wamid.out.rec.1")
    assert (aviso_sol.estado, aviso_sol.error) == ("FALLIDO", "META_131026")

    # Webhook de Meta reporta sent -> delivered -> sent (fuera de orden ignorado)
    for estado_meta in ("sent", "delivered", "sent"):
        assert (
            _post_meta(
                client,
                _payload_meta(
                    statuses=[{"id": "wamid.out.rec.1", "status": estado_meta}]
                ),
            ).status_code
            == 200
        )
    db.expire_all()
    assert db.get(AvisoWhatsApp, aviso_rec.id).estado == "ENTREGADO"

    # Reintentar fallo confirmado del solicitante -> timeout -> CONCILIAR -> reintento bloqueado (409)
    retry_url = f"/api/solicitudes/{sol_org_id}/avisos/{aviso_sol.id}/reintentar"
    assert client.post(retry_url, headers=coord_h).status_code == 202
    assert despachar_uno(session_factory) is True
    db.expire_all()
    aviso_sol = db.get(AvisoWhatsApp, aviso_sol.id)
    assert aviso_sol.estado == "CONCILIAR"
    assert client.post(retry_url, headers=coord_h).status_code == 409

    # Conciliación vía biz_opaque_callback_data del webhook de Meta cuando llega delivered
    assert (
        _post_meta(
            client,
            _payload_meta(
                statuses=[
                    {
                        "id": "wamid.out.sol.conciliado",
                        "status": "delivered",
                        "biz_opaque_callback_data": aviso_sol.intento,
                    }
                ]
            ),
        ).status_code
        == 200
    )
    db.expire_all()
    aviso_sol = db.get(AvisoWhatsApp, aviso_sol.id)
    assert aviso_sol.estado == "ENTREGADO"
    assert aviso_sol.sid == "wamid.out.sol.conciliado"

    # 5. Probar panel de Recicladores: recolector con consentimiento explícito y hogar revocado
    hogar = usuario_por_rol(db, "HOGAR", telefono["HOGAR"])
    actualizar_consentimiento_whatsapp(db, reciclador.id, aceptado=True, origen="PILOTO")
    actualizar_consentimiento_whatsapp(db, hogar.id, aceptado=False, origen="REVOCACION")

    prog_rec = client.patch(
        f"/api/solicitudes/{sol_rec_id}/programar",
        headers=coord_r,
        json={
            "recolector_id": str(reciclador.id),
            "fecha_programada": fecha_futura().isoformat(),
            "hora_programada": "11:00",
            "subtipo_material": "Cartón prensado",
            "cantidad_estimada_kg": 3.0,
        },
    )
    assert prog_rec.status_code == 200
    db.expire_all()
    avisos_rec = db.scalars(
        select(AvisoWhatsApp)
        .where(AvisoWhatsApp.solicitud_id == sol_rec_id)
        .order_by(AvisoWhatsApp.destinatario)
    ).all()
    # Sin consentimiento del hogar, solo el recolector queda PENDIENTE y el solicitante queda bloqueado
    por_dest = {a.destinatario: a.estado for a in avisos_rec}
    assert por_dest == {
        "RECOLECTOR": "PENDIENTE",
        "SOLICITANTE": ESTADO_SIN_CONSENTIMIENTO,
    }

    # 6. Cierre manual con acreditación única en ambos paneles
    cierre_org = client.post(
        f"/api/solicitudes/{sol_org_id}/cerrar",
        headers=coord_h,
        json={"cantidad_real_kg": 10.0, "nota_operativa": "Cierre manual de prueba"},
    )
    assert cierre_org.status_code == 200, cierre_org.text
    assert cierre_org.json()["puntos_otorgados"] == 75.0

    # Repetir cierre manual devuelve 409 y no duplica puntos
    doble_cierre = client.post(
        f"/api/solicitudes/{sol_org_id}/cerrar",
        headers=coord_h,
        json={"cantidad_real_kg": 10.0, "nota_operativa": "Segundo intento"},
    )
    assert doble_cierre.status_code == 409
    assert doble_cierre.json()["detail"]["codigo"] == "SOLICITUD_YA_CERRADA"

    unidad = usuario_por_rol(db, "UNIDAD_PRODUCTIVA", telefono["UNIDAD_PRODUCTIVA"])
    db.expire_all()
    assert db.get(Usuario, unidad.id).puntos_acumulados == Decimal("75.00")
    assert (
        db.scalar(
            select(func.count(HistorialEstado.id)).where(
                HistorialEstado.solicitud_id == sol_org_id,
                HistorialEstado.estado_nuevo == "RECOLECTADA",
            )
        )
        == 1
    )

    cierre_rec = client.post(
        f"/api/solicitudes/{sol_rec_id}/cerrar",
        headers=coord_r,
        json={"cantidad_real_kg": 5.0, "nota_operativa": "Cierre reciclaje"},
    )
    assert cierre_rec.status_code == 200
    assert cierre_rec.json()["puntos_otorgados"] == 50.0  # 10 base + 8 * 5 kg

    # ejecutar_ciclo drena sin error
    assert isinstance(ejecutar_ciclo(session_factory), bool)


def test_consentimiento_revocado_no_se_reactiva_y_se_verifica_al_encolar_enviar_y_reintentar(
    client, db, login, session_factory, monkeypatch, entorno_meta, telefono
):
    admin = login(telefono["ADMIN"])
    coord_h = login(telefono["COORD_HUERTEROS"])
    hogar = usuario_por_rol(db, "HOGAR", telefono["HOGAR"])
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])

    # 1. Otorgar y luego revocar consentimiento explícito del hogar
    assert (
        client.patch(
            f"/api/admin/usuarios/{hogar.id}/consentimiento-whatsapp",
            headers=admin,
            json={"aceptado": True, "origen": "REGISTRO_PILOTO"},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/admin/usuarios/{hogar.id}/consentimiento-whatsapp",
            headers=admin,
            json={"aceptado": False, "origen": "REVOCACION_USUARIO"},
        ).status_code
        == 200
    )

    # 2. Enviar otro mensaje entrante por Meta NO debe reactivar el consentimiento revocado
    monkeypatch.setattr(
        "app.whatsapp.meta.extraer_solicitud_gemini",
        lambda _t: ExtraccionSolicitudMeta(
            flujo="ORGANICO",
            material="Cáscaras de fruta",
            cantidad=2,
            unidad="KG",
            referencia_general="Mañana 9am",
            es_solicitud=True,
        ),
    )
    assert (
        _post_meta(
            client,
            _payload_meta(
                messages=[
                    {
                        "id": "wamid.revocado.1",
                        "from": telefono["HOGAR"].lstrip("+"),
                        "type": "text",
                        "text": {"body": "Tengo 2 kg de cáscaras de fruta"},
                    }
                ]
            ),
        ).status_code
        == 200
    )
    assert procesar_entrante_meta_uno(session_factory) is True
    db.expire_all()
    cons_hogar = db.get(ConsentimientoWhatsApp, hogar.id)
    assert cons_hogar is not None and cons_hogar.aceptado is False

    solicitud = db.scalar(select(Solicitud).where(Solicitud.solicitante_id == hogar.id))
    assert solicitud is not None and solicitud.estado == "RECIBIDA"

    # 3. Programar cuando NI solicitante NI recolector tienen consentimiento vigente:
    #    la programación DEBE guardarse, pero ningún aviso queda PENDIENTE ni se envía.
    envios_graph: list[dict] = []

    class _Resp:
        def __init__(self, status_code: int, body: dict):
            self.status_code = status_code
            self._body = body

        def json(self) -> dict:
            return self._body

    class _FakeClient:
        def __init__(self, timeout: float = 12.0):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url: str, headers: dict, json: dict):
            envios_graph.append(json)
            if json["to"] == hogar.telefono.lstrip("+"):
                return _Resp(400, {"error": {"code": 131026}})
            return _Resp(200, {"messages": [{"id": f"wamid.ok.{len(envios_graph)}"}]})

    monkeypatch.setattr("app.whatsapp.meta.httpx.Client", _FakeClient)

    prog1 = client.patch(
        f"/api/solicitudes/{solicitud.id}/programar",
        headers=coord_h,
        json={
            "recolector_id": str(huertero.id),
            "fecha_programada": fecha_futura().isoformat(),
            "hora_programada": "09:00",
        },
    )
    assert prog1.status_code == 200, prog1.text
    assert prog1.json()["estado"] == "PROGRAMADA"
    assert despachar_uno(session_factory) is False
    assert envios_graph == []

    db.expire_all()
    avisos_sin_cons = db.scalars(
        select(AvisoWhatsApp).where(AvisoWhatsApp.solicitud_id == solicitud.id)
    ).all()
    assert len(avisos_sin_cons) == 2
    assert all(a.estado == ESTADO_SIN_CONSENTIMIENTO for a in avisos_sin_cons)

    # 4. Otorgar consentimiento a ambos, reprogramar -> ambos quedan PENDIENTE;
    #    luego revocar al recolector MIENTRAS está en cola -> no se envía al recolector.
    actualizar_consentimiento_whatsapp(db, hogar.id, aceptado=True, origen="PILOTO")
    actualizar_consentimiento_whatsapp(db, huertero.id, aceptado=True, origen="PILOTO")

    prog2 = client.patch(
        f"/api/solicitudes/{solicitud.id}/programar",
        headers=coord_h,
        json={
            "recolector_id": str(huertero.id),
            "fecha_programada": fecha_futura().isoformat(),
            "hora_programada": "10:00",
        },
    )
    assert prog2.status_code == 200

    # Revocar consentimiento del recolector justo antes de despachar
    actualizar_consentimiento_whatsapp(
        db, huertero.id, aceptado=False, origen="REVOCACION_EN_COLA"
    )
    assert despachar_uno(session_factory) is True
    assert despachar_uno(session_factory) is True
    assert despachar_uno(session_factory) is False

    # Solo se intentó enviar al hogar (que recibió 400 -> FALLIDO), NUNCA al recolector revocado
    assert len(envios_graph) == 1
    assert envios_graph[0]["to"] == hogar.telefono.lstrip("+")

    db.expire_all()
    avisos_vigentes = db.scalars(
        select(AvisoWhatsApp)
        .where(AvisoWhatsApp.solicitud_id == solicitud.id)
        .order_by(AvisoWhatsApp.id.desc())
        .limit(2)
    ).all()
    mapa = {a.destinatario: a for a in avisos_vigentes}
    assert mapa["RECOLECTOR"].estado == ESTADO_SIN_CONSENTIMIENTO
    assert mapa["SOLICITANTE"].estado == "FALLIDO"

    # 5. Revocar consentimiento del solicitante ANTES de pulsar reintentar -> 409 SIN_CONSENTIMIENTO
    actualizar_consentimiento_whatsapp(
        db, hogar.id, aceptado=False, origen="REVOCACION_PRE_REINTENTO"
    )
    retry = client.post(
        f"/api/solicitudes/{solicitud.id}/avisos/{mapa['SOLICITANTE'].id}/reintentar",
        headers=coord_h,
    )
    assert retry.status_code == 409
    assert retry.json()["detail"]["codigo"] == "SIN_CONSENTIMIENTO"

    db.expire_all()
    assert db.get(AvisoWhatsApp, mapa["SOLICITANTE"].id).estado == ESTADO_SIN_CONSENTIMIENTO
    assert despachar_uno(session_factory) is False
    assert len(envios_graph) == 1
