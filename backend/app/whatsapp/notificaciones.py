"""Construye los avisos de WhatsApp dentro de la transacción de negocio."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AvisoWhatsApp,
    ConsentimientoWhatsApp,
    HistorialEstado,
    Solicitud,
    Usuario,
)
from app.services.errors import NoEncontrado
from app.whatsapp.config import (
    obtener_config,
    plantilla_meta_para,
    proveedor_whatsapp_activo,
)

ESTADO_SIN_CONSENTIMIENTO = "SIN_CONSENTIMIENTO"


def actualizar_consentimiento_whatsapp(
    db: Session,
    usuario_id: uuid.UUID,
    *,
    aceptado: bool,
    origen: str = "ADMIN",
    commit: bool = True,
) -> ConsentimientoWhatsApp:
    """Registra o revoca explícitamente el consentimiento de avisos WhatsApp."""
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise NoEncontrado("Usuario no encontrado.")

    ahora = datetime.now(UTC)
    registro = db.get(ConsentimientoWhatsApp, usuario_id)
    if registro is None:
        registro = ConsentimientoWhatsApp(
            usuario_id=usuario_id,
            aceptado=bool(aceptado),
            origen=origen[:40],
            actualizado_en=ahora,
        )
        db.add(registro)
    else:
        registro.aceptado = bool(aceptado)
        registro.origen = origen[:40]
        registro.actualizado_en = ahora

    if commit:
        db.commit()
        db.refresh(registro)
    else:
        db.flush()
    return registro


def tiene_consentimiento_whatsapp(
    db: Session,
    usuario: Usuario | None,
    *,
    proveedor: str | None = None,
) -> bool:
    """Evalúa el consentimiento vigente del destinatario para recibir avisos por WhatsApp.

    En Meta se exige siempre consentimiento explícito y vigente (aceptado=True)
    tanto para solicitantes como para recolectores.
    """
    if usuario is None or not usuario.activo:
        return False

    cfg = obtener_config()
    prov = (proveedor or proveedor_whatsapp_activo(cfg)).strip().upper()
    if prov == "AUTO":
        prov = proveedor_whatsapp_activo(cfg).upper()

    registro = db.get(ConsentimientoWhatsApp, usuario.id)
    if prov == "META":
        return registro is not None and bool(registro.aceptado)

    if registro is not None:
        return bool(registro.aceptado)
    return not cfg.whatsapp_exigir_consentimiento_explicito


def tiene_consentimiento_para_aviso(db: Session, aviso: AvisoWhatsApp) -> bool:
    """Verifica el consentimiento vigente del destinatario de un aviso ya encolado."""
    usuario = db.scalar(
        select(Usuario).where(Usuario.telefono == aviso.telefono)
    )
    if usuario is None:
        solicitud = db.get(Solicitud, aviso.solicitud_id)
        if solicitud is not None:
            if aviso.destinatario == "SOLICITANTE":
                usuario = db.get(Usuario, solicitud.solicitante_id)
            elif aviso.destinatario == "RECOLECTOR" and solicitud.recolector_id:
                usuario = db.get(Usuario, solicitud.recolector_id)
    return tiene_consentimiento_whatsapp(
        db,
        usuario,
        proveedor=aviso.proveedor,
    )


def encolar(
    db: Session,
    historial: HistorialEstado,
    solicitud: Solicitud,
    recolector: Usuario | None,
) -> None:
    db.flush()
    cfg = obtener_config()
    proveedor = proveedor_whatsapp_activo(cfg).upper()
    hogar = solicitud.solicitante
    codigo = solicitud.codigo_publico
    evento = historial.estado_nuevo

    if evento == "PROGRAMADA":
        horario = f"{solicitud.fecha_programada} a las {solicitud.hora_programada:%H:%M}"
        peso_txt = (
            f"{solicitud.cantidad_estimada_kg:.2f} kg estimados"
            if solicitud.cantidad_estimada_kg is not None
            else "peso pendiente"
        )
        ubicacion = " ".join(
            parte
            for parte in (hogar.direccion or "sin registrar", hogar.sector_manzana or "")
            if parte
        ).strip()
        extra_notas = (
            f" Notas: {solicitud.observaciones}."
            if solicitud.observaciones
            else ""
        )
        orden = (
            f"Recolección {codigo}: {solicitud.flujo}, "
            f"{solicitud.subtipo_material or 'sin subtipo'} ({peso_txt}). "
            f"Dirección: {ubicacion}. "
            f"Referencia: {solicitud.disponibilidad_usuario}. "
            f"Horario: {horario}.{extra_notas} "
            f"Al terminar responde LISTO {codigo} [kilos]."
        )
        nombre_recolector = (
            recolector.nombre if recolector is not None else "el equipo asignado"
        )
        aviso = (
            f"Tu solicitud {codigo} está programada para {horario}. "
            f"Te atenderá {nombre_recolector}."
        )
    else:
        orden = f"Cierre confirmado para {codigo}: {solicitud.cantidad_real_kg:.2f} kg."
        aviso = f"{orden} Recibiste {solicitud.puntos_otorgados:.2f} EcoPuntos."

    destinatarios: list[tuple[str, Usuario, str]] = []
    if recolector is not None:
        destinatarios.append(("RECOLECTOR", recolector, orden))
    if hogar is not None:
        destinatarios.append(("SOLICITANTE", hogar, aviso))

    for rol, usuario, texto in destinatarios:
        autorizado = tiene_consentimiento_whatsapp(db, usuario, proveedor=proveedor)
        plantilla = (
            plantilla_meta_para(evento, rol) or None
            if proveedor == "META"
            else None
        )
        db.add(
            AvisoWhatsApp(
                historial_id=historial.id,
                solicitud_id=solicitud.id,
                evento=evento,
                destinatario=rol,
                telefono=usuario.telefono,
                contenido=texto,
                estado="PENDIENTE" if autorizado else ESTADO_SIN_CONSENTIMIENTO,
                error=None if autorizado else ESTADO_SIN_CONSENTIMIENTO,
                proveedor=proveedor,
                plantilla=plantilla,
            )
        )


__all__ = [
    "ESTADO_SIN_CONSENTIMIENTO",
    "actualizar_consentimiento_whatsapp",
    "encolar",
    "tiene_consentimiento_para_aviso",
    "tiene_consentimiento_whatsapp",
]
