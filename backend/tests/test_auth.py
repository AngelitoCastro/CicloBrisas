"""Pruebas de autenticación bcrypt/JWT y de exposición de datos de cuenta."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from sqlalchemy import select

from app.config import settings
from app.models import Usuario
from tests.conftest import TEST_PASSWORD, usuario_por_rol


def test_login_me_y_hash_bcrypt(client, db, telefono):
    respuesta = client.post(
        "/api/auth/login",
        json={
            "telefono": telefono["UNIDAD_PRODUCTIVA"],
            "password": TEST_PASSWORD,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["expira_en_segundos"] == settings.access_token_expire_minutes * 60
    assert cuerpo["usuario"]["rol"] == "UNIDAD_PRODUCTIVA"
    assert "password_hash" not in json.dumps(cuerpo)

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {cuerpo['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["id"] == cuerpo["usuario"]["id"]
    assert "telefono" in me.json()

    usuario = db.scalar(
        select(Usuario).where(Usuario.telefono == telefono["UNIDAD_PRODUCTIVA"])
    )
    assert usuario is not None
    assert usuario.password_hash != TEST_PASSWORD
    assert usuario.password_hash.startswith("$2")
    assert bcrypt.checkpw(
        TEST_PASSWORD.encode("utf-8"),
        usuario.password_hash.encode("utf-8"),
    )


def test_login_con_password_incorrecta_no_revela_si_el_telefono_existe(
    client, telefono
):
    inexistente = client.post(
        "/api/auth/login",
        json={"telefono": "+573009999999", "password": "lo-que-sea-2026"},
    )
    incorrecta = client.post(
        "/api/auth/login",
        json={"telefono": telefono["HOGAR"], "password": "contraseña-equivocada"},
    )
    assert inexistente.status_code == 401
    assert incorrecta.status_code == 401
    assert inexistente.json()["detail"]["codigo"] == "NO_AUTENTICADO"
    assert incorrecta.json()["detail"]["codigo"] == "NO_AUTENTICADO"
    assert (
        inexistente.json()["detail"]["mensaje"]
        == incorrecta.json()["detail"]["mensaje"]
    )


def test_cuenta_inactiva_no_puede_iniciar_sesion(client, db, telefono):
    usuario = usuario_por_rol(db, "HOGAR", telefono["HOGAR_GENERAL"])
    usuario.activo = False
    db.commit()

    respuesta = client.post(
        "/api/auth/login",
        json={"telefono": telefono["HOGAR_GENERAL"], "password": TEST_PASSWORD},
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["codigo"] == "USUARIO_INACTIVO"


def test_token_expirado_invalido_y_ausente(client, db, telefono):
    usuario = usuario_por_rol(db, "HOGAR", telefono["HOGAR"])
    ahora = datetime.now(UTC)
    expirado = jwt.encode(
        {
            "sub": str(usuario.id),
            "rol": usuario.rol,
            "tipo": "access",
            "iat": ahora - timedelta(hours=2),
            "exp": ahora - timedelta(hours=1),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    respuesta_expirada = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expirado}"},
    )
    assert respuesta_expirada.status_code == 401
    assert respuesta_expirada.json()["detail"]["codigo"] == "TOKEN_EXPIRADO"
    assert respuesta_expirada.headers["www-authenticate"] == "Bearer"

    respuesta_invalida = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer no-es-un-jwt"},
    )
    assert respuesta_invalida.status_code == 401
    assert respuesta_invalida.json()["detail"]["codigo"] == "TOKEN_INVALIDO"

    respuesta_ausente = client.get("/api/auth/me")
    assert respuesta_ausente.status_code == 401
    assert respuesta_ausente.json()["detail"]["codigo"] == "NO_AUTENTICADO"


def test_demo_login_solo_disponible_en_development(client, monkeypatch):
    # En entorno test debe estar bloqueado por defecto
    bloqueado = client.post("/api/auth/demo-login", json={"rol": "COORD_HUERTEROS"})
    assert bloqueado.status_code == 403
    assert bloqueado.json()["detail"]["codigo"] == "DEMO_NO_HABILITADO"

    # En entorno development emite un JWT real para el rol solicitado
    import app.routers.auth as auth_router
    from dataclasses import replace

    monkeypatch.setattr(
        auth_router,
        "settings",
        replace(auth_router.settings, entorno="development"),
    )
    permitido = client.post("/api/auth/demo-login", json={"rol": "COORD_HUERTEROS"})
    assert permitido.status_code == 200, permitido.text
    cuerpo = permitido.json()
    assert cuerpo["usuario"]["rol"] == "COORD_HUERTEROS"
    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {cuerpo['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["rol"] == "COORD_HUERTEROS"
