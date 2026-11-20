"""Pruebas HTTP del recorrido de solicitudes, permisos, programación y cierre."""

from __future__ import annotations

from datetime import time

from app.models import Usuario
from tests.conftest import (
    HORA_PROGRAMADA,
    fecha_futura,
    usuario_por_rol,
)


def _crear(client, headers, flujo: str = "ORGANICO", **cambios):
    payload = {
        "flujo": flujo,
        "subtipo_material": "Cáscaras y vegetales" if flujo == "ORGANICO" else "Cartón y PET",
        "cantidad_estimada_kg": 12.5,
        "disponibilidad_usuario": "Lunes a viernes de 8:00 a.m. a 11:00 a.m.",
        "observaciones": "Dejar el balde en la portería.",
    }
    payload.update(cambios)
    return client.post("/api/solicitudes", json=payload, headers=headers)


def _programar(client, headers, solicitud_id: int, recolector_id, **cambios):
    payload = {
        "recolector_id": str(recolector_id),
        "fecha_programada": fecha_futura().isoformat(),
        "hora_programada": HORA_PROGRAMADA.strftime("%H:%M"),
        "nota_operativa": "Ruta de prueba",
    }
    payload.update(cambios)
    return client.patch(
        f"/api/solicitudes/{solicitud_id}/programar",
        json=payload,
        headers=headers,
    )


def _cerrar(client, headers, solicitud_id: int, cantidad: float = 10.0):
    return client.post(
        f"/api/solicitudes/{solicitud_id}/cerrar",
        json={"cantidad_real_kg": cantidad, "nota_operativa": "Confirmado en campo"},
        headers=headers,
    )


def test_alta_listado_e_historial_con_contacto_del_propietario(
    client,
    db,
    login,
    telefono,
):
    headers_up = login(telefono["UNIDAD_PRODUCTIVA"])
    creada = _crear(client, headers_up, "ORGANICO")
    assert creada.status_code == 201, creada.text
    solicitud = creada.json()
    assert solicitud["estado"] == "RECIBIDA"
    assert solicitud["codigo_publico"].startswith("ECO-")
    assert solicitud["codigo_publico"].endswith(f"{solicitud['id']:06d}")
    # El propietario sí ve sus datos de contacto.
    assert solicitud["solicitante"]["telefono"] == telefono["UNIDAD_PRODUCTIVA"]
    assert solicitud["solicitante"]["direccion"]
    assert solicitud["coordinador"] is None
    assert solicitud["recolector"] is None
    assert solicitud["puntos_otorgados"] == 0.0

    historial = client.get(
        f"/api/solicitudes/{solicitud['id']}/historial",
        headers=headers_up,
    )
    assert historial.status_code == 200
    registros = historial.json()
    assert len(registros) == 1
    assert registros[0]["estado_anterior"] is None
    assert registros[0]["estado_nuevo"] == "RECIBIDA"
    assert registros[0]["actor"]["rol"] == "UNIDAD_PRODUCTIVA"

    # RN-01: el coordinador de huerteros ve el flujo orgánico; el de recicladores no.
    lista_huerteros = client.get("/api/solicitudes", headers=login(telefono["COORD_HUERTEROS"]))
    assert lista_huerteros.status_code == 200
    assert lista_huerteros.json()["total"] == 1
    assert lista_huerteros.json()["items"][0]["solicitante"]["telefono"]

    lista_recicladores = client.get(
        "/api/solicitudes",
        headers=login(telefono["COORD_RECICLADORES"]),
    )
    assert lista_recicladores.status_code == 200
    assert lista_recicladores.json()["total"] == 0

    lista_admin = client.get("/api/solicitudes", headers=login(telefono["ADMIN"]))
    assert lista_admin.status_code == 200
    assert lista_admin.json()["total"] == 1

    # Otro usuario externo no puede ver el detalle ni listar la solicitud ajena.
    headers_otro_hogar = login(telefono["HOGAR_GENERAL"])
    detalle_ajeno = client.get(f"/api/solicitudes/{solicitud['id']}", headers=headers_otro_hogar)
    assert detalle_ajeno.status_code == 404
    assert detalle_ajeno.json()["detail"]["codigo"] == "NO_ENCONTRADO"
    lista_ajena = client.get("/api/solicitudes", headers=headers_otro_hogar)
    assert lista_ajena.status_code == 200
    assert lista_ajena.json()["total"] == 0

    # El coordinador de recicladores tampoco puede abrir el detalle orgánico.
    detalle_flujo_ajeno = client.get(
        f"/api/solicitudes/{solicitud['id']}",
        headers=login(telefono["COORD_RECICLADORES"]),
    )
    assert detalle_flujo_ajeno.status_code == 404


def test_revision_asignacion_programacion_e_historial(client, db, login, telefono):
    headers_hogar = login(telefono["HOGAR"])
    creada = _crear(client, headers_hogar, "RECICLABLE").json()
    solicitud_id = creada["id"]
    coord = login(telefono["COORD_RECICLADORES"])
    coordinador_usuario = usuario_por_rol(
        db,
        "COORD_RECICLADORES",
        telefono["COORD_RECICLADORES"],
    )
    reciclador = usuario_por_rol(db, "RECICLADOR", telefono["RECICLADOR"])
    otro_reciclador = usuario_por_rol(db, "RECICLADOR", "+573000000106")

    revisar = client.post(
        f"/api/solicitudes/{solicitud_id}/revisar",
        json={"nota_operativa": "Revisada por coordinación"},
        headers=coord,
    )
    assert revisar.status_code == 200, revisar.text
    assert revisar.json()["estado"] == "EN_REVISION"

    asignar = client.post(
        f"/api/solicitudes/{solicitud_id}/asignar",
        json={"recolector_id": str(reciclador.id), "nota_operativa": "Asignada a ruta A"},
        headers=coord,
    )
    assert asignar.status_code == 200, asignar.text
    assert asignar.json()["estado"] == "ASIGNADA"
    assert asignar.json()["coordinador"]["id"] == str(coordinador_usuario.id)
    assert asignar.json()["recolector"]["id"] == str(reciclador.id)

    # Campos obligatorios de programación (RN-02).
    incompleta = client.patch(
        f"/api/solicitudes/{solicitud_id}/programar",
        json={"recolector_id": str(reciclador.id)},
        headers=coord,
    )
    assert incompleta.status_code == 422
    assert incompleta.json()["detail"]["codigo"] == "VALIDACION"
    campos = {error["campo"] for error in incompleta.json()["detail"]["errores"]}
    assert {"fecha_programada", "hora_programada"}.issubset(campos)

    # Un recolector del otro flujo no es compatible.
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])
    incompatible = _programar(client, coord, solicitud_id, huertero.id)
    assert incompatible.status_code == 422
    assert incompatible.json()["detail"]["codigo"] == "RECOLECTOR_INCOMPATIBLE"

    # Fecha pasada rechazada.
    pasada = _programar(
        client,
        coord,
        solicitud_id,
        reciclador.id,
        fecha_programada="2020-01-01",
    )
    assert pasada.status_code == 422
    assert pasada.json()["detail"]["codigo"] == "FECHA_PROGRAMADA_INVALIDA"

    programada = _programar(client, coord, solicitud_id, reciclador.id)
    assert programada.status_code == 200, programada.text
    cuerpo = programada.json()
    assert cuerpo["estado"] == "PROGRAMADA"
    assert cuerpo["recolector"]["id"] == str(reciclador.id)
    assert cuerpo["coordinador"]["id"] is not None
    assert cuerpo["fecha_programada"] == fecha_futura().isoformat()
    assert cuerpo["hora_programada"] == "09:30"

    historial = client.get(
        f"/api/solicitudes/{solicitud_id}/historial",
        headers=login(telefono["HOGAR"]),
    ).json()
    assert [registro["estado_nuevo"] for registro in historial] == [
        "RECIBIDA",
        "EN_REVISION",
        "ASIGNADA",
        "PROGRAMADA",
    ]

    # El recolector asignado ve el detalle; otro recolector del mismo flujo no.
    detalle_asignado = client.get(
        f"/api/solicitudes/{solicitud_id}",
        headers=login(reciclador.telefono),
    )
    assert detalle_asignado.status_code == 200
    assert detalle_asignado.json()["solicitante"]["telefono"] == telefono["HOGAR"]
    detalle_otro = client.get(
        f"/api/solicitudes/{solicitud_id}",
        headers=login(otro_reciclador.telefono),
    )
    assert detalle_otro.status_code == 404

    # El coordinador del otro flujo no puede operar sobre esta solicitud.
    coord_h = login(telefono["COORD_HUERTEROS"])
    assert client.post(
        f"/api/solicitudes/{solicitud_id}/revisar",
        json={},
        headers=coord_h,
    ).status_code == 403
    assert _programar(client, coord_h, solicitud_id, reciclador.id).status_code == 403


def test_programacion_directa_desde_recibida(client, db, login, telefono):
    headers = login(telefono["UNIDAD_PRODUCTIVA"])
    solicitud = _crear(client, headers, "ORGANICO").json()
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])
    coordinador = login(telefono["COORD_HUERTEROS"])

    programada = _programar(client, coordinador, solicitud["id"], huertero.id)
    assert programada.status_code == 200, programada.text
    assert programada.json()["estado"] == "PROGRAMADA"
    assert programada.json()["coordinador"]["rol"] == "COORD_HUERTEROS"


def test_cierre_con_peso_puntos_y_proteccion_contra_doble_cierre(
    client,
    db,
    login,
    telefono,
):
    headers_up = login(telefono["UNIDAD_PRODUCTIVA"])
    solicitud = _crear(client, headers_up, "ORGANICO").json()
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])
    otro_huertero = usuario_por_rol(db, "HUERTERO", "+573000000103")
    coordinador = login(telefono["COORD_HUERTEROS"])

    # Todavía no está PROGRAMADA: no se puede cerrar ni acreditar.
    anticipado = _cerrar(client, coordinador, solicitud["id"])
    assert anticipado.status_code == 409
    assert anticipado.json()["detail"]["codigo"] == "ESTADO_INVALIDO"

    assert _programar(client, coordinador, solicitud["id"], huertero.id).status_code == 200

    # Solo el recolector asignado, el coordinador del flujo o ADMIN pueden cerrar.
    assert _cerrar(client, headers_up, solicitud["id"]).status_code == 403
    assert _cerrar(client, login(otro_huertero.telefono), solicitud["id"]).status_code == 403

    cierre = _cerrar(client, login(huertero.telefono), solicitud["id"], 10.0)
    assert cierre.status_code == 200, cierre.text
    cuerpo = cierre.json()
    assert cuerpo["estado"] == "RECOLECTADA"
    assert cuerpo["cantidad_real_kg"] == 10.0
    # Semilla: ORGANICO/UNIDAD_PRODUCTIVA = 15 base + 6 por kg.
    assert cuerpo["puntos_otorgados"] == 75.0
    assert cuerpo["regla_puntos_id"] is not None
    assert cuerpo["calculo_puntos"]["formula"].startswith("15.00 base + 10.00 kg × 6.00")
    assert "validación FSD" in cuerpo["calculo_puntos"]["nota_fsd"]

    me = client.get("/api/auth/me", headers=headers_up)
    assert me.json()["puntos_acumulados"] == 75.0

    repeticion = _cerrar(client, login(huertero.telefono), solicitud["id"], 10.0)
    assert repeticion.status_code == 409
    assert repeticion.json()["detail"]["codigo"] == "SOLICITUD_YA_CERRADA"
    me_despues = client.get("/api/auth/me", headers=headers_up)
    assert me_despues.json()["puntos_acumulados"] == 75.0

    historial = client.get(
        f"/api/solicitudes/{solicitud['id']}/historial",
        headers=headers_up,
    ).json()
    assert [registro["estado_nuevo"] for registro in historial] == [
        "RECIBIDA",
        "PROGRAMADA",
        "RECOLECTADA",
    ]
    assert "Cálculo parametrizable sujeto a validación FSD" in historial[-1]["nota_operativa"]
    assert historial[-1]["actor"]["rol"] == "HUERTERO"

    # Tampoco se puede cancelar una solicitud ya recolectada.
    cancelada = client.post(
        f"/api/solicitudes/{solicitud['id']}/cancelar",
        json={"motivo": "Prueba de estado final"},
        headers=coordinador,
    )
    assert cancelada.status_code == 409


def test_cierre_sin_regla_activa_no_acredita_y_luego_funciona(client, db, login, telefono):
    admin = login(telefono["ADMIN"])
    reglas = client.get(
        "/api/admin/reglas-puntos",
        params={"flujo": "ORGANICO", "tipo_generador": "HOGAR"},
        headers=admin,
    ).json()
    regla_activa = next(regla for regla in reglas if regla["activa"])
    desactivar = client.patch(
        f"/api/admin/reglas-puntos/{regla_activa['id']}",
        json={"activa": False},
        headers=admin,
    )
    assert desactivar.status_code == 200, desactivar.text
    assert desactivar.json()["activa"] is False

    headers_hogar = login(telefono["HOGAR"])
    solicitud = _crear(client, headers_hogar, "ORGANICO").json()
    huertero = usuario_por_rol(db, "HUERTERO", telefono["HUERTERO"])
    assert _programar(
        client,
        login(telefono["COORD_HUERTEROS"]),
        solicitud["id"],
        huertero.id,
    ).status_code == 200

    sin_regla = _cerrar(client, login(huertero.telefono), solicitud["id"])
    assert sin_regla.status_code == 409
    assert sin_regla.json()["detail"]["codigo"] == "REGLA_PUNTOS_NO_DISPONIBLE"

    detalle = client.get(f"/api/solicitudes/{solicitud['id']}", headers=headers_hogar).json()
    assert detalle["estado"] == "PROGRAMADA"
    assert detalle["puntos_otorgados"] == 0.0
    assert detalle["regla_puntos_id"] is None
    assert client.get("/api/auth/me", headers=headers_hogar).json()["puntos_acumulados"] == 0.0

    nueva = client.post(
        "/api/admin/reglas-puntos",
        json={
            "flujo": "ORGANICO",
            "tipo_generador": "HOGAR",
            "puntos_base_solicitud": 20,
            "puntos_por_kg": 7,
            "valor_referencia_kg_cop": 100,
            "descripcion_regla": "Regla de prueba posterior al cierre fallido.",
            "activa": True,
        },
        headers=admin,
    )
    assert nueva.status_code == 200, nueva.text

    cierre = _cerrar(client, login(huertero.telefono), solicitud["id"], 10.0)
    assert cierre.status_code == 200, cierre.text
    assert cierre.json()["puntos_otorgados"] == 90.0
    assert client.get("/api/auth/me", headers=headers_hogar).json()["puntos_acumulados"] == 90.0


def test_cancelacion_por_propietario_y_por_coordinacion(client, db, login, telefono):
    headers_hogar = login(telefono["HOGAR_GENERAL"])
    cancelable = _crear(client, headers_hogar, "RECICLABLE").json()
    respuesta = client.post(
        f"/api/solicitudes/{cancelable['id']}/cancelar",
        json={"motivo": "Cambio de planes del hogar"},
        headers=headers_hogar,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "CANCELADA"

    programada = _crear(client, headers_hogar, "RECICLABLE").json()
    reciclador = usuario_por_rol(db, "RECICLADOR", telefono["RECICLADOR"])
    coordinador = login(telefono["COORD_RECICLADORES"])
    assert _programar(client, coordinador, programada["id"], reciclador.id).status_code == 200

    propia_tarde = client.post(
        f"/api/solicitudes/{programada['id']}/cancelar",
        json={"motivo": "Ya no la necesito"},
        headers=headers_hogar,
    )
    assert propia_tarde.status_code == 409

    por_coordinacion = client.post(
        f"/api/solicitudes/{programada['id']}/cancelar",
        json={"motivo": "Ruta cancelada por lluvia"},
        headers=coordinador,
    )
    assert por_coordinacion.status_code == 200
    assert por_coordinacion.json()["estado"] == "CANCELADA"
