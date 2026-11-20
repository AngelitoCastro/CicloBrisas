"""Esquema inicial de EcoConecta (usuarios, reglas_puntos, solicitudes, historial y soporte).

Revision ID: 20261120_0001
Revises:
Create Date: 2026-11-20 10:35:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "usuarios",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("telefono", sa.String(length=25), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("rol", sa.String(length=30), nullable=False),
        sa.Column("direccion", sa.String(length=200), nullable=True),
        sa.Column("sector_manzana", sa.String(length=100), nullable=True),
        sa.Column("es_piloto", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "puntos_acumulados",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rol IN ('HOGAR', 'UNIDAD_PRODUCTIVA', 'COORD_HUERTEROS', 'HUERTERO', "
            "'COORD_RECICLADORES', 'RECICLADOR', 'ADMIN')",
            name="ck_usuarios_rol_valido",
        ),
        sa.CheckConstraint(
            "puntos_acumulados >= 0",
            name="ck_usuarios_puntos_acumulados_no_negativos",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_usuarios"),
        sa.UniqueConstraint("telefono", name="uq_usuarios_telefono"),
    )
    op.create_index("ix_usuarios_rol_activo", "usuarios", ["rol", "activo"], unique=False)
    op.create_index("ix_usuarios_es_piloto", "usuarios", ["es_piloto"], unique=False)

    op.create_table(
        "reglas_puntos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("flujo", sa.String(length=20), nullable=False),
        sa.Column("tipo_generador", sa.String(length=30), nullable=False),
        sa.Column(
            "puntos_base_solicitud",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("10"),
            nullable=False,
        ),
        sa.Column(
            "puntos_por_kg",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("5"),
            nullable=False,
        ),
        sa.Column(
            "valor_referencia_kg_cop",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("80"),
            nullable=False,
        ),
        sa.Column("descripcion_regla", sa.Text(), nullable=True),
        sa.Column("activa", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "flujo IN ('ORGANICO', 'RECICLABLE')",
            name="ck_reglas_puntos_flujo_valido",
        ),
        sa.CheckConstraint(
            "tipo_generador IN ('HOGAR', 'UNIDAD_PRODUCTIVA')",
            name="ck_reglas_puntos_tipo_generador_valido",
        ),
        sa.CheckConstraint(
            "puntos_base_solicitud >= 0",
            name="ck_reglas_puntos_puntos_base_no_negativos",
        ),
        sa.CheckConstraint(
            "puntos_por_kg >= 0",
            name="ck_reglas_puntos_puntos_por_kg_no_negativos",
        ),
        sa.CheckConstraint(
            "valor_referencia_kg_cop >= 0",
            name="ck_reglas_puntos_valor_referencia_no_negativo",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reglas_puntos"),
    )
    op.create_index(
        "uq_reglas_puntos_activa_flujo_generador",
        "reglas_puntos",
        ["flujo", "tipo_generador"],
        unique=True,
        postgresql_where=sa.text("activa IS TRUE"),
    )

    op.create_table(
        "solicitudes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_publico", sa.String(length=20), nullable=False),
        sa.Column("solicitante_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("flujo", sa.String(length=20), nullable=False),
        sa.Column("subtipo_material", sa.String(length=100), nullable=True),
        sa.Column("cantidad_estimada_kg", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("cantidad_real_kg", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("disponibilidad_usuario", sa.String(length=120), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column(
            "estado",
            sa.String(length=25),
            server_default=sa.text("'RECIBIDA'"),
            nullable=False,
        ),
        sa.Column("coordinador_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("recolector_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("fecha_programada", sa.Date(), nullable=True),
        sa.Column("hora_programada", sa.Time(), nullable=True),
        sa.Column(
            "puntos_otorgados",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("regla_puntos_id", sa.Integer(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "flujo IN ('ORGANICO', 'RECICLABLE')",
            name="ck_solicitudes_flujo_valido",
        ),
        sa.CheckConstraint(
            "estado IN ('RECIBIDA', 'EN_REVISION', 'ASIGNADA', 'PROGRAMADA', 'RECOLECTADA', 'CANCELADA')",
            name="ck_solicitudes_estado_valido",
        ),
        sa.CheckConstraint(
            "cantidad_estimada_kg IS NULL OR cantidad_estimada_kg > 0",
            name="ck_solicitudes_cantidad_estimada_positiva",
        ),
        sa.CheckConstraint(
            "cantidad_real_kg IS NULL OR cantidad_real_kg > 0",
            name="ck_solicitudes_cantidad_real_positiva",
        ),
        sa.CheckConstraint(
            "puntos_otorgados >= 0",
            name="ck_solicitudes_puntos_otorgados_no_negativos",
        ),
        sa.CheckConstraint(
            "(estado = 'RECOLECTADA') OR (puntos_otorgados = 0 AND regla_puntos_id IS NULL)",
            name="ck_solicitudes_puntos_solo_en_recolectada",
        ),
        sa.CheckConstraint(
            "(estado <> 'ASIGNADA') OR (coordinador_id IS NOT NULL AND recolector_id IS NOT NULL)",
            name="ck_solicitudes_asignada_con_responsables",
        ),
        sa.CheckConstraint(
            "(estado <> 'PROGRAMADA') OR ("
            "coordinador_id IS NOT NULL AND recolector_id IS NOT NULL "
            "AND fecha_programada IS NOT NULL AND hora_programada IS NOT NULL"
            ")",
            name="ck_solicitudes_programada_completa",
        ),
        sa.ForeignKeyConstraint(
            ["coordinador_id"],
            ["usuarios.id"],
            name="fk_solicitudes_coordinador_id_usuarios",
        ),
        sa.ForeignKeyConstraint(
            ["recolector_id"],
            ["usuarios.id"],
            name="fk_solicitudes_recolector_id_usuarios",
        ),
        sa.ForeignKeyConstraint(
            ["regla_puntos_id"],
            ["reglas_puntos.id"],
            name="fk_solicitudes_regla_puntos_id_reglas_puntos",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["solicitante_id"],
            ["usuarios.id"],
            name="fk_solicitudes_solicitante_id_usuarios",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_solicitudes"),
        sa.UniqueConstraint("codigo_publico", name="uq_solicitudes_codigo_publico"),
    )
    op.create_index("ix_solicitudes_flujo_estado", "solicitudes", ["flujo", "estado"], unique=False)
    op.create_index(
        "ix_solicitudes_solicitante_creado",
        "solicitudes",
        ["solicitante_id", "creado_en"],
        unique=False,
    )
    op.create_index(
        "ix_solicitudes_recolector_estado",
        "solicitudes",
        ["recolector_id", "estado"],
        unique=False,
    )
    op.create_index("ix_solicitudes_coordinador_id", "solicitudes", ["coordinador_id"], unique=False)
    op.create_index(
        "ix_solicitudes_fecha_programada", "solicitudes", ["fecha_programada"], unique=False
    )
    op.create_index(
        "ix_solicitudes_regla_puntos_id", "solicitudes", ["regla_puntos_id"], unique=False
    )

    op.create_table(
        "historial_estados",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("solicitud_id", sa.Integer(), nullable=False),
        sa.Column("estado_anterior", sa.String(length=25), nullable=True),
        sa.Column("estado_nuevo", sa.String(length=25), nullable=False),
        sa.Column("cambiado_por", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("nota_operativa", sa.Text(), nullable=True),
        sa.Column(
            "fecha_cambio",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado_anterior IS NULL OR estado_anterior IN "
            "('RECIBIDA', 'EN_REVISION', 'ASIGNADA', 'PROGRAMADA', 'RECOLECTADA', 'CANCELADA')",
            name="ck_historial_estados_estado_anterior_valido",
        ),
        sa.CheckConstraint(
            "estado_nuevo IN "
            "('RECIBIDA', 'EN_REVISION', 'ASIGNADA', 'PROGRAMADA', 'RECOLECTADA', 'CANCELADA')",
            name="ck_historial_estados_estado_nuevo_valido",
        ),
        sa.ForeignKeyConstraint(
            ["cambiado_por"],
            ["usuarios.id"],
            name="fk_historial_estados_cambiado_por_usuarios",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["solicitud_id"],
            ["solicitudes.id"],
            name="fk_historial_estados_solicitud_id_solicitudes",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_historial_estados"),
    )
    op.create_index(
        "ix_historial_estados_solicitud_fecha",
        "historial_estados",
        ["solicitud_id", "fecha_cambio"],
        unique=False,
    )
    op.create_index(
        "ix_historial_estados_cambiado_por",
        "historial_estados",
        ["cambiado_por"],
        unique=False,
    )

    op.create_table(
        "mensajes_whatsapp",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("solicitud_id", sa.Integer(), nullable=True),
        sa.Column("telefono_remitente", sa.String(length=25), nullable=False),
        sa.Column("direccion", sa.String(length=15), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("intencion_ia", sa.String(length=50), nullable=True),
        sa.Column("procesado_por_ia", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "direccion IN ('ENTRANTE', 'SALIENTE')",
            name="ck_mensajes_whatsapp_direccion_valida",
        ),
        sa.ForeignKeyConstraint(
            ["solicitud_id"],
            ["solicitudes.id"],
            name="fk_mensajes_whatsapp_solicitud_id_solicitudes",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mensajes_whatsapp"),
    )
    op.create_index(
        "ix_mensajes_whatsapp_solicitud_id", "mensajes_whatsapp", ["solicitud_id"], unique=False
    )
    op.create_index(
        "ix_mensajes_whatsapp_telefono_creado",
        "mensajes_whatsapp",
        ["telefono_remitente", "creado_en"],
        unique=False,
    )

    op.create_table(
        "contenidos_educativos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("titulo", sa.String(length=150), nullable=False),
        sa.Column("categoria", sa.String(length=30), nullable=False),
        sa.Column("resumen", sa.Text(), nullable=False),
        sa.Column("que_si_va", sa.Text(), nullable=True),
        sa.Column("que_no_va", sa.Text(), nullable=True),
        sa.Column("orden", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("publicado", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint(
            "categoria IN ('ORGANICO', 'RECICLABLE', 'HUERTA', 'RUTAS')",
            name="ck_contenidos_educativos_categoria_valida",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_contenidos_educativos"),
        sa.UniqueConstraint(
            "categoria",
            "titulo",
            name="uq_contenidos_educativos_categoria_titulo",
        ),
    )
    op.create_index(
        "ix_contenidos_educativos_categoria_orden",
        "contenidos_educativos",
        ["categoria", "orden"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_contenidos_educativos_categoria_orden", table_name="contenidos_educativos")
    op.drop_table("contenidos_educativos")

    op.drop_index("ix_mensajes_whatsapp_telefono_creado", table_name="mensajes_whatsapp")
    op.drop_index("ix_mensajes_whatsapp_solicitud_id", table_name="mensajes_whatsapp")
    op.drop_table("mensajes_whatsapp")

    op.drop_index("ix_historial_estados_cambiado_por", table_name="historial_estados")
    op.drop_index("ix_historial_estados_solicitud_fecha", table_name="historial_estados")
    op.drop_table("historial_estados")

    op.drop_index("ix_solicitudes_regla_puntos_id", table_name="solicitudes")
    op.drop_index("ix_solicitudes_fecha_programada", table_name="solicitudes")
    op.drop_index("ix_solicitudes_coordinador_id", table_name="solicitudes")
    op.drop_index("ix_solicitudes_recolector_estado", table_name="solicitudes")
    op.drop_index("ix_solicitudes_solicitante_creado", table_name="solicitudes")
    op.drop_index("ix_solicitudes_flujo_estado", table_name="solicitudes")
    op.drop_table("solicitudes")

    op.drop_index("uq_reglas_puntos_activa_flujo_generador", table_name="reglas_puntos")
    op.drop_table("reglas_puntos")

    op.drop_index("ix_usuarios_es_piloto", table_name="usuarios")
    op.drop_index("ix_usuarios_rol_activo", table_name="usuarios")
    op.drop_table("usuarios")
