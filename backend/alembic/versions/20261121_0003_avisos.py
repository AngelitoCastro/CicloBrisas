"""Bandeja transaccional de avisos por destinatario."""
import sqlalchemy as sa
from alembic import op

revision = "20261121_0003"
down_revision = "20261120_0002"
branch_labels = depends_on = None


def upgrade():
    op.create_table("avisos_whatsapp",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("historial_id", sa.Integer, sa.ForeignKey("historial_estados.id"), nullable=False),
        sa.Column("solicitud_id", sa.Integer, sa.ForeignKey("solicitudes.id"), nullable=False),
        sa.Column("evento", sa.String(20), nullable=False),
        sa.Column("destinatario", sa.String(20), nullable=False),
        sa.Column("telefono", sa.String(25), nullable=False),
        sa.Column("contenido", sa.Text, nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("intento", sa.String(32), nullable=False, unique=True),
        sa.Column("sid", sa.String(100), unique=True),
        sa.Column("error", sa.String(80)),
        sa.UniqueConstraint("historial_id", "destinatario"))
    for col in ("solicitud_id", "estado"):
        op.create_index(f"ix_avisos_whatsapp_{col}", "avisos_whatsapp", [col])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE avisos_whatsapp ENABLE ROW LEVEL SECURITY")


def downgrade():
    op.drop_table("avisos_whatsapp")
