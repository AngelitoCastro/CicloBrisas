"""Prueba PostgreSQL del cierre concurrente con bloqueo de fila (requiere TEST_DATABASE_URL)."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import time, timedelta
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base, create_db_engine
from app.models import HistorialEstado, ReglaPuntos, Solicitud, Usuario
from app.schemas import CerrarSolicitud, ProgramarSolicitud, SolicitudCrear
from app.seed import run_seed
from app.services.errors import ErrorDominio
from app.services.solicitudes import cerrar_solicitud, crear_solicitud, programar_solicitud
from app.tiempo import hoy_bogota


def _url_postgres() -> str:
    url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("Define TEST_DATABASE_URL con una base PostgreSQL desechable.")
    if not url.startswith(("postgresql://", "postgresql+psycopg://")):
        pytest.skip("La prueba concurrente requiere PostgreSQL.")
    nombre = make_url(url).database or ""
    if "test" not in nombre.lower() and os.getenv("ALLOW_DESTRUCTIVE_DB_TESTS") != "1":
        pytest.skip(
            "El nombre de la base no contiene 'test'. "
            "Define ALLOW_DESTRUCTIVE_DB_TESTS=1 si es una base desechable."
        )
    return url


def test_cierre_concurrente_acredita_puntos_una_sola_vez():
    url = _url_postgres()
    engine = create_db_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
        Base.metadata.create_all(engine)
        fabrica = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )
        with fabrica() as session:
            run_seed(session, default_password="PruebaConcurrente2026!", env={})

            unidad = session.scalar(
                select(Usuario).where(Usuario.rol == "UNIDAD_PRODUCTIVA")
            )
            coordinador = session.scalar(
                select(Usuario).where(Usuario.rol == "COORD_HUERTEROS")
            )
            huertero = session.scalar(
                select(Usuario).where(Usuario.rol == "HUERTERO").order_by(Usuario.telefono)
            )
            assert unidad and coordinador and huertero

            solicitud = crear_solicitud(
                session,
                unidad,
                SolicitudCrear(
                    flujo="ORGANICO",
                    cantidad_estimada_kg=Decimal("10.00"),
                    disponibilidad_usuario="Mañana",
                ),
            )
            programada = programar_solicitud(
                session,
                coordinador,
                solicitud.id,
                ProgramarSolicitud(
                    recolector_id=huertero.id,
                    fecha_programada=hoy_bogota() + timedelta(days=1),
                    hora_programada=time(9, 0),
                ),
            )
            solicitud_id = programada.id
            solicitante_id = unidad.id
            huertero_id = huertero.id

        barrera = Barrier(2)

        def intentar_cierre(actor_id):
            with fabrica() as session:
                actor = session.get(Usuario, actor_id)
                assert actor is not None
                barrera.wait(timeout=10)
                try:
                    resultado = cerrar_solicitud(
                        session,
                        actor,
                        solicitud_id,
                        CerrarSolicitud(cantidad_real_kg=Decimal("10.00")),
                    )
                    return ("ok", float(resultado.puntos_otorgados))
                except ErrorDominio as exc:
                    return (exc.codigo, None)

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(intentar_cierre, [huertero_id, huertero_id]))

        codigos = sorted(resultado[0] for resultado in resultados)
        assert codigos == ["SOLICITUD_YA_CERRADA", "ok"], resultados
        exitos = [resultado for resultado in resultados if resultado[0] == "ok"]
        assert exitos[0][1] == 75.0

        with fabrica() as session:
            solicitud_db = session.get(Solicitud, solicitud_id)
            solicitante_db = session.get(Usuario, solicitante_id)
            assert solicitud_db is not None and solicitante_db is not None
            assert solicitud_db.estado == "RECOLECTADA"
            assert solicitud_db.puntos_otorgados == Decimal("75.00")
            assert solicitante_db.puntos_acumulados == Decimal("75.00")

            cierres = session.scalar(
                select(func.count(HistorialEstado.id)).where(
                    HistorialEstado.solicitud_id == solicitud_id,
                    HistorialEstado.estado_nuevo == "RECOLECTADA",
                )
            )
            assert cierres == 1
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
        engine.dispose()
