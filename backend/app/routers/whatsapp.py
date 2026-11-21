"""Webhook de WhatsApp de Twilio: verificación de firma y mensajes entrantes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app.security import SesionDB
from app.whatsapp.despacho import ESTADOS, actualizar
from app.schemas_whatsapp import PayloadTwilio, es_callback_estado
from app.services.errors import Validacion
from app.whatsapp.config import obtener_config
from app.whatsapp.errores import CuentaTwilioInvalida
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


@router.post("/whatsapp", status_code=200)
async def recibir_webhook(
    request: Request,
    x_twilio_signature: Annotated[
        str | None,
        Header(alias="X-Twilio-Signature"),
    ] = None,
) -> Response:
    formulario = await request.form()
    parametros = {clave: str(valor) for clave, valor in formulario.items()}
    configuracion = obtener_config()

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


__all__ = ["router"]


@router.post("/whatsapp/estado/{intento}")
async def estado_aviso(intento: str, request: Request, db: SesionDB) -> Response:
    parametros = {k: str(v) for k, v in (await request.form()).items()}
    cfg = obtener_config()
    url = f"{cfg.webhook_public_url}/estado/{intento}" if cfg.webhook_public_url else str(request.url)
    verificar_firma_twilio({url}, parametros, request.headers.get("X-Twilio-Signature"), cfg.auth_token)
    if not cfg.account_sid or parametros.get("AccountSid") != cfg.account_sid:
        raise CuentaTwilioInvalida()
    estado = ESTADOS.get(parametros.get("MessageStatus", ""))
    sid = parametros.get("MessageSid")
    if estado and sid:
        actualizar(db, intento, sid, estado, parametros.get("ErrorCode"))
    return Response(status_code=204)
