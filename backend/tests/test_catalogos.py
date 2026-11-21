"""Pruebas de catálogos compartidos: recolectores por flujo y contenidos educativos."""

from __future__ import annotations


def test_recolectores_aislados_por_flujo_y_rol(client, login, telefono):
    huerteros_resp = client.get(
        "/api/recolectores", headers=login(telefono["COORD_HUERTEROS"])
    )
    assert huerteros_resp.status_code == 200
    huerteros = huerteros_resp.json()
    assert len(huerteros) >= 2
    assert all(item["rol"] == "HUERTERO" and item["activo"] for item in huerteros)

    # Coordinador de huerta no puede pedir recolectores reciclables (RN-01)
    bloqueado = client.get(
        "/api/recolectores?flujo=RECICLABLE",
        headers=login(telefono["COORD_HUERTEROS"]),
    )
    assert bloqueado.status_code == 403
    assert bloqueado.json()["detail"]["codigo"] == "FLUJO_NO_AUTORIZADO"

    recicladores_resp = client.get(
        "/api/recolectores", headers=login(telefono["COORD_RECICLADORES"])
    )
    assert recicladores_resp.status_code == 200
    recicladores = recicladores_resp.json()
    assert len(recicladores) >= 2
    assert all(item["rol"] == "RECICLADOR" and item["activo"] for item in recicladores)

    # Admin ve ambos y puede filtrar por flujo
    admin_todos = client.get("/api/recolectores", headers=login(telefono["ADMIN"]))
    assert admin_todos.status_code == 200
    roles_admin = {item["rol"] for item in admin_todos.json()}
    assert roles_admin == {"HUERTERO", "RECICLADOR"}

    admin_organico = client.get(
        "/api/recolectores?flujo=ORGANICO", headers=login(telefono["ADMIN"])
    )
    assert admin_organico.status_code == 200
    assert all(item["rol"] == "HUERTERO" for item in admin_organico.json())

    # Usuarios externos y recolectores no pueden listar el catálogo
    for rol in ("HOGAR", "UNIDAD_PRODUCTIVA", "HUERTERO", "RECICLADOR"):
        denegado = client.get("/api/recolectores", headers=login(telefono[rol]))
        assert denegado.status_code == 403
        assert denegado.json()["detail"]["codigo"] == "ROL_NO_AUTORIZADO"


def test_contenidos_educativos_y_piloto_en_solicitud(client, login, telefono):
    resp = client.get("/api/contenidos-educativos", headers=login(telefono["HOGAR"]))
    assert resp.status_code == 200
    contenidos = resp.json()
    assert len(contenidos) >= 4
    assert all("titulo" in c and "resumen" in c for c in contenidos)

    resp_cat = client.get(
        "/api/contenidos-educativos?categoria=ORGANICO",
        headers=login(telefono["HOGAR"]),
    )
    assert resp_cat.status_code == 200
    assert all(c["categoria"] == "ORGANICO" for c in resp_cat.json())

    creada = client.post(
        "/api/solicitudes",
        headers=login(telefono["UNIDAD_PRODUCTIVA"]),
        json={
            "flujo": "ORGANICO",
            "subtipo_material": "Cáscaras vegetales",
            "cantidad_estimada_kg": 8.0,
            "disponibilidad_usuario": "Mañanas 8 a 11",
        },
    )
    assert creada.status_code == 201
    assert creada.json()["solicitante"]["es_piloto"] is True
