"""Fixtures de pruebas HTTP con SQLite aislado y datos semilla ficticios."""

from __future__ import annotations

import os
import shutil
from datetime import time, timedelta
from pathlib import Path

# Debe configurarse antes de importar app.main, que exige SECRET_KEY al arrancar.
if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "clave-de-pruebas-ecoconecta-2026-0123456789"
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("ENTORNO", "test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import Usuario
from app.seed import run_seed
from app.tiempo import hoy_bogota

TEST_PASSWORD = "PruebaHTTP2026!"
_TELEFONOS = {
    "ADMIN": "+573000000100",
    "COORD_HUERTEROS": "+573000000101",
    "HUERTERO": "+573000000102",
    "COORD_RECICLADORES": "+573000000104",
    "RECICLADOR": "+573000000105",
    "UNIDAD_PRODUCTIVA": "+573000000107",
    "HOGAR": "+573000000108",
    "HOGAR_GENERAL": "+573000000109",
}


def _crear_engine(ruta: Path):
    engine = create_engine(
        f"sqlite+pysqlite:///{ruta}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _activar_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture(scope="session")
def plantilla_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    ruta = tmp_path_factory.mktemp("plantilla") / "ecoconecta_plantilla.db"
    engine = _crear_engine(ruta)
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    with fabrica() as session:
        resumen = run_seed(session, default_password=TEST_PASSWORD, env={})
        assert resumen.usuarios_creados == 10
    engine.dispose()
    return ruta


@pytest.fixture()
def engine(plantilla_db: Path, tmp_path: Path):
    ruta = tmp_path / "ecoconecta_test.db"
    shutil.copy2(plantilla_db, ruta)
    engine = _crear_engine(ruta)
    yield engine
    engine.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


@pytest.fixture()
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


_TOKEN_CACHE: dict[str, str] = {}


@pytest.fixture()
def login(client):
    def _login(telefono: str, password: str = TEST_PASSWORD) -> dict[str, str]:
        if telefono not in _TOKEN_CACHE:
            respuesta = client.post(
                "/api/auth/login",
                json={"telefono": telefono, "password": password},
            )
            assert respuesta.status_code == 200, respuesta.text
            _TOKEN_CACHE[telefono] = respuesta.json()["access_token"]
        return {"Authorization": f"Bearer {_TOKEN_CACHE[telefono]}"}

    return _login


@pytest.fixture()
def telefono() -> dict[str, str]:
    return dict(_TELEFONOS)


def usuario_por_rol(db: Session, rol: str, telefono: str | None = None) -> Usuario:
    stmt = select(Usuario).where(Usuario.rol == rol).order_by(Usuario.telefono.asc())
    if telefono is not None:
        stmt = select(Usuario).where(Usuario.telefono == telefono)
    usuario = db.scalar(stmt)
    assert usuario is not None, f"No existe usuario semilla con rol {rol}."
    return usuario


def fecha_futura(dias: int = 1):
    return hoy_bogota() + timedelta(days=dias)


HORA_PROGRAMADA = time(9, 30)
