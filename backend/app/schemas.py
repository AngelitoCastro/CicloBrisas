"""Esquemas Pydantic de entrada y salida de la API EcoConecta."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_serializer,
    field_validator,
    model_validator,
)

RolUsuario = Literal[
    "HOGAR",
    "UNIDAD_PRODUCTIVA",
    "COORD_HUERTEROS",
    "HUERTERO",
    "COORD_RECICLADORES",
    "RECICLADOR",
    "ADMIN",
]
FlujoResiduo = Literal["ORGANICO", "RECICLABLE"]
EstadoSolicitud = Literal[
    "RECIBIDA",
    "EN_REVISION",
    "ASIGNADA",
    "PROGRAMADA",
    "RECOLECTADA",
    "CANCELADA",
]
TipoGenerador = Literal["HOGAR", "UNIDAD_PRODUCTIVA"]
CategoriaContenido = Literal["ORGANICO", "RECICLABLE", "HUERTA", "RUTAS"]

DecimalSalida = Annotated[
    Decimal,
    PlainSerializer(lambda valor: float(valor), return_type=float),
]


def _serializar_fecha_hora(valor: datetime | None) -> str | None:
    if valor is None:
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=UTC)
    return valor.isoformat()


class ModeloSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Autenticación y usuarios
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    telefono: str = Field(min_length=7, max_length=25, examples=["+573000000108"])
    password: str = Field(
        min_length=1, max_length=128, examples=["clave-de-demostracion"]
    )

    @field_validator("telefono")
    @classmethod
    def _limpiar_telefono(cls, valor: str) -> str:
        limpio = valor.strip()
        if not limpio:
            raise ValueError("El teléfono no puede estar vacío.")
        return limpio

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "telefono": "+573000000108",
                "password": "clave-de-demostracion",
            }
        }
    )


class UsuarioResponse(ModeloSalida):
    id: UUID
    nombre: str
    telefono: str
    rol: RolUsuario
    direccion: str | None
    sector_manzana: str | None
    es_piloto: bool
    puntos_acumulados: DecimalSalida
    activo: bool
    creado_en: datetime

    @field_serializer("creado_en")
    def _fecha(self, valor: datetime) -> str | None:
        return _serializar_fecha_hora(valor)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expira_en_segundos: int
    usuario: UsuarioResponse


class DemoLoginRequest(BaseModel):
    rol: RolUsuario


class UsuarioResumen(ModeloSalida):
    id: UUID
    nombre: str
    rol: RolUsuario


class ContactoSolicitante(UsuarioResumen):
    telefono: str | None = None
    direccion: str | None = None
    sector_manzana: str | None = None
    es_piloto: bool = False


class RecolectorCatalogoResponse(ModeloSalida):
    id: UUID
    nombre: str
    rol: Literal["HUERTERO", "RECICLADOR"]
    telefono: str
    activo: bool


class ContenidoEducativoResponse(ModeloSalida):
    id: int
    titulo: str
    categoria: CategoriaContenido
    resumen: str
    que_si_va: str | None
    que_no_va: str | None
    orden: int


class UsuarioListResponse(BaseModel):
    items: list[UsuarioResponse]
    total: int
    limit: int
    offset: int


class PilotoUpdate(BaseModel):
    es_piloto: bool = Field(
        description="Etiqueta la cuenta como piloto FSD. No restringe el acceso a la API.",
        examples=[True],
    )


# ---------------------------------------------------------------------------
# Solicitudes
# ---------------------------------------------------------------------------


class SolicitudCrear(BaseModel):
    flujo: FlujoResiduo = Field(examples=["ORGANICO"])
    subtipo_material: str | None = Field(
        default=None,
        max_length=100,
        examples=["Cáscaras y restos de vegetales"],
    )
    cantidad_estimada_kg: Decimal | None = Field(
        default=None,
        gt=0,
        le=100_000,
        max_digits=8,
        decimal_places=2,
        examples=[12.5],
    )
    disponibilidad_usuario: str = Field(
        min_length=3,
        max_length=120,
        examples=["Lunes a viernes de 8:00 a.m. a 11:00 a.m."],
    )
    observaciones: str | None = Field(
        default=None,
        max_length=2000,
        examples=["Dejar el balde en la portería."],
    )

    @field_validator("subtipo_material", "observaciones")
    @classmethod
    def _limpiar_opcionales(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        limpio = valor.strip()
        return limpio or None

    @field_validator("disponibilidad_usuario")
    @classmethod
    def _limpiar_disponibilidad(cls, valor: str) -> str:
        limpio = valor.strip()
        if len(limpio) < 3:
            raise ValueError("Indica una disponibilidad horaria válida.")
        return limpio

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "flujo": "ORGANICO",
                "subtipo_material": "Cáscaras y restos de vegetales",
                "cantidad_estimada_kg": 12.5,
                "disponibilidad_usuario": "Lunes a viernes de 8:00 a.m. a 11:00 a.m.",
                "observaciones": "Dejar el balde en la portería.",
            }
        }
    )


class RevisarSolicitud(BaseModel):
    nota_operativa: str | None = Field(default=None, max_length=500)


class AsignarSolicitud(BaseModel):
    recolector_id: UUID
    nota_operativa: str | None = Field(default=None, max_length=500)


class ProgramarSolicitud(BaseModel):
    recolector_id: UUID
    fecha_programada: date = Field(examples=["2026-11-21"])
    hora_programada: time = Field(examples=["09:30"])
    nota_operativa: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "recolector_id": "00000000-0000-0000-0000-000000000000",
                "fecha_programada": "2026-11-21",
                "hora_programada": "09:30",
                "nota_operativa": "Ruta de la mañana",
            }
        }
    )


class CerrarSolicitud(BaseModel):
    cantidad_real_kg: Decimal = Field(
        gt=0,
        le=100_000,
        max_digits=8,
        decimal_places=2,
        examples=[10.0],
    )
    nota_operativa: str | None = Field(default=None, max_length=1000)

    @field_validator("nota_operativa")
    @classmethod
    def _limpiar_nota(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        limpio = valor.strip()
        return limpio or None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cantidad_real_kg": 10.0,
                "nota_operativa": "Recolección confirmada en campo.",
            }
        }
    )


class CancelarSolicitud(BaseModel):
    motivo: str = Field(min_length=5, max_length=500)

    @field_validator("motivo")
    @classmethod
    def _limpiar_motivo(cls, valor: str) -> str:
        limpio = valor.strip()
        if len(limpio) < 5:
            raise ValueError("El motivo debe tener al menos 5 caracteres.")
        return limpio


class SolicitudPublicaResponse(ModeloSalida):
    id: int
    codigo_publico: str
    flujo: FlujoResiduo
    subtipo_material: str | None
    cantidad_estimada_kg: DecimalSalida | None
    cantidad_real_kg: DecimalSalida | None
    disponibilidad_usuario: str
    observaciones: str | None
    estado: EstadoSolicitud
    solicitante: ContactoSolicitante
    coordinador: UsuarioResumen | None
    recolector: UsuarioResumen | None
    fecha_programada: date | None
    hora_programada: time | None
    puntos_otorgados: DecimalSalida
    regla_puntos_id: int | None
    creado_en: datetime
    actualizado_en: datetime

    @field_serializer("hora_programada")
    def _hora(self, valor: time | None) -> str | None:
        return valor.strftime("%H:%M") if valor is not None else None

    @field_serializer("creado_en", "actualizado_en")
    def _fechas(self, valor: datetime) -> str | None:
        return _serializar_fecha_hora(valor)


class SolicitudListResponse(BaseModel):
    items: list[SolicitudPublicaResponse]
    total: int
    limit: int
    offset: int


class HistorialEstadoResponse(ModeloSalida):
    id: int
    estado_anterior: EstadoSolicitud | None
    estado_nuevo: EstadoSolicitud
    actor: UsuarioResumen | None
    nota_operativa: str | None
    fecha_cambio: datetime

    @field_serializer("fecha_cambio")
    def _fecha(self, valor: datetime) -> str | None:
        return _serializar_fecha_hora(valor)


class CalculoPuntosResponse(BaseModel):
    regla_puntos_id: int
    flujo: FlujoResiduo
    tipo_generador: TipoGenerador
    puntos_base_solicitud: DecimalSalida
    puntos_por_kg: DecimalSalida
    cantidad_real_kg: DecimalSalida
    puntos_otorgados: DecimalSalida
    formula: str
    nota_fsd: str = "Cálculo parametrizable sujeto a validación FSD."


class CierreSolicitudResponse(SolicitudPublicaResponse):
    calculo_puntos: CalculoPuntosResponse


# ---------------------------------------------------------------------------
# Reglas de puntos
# ---------------------------------------------------------------------------


class ReglaPuntosResponse(ModeloSalida):
    id: int
    flujo: FlujoResiduo
    tipo_generador: TipoGenerador
    puntos_base_solicitud: DecimalSalida
    puntos_por_kg: DecimalSalida
    valor_referencia_kg_cop: DecimalSalida
    descripcion_regla: str | None
    activa: bool
    actualizado_en: datetime

    @field_serializer("actualizado_en")
    def _fecha(self, valor: datetime) -> str | None:
        return _serializar_fecha_hora(valor)


class ReglaPuntosCrear(BaseModel):
    flujo: FlujoResiduo
    tipo_generador: TipoGenerador
    puntos_base_solicitud: Decimal = Field(
        ge=0, le=100_000, max_digits=10, decimal_places=2
    )
    puntos_por_kg: Decimal = Field(ge=0, le=100_000, max_digits=10, decimal_places=2)
    valor_referencia_kg_cop: Decimal = Field(
        ge=0,
        le=10_000_000,
        max_digits=10,
        decimal_places=2,
    )
    descripcion_regla: str | None = Field(default=None, max_length=1000)
    activa: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "flujo": "ORGANICO",
                "tipo_generador": "HOGAR",
                "puntos_base_solicitud": 10,
                "puntos_por_kg": 5,
                "valor_referencia_kg_cop": 80,
                "descripcion_regla": "Regla piloto de hogar para orgánicos.",
                "activa": True,
            }
        }
    )


class ReglaPuntosActualizar(BaseModel):
    puntos_base_solicitud: Decimal | None = Field(
        default=None,
        ge=0,
        le=100_000,
        max_digits=10,
        decimal_places=2,
    )
    puntos_por_kg: Decimal | None = Field(
        default=None,
        ge=0,
        le=100_000,
        max_digits=10,
        decimal_places=2,
    )
    valor_referencia_kg_cop: Decimal | None = Field(
        default=None,
        ge=0,
        le=10_000_000,
        max_digits=10,
        decimal_places=2,
    )
    descripcion_regla: str | None = Field(default=None, max_length=1000)
    activa: bool | None = None

    @model_validator(mode="after")
    def _al_menos_un_campo(self) -> ReglaPuntosActualizar:
        if not self.model_fields_set:
            raise ValueError("Debe indicar al menos un campo para actualizar.")
        return self


# ---------------------------------------------------------------------------
# Errores documentados
# ---------------------------------------------------------------------------


class ErrorDetalle(BaseModel):
    codigo: str
    mensaje: str
    errores: list[dict[str, str]] | None = None


class ErrorRespuesta(BaseModel):
    detail: ErrorDetalle


class HealthResponse(BaseModel):
    estado: Literal["ok"]
    servicio: str


__all__ = [
    "AsignarSolicitud",
    "CalculoPuntosResponse",
    "CancelarSolicitud",
    "CategoriaContenido",
    "CerrarSolicitud",
    "CierreSolicitudResponse",
    "ContactoSolicitante",
    "ContenidoEducativoResponse",
    "DemoLoginRequest",
    "ErrorDetalle",
    "ErrorRespuesta",
    "EstadoSolicitud",
    "FlujoResiduo",
    "HealthResponse",
    "HistorialEstadoResponse",
    "LoginRequest",
    "PilotoUpdate",
    "ProgramarSolicitud",
    "RecolectorCatalogoResponse",
    "ReglaPuntosActualizar",
    "ReglaPuntosCrear",
    "ReglaPuntosResponse",
    "RevisarSolicitud",
    "RolUsuario",
    "SolicitudCrear",
    "SolicitudListResponse",
    "SolicitudPublicaResponse",
    "TipoGenerador",
    "TokenResponse",
    "UsuarioListResponse",
    "UsuarioResponse",
    "UsuarioResumen",
]
