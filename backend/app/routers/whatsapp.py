"""Webhook de WhatsApp (Meta Cloud API y Twilio): verificación, recepción y estados."""

from __future__ import annotations

import hmac
import json
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import ValidationError

from app.schemas_whatsapp import PayloadTwilio, es_callback_estado
from app.security import SesionDB
from app.services.errors import Validacion
from app.whatsapp.config import obtener_config
from app.whatsapp.despacho import ESTADOS, actualizar
from app.whatsapp.errores import CuentaTwilioInvalida
from app.whatsapp.meta import (
    extraer_eventos_meta,
    registrar_lote_meta,
    verificar_firma_meta,
)
from app.whatsapp.payload import extraer_mensajes, verificar_firma_twilio
from app.whatsapp.webhook_service import procesar_mensaje

router = APIRouter(prefix="/api/webhooks", tags=["WhatsApp"])


def _url_para_firma(request: Request, url_publica: str) -> str:
    if url_publica:
        return url_publica
    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    if not proto or not host:
        return str(request.url)
    consulta = f"?{request.url.query}" if request.url.query else ""
    return f"{proto}://{host}{request.url.path}{consulta}"


def _es_peticion_meta(request: Request, x_hub_signature_256: str | None) -> bool:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        return True
    if x_hub_signature_256 and "application/x-www-form-urlencoded" not in content_type:
        return True
    return False


@router.get("/whatsapp")
async def verificar_webhook_meta(
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    """Verifica el webhook de Meta WhatsApp Cloud API exigiendo token explícito."""
    configuracion = obtener_config()
    esperado = configuracion.whatsapp_verify_token
    if (
        esperado
        and hub_mode == "subscribe"
        and hub_verify_token is not None
        and hub_challenge is not None
        and hmac.compare_digest(hub_verify_token, esperado)
    ):
        return PlainTextResponse(content=hub_challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@router.post("/whatsapp", status_code=200)
async def recibir_webhook(
    request: Request,
    db: SesionDB,
    x_twilio_signature: Annotated[
        str | None,
        Header(alias="X-Twilio-Signature"),
    ] = None,
    x_hub_signature_256: Annotated[
        str | None,
        Header(alias="X-Hub-Signature-256"),
    ] = None,
) -> Response:
    configuracion = obtener_config()

    if _es_peticion_meta(request, x_hub_signature_256):
        cuerpo_bruto = await request.body()
        verificar_firma_meta(
            cuerpo_bruto,
            x_hub_signature_256,
            configuracion.whatsapp_app_secret,
        )
        try:
            payload_meta = json.loads(cuerpo_bruto.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise Validacion(
                "WEBHOOK_PAYLOAD_INVALIDO",
                "El cuerpo JSON del webhook de Meta no es válido.",
            ) from exc

        mensajes, estados = extraer_eventos_meta(
            payload_meta,
            configuracion.whatsapp_phone_number_id,
        )
        resultado = registrar_lote_meta(db, mensajes, estados)
        return JSONResponse(
            status_code=200,
            content={
                "estado": "ok",
                "mensajes_guardados": resultado.guardados,
                "mensajes_duplicados": resultado.duplicados,
                "estados_procesados": resultado.estados_procesados,
            },
        )

    formulario = await request.form()
    parametros = {clave: str(valor) for clave, valor in formulario.items()}

    url_firma = _url_para_firma(request, configuracion.webhook_public_url)
    verificar_firma_twilio(
        {url_firma, f"{url_firma}/"},
        parametros,
        x_twilio_signature,
        configuracion.auth_token,
    )
    if (
        configuracion.account_sid
        and parametros.get("AccountSid") != configuracion.account_sid
    ):
        raise CuentaTwilioInvalida()
    if es_callback_estado(parametros):
        return Response(content="<Response/>", media_type="application/xml")

    try:
        payload = PayloadTwilio.model_validate(parametros)
    except ValidationError as exc:
        raise Validacion(
            "WEBHOOK_PAYLOAD_INVALIDO",
            "El payload del webhook no tiene el formato esperado.",
        ) from exc

    if payload.es_actualizacion_estado:
        return Response(content="<Response/>", media_type="application/xml")

    for mensaje in extraer_mensajes(payload):
        await run_in_threadpool(procesar_mensaje, mensaje)
    return Response(content="<Response/>", media_type="application/xml")


@router.post("/whatsapp/estado/{intento}")
async def estado_aviso(intento: str, request: Request, db: SesionDB) -> Response:
    parametros = {k: str(v) for k, v in (await request.form()).items()}
    cfg = obtener_config()
    url = (
        f"{cfg.webhook_public_url}/estado/{intento}"
        if cfg.webhook_public_url
        else str(request.url)
    )
    verificar_firma_twilio(
        {url},
        parametros,
        request.headers.get("X-Twilio-Signature"),
        cfg.auth_token,
    )
    if not cfg.account_sid or parametros.get("AccountSid") != cfg.account_sid:
        raise CuentaTwilioInvalida()
    estado = ESTADOS.get(parametros.get("MessageStatus", ""))
    sid = parametros.get("MessageSid")
    if estado and sid:
        actualizar(db, intento, sid, estado, parametros.get("ErrorCode"))
    return Response(status_code=204)


__all__ = ["router"]
