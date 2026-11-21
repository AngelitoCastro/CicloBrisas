"""Esquemas Pydantic del webhook de Twilio y de la salida estructurada de la IA."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FlujoSugerido = Literal["ORGANICO", "RECICLABLE"]

ESTADOS_CALLBACK = frozenset(
    {"queued", "accepted", "sent", "delivered", "undelivered", "failed", "read"}
)


def es_callback_estado(parametros: Mapping[str, str]) -> bool:
    estados = {parametros.get("MessageStatus"), parametros.get("SmsStatus")}
    return (
        bool(estados & ESTADOS_CALLBACK)
        and not parametros.get("Body")
        and parametros.get("NumMedia", "0") == "0"
    )


class IntencionIA(StrEnum):
    SOLICITUD_RECOLECCION = "SOLICITUD_RECOLECCION"
    DUDA_AMBIENTAL = "DUDA_AMBIENTAL"
    CIERRE_RECOLECCION = "CIERRE_RECOLECCION"
    CONSULTA_ESTADO = "CONSULTA_ESTADO"
    OTRO = "OTRO"


class ClasificacionIA(BaseModel):
    intencion: IntencionIA
    codigo_solicitud: str | None = None
    flujo_sugerido: FlujoSugerido | None = None
    subtipo_material: str | None = None
    descripcion_material: str | None = None
    disponibilidad_texto: str | None = None
    peso_kg: Decimal | None = Field(
        default=None,
        gt=0,
        le=100_000,
        max_digits=8,
        decimal_places=2,
    )
    respuesta_usuario: str = Field(min_length=1, max_length=800)

    model_config = ConfigDict(extra="forbid")


class PayloadTwilio(BaseModel):
    account_sid: str = Field(alias="AccountSid")
    message_sid: str = Field(alias="MessageSid")
    from_telefono: str = Field(alias="From")
    to_telefono: str | None = Field(default=None, alias="To")
    body: str = Field(default="", alias="Body")
    num_media: int = Field(default=0, alias="NumMedia", ge=0)
    media_url0: str | None = Field(default=None, alias="MediaUrl0")
    media_content_type0: str | None = Field(default=None, alias="MediaContentType0")
    message_status: str | None = Field(default=None, alias="MessageStatus")
    sms_status: str | None = Field(default=None, alias="SmsStatus")

    model_config = ConfigDict(populate_by_name=True)

    @property
    def es_actualizacion_estado(self) -> bool:
        estados = {self.message_status, self.sms_status}
        return bool(estados & ESTADOS_CALLBACK) and not self.body and self.num_media == 0


class MensajeNormalizado(BaseModel):
    id: str
    telefono: str
    tipo: str
    texto: str | None = None
    media_id: str | None = None
    media_mime: str | None = None
    es_voz: bool = False


__all__ = [
    "ClasificacionIA",
    "IntencionIA",
    "MensajeNormalizado",
    "PayloadTwilio",
    "es_callback_estado",
]
