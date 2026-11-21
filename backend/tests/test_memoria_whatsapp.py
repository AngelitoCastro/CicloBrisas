"""Pruebas de memoria conversacional y perfil seguro de usuarios."""

from __future__ import annotations

from sqlalchemy import select

from app.models import MensajeWhatsapp, Solicitud, Usuario
from app.whatsapp.memoria import obtener_historial, obtener_perfil_usuario


def test_historial_solo_mensajes_exitosos_y_en_orden(db, telefono) -> None:
    numero = telefono["HOGAR"]
    db.add_all(
        [
            MensajeWhatsapp(
                telefono_remitente=numero,
                direccion="ENTRANTE",
                contenido="Hola",
                estado_envio="ENVIADO",
            ),
            MensajeWhatsapp(
                telefono_remitente=numero,
                direccion="SALIENTE",
                contenido="¿Qué material es?",
                estado_envio="ENVIADO",
            ),
            MensajeWhatsapp(
                telefono_remitente=numero,
                direccion="SALIENTE",
                contenido="Mensaje fallido",
                estado_envio="FALLIDO",
                error="WHATSAPP_ENVIO_FALLIDO",
            ),
            MensajeWhatsapp(
                telefono_remitente=numero,
                direccion="ENTRANTE",
                contenido="Mensaje actual",
                estado_envio="ENVIADO",
            ),
        ]
    )
    db.commit()
    actual = db.scalar(
        select(MensajeWhatsapp).where(
            MensajeWhatsapp.telefono_remitente == numero,
            MensajeWhatsapp.contenido == "Mensaje actual",
        )
    )
    assert actual is not None

    historial = obtener_historial(db, numero, excluir_id=actual.id)

    assert historial == [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "¿Qué material es?"},
    ]


def test_historial_anonimiza_datos_personales(db, telefono) -> None:
    numero = telefono["HOGAR"]
    db.add(
        MensajeWhatsapp(
            telefono_remitente=numero,
            direccion="ENTRANTE",
            contenido="Señora Ana, llámame al 3001112222. Vivo en calle 1.",
            estado_envio="ENVIADO",
        )
    )
    db.commit()

    historial = obtener_historial(db, numero)

    assert len(historial) == 1
    contenido = historial[0]["content"]
    assert "Ana" not in contenido
    assert "3001112222" not in contenido
    assert "calle 1" not in contenido
    assert "[TELEFONO]" in contenido
    assert "[DIRECCION]" in contenido


def test_perfil_usuario_recuerda_solicitud_sin_exponer_pii(db, telefono) -> None:
    usuario = db.scalar(
        select(Usuario).where(Usuario.telefono == telefono["HOGAR"])
    )
    assert usuario is not None
    db.add(
        Solicitud(
            codigo_publico="ECO-2026-999999",
            solicitante_id=usuario.id,
            flujo="ORGANICO",
            disponibilidad_usuario="viernes",
            estado="RECIBIDA",
        )
    )
    db.commit()

    perfil = obtener_perfil_usuario(db, usuario)

    assert "Rol registrado: HOGAR" in perfil
    assert "EcoPuntos acumulados" in perfil
    assert "ECO-2026-999999" in perfil
    assert "ORGANICO" in perfil
    assert "viernes" in perfil
    assert usuario.nombre not in perfil
    assert usuario.telefono not in perfil
    if usuario.direccion:
        assert usuario.direccion not in perfil
