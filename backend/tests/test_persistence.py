"""Pruebas de persistencia, migraciones Alembic, semilla idempotente y restricciones SQL."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, time
from decimal import Decimal
from pathlib import Path

import bcrypt
import pytest
from alembic.config import Config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from alembic import command
from app.db import (
    SessionLocal,
    create_db_engine,
    engine,
    get_db,
    normalize_database_url,
)
from app.fixtures import (
    CONTENIDOS_EDUCATIVOS_INICIALES,
    REGLAS_PUNTOS_INICIALES,
    USUARIOS_PILOTO,
)
from app.models import (
    ROLES_USUARIO,
    ContenidoEducativo,
    HistorialEstado,
    MensajeWhatsapp,
    ReglaPuntos,
    Solicitud,
    Usuario,
)
from app.seed import hash_password, run_seed

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_SEED_PASSWORD = os.getenv("TEST_SEED_PASSWORD", "PruebaSemilla2026!")


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("Define TEST_DATABASE_URL con una base PostgreSQL desechable.")
    if os.getenv("ALLOW_DESTRUCTIVE_DB_TESTS", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "si",
        "sí",
    }:
        pytest.skip("Define ALLOW_DESTRUCTIVE_DB_TESTS=1 para pruebas destructivas.")
    url = normalize_database_url(url)
    if not url.startswith("postgresql+psycopg://"):
        pytest.skip("Las pruebas de persistencia requieren PostgreSQL con psycopg 3.")
    return url


@pytest.fixture(scope="module")
def database_url() -> str:
    url = _test_database_url()
    test_engine = create_db_engine(url)
    try:
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:  # pragma: no cover - entorno sin Postgres activo
        pytest.fail(f"No fue posible conectar a PostgreSQL ({url}): {exc}")
    finally:
        test_engine.dispose()
    return url


@pytest.fixture()
def migrated_db(database_url: str) -> str:
    """Reinicia el esquema desde base hasta head antes de cada prueba."""
    engine.dispose()
    cfg = _alembic_config(database_url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield database_url
    engine.dispose()


def test_alembic_upgrade_downgrade_upgrade_reproducible(database_url: str) -> None:
    """Verifica que las migraciones crean, revierten y recrean tablas e índices esperados."""
    engine.dispose()
    cfg = _alembic_config(database_url)

    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "usuarios",
        "reglas_puntos",
        "solicitudes",
        "historial_estados",
        "mensajes_whatsapp",
        "contenidos_educativos",
        "alembic_version",
    }.issubset(tables)

    usuario_cols = {col["name"] for col in inspector.get_columns("usuarios")}
    assert "password_hash" in usuario_cols
    assert "es_piloto" in usuario_cols

    solicitud_cols = {col["name"] for col in inspector.get_columns("solicitudes")}
    assert "regla_puntos_id" in solicitud_cols

    regla_indexes = {idx["name"] for idx in inspector.get_indexes("reglas_puntos")}
    assert "uq_reglas_puntos_activa_flujo_generador" in regla_indexes

    solicitud_indexes = {idx["name"] for idx in inspector.get_indexes("solicitudes")}
    assert {
        "ix_solicitudes_flujo_estado",
        "ix_solicitudes_solicitante_creado",
        "ix_solicitudes_recolector_estado",
        "ix_solicitudes_coordinador_id",
        "ix_solicitudes_fecha_programada",
        "ix_solicitudes_regla_puntos_id",
    }.issubset(solicitud_indexes)

    # Reversibilidad y reaplicación limpia
    command.downgrade(cfg, "base")
    remaining = set(inspect(engine).get_table_names())
    assert "usuarios" not in remaining
    assert "solicitudes" not in remaining

    command.upgrade(cfg, "head")
    assert "usuarios" in set(inspect(engine).get_table_names())


def test_seed_is_idempotent_on_two_runs(migrated_db: str) -> None:
    """Ejecutar la semilla dos veces no duplica registros ni borra puntos acumulados."""
    with SessionLocal() as session:
        first = run_seed(session, default_password=TEST_SEED_PASSWORD, env={})
        assert first.usuarios_creados == len(USUARIOS_PILOTO)
        assert first.reglas_creadas == len(REGLAS_PUNTOS_INICIALES)
        assert first.contenidos_creados == len(CONTENIDOS_EDUCATIVOS_INICIALES)

        # Simular acumulación de puntos y ajuste administrativo de regla antes de la segunda carga
        hogar_piloto = session.scalar(
            select(Usuario).where(Usuario.telefono == "+573000000108")
        )
        assert hogar_piloto is not None
        assert bcrypt.checkpw(
            TEST_SEED_PASSWORD.encode("utf-8"),
            hogar_piloto.password_hash.encode("utf-8"),
        )
        hogar_piloto.puntos_acumulados = Decimal("42.50")

        regla_org_hogar = session.scalar(
            select(ReglaPuntos).where(
                ReglaPuntos.flujo == "ORGANICO",
                ReglaPuntos.tipo_generador == "HOGAR",
                ReglaPuntos.activa.is_(True),
            )
        )
        assert regla_org_hogar is not None
        regla_org_hogar.puntos_por_kg = Decimal("7.50")
        session.commit()

        # Segunda ejecución de la semilla
        second = run_seed(session, default_password=TEST_SEED_PASSWORD, env={})
        assert second.usuarios_creados == 0
        assert second.usuarios_actualizados == len(USUARIOS_PILOTO)
        assert second.reglas_creadas == 0
        assert second.reglas_existentes == len(REGLAS_PUNTOS_INICIALES)
        assert second.contenidos_creados == 0

        assert session.scalar(select(func.count(Usuario.id))) == len(USUARIOS_PILOTO)
        assert session.scalar(select(func.count(ReglaPuntos.id))) == len(
            REGLAS_PUNTOS_INICIALES
        )
        assert session.scalar(select(func.count(ContenidoEducativo.id))) == len(
            CONTENIDOS_EDUCATIVOS_INICIALES
        )

        # Todos los roles y pilotos presentes
        roles_cargados = set(session.scalars(select(Usuario.rol)).all())
        assert roles_cargados == set(ROLES_USUARIO)
        pilotos = session.scalars(
            select(Usuario).where(Usuario.es_piloto.is_(True))
        ).all()
        assert len(pilotos) == 2

        # Preserva puntos acumulados y ajuste de regla activa
        session.refresh(hogar_piloto)
        session.refresh(regla_org_hogar)
        assert hogar_piloto.puntos_acumulados == Decimal("42.50")
        assert regla_org_hogar.puntos_por_kg == Decimal("7.50")


def test_seed_cli_runs_twice_successfully(migrated_db: str) -> None:
    """Verifica que tanto `python -m app.seed` como `python app/seed.py` corren dos veces sin duplicar."""
    env = os.environ.copy()
    env["DATABASE_URL"] = migrated_db
    env["SEED_DEFAULT_PASSWORD"] = TEST_SEED_PASSWORD

    run_module = subprocess.run(
        [sys.executable, "-m", "app.seed"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run_module.returncode == 0, run_module.stderr

    run_script = subprocess.run(
        [sys.executable, "app/seed.py"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run_script.returncode == 0, run_script.stderr

    with SessionLocal() as session:
        assert session.scalar(select(func.count(Usuario.id))) == len(USUARIOS_PILOTO)
        assert session.scalar(select(func.count(ReglaPuntos.id))) == len(
            REGLAS_PUNTOS_INICIALES
        )
        assert session.scalar(select(func.count(ContenidoEducativo.id))) == len(
            CONTENIDOS_EDUCATIVOS_INICIALES
        )


def test_get_db_lifecycle_and_constraints(migrated_db: str) -> None:
    """Valida get_db(), relaciones ORM y constraints críticos de dominio en PostgreSQL."""
    db_gen = get_db()
    session = next(db_gen)
    try:
        run_seed(session, default_password=TEST_SEED_PASSWORD, env={})

        unidad = session.scalar(
            select(Usuario).where(Usuario.rol == "UNIDAD_PRODUCTIVA")
        )
        coord_h = session.scalar(
            select(Usuario).where(Usuario.rol == "COORD_HUERTEROS")
        )
        huertero = session.scalar(select(Usuario).where(Usuario.rol == "HUERTERO"))
        regla_org_up = session.scalar(
            select(ReglaPuntos).where(
                ReglaPuntos.flujo == "ORGANICO",
                ReglaPuntos.tipo_generador == "UNIDAD_PRODUCTIVA",
                ReglaPuntos.activa.is_(True),
            )
        )
        assert unidad and coord_h and huertero and regla_org_up

        # 1. Flujo válido RECIBIDA -> PROGRAMADA -> RECOLECTADA con historial y regla_puntos_id
        solicitud = Solicitud(
            codigo_publico="ECO-2026-001",
            solicitante_id=unidad.id,
            flujo="ORGANICO",
            subtipo_material="Cáscaras y vegetales",
            cantidad_estimada_kg=Decimal("12.00"),
            disponibilidad_usuario="Lunes a viernes 8:00 a.m. - 11:00 a.m.",
            estado="RECIBIDA",
        )
        session.add(solicitud)
        session.flush()

        session.add(
            HistorialEstado(
                solicitud_id=solicitud.id,
                estado_anterior=None,
                estado_nuevo="RECIBIDA",
                cambiado_por=unidad.id,
                nota_operativa="Solicitud inicial piloto",
            )
        )

        solicitud.estado = "PROGRAMADA"
        solicitud.coordinador_id = coord_h.id
        solicitud.recolector_id = huertero.id
        solicitud.fecha_programada = date(2026, 11, 21)
        solicitud.hora_programada = time(9, 30)
        session.add(
            HistorialEstado(
                solicitud_id=solicitud.id,
                estado_anterior="RECIBIDA",
                estado_nuevo="PROGRAMADA",
                cambiado_por=coord_h.id,
                nota_operativa="Programada con huertero",
            )
        )
        session.flush()

        solicitud.estado = "RECOLECTADA"
        solicitud.cantidad_real_kg = Decimal("10.00")
        solicitud.regla_puntos_id = regla_org_up.id
        solicitud.puntos_otorgados = (
            regla_org_up.puntos_base_solicitud
            + regla_org_up.puntos_por_kg * Decimal("10.00")
        )
        session.add(
            HistorialEstado(
                solicitud_id=solicitud.id,
                estado_anterior="PROGRAMADA",
                estado_nuevo="RECOLECTADA",
                cambiado_por=huertero.id,
                nota_operativa="Recolección confirmada en campo",
            )
        )
        session.add(
            MensajeWhatsapp(
                solicitud_id=solicitud.id,
                telefono_remitente=huertero.telefono,
                direccion="ENTRANTE",
                contenido="LISTO ECO-2026-001 10",
                intencion_ia="CIERRE_RECOLECCION",
                procesado_por_ia=True,
            )
        )
        session.commit()

        session.refresh(solicitud)
        assert solicitud.regla_puntos_id == regla_org_up.id
        assert solicitud.puntos_otorgados == Decimal("75.00")
        assert len(solicitud.historial_estados) == 3

        # 2. RN-02 / RN-03: rechazar PROGRAMADA incompleta
        with pytest.raises(IntegrityError), session.begin_nested():
            session.add(
                Solicitud(
                    codigo_publico="ECO-2026-ERR-PROG",
                    solicitante_id=unidad.id,
                    flujo="ORGANICO",
                    disponibilidad_usuario="Mañana",
                    estado="PROGRAMADA",
                    coordinador_id=coord_h.id,
                    recolector_id=huertero.id,
                    fecha_programada=None,
                    hora_programada=None,
                )
            )
            session.flush()

        # 3. RN-05: rechazar puntos acreditados antes de RECOLECTADA
        with pytest.raises(IntegrityError), session.begin_nested():
            session.add(
                Solicitud(
                    codigo_publico="ECO-2026-ERR-PTS",
                    solicitante_id=unidad.id,
                    flujo="ORGANICO",
                    disponibilidad_usuario="Mañana",
                    estado="RECIBIDA",
                    puntos_otorgados=Decimal("10.00"),
                )
            )
            session.flush()

        # 4. Rechazar peso no positivo
        with pytest.raises(IntegrityError), session.begin_nested():
            session.add(
                Solicitud(
                    codigo_publico="ECO-2026-ERR-KG",
                    solicitante_id=unidad.id,
                    flujo="ORGANICO",
                    disponibilidad_usuario="Mañana",
                    cantidad_estimada_kg=Decimal("0.00"),
                )
            )
            session.flush()

        # 5. Índice único parcial: impedir segunda regla activa para (ORGANICO, HOGAR),
        #    pero permitir guardar una regla histórica inactiva.
        with pytest.raises(IntegrityError), session.begin_nested():
            session.add(
                ReglaPuntos(
                    flujo="ORGANICO",
                    tipo_generador="HOGAR",
                    puntos_base_solicitud=Decimal("12.00"),
                    puntos_por_kg=Decimal("6.00"),
                    valor_referencia_kg_cop=Decimal("85.00"),
                    activa=True,
                )
            )
            session.flush()

        with session.begin_nested():
            session.add(
                ReglaPuntos(
                    flujo="ORGANICO",
                    tipo_generador="HOGAR",
                    puntos_base_solicitud=Decimal("8.00"),
                    puntos_por_kg=Decimal("4.00"),
                    valor_referencia_kg_cop=Decimal("70.00"),
                    activa=False,
                )
            )
            session.flush()

        # 6. Rol inválido en Usuario
        with pytest.raises(IntegrityError), session.begin_nested():
            session.add(
                Usuario(
                    nombre="Rol Invalido",
                    telefono="+573009999999",
                    password_hash=hash_password(TEST_SEED_PASSWORD),
                    rol="INVITADO",
                )
            )
            session.flush()
    finally:
        with pytest.raises(StopIteration):
            next(db_gen)
