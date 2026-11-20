"""Pruebas de operaciones administrativas: reglas de puntos y modo piloto."""

from __future__ import annotations

from app.models import Usuario
from tests.conftest import usuario_por_rol


def test_solo_admin_puede_gestionar_reglas_y_piloto(client, db, login, telefono):
    headers_externo = login(telefono["HOGAR"])
    headers_coord = login(telefono["COORD_HUERTEROS"])

    for headers in (headers_externo, headers_coord):
        assert client.get("/api/admin/reglas-puntos", headers=headers).status_code == 403
        assert client.get("/api/admin/usuarios", headers=headers).status_code == 403
        assert client.post(
            "/api/admin/reglas-puntos",
            json={
                "flujo": "ORGANICO",
                "tipo_generador": "HOGAR",
                "puntos_base_solicitud": 1,
                "puntos_por_kg": 1,
                "valor_referencia_kg_cop": 1,
            },
            headers=headers,
        ).status_code == 403

    usuario = usuario_por_rol(db, "HOGAR", telefono["HOGAR"])
    respuesta = client.patch(
        f"/api/admin/usuarios/{usuario.id}/piloto",
        json={"es_piloto": False},
        headers=headers_externo,
    )
    assert respuesta.status_code == 403


def test_crear_reemplazar_y_actualizar_reglas(client, login, telefono):
    admin = login(telefono["ADMIN"])
    iniciales = client.get("/api/admin/reglas-puntos", headers=admin)
    assert iniciales.status_code == 200
    assert len(iniciales.json()) == 4

    anterior = next(
        regla
        for regla in iniciales.json()
        if regla["flujo"] == "ORGANICO"
        and regla["tipo_generador"] == "HOGAR"
        and regla["activa"]
    )

    creada = client.post(
        "/api/admin/reglas-puntos",
        json={
            "flujo": "ORGANICO",
            "tipo_generador": "HOGAR",
            "puntos_base_solicitud": 20,
            "puntos_por_kg": 7,
            "valor_referencia_kg_cop": 100,
            "descripcion_regla": "Ajuste administrativo de prueba.",
            "activa": True,
        },
        headers=admin,
    )
    assert creada.status_code == 200, creada.text
    nueva = creada.json()
    assert nueva["activa"] is True
    assert nueva["puntos_base_solicitud"] == 20.0

    desactivada = client.get(
        "/api/admin/reglas-puntos",
        params={"flujo": "ORGANICO", "tipo_generador": "HOGAR", "activa": False},
        headers=admin,
    ).json()
    assert any(regla["id"] == anterior["id"] for regla in desactivada)

    activas = client.get(
        "/api/admin/reglas-puntos",
        params={"flujo": "ORGANICO", "tipo_generador": "HOGAR", "activa": True},
        headers=admin,
    ).json()
    assert [regla["id"] for regla in activas] == [nueva["id"]]

    actualizada = client.patch(
        f"/api/admin/reglas-puntos/{nueva['id']}",
        json={"puntos_por_kg": 8, "descripcion_regla": "Ajuste posterior."},
        headers=admin,
    )
    assert actualizada.status_code == 200, actualizada.text
    assert actualizada.json()["puntos_por_kg"] == 8.0
    assert actualizada.json()["descripcion_regla"] == "Ajuste posterior."

    # Un usuario externo puede consultar las reglas activas para entender sus puntos.
    externo = login(telefono["HOGAR"])
    reglas_publicas = client.get("/api/reglas-puntos", headers=externo)
    assert reglas_publicas.status_code == 200
    assert any(regla["id"] == nueva["id"] for regla in reglas_publicas.json())

    # Validaciones de parámetros.
    invalida = client.post(
        "/api/admin/reglas-puntos",
        json={
            "flujo": "ORGANICO",
            "tipo_generador": "HOGAR",
            "puntos_base_solicitud": -1,
            "puntos_por_kg": 5,
            "valor_referencia_kg_cop": 80,
            "activa": False,
        },
        headers=admin,
    )
    assert invalida.status_code == 422
    assert invalida.json()["detail"]["codigo"] == "VALIDACION"

    sin_cambios = client.patch(
        f"/api/admin/reglas-puntos/{nueva['id']}",
        json={},
        headers=admin,
    )
    assert sin_cambios.status_code == 422

    inexistente = client.patch(
        "/api/admin/reglas-puntos/999999",
        json={"puntos_por_kg": 9},
        headers=admin,
    )
    assert inexistente.status_code == 404


def test_modo_piloto_solo_aplica_a_cuentas_externas(client, db, login, telefono):
    admin = login(telefono["ADMIN"])
    hogar = usuario_por_rol(db, "HOGAR", telefono["HOGAR"])

    respuesta = client.patch(
        f"/api/admin/usuarios/{hogar.id}/piloto",
        json={"es_piloto": False},
        headers=admin,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["es_piloto"] is False
    # RN-08: la etiqueta no restringe el acceso.
    assert client.post(
        "/api/auth/login",
        json={"telefono": telefono["HOGAR"], "password": "PruebaHTTP2026!"},
    ).status_code == 200

    listado = client.get(
        "/api/admin/usuarios",
        params={"rol": "HOGAR", "es_piloto": False},
        headers=admin,
    )
    assert listado.status_code == 200
    assert listado.json()["total"] >= 1
    assert all(item["rol"] == "HOGAR" for item in listado.json()["items"])

    coordinador = usuario_por_rol(db, "COORD_HUERTEROS", telefono["COORD_HUERTEROS"])
    no_aplica = client.patch(
        f"/api/admin/usuarios/{coordinador.id}/piloto",
        json={"es_piloto": True},
        headers=admin,
    )
    assert no_aplica.status_code == 422
    assert no_aplica.json()["detail"]["codigo"] == "USUARIO_NO_APLICA_PILOTO"

    inexistente = client.patch(
        "/api/admin/usuarios/00000000-0000-0000-0000-000000000000/piloto",
        json={"es_piloto": True},
        headers=admin,
    )
    assert inexistente.status_code == 404


def test_regla_nueva_aplica_a_cierres_posteriores(client, db, login, telefono):
    admin = login(telefono["ADMIN"])
    client.post(
        "/api/admin/reglas-puntos",
        json={
            "flujo": "ORGANICO",
            "tipo_generador": "HOGAR",
            "puntos_base_solicitud": 20,
            "puntos_por_kg": 7,
            "valor_referencia_kg_cop": 100,
            "activa": True,
        },
        headers=admin,
    )

    headers_hogar = login(telefono["HOGAR"])
    solicitud = client.post(
        "/api/solicitudes",
        json={
            "flujo": "ORGANICO",
            "cantidad_estimada_kg": 10,
            "disponibilidad_usuario": "Mañana",
        },
        headers=headers_hogar,
    ).json()
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])
    assert client.patch(
        f"/api/solicitudes/{solicitud['id']}/programar",
        json={
            "recolector_id": str(huertero.id),
            "fecha_programada": "2099-01-01",
            "hora_programada": "09:00",
        },
        headers=login(telefono["COORD_HUERTEROS"]),
    ).status_code == 200

    cierre = client.post(
        f"/api/solicitudes/{solicitud['id']}/cerrar",
        json={"cantidad_real_kg": 10},
        headers=login(huertero.telefono),
    )
    assert cierre.status_code == 200, cierre.text
    assert cierre.json()["puntos_otorgados"] == 90.0
