"""Memoria conversacional y perfil seguro de usuarios para la IA."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MensajeWhatsapp, Usuario
from app.services.solicitudes import solicitud_activa_del_solicitante
from app.whatsapp.anonimizacion import anonimizar

LIMITE_MENSAJES = 8
LONGITUD_CONTENIDO = 800
_DIRECCIONES = ("ENTRANTE", "SALIENTE")


def obtener_historial(
    db: Session,
    telefono: str,
    *,
    excluir_id: int | None = None,
    limite: int = LIMITE_MENSAJES,
) -> list[dict[str, str]]:
    consulta = select(MensajeWhatsapp).where(
        MensajeWhatsapp.telefono_remitente == telefono,
        MensajeWhatsapp.direccion.in_(_DIRECCIONES),
        MensajeWhatsapp.estado_envio == "ENVIADO",
        MensajeWhatsapp.error.is_(None),
    )
    if excluir_id is not None:
        consulta = consulta.where(MensajeWhatsapp.id != excluir_id)
    filas = db.scalars(
        consulta.order_by(MensajeWhatsapp.id.desc()).limit(limite)
    ).all()

    historial: list[dict[str, str]] = []
    for fila in reversed(filas):
        contenido = anonimizar(fila.contenido).strip()
        if not contenido:
            continue
        rol = "user" if fila.direccion == "ENTRANTE" else "assistant"
        historial.append({"role": rol, "content": contenido[:LONGITUD_CONTENIDO]})
    return historial


def obtener_perfil_usuario(db: Session, usuario: Usuario) -> str:
    partes = [
        f"Rol registrado: {usuario.rol}.",
        f"Usuario del piloto: {'sí' if usuario.es_piloto else 'no'}.",
        f"EcoPuntos acumulados: {usuario.puntos_acumulados:.2f}.",
    ]
    solicitud = solicitud_activa_del_solicitante(db, usuario)
    if solicitud is None:
        partes.append("No tiene solicitud activa.")
    else:
        detalle = [
            f"Código de solicitud activa: {solicitud.codigo_publico}.",
            f"Flujo: {solicitud.flujo}.",
            f"Estado: {solicitud.estado}.",
        ]
        if solicitud.subtipo_material:
            detalle.append(
                f"Material: {anonimizar(solicitud.subtipo_material)[:120]}."
            )
        if solicitud.disponibilidad_usuario:
            detalle.append(
                "Disponibilidad declarada: "
                f"{anonimizar(solicitud.disponibilidad_usuario)[:120]}."
            )
        if solicitud.fecha_programada and solicitud.hora_programada:
            detalle.append(
                "Programación confirmada: "
                f"{solicitud.fecha_programada.isoformat()} "
                f"a las {solicitud.hora_programada.strftime('%H:%M')}."
            )
        partes.append(" ".join(detalle))
    return " ".join(partes)


__all__ = ["obtener_historial", "obtener_perfil_usuario"]
