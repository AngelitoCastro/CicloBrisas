"""Esquemas Pydantic de webhooks (Meta y Twilio) y de la salida estructurada de la IA."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

FlujoSugerido = Literal["ORGANICO", "RECICLABLE"]
FlujoExtraidoMeta = Literal["ORGANICO", "RECICLABLE", "AMBIGUO"]
UnidadCantidadMeta = Literal[
    "KG", "G", "BOLSAS", "CAJAS", "BOTELLAS", "UNIDADES", "OTRA"
]

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


class ExtraccionSolicitudMeta(BaseModel):
    """Esquema estructurado de extracción de solicitudes con Gemini (google-genai)."""

    flujo: FlujoExtraidoMeta = Field(
        description=(
            "ORGANICO si son residuos compostables/vegetales/alimentos; "
            "RECICLABLE si son cartón, papel, plástico, vidrio o metal; "
            "AMBIGUO si no es inequívoco o faltan datos para clasificar."
        )
    )
    material: str | None = Field(
        default=None,
        max_length=100,
        description="Descripción breve del material sin datos personales.",
    )
    cantidad: float | None = Field(
        default=None,
        description="Cantidad numérica mencionada o null si no se indicó.",
    )
    unidad: UnidadCantidadMeta | None = Field(
        default=None,
        description="Unidad de la cantidad: KG, G, BOLSAS, CAJAS, BOTELLAS, UNIDADES, OTRA o null.",
    )
    referencia_general: str | None = Field(
        default=None,
        max_length=120,
        description="Disponibilidad horaria o referencia general sin datos personales exactos.",
    )
    notas: str | None = Field(
        default=None,
        max_length=500,
        description="Notas operativas adicionales sin datos personales.",
    )
    es_solicitud: bool = Field(
        default=True,
        description="True si el mensaje solicita recolección; False si es saludo, duda u otro.",
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("material", "referencia_general", "notas")
    @classmethod
    def _limpiar_texto(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        limpio = " ".join(valor.split()).strip()
        return limpio or None

    @field_validator("cantidad")
    @classmethod
    def _validar_cantidad(cls, valor: float | None) -> float | None:
        if valor is None:
            return None
        if valor <= 0 or valor > 100_000_000:
            return None
        return valor


def convertir_peso_a_kg(cantidad: float | None, unidad: str | None) -> Decimal | None:
    """Convierte KG o G a kilos con dos decimales; deja None si falta o no es peso."""
    if cantidad is None or unidad is None:
        return None
    valor = Decimal(str(cantidad))
    if not valor.is_finite() or valor <= 0:
        return None
    unidad_norm = unidad.strip().upper()
    if unidad_norm == "KG":
        peso = valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif unidad_norm == "G":
        peso = (valor / Decimal("1000")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        return None
    if peso <= 0 or peso > Decimal("100000.00"):
        return None
    return peso


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
    "ExtraccionSolicitudMeta",
    "FlujoExtraidoMeta",
    "IntencionIA",
    "MensajeNormalizado",
    "PayloadTwilio",
    "UnidadCantidadMeta",
    "convertir_peso_a_kg",
    "es_callback_estado",
]
