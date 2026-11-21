"""Orquestación del flujo entrante de WhatsApp con servicios de dominio."""

from __future__ import annotations

import json
import re
import secrets
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import MensajeWhatsapp, Usuario
from app.schemas import CerrarSolicitud, SolicitudCrear
from app.schemas_whatsapp import ClasificacionIA, IntencionIA, MensajeNormalizado
from app.security import hash_password
from app.services.errors import ErrorDominio
from app.services.solicitudes import (
    cerrar_solicitud_por_codigo,
    crear_solicitud,
    solicitud_activa_del_solicitante,
)
from app.tiempo import hoy_bogota
from app.whatsapp import dedupe
from app.whatsapp.cliente import enviar_texto
from app.whatsapp.estado import texto_estado
from app.whatsapp.ia import client as ia
from app.whatsapp.media import descargar_media, preparar_imagen
from app.whatsapp.memoria import obtener_historial, obtener_perfil_usuario
from app.whatsapp.transcripcion import transcribir_audio

PENDIENTE_REGISTRO = "REGISTRO_PENDIENTE"
PENDIENTE_FLUJO = "ACLARACION_PENDIENTE"
_ORGANICOS = (
    "organico",
    "orgánico",
    "casca",
    "vegetal",
    "verdura",
    "fruta",
    "cafe",
    "café",
    "compost",
)
_RECICLABLES = (
    "reciclable",
    "reciclaje",
    "pet",
    "plastico",
    "plástico",
    "carton",
    "cartón",
    "papel",
    "lata",
    "vidrio",
    "botella",
)


def _usuario_por_telefono(db: Session, telefono: str) -> Usuario | None:
    return db.scalar(
        select(Usuario).where(Usuario.telefono == telefono, Usuario.activo.is_(True))
    )


def _estado_pendiente(db: Session, telefono: str) -> str | None:
    fila = db.scalar(
        select(MensajeWhatsapp)
        .where(
            MensajeWhatsapp.telefono_remitente == telefono,
            MensajeWhatsapp.estado_conversacion.is_not(None),
        )
        .order_by(MensajeWhatsapp.creado_en.desc(), MensajeWhatsapp.id.desc())
        .limit(1)
    )
    return fila.estado_conversacion if fila else None


def _limpiar_pendientes(db: Session, telefono: str) -> None:
    filas = db.scalars(
        select(MensajeWhatsapp).where(
            MensajeWhatsapp.telefono_remitente == telefono,
            MensajeWhatsapp.estado_conversacion.is_not(None),
        )
    ).all()
    for fila in filas:
        fila.estado_conversacion = None
    db.commit()


def _borrador_previo(db: Session, telefono: str) -> dict:
    fila = db.scalar(
        select(MensajeWhatsapp)
        .where(
            MensajeWhatsapp.telefono_remitente == telefono,
            MensajeWhatsapp.estado_conversacion == PENDIENTE_FLUJO,
            MensajeWhatsapp.borrador_json.is_not(None),
        )
        .order_by(MensajeWhatsapp.creado_en.desc(), MensajeWhatsapp.id.desc())
        .limit(1)
    )
    if fila is None or not fila.borrador_json:
        return {}
    try:
        datos = json.loads(fila.borrador_json)
    except ValueError:
        return {}
    return datos if isinstance(datos, dict) else {}


def _crear_usuario_desde_texto(
    db: Session, telefono: str, texto: str
) -> Usuario | None:
    nombre = re.search(r"(?i)\bnombre\s*:\s*([^\n,;]+)", texto)
    direccion = re.search(r"(?i)\bdirecc[ií]?[oó]n\s*:\s*([^\n;]+)", texto)
    if nombre and direccion:
        valor_nombre = nombre.group(1).strip()
        valor_direccion = direccion.group(1).strip()
    else:
        partes = [parte.strip() for parte in texto.split(",") if parte.strip()]
        valor_nombre = partes[0] if partes else ""
        valor_direccion = partes[1] if len(partes) > 1 else ""
    if not valor_nombre or not valor_direccion:
        return None
    usuario = Usuario(
        nombre=valor_nombre[:120],
        telefono=telefono,
        password_hash=hash_password(secrets.token_urlsafe(24)),
        rol="HOGAR",
        direccion=valor_direccion[:200],
        es_piloto=True,
        puntos_acumulados=Decimal(0),
        activo=True,
    )
    db.add(usuario)
    try:
        db.commit()
        db.refresh(usuario)
    except IntegrityError:
        db.rollback()
        return None
    return usuario


def _inferir_flujo(texto: str) -> str | None:
    normalizado = (texto or "").lower()
    if any(palabra in normalizado for palabra in _RECICLABLES):
        return "RECICLABLE"
    if any(palabra in normalizado for palabra in _ORGANICOS):
        return "ORGANICO"
    return None


def _normalizar_codigo(valor: str | None) -> str | None:
    if not valor:
        return None
    coincidencia = re.fullmatch(
        r"ECO-?(?:(\d{4})-?)?(\d{1,6})", valor.strip(), re.IGNORECASE
    )
    if coincidencia is None:
        return None
    anio = coincidencia.group(1) or str(hoy_bogota().year)
    numero = int(coincidencia.group(2))
    return f"ECO-{anio}-{numero:06d}"


def _extraer_codigo(texto: str) -> str | None:
    coincidencia = re.search(
        r"ECO[-\s]?\d{1,6}(?:[-\s]?\d{1,4})?", texto, re.IGNORECASE
    )
    return coincidencia.group(0) if coincidencia else None


def _responder(
    db: Session,
    telefono: str,
    texto: str,
    *,
    solicitud_id: int | None = None,
) -> None:
    try:
        wa_message_id = enviar_texto(telefono, texto)
        error = None
    except ErrorDominio as exc:
        wa_message_id = None
        error = exc.codigo
    registro = MensajeWhatsapp(
        solicitud_id=solicitud_id,
        telefono_remitente=telefono,
        direccion="SALIENTE",
        contenido=texto,
        intencion_ia="RESPUESTA",
        procesado_por_ia=True,
        procesado_en=datetime.now(UTC),
        estado_envio="ENVIADO" if wa_message_id else "FALLIDO",
        wa_message_id=wa_message_id,
        error=error,
    )
    db.add(registro)
    db.commit()


def _ejecutar_intencion(
    db: Session,
    usuario: Usuario,
    clasificacion: ClasificacionIA,
    texto_original: str,
    borrador: dict,
) -> tuple[str, int | None, str | None, str | None]:
    if clasificacion.intencion == IntencionIA.SOLICITUD_RECOLECCION:
        flujo = clasificacion.flujo_sugerido or _inferir_flujo(texto_original)
        if flujo is None:
            datos_pendientes = {
                "disponibilidad_texto": clasificacion.disponibilidad_texto
                or borrador.get("disponibilidad_texto"),
                "subtipo_material": clasificacion.subtipo_material
                or borrador.get("subtipo_material"),
            }
            pregunta = (
                clasificacion.respuesta_usuario or "¿Son orgánicos o reciclables?"
            )
            return pregunta, None, PENDIENTE_FLUJO, json.dumps(datos_pendientes)
        disponibilidad = (
            clasificacion.disponibilidad_texto
            or borrador.get("disponibilidad_texto")
            or "Sin preferencia de día"
        )
        solicitud = crear_solicitud(
            db,
            usuario,
            SolicitudCrear(
                flujo=flujo,
                subtipo_material=clasificacion.subtipo_material
                or borrador.get("subtipo_material"),
                disponibilidad_usuario=disponibilidad[:120],
                observaciones="Solicitud iniciada desde WhatsApp.",
            ),
        )
        return (
            f"Listo, registré tu solicitud {solicitud.codigo_publico}. {clasificacion.respuesta_usuario}",
            solicitud.id,
            None,
            None,
        )

    if clasificacion.intencion == IntencionIA.CIERRE_RECOLECCION:
        codigo = _normalizar_codigo(
            clasificacion.codigo_solicitud or _extraer_codigo(texto_original)
        )
        if codigo is None or clasificacion.peso_kg is None:
            return (
                "Necesito el código de la solicitud y los kilos para confirmar el cierre.",
                None,
                None,
                None,
            )
        try:
            resultado = cerrar_solicitud_por_codigo(
                db,
                usuario,
                codigo,
                CerrarSolicitud(
                    cantidad_real_kg=clasificacion.peso_kg,
                    nota_operativa="Cierre confirmado desde WhatsApp.",
                ),
            )
        except ErrorDominio as exc:
            return exc.mensaje, None, None, None
        return (
            f"Cierre registrado para {codigo}: {resultado.puntos_otorgados:.2f} EcoPuntos.",
            resultado.solicitud.id,
            None,
            None,
        )

    if clasificacion.intencion == IntencionIA.CONSULTA_ESTADO:
        solicitud = solicitud_activa_del_solicitante(db, usuario)
        if solicitud is None:
            return "No tienes una solicitud activa en este momento.", None, None, None
        return texto_estado(solicitud), solicitud.id, None, None

    return clasificacion.respuesta_usuario, None, None, None


def _clasificar_mensaje(
    mensaje: MensajeNormalizado,
    historial: list[dict[str, str]],
    perfil: str,
) -> tuple[ClasificacionIA, str | None]:
    if mensaje.tipo == "text":
        return (
            ia.clasificar_texto(
                mensaje.texto or "", historial=historial, perfil=perfil
            ),
            mensaje.texto,
        )
    if mensaje.media_id is None:
        return (
            ClasificacionIA(
                intencion=IntencionIA.OTRO,
                respuesta_usuario="Por ahora solo puedo leer mensajes, fotos y notas de voz.",
            ),
            None,
        )
    archivo = descargar_media(mensaje.media_id, mensaje.media_mime)
    if mensaje.tipo == "image":
        return (
            ia.clasificar_imagen(
                preparar_imagen(archivo),
                mensaje.texto,
                historial=historial,
                perfil=perfil,
            ),
            mensaje.texto,
        )
    if mensaje.tipo == "audio":
        transcripcion = transcribir_audio(archivo)
        return (
            ia.clasificar_texto(
                transcripcion, historial=historial, perfil=perfil
            ),
            transcripcion,
        )
    return (
        ClasificacionIA(
            intencion=IntencionIA.OTRO,
            respuesta_usuario="Por ahora solo puedo leer mensajes, fotos y notas de voz.",
        ),
        None,
    )


def procesar_mensaje(mensaje: MensajeNormalizado) -> None:
    with SessionLocal() as db:
        registro = dedupe.registrar_entrante(
            db,
            wa_message_id=mensaje.id,
            telefono=mensaje.telefono,
            contenido=mensaje.texto or f"[{mensaje.tipo}]",
            media_id=mensaje.media_id,
            media_tipo=mensaje.tipo,
            media_mime=mensaje.media_mime,
        )
        if registro is None:
            return

        try:
            pendiente = _estado_pendiente(db, mensaje.telefono)
            usuario = _usuario_por_telefono(db, mensaje.telefono)
            if usuario is None and pendiente == PENDIENTE_REGISTRO:
                usuario = _crear_usuario_desde_texto(
                    db, mensaje.telefono, mensaje.texto or ""
                )
            if usuario is None:
                _limpiar_pendientes(db, mensaje.telefono)
                respuesta = (
                    "Para ayudarte necesito tu nombre y dirección. "
                    "Escríbelos así: Nombre: Ana, Dirección: Calle 1 # 2."
                )
                _responder(db, mensaje.telefono, respuesta)
                dedupe.marcar_procesado(
                    db,
                    registro,
                    intencion="REGISTRO_PENDIENTE",
                    estado_conversacion=PENDIENTE_REGISTRO,
                )
                return

            borrador = _borrador_previo(db, mensaje.telefono)
            if pendiente:
                _limpiar_pendientes(db, mensaje.telefono)
            historial = obtener_historial(
                db, mensaje.telefono, excluir_id=registro.id
            )
            perfil = obtener_perfil_usuario(db, usuario)
            clasificacion, texto_extraido = _clasificar_mensaje(
                mensaje, historial, perfil
            )
            respuesta, solicitud_id, conversacion, nuevo_borrador = _ejecutar_intencion(
                db,
                usuario,
                clasificacion,
                mensaje.texto or texto_extraido or "",
                borrador,
            )
            _responder(db, mensaje.telefono, respuesta, solicitud_id=solicitud_id)
            dedupe.marcar_procesado(
                db,
                registro,
                intencion=clasificacion.intencion.value,
                solicitud_id=solicitud_id,
                texto_extraido=texto_extraido,
                estado_conversacion=conversacion,
                borrador_json=nuevo_borrador,
            )
        except (ErrorDominio, SQLAlchemyError) as exc:
            db.rollback()
            _responder(
                db,
                mensaje.telefono,
                "No pude procesar tu mensaje en este momento. ¿Lo puedes enviar de nuevo?",
            )
            dedupe.marcar_procesado(db, registro, error=type(exc).__name__)


__all__ = ["procesar_mensaje"]
