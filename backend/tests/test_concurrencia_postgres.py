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
from app.models import (
    AvisoWhatsApp,
    HistorialEstado,
    MensajeWhatsapp,
    Solicitud,
    Usuario,
)
from app.schemas import CerrarSolicitud, ProgramarSolicitud, SolicitudCrear
from app.schemas_whatsapp import ExtraccionSolicitudMeta
from app.seed import run_seed
from app.services.errors import ErrorDominio
from app.services.solicitudes import (
    cerrar_solicitud,
    crear_solicitud,
    programar_solicitud,
)
from app.tiempo import hoy_bogota
from app.whatsapp.meta import (
    MensajeMetaEntrante,
    procesar_entrante_meta_uno,
    registrar_lote_meta,
)


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
                select(Usuario)
                .where(Usuario.rol == "HUERTERO")
                .order_by(Usuario.telefono)
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


def test_postgres_evento_meta_duplicado_y_programacion_repetida(monkeypatch):
    """Valida en PostgreSQL que duplicados concurrentes crean una solicitud y repetir programación genera un aviso por destinatario."""
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
            hogar = session.scalar(
                select(Usuario).where(Usuario.telefono == "+573000000108")
            )
            coordinador = session.scalar(
                select(Usuario).where(Usuario.rol == "COORD_RECICLADORES")
            )
            reciclador = session.scalar(
                select(Usuario)
                .where(Usuario.rol == "RECICLADOR")
                .order_by(Usuario.telefono)
            )
            assert hogar and coordinador and reciclador
            telefono_hogar = hogar.telefono
            coord_id = coordinador.id
            reciclador_id = reciclador.id

        # 1. Duplicados concurrentes del mismo wamid en PostgreSQL
        barrera_webhook = Barrier(4)

        def registrar_concurrente(_idx: int):
            with fabrica() as session:
                barrera_webhook.wait(timeout=10)
                return registrar_lote_meta(
                    session,
                    [
                        MensajeMetaEntrante(
                            wamid="wamid.pg.concurrente.1",
                            telefono=telefono_hogar,
                            texto="Tengo 2500 gramos de cartón",
                        )
                    ],
                    [],
                )

        with ThreadPoolExecutor(max_workers=4) as executor:
            lotes = list(executor.map(registrar_concurrente, range(4)))

        assert sum(r.guardados for r in lotes) == 1
        assert sum(r.duplicados for r in lotes) == 3

        # 2. Workers concurrentes con FOR UPDATE SKIP LOCKED crean exactamente una solicitud
        monkeypatch.setattr(
            "app.whatsapp.meta.extraer_solicitud_gemini",
            lambda _texto: ExtraccionSolicitudMeta(
                flujo="RECICLABLE",
                material="Cartón",
                cantidad=2500,
                unidad="G",
                referencia_general="Mañana en la tarde",
                es_solicitud=True,
            ),
        )
        barrera_worker = Barrier(3)

        def correr_worker(_idx: int) -> bool:
            barrera_worker.wait(timeout=10)
            return procesar_entrante_meta_uno(fabrica)

        with ThreadPoolExecutor(max_workers=3) as executor:
            procesados = list(executor.map(correr_worker, range(3)))

        assert procesados.count(True) == 1

        with fabrica() as session:
            solicitudes = session.scalars(select(Solicitud)).all()
            assert len(solicitudes) == 1
            solicitud = solicitudes[0]
            assert solicitud.cantidad_estimada_kg == Decimal("2.50")
            mensajes = session.scalars(select(MensajeWhatsapp)).all()
            assert len(mensajes) == 1
            assert mensajes[0].solicitud_id == solicitud.id
            solicitud_id = solicitud.id

        # 3. Repetir programación concurrentemente genera exactamente un aviso por destinatario
        barrera_prog = Barrier(3)
        fecha = hoy_bogota() + timedelta(days=1)

        def programar_concurrente(_idx: int) -> str:
            with fabrica() as session:
                coord = session.get(Usuario, coord_id)
                assert coord is not None
                barrera_prog.wait(timeout=10)
                programar_solicitud(
                    session,
                    coord,
                    solicitud_id,
                    ProgramarSolicitud(
                        recolector_id=reciclador_id,
                        fecha_programada=fecha,
                        hora_programada=time(10, 0),
                        subtipo_material="Cartón seco",
                        cantidad_estimada_kg=Decimal("3.00"),
                        disponibilidad_usuario="Portería principal",
                        observaciones="Llevar costales",
                    ),
                )
                return "ok"

        with ThreadPoolExecutor(max_workers=3) as executor:
            assert list(executor.map(programar_concurrente, range(3))) == [
                "ok",
                "ok",
                "ok",
            ]

        with fabrica() as session:
            avisos = session.scalars(
                select(AvisoWhatsApp).where(AvisoWhatsApp.solicitud_id == solicitud_id)
            ).all()
            assert len(avisos) == 2
            assert sorted(a.destinatario for a in avisos) == [
                "RECOLECTOR",
                "SOLICITANTE",
            ]
            transiciones = session.scalar(
                select(func.count(HistorialEstado.id)).where(
                    HistorialEstado.solicitud_id == solicitud_id,
                    HistorialEstado.estado_nuevo == "PROGRAMADA",
                )
            )
            assert transiciones == 1
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
        engine.dispose()
