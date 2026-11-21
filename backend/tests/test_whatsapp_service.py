"""Pruebas del servicio de cierre compartido con el webhook de WhatsApp."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import Solicitud, Usuario
from app.schemas import CerrarSolicitud
from app.services.errors import Conflicto, NoEncontrado, PermisoDenegado
from app.services.solicitudes import (
    buscar_solicitud_por_codigo,
    cerrar_solicitud_por_codigo,
)
from tests.conftest import fecha_futura, usuario_por_rol


def test_cierre_por_codigo_es_idempotente_y_valida_actor(client, db, login, telefono):
    headers_hogar = login(telefono["HOGAR"])
    creada = client.post(
        "/api/solicitudes",
        json={
            "flujo": "ORGANICO",
            "cantidad_estimada_kg": 8,
            "disponibilidad_usuario": "Mañana",
        },
        headers=headers_hogar,
    ).json()
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])
    assert (
        client.patch(
            f"/api/solicitudes/{creada['id']}/programar",
            json={
                "recolector_id": str(huertero.id),
                "fecha_programada": fecha_futura().isoformat(),
                "hora_programada": "11:00",
            },
            headers=login(telefono["COORD_HUERTEROS"]),
        ).status_code
        == 200
    )

    db.expire_all()
    encontrada = buscar_solicitud_por_codigo(db, creada["codigo_publico"].lower())
    assert encontrada.id == creada["id"]

    with pytest.raises(NoEncontrado):
        buscar_solicitud_por_codigo(db, "ECO-2099-999999")

    propietario = usuario_por_rol(db, "HOGAR", telefono["HOGAR"])
    with pytest.raises(PermisoDenegado):
        cerrar_solicitud_por_codigo(
            db,
            propietario,
            creada["codigo_publico"],
            CerrarSolicitud(cantidad_real_kg=8),
        )

    actor = db.get(Usuario, huertero.id)
    assert actor is not None
    resultado = cerrar_solicitud_por_codigo(
        db,
        actor,
        creada["codigo_publico"],
        CerrarSolicitud(cantidad_real_kg=8, nota_operativa="Mensaje LISTO de WhatsApp"),
    )
    assert resultado.solicitud.estado == "RECOLECTADA"
    assert resultado.puntos_otorgados == 50.0  # 10 base + 5 * 8 kg para hogar orgánico.

    with pytest.raises(Conflicto) as error:
        cerrar_solicitud_por_codigo(
            db,
            actor,
            creada["codigo_publico"],
            CerrarSolicitud(cantidad_real_kg=8),
        )
    assert error.value.codigo == "SOLICITUD_YA_CERRADA"

    db.expire_all()
    solicitud = db.scalar(select(Solicitud).where(Solicitud.id == creada["id"]))
    propietario_db = db.get(Usuario, propietario.id)
    assert solicitud is not None and propietario_db is not None
    assert solicitud.puntos_otorgados == 50.0
    assert propietario_db.puntos_acumulados == 50.0
