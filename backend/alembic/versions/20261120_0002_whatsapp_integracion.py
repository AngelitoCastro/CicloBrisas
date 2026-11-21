"""Columnas de integración WhatsApp e IA en mensajes_whatsapp.

Revision ID: 20261120_0002
Revises: 20261120_0001
Create Date: 2026-11-20 12:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261120_0002"
down_revision: str | Sequence[str] | None = "20261120_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    ("wa_message_id", sa.String(length=100)),
    ("estado_envio", sa.String(length=20)),
    ("intentos", sa.Integer()),
    ("error", sa.Text()),
    ("procesado_en", sa.DateTime(timezone=True)),
    ("estado_conversacion", sa.String(length=30)),
    ("borrador_json", sa.Text()),
    ("media_id", sa.String(length=100)),
    ("media_tipo", sa.String(length=20)),
    ("media_mime", sa.String(length=100)),
    ("texto_extraido", sa.Text()),
)


def upgrade() -> None:
    for nombre, tipo in _COLUMNS:
        nullable = nombre not in {"estado_envio", "intentos"}
        server_default = None
        if nombre == "estado_envio":
            server_default = sa.text("'PENDIENTE'")
        elif nombre == "intentos":
            server_default = sa.text("0")
        op.add_column(
            "mensajes_whatsapp",
            sa.Column(nombre, tipo, server_default=server_default, nullable=nullable),
        )
    op.create_index(
        "uq_mensajes_whatsapp_wa_message_id",
        "mensajes_whatsapp",
        ["wa_message_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_mensajes_whatsapp_wa_message_id", table_name="mensajes_whatsapp")
    for nombre, _ in reversed(_COLUMNS):
        op.drop_column("mensajes_whatsapp", nombre)
