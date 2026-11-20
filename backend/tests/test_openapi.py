"""Pruebas de salud, contrato OpenAPI y forma estable de errores."""

from __future__ import annotations


def test_health_y_raiz(client):
    salud = client.get("/health")
    assert salud.status_code == 200
    assert salud.json() == {"estado": "ok", "servicio": "ecoconecta-api"}
    assert client.get("/api/health").status_code == 200

    raiz = client.get("/")
    assert raiz.status_code == 200
    assert raiz.json()["documentacion"] == "/docs"


def test_openapi_expone_rutas_principales(client):
    esquema = client.get("/openapi.json")
    assert esquema.status_code == 200
    rutas = esquema.json()["paths"]
    assert {
        "/api/auth/login",
        "/api/solicitudes",
        "/api/solicitudes/{solicitud_id}/programar",
        "/api/solicitudes/{solicitud_id}/cerrar",
        "/api/solicitudes/{solicitud_id}/historial",
        "/api/admin/reglas-puntos",
        "/api/admin/usuarios/{usuario_id}/piloto",
    }.issubset(rutas)


def test_error_http_y_validacion_tienen_forma_estable(client):
    inexistente = client.get("/api/ruta-inexistente")
    assert inexistente.status_code == 404
    assert inexistente.json()["detail"]["codigo"] == "ERROR_HTTP"

    validacion = client.post(
        "/api/auth/login",
        json={"telefono": "123", "password": ""},
    )
    assert validacion.status_code == 422
    assert validacion.json()["detail"]["codigo"] == "VALIDACION"
    assert validacion.json()["detail"]["errores"]
    assert all(
        set(error).issuperset({"campo", "mensaje", "tipo"})
        for error in validacion.json()["detail"]["errores"]
    )
