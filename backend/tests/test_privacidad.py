"""Pruebas del filtro de datos personales en los serializadores (RN-07)."""

from __future__ import annotations

from sqlalchemy import select

from app.models import Solicitud
from app.presenters import construir_solicitud_response
from tests.conftest import fecha_futura, usuario_por_rol


def _solicitud_programada(client, db, login, telefono):
    headers_up = login(telefono["UNIDAD_PRODUCTIVA"])
    creada = client.post(
        "/api/solicitudes",
        json={
            "flujo": "ORGANICO",
            "cantidad_estimada_kg": 5,
            "disponibilidad_usuario": "Tarde",
        },
        headers=headers_up,
    ).json()
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])
    programada = client.patch(
        f"/api/solicitudes/{creada['id']}/programar",
        json={
            "recolector_id": str(huertero.id),
            "fecha_programada": fecha_futura().isoformat(),
            "hora_programada": "10:00",
        },
        headers=login(telefono["COORD_HUERTEROS"]),
    )
    assert programada.status_code == 200, programada.text
    db.expire_all()
    solicitud = db.scalar(select(Solicitud).where(Solicitud.id == creada["id"]))
    assert solicitud is not None
    return solicitud, huertero


def test_contacto_visible_solo_para_perfiles_autorizados(client, db, login, telefono):
    solicitud, huertero = _solicitud_programada(client, db, login, telefono)

    propietario = usuario_por_rol(
        db, "UNIDAD_PRODUCTIVA", telefono["UNIDAD_PRODUCTIVA"]
    )
    coordinador = usuario_por_rol(db, "COORD_HUERTEROS", telefono["COORD_HUERTEROS"])
    admin = usuario_por_rol(db, "ADMIN", telefono["ADMIN"])
    externo_ajeno = usuario_por_rol(db, "HOGAR", telefono["HOGAR_GENERAL"])
    coordinador_otro_flujo = usuario_por_rol(
        db,
        "COORD_RECICLADORES",
        telefono["COORD_RECICLADORES"],
    )

    for observador in (propietario, coordinador, admin, huertero):
        respuesta = construir_solicitud_response(solicitud, observador)
        assert respuesta.solicitante.telefono is not None
        assert respuesta.solicitante.direccion is not None
        assert respuesta.solicitante.sector_manzana is not None

    for observador in (externo_ajeno, coordinador_otro_flujo):
        respuesta = construir_solicitud_response(solicitud, observador)
        assert respuesta.solicitante.telefono is None
        assert respuesta.solicitante.direccion is None
        assert respuesta.solicitante.sector_manzana is None

    forzado = construir_solicitud_response(
        solicitud, propietario, ocultar_contacto=True
    )
    assert forzado.solicitante.telefono is None
    assert forzado.solicitante.direccion is None

    # El nombre y el rol del solicitante sí son necesarios para operar.
    assert respuesta.solicitante.nombre
    assert respuesta.solicitante.rol == "UNIDAD_PRODUCTIVA"
