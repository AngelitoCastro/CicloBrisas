"""Integración Meta WhatsApp Cloud API (Graph API v25.0): webhook, extracción Gemini y envío."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AvisoWhatsApp, MensajeWhatsapp, Usuario
from app.schemas import CerrarSolicitud, SolicitudCrear
from app.schemas_whatsapp import ExtraccionSolicitudMeta, convertir_peso_a_kg
from app.services.errors import ErrorDominio, Validacion
from app.services.solicitudes import (
    TIPO_GENERADOR_POR_ROL,
    cerrar_solicitud_por_codigo,
    crear_solicitud,
)
from app.tiempo import hoy_bogota
from app.whatsapp.anonimizacion import anonimizar
from app.whatsapp.config import (
    ConfiguracionWhatsApp,
    obtener_config,
    plantilla_meta_para,
)
from app.whatsapp.errores import (
    ErrorMetaDefinitivo,
    ErrorMetaIncierto,
    ErrorTransitorioIA,
    ErrorWhatsApp,
    FirmaInvalida,
    NumeroMetaInvalido,
    SalidaIAInvalida,
)
from app.whatsapp.ia.gemini import extraer_solicitud_gemini
from app.whatsapp.payload import normalizar_telefono

ESTADOS_META: dict[str, str] = {
    "accepted": "ACEPTADO",
    "sent": "ENVIADO",
    "delivered": "ENTREGADO",
    "read": "LEIDO",
    "failed": "FALLIDO",
}


@dataclass(frozen=True)
class MensajeMetaEntrante:
    wamid: str
    telefono: str
    texto: str


@dataclass(frozen=True)
class EstadoMetaEntrante:
    wamid: str
    status: str
    recipient_id: str | None = None
    biz_opaque_callback_data: str | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class ResultadoLoteMeta:
    guardados: int
    duplicados: int
    estados_procesados: int


def verificar_firma_meta(
    cuerpo_bruto: bytes,
    cabecera: str | None,
    app_secret: str,
) -> None:
    """Valida X-Hub-Signature-256 sobre los bytes originales con WHATSAPP_APP_SECRET."""
    if not app_secret or not cabecera:
        raise FirmaInvalida()
    firma = cabecera.strip()
    if not firma.startswith("sha256="):
        raise FirmaInvalida()
    esperada = (
        "sha256="
        + hmac.new(
            app_secret.encode("utf-8"),
            cuerpo_bruto,
            hashlib.sha256,
        ).hexdigest()
    )
    if not hmac.compare_digest(firma, esperada):
        raise FirmaInvalida()


def extraer_eventos_meta(
    payload: object,
    phone_number_id_esperado: str,
) -> tuple[list[MensajeMetaEntrante], list[EstadoMetaEntrante]]:
    """Valida el payload JSON de Meta, verifica phone_number_id y separa textos de estados."""
    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        raise Validacion(
            "WEBHOOK_PAYLOAD_INVALIDO",
            "El payload de Meta no corresponde a whatsapp_business_account.",
        )
    entries = payload.get("entry")
    if not isinstance(entries, list):
        raise Validacion(
            "WEBHOOK_PAYLOAD_INVALIDO",
            "El payload de Meta no contiene una lista válida en entry.",
        )
    if not phone_number_id_esperado:
        raise NumeroMetaInvalido()

    mensajes: list[MensajeMetaEntrante] = []
    estados: list[EstadoMetaEntrante] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        changes = entry.get("changes")
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, dict) or change.get("field") != "messages":
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            metadata = value.get("metadata")
            phone_number_id = (
                str(metadata.get("phone_number_id") or "").strip()
                if isinstance(metadata, dict)
                else ""
            )
            if phone_number_id != phone_number_id_esperado:
                raise NumeroMetaInvalido()

            for item in value.get("statuses") or []:
                if not isinstance(item, dict):
                    continue
                wamid = str(item.get("id") or "").strip()
                status = str(item.get("status") or "").strip().lower()
                if not wamid or not status:
                    continue
                errores = item.get("errors")
                error_code: str | None = None
                if isinstance(errores, list) and errores and isinstance(errores[0], dict):
                    primero = errores[0]
                    bruto = primero.get("code") or primero.get("title") or "META_FAILED"
                    error_code = f"META_{bruto}" if str(bruto).isdigit() else str(bruto)
                elif status == "failed":
                    error_code = "META_FAILED"
                estados.append(
                    EstadoMetaEntrante(
                        wamid=wamid,
                        status=status,
                        recipient_id=str(item.get("recipient_id") or "").strip() or None,
                        biz_opaque_callback_data=(
                            str(item.get("biz_opaque_callback_data") or "").strip() or None
                        ),
                        error_code=error_code,
                    )
                )

            for item in value.get("messages") or []:
                if not isinstance(item, dict):
                    continue
                if str(item.get("type") or "").strip().lower() != "text":
                    continue
                wamid = str(item.get("id") or "").strip()
                remitente = str(item.get("from") or "").strip()
                text_obj = item.get("text")
                body = (
                    str(text_obj.get("body") or "").strip()
                    if isinstance(text_obj, dict)
                    else ""
                )
                if not wamid or not remitente or not body:
                    continue
                mensajes.append(
                    MensajeMetaEntrante(
                        wamid=wamid,
                        telefono=normalizar_telefono(remitente),
                        texto=body,
                    )
                )

    return mensajes, estados


def registrar_lote_meta(
    db: Session,
    mensajes: list[MensajeMetaEntrante],
    estados: list[EstadoMetaEntrante],
) -> ResultadoLoteMeta:
    """Guarda textos entrantes deduplicados por wamid y aplica estados de entrega."""
    from app.whatsapp.despacho import actualizar_por_meta

    guardados = 0
    duplicados = 0
    estados_procesados = 0

    for msg in mensajes:
        try:
            with db.begin_nested():
                db.add(
                    MensajeWhatsapp(
                        wa_message_id=msg.wamid,
                        telefono_remitente=msg.telefono,
                        direccion="ENTRANTE",
                        contenido=msg.texto,
                        media_tipo="text",
                        proveedor="META",
                        estado_envio="PENDIENTE",
                        intentos=0,
                    )
                )
                db.flush()
            guardados += 1
        except IntegrityError:
            duplicados += 1

    for estado in estados:
        estado_interno = ESTADOS_META.get(estado.status)
        if not estado_interno:
            continue
        if actualizar_por_meta(
            db,
            wamid=estado.wamid,
            intento=estado.biz_opaque_callback_data,
            estado=estado_interno,
            error=estado.error_code,
            commit=False,
        ):
            estados_procesados += 1

    db.commit()
    return ResultadoLoteMeta(
        guardados=guardados,
        duplicados=duplicados,
        estados_procesados=estados_procesados,
    )


def _normalizar_codigo(valor: str | None) -> str | None:
    if not valor:
        return None
    coincidencia = re.fullmatch(
        r"ECO-?(?:(\d{4})-?)?(\d{1,6})", valor.strip(), re.IGNORECASE
    )
    if coincidencia is None:
        return None
    anio = coincidencia.group(1) or str(hoy_bogota().year)
    numero = int(coincidencia.group(2))
    return f"ECO-{anio}-{numero:06d}"


def _construir_observaciones(
    extraccion: ExtraccionSolicitudMeta,
    peso_kg: Decimal | None,
) -> str | None:
    partes: list[str] = []
    if extraccion.notas:
        partes.append(extraccion.notas)
    if peso_kg is None and extraccion.cantidad is not None and extraccion.unidad:
        cantidad_txt = (
            f"{extraccion.cantidad:g}"
            if isinstance(extraccion.cantidad, float)
            else str(extraccion.cantidad)
        )
        partes.append(
            f"Cantidad reportada: {cantidad_txt} {extraccion.unidad.lower()} (peso pendiente)."
        )
    if not partes:
        return None
    return " · ".join(partes)[:2000]


def _construir_disponibilidad(extraccion: ExtraccionSolicitudMeta) -> str:
    referencia = (extraccion.referencia_general or "").strip()
    if len(referencia) >= 3:
        return referencia[:120]
    return "Por coordinar vía WhatsApp"


def _programar_reintento_o_fallo(
    db: Session,
    registro: MensajeWhatsapp,
    codigo_error: str,
    *,
    reintentable: bool,
    cfg: ConfiguracionWhatsApp,
) -> None:
    ahora = datetime.now(UTC)
    registro.intentos = (registro.intentos or 0) + 1
    registro.error = codigo_error[:200]
    if reintentable and registro.intentos < cfg.gemini_max_intentos:
        espera = cfg.gemini_backoff_base_segundos * (2 ** (registro.intentos - 1))
        registro.estado_envio = "PENDIENTE"
        registro.proximo_intento_en = ahora + timedelta(seconds=espera)
    else:
        registro.estado_envio = "FALLIDO"
        registro.procesado_en = ahora
        registro.proximo_intento_en = None
    db.commit()


def procesar_entrante_meta_uno(fabrica=SessionLocal) -> bool:
    """Procesa un mensaje pendiente de Meta: valida remitente, extrae con Gemini y crea Solicitud."""
    ahora = datetime.now(UTC)
    cfg = obtener_config()

    with fabrica() as db:
        registro = db.scalar(
            select(MensajeWhatsapp)
            .where(
                MensajeWhatsapp.proveedor == "META",
                MensajeWhatsapp.direccion == "ENTRANTE",
                MensajeWhatsapp.estado_envio == "PENDIENTE",
                MensajeWhatsapp.solicitud_id.is_(None),
                or_(
                    MensajeWhatsapp.proximo_intento_en.is_(None),
                    MensajeWhatsapp.proximo_intento_en <= ahora,
                ),
            )
            .order_by(MensajeWhatsapp.id.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if registro is None:
            return False

        usuario = db.scalar(
            select(Usuario).where(
                Usuario.telefono == registro.telefono_remitente,
                Usuario.activo.is_(True),
            )
        )
        if usuario is None:
            registro.estado_envio = "DESCARTADO"
            registro.estado_conversacion = "REMITENTE_DESCONOCIDO"
            registro.error = "REMITENTE_DESCONOCIDO"
            registro.procesado_en = ahora
            registro.proximo_intento_en = None
            db.commit()
            return True

        # Permitir cierre explícito LISTO ECO-... [kilos] desde recolectores activos en Meta.
        comando = re.fullmatch(
            r"LISTO\s+(ECO-[\d-]+)\s+(\d{1,6}(?:[.,]\d{1,2})?)(?:\s*kg)?",
            (registro.contenido or "").strip(),
            re.IGNORECASE,
        )
        if comando and usuario.rol in {"HUERTERO", "RECICLADOR"}:
            codigo = _normalizar_codigo(comando.group(1))
            peso = Decimal(comando.group(2).replace(",", "."))
            if codigo and 0 < peso <= Decimal("100000"):
                try:
                    resultado = cerrar_solicitud_por_codigo(
                        db,
                        usuario,
                        codigo,
                        CerrarSolicitud(
                            cantidad_real_kg=peso,
                            nota_operativa="Cierre confirmado desde WhatsApp Meta.",
                        ),
                    )
                    registro.solicitud_id = resultado.solicitud.id
                    registro.intencion_ia = "CIERRE_RECOLECCION"
                    registro.procesado_por_ia = False
                    registro.estado_envio = "PROCESADO"
                    registro.procesado_en = datetime.now(UTC)
                    registro.error = None
                    db.commit()
                    return True
                except ErrorDominio as exc:
                    registro.estado_envio = "FALLIDO"
                    registro.error = exc.codigo
                    registro.procesado_en = datetime.now(UTC)
                    db.commit()
                    return True

        if usuario.rol not in TIPO_GENERADOR_POR_ROL:
            registro.estado_envio = "DESCARTADO"
            registro.estado_conversacion = "ROL_NO_AUTORIZADO"
            registro.error = "ROL_NO_AUTORIZADO"
            registro.procesado_en = ahora
            registro.proximo_intento_en = None
            db.commit()
            return True

        texto_anonimo = anonimizar(
            registro.contenido,
            nombre=usuario.nombre,
            telefono=usuario.telefono,
            direccion=usuario.direccion,
        )

        try:
            extraccion = extraer_solicitud_gemini(texto_anonimo)
        except (ErrorTransitorioIA, SalidaIAInvalida) as exc:
            _programar_reintento_o_fallo(
                db, registro, exc.codigo, reintentable=True, cfg=cfg
            )
            return True
        except ErrorWhatsApp as exc:
            _programar_reintento_o_fallo(
                db, registro, exc.codigo, reintentable=False, cfg=cfg
            )
            return True

        registro.texto_extraido = texto_anonimo
        registro.borrador_json = extraccion.model_dump_json()
        registro.procesado_por_ia = True
        registro.procesado_en = datetime.now(UTC)
        registro.proximo_intento_en = None
        registro.error = None

        if not extraccion.es_solicitud or extraccion.flujo not in {"ORGANICO", "RECICLABLE"}:
            registro.estado_envio = "PROCESADO"
            registro.intencion_ia = "ACLARACION_PENDIENTE"
            registro.estado_conversacion = "ACLARACION_PENDIENTE"
            db.commit()
            return True

        peso_kg = convertir_peso_a_kg(extraccion.cantidad, extraccion.unidad)
        observaciones = _construir_observaciones(extraccion, peso_kg)
        disponibilidad = _construir_disponibilidad(extraccion)

        try:
            solicitud = crear_solicitud(
                db,
                usuario,
                SolicitudCrear(
                    flujo=extraccion.flujo,
                    subtipo_material=extraccion.material,
                    cantidad_estimada_kg=peso_kg,
                    disponibilidad_usuario=disponibilidad,
                    observaciones=observaciones,
                ),
                commit=False,
            )
            registro.solicitud_id = solicitud.id
            registro.intencion_ia = "SOLICITUD_RECOLECCION"
            registro.estado_conversacion = None
            registro.estado_envio = "PROCESADO"
            db.commit()
        except (ErrorDominio, SQLAlchemyError) as exc:
            db.rollback()
            # Re-leer para registrar fallo de persistencia sin dejar estado inconsistente.
            fallido = db.get(MensajeWhatsapp, registro.id)
            if fallido is not None:
                fallido.estado_envio = "FALLIDO"
                fallido.error = getattr(exc, "codigo", type(exc).__name__)[:200]
                fallido.procesado_en = datetime.now(UTC)
                db.commit()
        return True


def enviar_aviso_meta(aviso: AvisoWhatsApp, cfg: ConfiguracionWhatsApp) -> str:
    """Envía un aviso usando plantillas aprobadas de Meta Graph API v25.0."""
    if not cfg.whatsapp_access_token or not cfg.whatsapp_phone_number_id:
        raise ErrorMetaDefinitivo(
            "CONFIGURACION_INCOMPLETA",
            "Faltan WHATSAPP_ACCESS_TOKEN o WHATSAPP_PHONE_NUMBER_ID.",
        )
    plantilla = aviso.plantilla or plantilla_meta_para(aviso.evento, aviso.destinatario)
    if not plantilla:
        raise ErrorMetaDefinitivo(
            "PLANTILLA_NO_CONFIGURADA",
            f"Falta configurar plantilla Meta para {aviso.evento}_{aviso.destinatario}.",
        )

    destino = re.sub(r"\D", "", aviso.telefono or "")
    if len(destino) < 10:
        raise ErrorMetaDefinitivo("TELEFONO_INVALIDO", "Teléfono de destino inválido.")

    template_obj: dict[str, Any] = {
        "name": plantilla,
        "language": {"code": cfg.whatsapp_template_lang or "es"},
    }
    if not cfg.whatsapp_template_sin_variables:
        texto_param = " ".join((aviso.contenido or "").split())[:1024]
        template_obj["components"] = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": texto_param}],
            }
        ]

    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": destino,
        "type": "template",
        "template": template_obj,
        "biz_opaque_callback_data": aviso.intento,
    }
    url = (
        f"https://graph.facebook.com/{cfg.whatsapp_graph_version}/"
        f"{cfg.whatsapp_phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {cfg.whatsapp_access_token}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=12.0) as cliente:
            respuesta = cliente.post(url, headers=headers, json=payload)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise ErrorMetaIncierto(type(exc).__name__) from exc

    if 400 <= respuesta.status_code < 500:
        codigo = str(respuesta.status_code)
        try:
            detalle = respuesta.json().get("error") or {}
            if isinstance(detalle, dict) and detalle.get("code") is not None:
                codigo = str(detalle["code"])
        except ValueError:
            pass
        raise ErrorMetaDefinitivo(f"META_{codigo}")

    if respuesta.status_code >= 500:
        raise ErrorMetaIncierto(f"META_HTTP_{respuesta.status_code}")

    try:
        datos = respuesta.json()
        wamid = str(datos["messages"][0]["id"]).strip()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ErrorMetaIncierto("RESPUESTA_INVALIDA") from exc

    if not wamid:
        raise ErrorMetaIncierto("RESPUESTA_SIN_WAMID")
    return wamid


__all__ = [
    "ESTADOS_META",
    "EstadoMetaEntrante",
    "MensajeMetaEntrante",
    "ResultadoLoteMeta",
    "enviar_aviso_meta",
    "extraer_eventos_meta",
    "procesar_entrante_meta_uno",
    "registrar_lote_meta",
    "verificar_firma_meta",
]
