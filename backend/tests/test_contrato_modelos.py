"""Pruebas del contrato compartido de modelos ORM y sesiones."""

from __future__ import annotations

import inspect

from sqlalchemy import String
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.models import HistorialEstado, ReglaPuntos, Solicitud, Usuario


def test_modelos_exportan_atributos_del_plan():
    assert set(Usuario.__table__.columns.keys()) == {
        "id",
        "nombre",
        "telefono",
        "password_hash",
        "rol",
        "direccion",
        "sector_manzana",
        "es_piloto",
        "puntos_acumulados",
        "activo",
        "creado_en",
    }
    assert set(ReglaPuntos.__table__.columns.keys()) == {
        "id",
        "flujo",
        "tipo_generador",
        "puntos_base_solicitud",
        "puntos_por_kg",
        "valor_referencia_kg_cop",
        "descripcion_regla",
        "activa",
        "actualizado_en",
    }
    assert set(Solicitud.__table__.columns.keys()) == {
        "id",
        "codigo_publico",
        "solicitante_id",
        "flujo",
        "subtipo_material",
        "cantidad_estimada_kg",
        "cantidad_real_kg",
        "disponibilidad_usuario",
        "observaciones",
        "estado",
        "coordinador_id",
        "recolector_id",
        "fecha_programada",
        "hora_programada",
        "puntos_otorgados",
        "regla_puntos_id",
        "creado_en",
        "actualizado_en",
    }
    assert set(HistorialEstado.__table__.columns.keys()) == {
        "id",
        "solicitud_id",
        "estado_anterior",
        "estado_nuevo",
        "cambiado_por",
        "nota_operativa",
        "fecha_cambio",
    }


def test_password_hash_bcrypt_y_regla_puntos_nullable():
    columna_password = Usuario.__table__.c.password_hash
    assert isinstance(columna_password.type, String)
    assert columna_password.nullable is False

    columna_regla = Solicitud.__table__.c.regla_puntos_id
    assert columna_regla.nullable is True
    assert len(columna_regla.foreign_keys) == 1
    foreign_key = next(iter(columna_regla.foreign_keys))
    assert foreign_key.column.table.name == "reglas_puntos"


def test_get_db_entrega_sesion_sincrona_y_punto_de_entrada():
    assert inspect.isgeneratorfunction(get_db)
    generador = get_db()
    sesion = next(generador)
    assert isinstance(sesion, Session)
    try:
        next(generador)
    except StopIteration:
        pass
    else:  # pragma: no cover - contrato de cierre
        raise AssertionError("get_db debe cerrar la sesión al finalizar.")
    assert app.title == "EcoConecta API"
