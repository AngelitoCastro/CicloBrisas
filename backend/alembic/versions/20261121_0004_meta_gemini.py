"""Soporte Meta Cloud API, cola de reintentos Gemini y consentimiento WhatsApp.

Revision ID: 20261121_0004
Revises: 20261121_0003
Create Date: 2026-11-21 02:10:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261121_0004"
down_revision: str | Sequence[str] | None = "20261121_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mensajes_whatsapp",
        sa.Column(
            "proveedor",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'TWILIO'"),
        ),
    )
    op.add_column(
        "mensajes_whatsapp",
        sa.Column("proximo_intento_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_mensajes_whatsapp_bandeja",
        "mensajes_whatsapp",
        ["proveedor", "direccion", "estado_envio", "proximo_intento_en"],
    )

    op.add_column(
        "avisos_whatsapp",
        sa.Column(
            "proveedor",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'AUTO'"),
        ),
    )
    op.add_column(
        "avisos_whatsapp",
        sa.Column("plantilla", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "avisos_whatsapp",
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "consentimientos_whatsapp",
        sa.Column(
            "usuario_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "aceptado",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "origen",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'WHATSAPP_ENTRANTE'"),
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE consentimientos_whatsapp ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("consentimientos_whatsapp")
    op.drop_column("avisos_whatsapp", "actualizado_en")
    op.drop_column("avisos_whatsapp", "plantilla")
    op.drop_column("avisos_whatsapp", "proveedor")
    op.drop_index("ix_mensajes_whatsapp_bandeja", table_name="mensajes_whatsapp")
    op.drop_column("mensajes_whatsapp", "proximo_intento_en")
    op.drop_column("mensajes_whatsapp", "proveedor")
