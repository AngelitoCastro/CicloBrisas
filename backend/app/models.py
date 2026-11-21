"""Modelos ORM SQLAlchemy 2 para EcoConecta (Villas de San Pablo)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    false,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

ROLES_USUARIO: tuple[str, ...] = (
    "HOGAR",
    "UNIDAD_PRODUCTIVA",
    "COORD_HUERTEROS",
    "HUERTERO",
    "COORD_RECICLADORES",
    "RECICLADOR",
    "ADMIN",
)
FLUJOS_RESIDUO: tuple[str, ...] = ("ORGANICO", "RECICLABLE")
TIPOS_GENERADOR: tuple[str, ...] = ("HOGAR", "UNIDAD_PRODUCTIVA")
ESTADOS_SOLICITUD: tuple[str, ...] = (
    "RECIBIDA",
    "EN_REVISION",
    "ASIGNADA",
    "PROGRAMADA",
    "RECOLECTADA",
    "CANCELADA",
)
DIRECCIONES_MENSAJE: tuple[str, ...] = ("ENTRANTE", "SALIENTE")
CATEGORIAS_CONTENIDO: tuple[str, ...] = ("ORGANICO", "RECICLABLE", "HUERTA", "RUTAS")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _sql_in(column_name: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted})"


class Usuario(Base):
    """Actores de EcoConecta: hogares, unidades productivas, coordinadores, recolectores y admin."""

    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(_sql_in("rol", ROLES_USUARIO), name="rol_valido"),
        CheckConstraint(
            "puntos_acumulados >= 0", name="puntos_acumulados_no_negativos"
        ),
        Index("ix_usuarios_rol_activo", "rol", "activo"),
        Index("ix_usuarios_es_piloto", "es_piloto"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    telefono: Mapped[str] = mapped_column(String(25), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(30), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sector_manzana: Mapped[str | None] = mapped_column(String(100), nullable=True)
    es_piloto: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    puntos_acumulados: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )

    solicitudes_creadas: Mapped[list[Solicitud]] = relationship(
        back_populates="solicitante",
        foreign_keys="Solicitud.solicitante_id",
    )
    solicitudes_coordinadas: Mapped[list[Solicitud]] = relationship(
        back_populates="coordinador",
        foreign_keys="Solicitud.coordinador_id",
    )
    solicitudes_asignadas: Mapped[list[Solicitud]] = relationship(
        back_populates="recolector",
        foreign_keys="Solicitud.recolector_id",
    )


class ReglaPuntos(Base):
    """Reglas parametrizables de puntos adaptables sujetas a validación FSD (RN-06)."""

    __tablename__ = "reglas_puntos"
    __table_args__ = (
        CheckConstraint(_sql_in("flujo", FLUJOS_RESIDUO), name="flujo_valido"),
        CheckConstraint(
            _sql_in("tipo_generador", TIPOS_GENERADOR), name="tipo_generador_valido"
        ),
        CheckConstraint("puntos_base_solicitud >= 0", name="puntos_base_no_negativos"),
        CheckConstraint("puntos_por_kg >= 0", name="puntos_por_kg_no_negativos"),
        CheckConstraint(
            "valor_referencia_kg_cop >= 0", name="valor_referencia_no_negativo"
        ),
        Index(
            "uq_reglas_puntos_activa_flujo_generador",
            "flujo",
            "tipo_generador",
            unique=True,
            postgresql_where=text("activa IS TRUE"),
            sqlite_where=text("activa = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flujo: Mapped[str] = mapped_column(String(20), nullable=False)
    tipo_generador: Mapped[str] = mapped_column(String(30), nullable=False)
    puntos_base_solicitud: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("10.00"),
        server_default=text("10"),
    )
    puntos_por_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("5.00"),
        server_default=text("5"),
    )
    valor_referencia_kg_cop: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("80.00"),
        server_default=text("80"),
    )
    descripcion_regla: Mapped[str | None] = mapped_column(Text, nullable=True)
    activa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
    )

    solicitudes: Mapped[list[Solicitud]] = relationship(back_populates="regla_puntos")


class Solicitud(Base):
    """Solicitudes de recolección orgánica o reciclable (RN-01 a RN-05)."""

    __tablename__ = "solicitudes"
    __table_args__ = (
        CheckConstraint(_sql_in("flujo", FLUJOS_RESIDUO), name="flujo_valido"),
        CheckConstraint(_sql_in("estado", ESTADOS_SOLICITUD), name="estado_valido"),
        CheckConstraint(
            "cantidad_estimada_kg IS NULL OR cantidad_estimada_kg > 0",
            name="cantidad_estimada_positiva",
        ),
        CheckConstraint(
            "cantidad_real_kg IS NULL OR cantidad_real_kg > 0",
            name="cantidad_real_positiva",
        ),
        CheckConstraint("puntos_otorgados >= 0", name="puntos_otorgados_no_negativos"),
        CheckConstraint(
            "(estado = 'RECOLECTADA') OR (puntos_otorgados = 0 AND regla_puntos_id IS NULL)",
            name="puntos_solo_en_recolectada",
        ),
        CheckConstraint(
            "(estado <> 'ASIGNADA') OR (coordinador_id IS NOT NULL AND recolector_id IS NOT NULL)",
            name="asignada_con_responsables",
        ),
        CheckConstraint(
            "(estado <> 'PROGRAMADA') OR ("
            "coordinador_id IS NOT NULL AND recolector_id IS NOT NULL "
            "AND fecha_programada IS NOT NULL AND hora_programada IS NOT NULL"
            ")",
            name="programada_completa",
        ),
        Index("ix_solicitudes_flujo_estado", "flujo", "estado"),
        Index("ix_solicitudes_solicitante_creado", "solicitante_id", "creado_en"),
        Index("ix_solicitudes_recolector_estado", "recolector_id", "estado"),
        Index("ix_solicitudes_coordinador_id", "coordinador_id"),
        Index("ix_solicitudes_fecha_programada", "fecha_programada"),
        Index("ix_solicitudes_regla_puntos_id", "regla_puntos_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo_publico: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    solicitante_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=False,
    )
    flujo: Mapped[str] = mapped_column(String(20), nullable=False)
    subtipo_material: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cantidad_estimada_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    cantidad_real_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    disponibilidad_usuario: Mapped[str] = mapped_column(String(120), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
        default="RECIBIDA",
        server_default=text("'RECIBIDA'"),
    )
    coordinador_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=True,
    )
    recolector_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=True,
    )
    fecha_programada: Mapped[date | None] = mapped_column(Date, nullable=True)
    hora_programada: Mapped[time | None] = mapped_column(Time, nullable=True)
    puntos_otorgados: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    regla_puntos_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("reglas_puntos.id", ondelete="RESTRICT"),
        nullable=True,
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
    )

    solicitante: Mapped[Usuario] = relationship(
        back_populates="solicitudes_creadas",
        foreign_keys=[solicitante_id],
    )
    coordinador: Mapped[Usuario | None] = relationship(
        back_populates="solicitudes_coordinadas",
        foreign_keys=[coordinador_id],
    )
    recolector: Mapped[Usuario | None] = relationship(
        back_populates="solicitudes_asignadas",
        foreign_keys=[recolector_id],
    )
    regla_puntos: Mapped[ReglaPuntos | None] = relationship(
        back_populates="solicitudes",
        foreign_keys=[regla_puntos_id],
    )
    historial_estados: Mapped[list[HistorialEstado]] = relationship(
        back_populates="solicitud",
        cascade="all, delete-orphan",
        order_by="HistorialEstado.fecha_cambio, HistorialEstado.id",
    )
    mensajes_whatsapp: Mapped[list[MensajeWhatsapp]] = relationship(
        back_populates="solicitud",
    )


class HistorialEstado(Base):
    """Trazabilidad auditable de cada transición de estado de una solicitud (RN-04)."""

    __tablename__ = "historial_estados"
    __table_args__ = (
        CheckConstraint(
            f"estado_anterior IS NULL OR {_sql_in('estado_anterior', ESTADOS_SOLICITUD)}",
            name="estado_anterior_valido",
        ),
        CheckConstraint(
            _sql_in("estado_nuevo", ESTADOS_SOLICITUD), name="estado_nuevo_valido"
        ),
        Index("ix_historial_estados_solicitud_fecha", "solicitud_id", "fecha_cambio"),
        Index("ix_historial_estados_cambiado_por", "cambiado_por"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitud_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("solicitudes.id", ondelete="CASCADE"),
        nullable=False,
    )
    estado_anterior: Mapped[str | None] = mapped_column(String(25), nullable=True)
    estado_nuevo: Mapped[str] = mapped_column(String(25), nullable=False)
    cambiado_por: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    nota_operativa: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_cambio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )

    solicitud: Mapped[Solicitud] = relationship(back_populates="historial_estados")
    actor: Mapped[Usuario | None] = relationship(foreign_keys=[cambiado_por])


class MensajeWhatsapp(Base):
    """Registro de mensajes entrantes y salientes de WhatsApp y clasificación IA."""

    __tablename__ = "mensajes_whatsapp"
    __table_args__ = (
        CheckConstraint(
            _sql_in("direccion", DIRECCIONES_MENSAJE), name="direccion_valida"
        ),
        Index("ix_mensajes_whatsapp_solicitud_id", "solicitud_id"),
        Index(
            "ix_mensajes_whatsapp_telefono_creado", "telefono_remitente", "creado_en"
        ),
        Index("uq_mensajes_whatsapp_wa_message_id", "wa_message_id", unique=True),
        Index(
            "ix_mensajes_whatsapp_bandeja",
            "proveedor",
            "direccion",
            "estado_envio",
            "proximo_intento_en",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitud_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("solicitudes.id", ondelete="SET NULL"),
        nullable=True,
    )
    telefono_remitente: Mapped[str] = mapped_column(String(25), nullable=False)
    direccion: Mapped[str] = mapped_column(String(15), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    intencion_ia: Mapped[str | None] = mapped_column(String(50), nullable=True)
    procesado_por_ia: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    wa_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado_envio: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDIENTE",
        server_default=text("'PENDIENTE'"),
    )
    intentos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    procesado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estado_conversacion: Mapped[str | None] = mapped_column(String(30), nullable=True)
    borrador_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    media_tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    media_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    texto_extraido: Mapped[str | None] = mapped_column(Text, nullable=True)
    proveedor: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="TWILIO",
        server_default=text("'TWILIO'"),
    )
    proximo_intento_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    solicitud: Mapped[Solicitud | None] = relationship(
        back_populates="mensajes_whatsapp"
    )


class ContenidoEducativo(Base):
    """Contenidos de educación ambiental del portal comunitario."""

    __tablename__ = "contenidos_educativos"
    __table_args__ = (
        CheckConstraint(
            _sql_in("categoria", CATEGORIAS_CONTENIDO), name="categoria_valida"
        ),
        UniqueConstraint(
            "categoria", "titulo", name="uq_contenidos_educativos_categoria_titulo"
        ),
        Index("ix_contenidos_educativos_categoria_orden", "categoria", "orden"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    categoria: Mapped[str] = mapped_column(String(30), nullable=False)
    resumen: Mapped[str] = mapped_column(Text, nullable=False)
    que_si_va: Mapped[str | None] = mapped_column(Text, nullable=True)
    que_no_va: Mapped[str | None] = mapped_column(Text, nullable=True)
    orden: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    publicado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )


__all__ = [
    "CATEGORIAS_CONTENIDO",
    "DIRECCIONES_MENSAJE",
    "ESTADOS_SOLICITUD",
    "FLUJOS_RESIDUO",
    "ROLES_USUARIO",
    "TIPOS_GENERADOR",
    "AvisoWhatsApp",
    "Base",
    "ConsentimientoWhatsApp",
    "ContenidoEducativo",
    "HistorialEstado",
    "MensajeWhatsapp",
    "ReglaPuntos",
    "Solicitud",
    "Usuario",
]


class AvisoWhatsApp(Base):
    """Instantánea del aviso asociada a una transición ya guardada."""

    __tablename__ = "avisos_whatsapp"
    __table_args__ = (UniqueConstraint("historial_id", "destinatario"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    historial_id: Mapped[int] = mapped_column(ForeignKey("historial_estados.id"))
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), index=True)
    evento: Mapped[str] = mapped_column(String(20))
    destinatario: Mapped[str] = mapped_column(String(20))
    telefono: Mapped[str] = mapped_column(String(25))
    contenido: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", index=True)
    intento: Mapped[str] = mapped_column(
        String(32), unique=True, default=lambda: uuid.uuid4().hex
    )
    sid: Mapped[str | None] = mapped_column(String(100), unique=True)
    error: Mapped[str | None] = mapped_column(String(80))
    proveedor: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="AUTO",
        server_default=text("'AUTO'"),
    )
    plantilla: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
    )


class ConsentimientoWhatsApp(Base):
    """Consentimiento explícito del solicitante para recibir avisos por WhatsApp."""

    __tablename__ = "consentimientos_whatsapp"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    aceptado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    origen: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="WHATSAPP_ENTRANTE",
        server_default=text("'WHATSAPP_ENTRANTE'"),
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
    )
