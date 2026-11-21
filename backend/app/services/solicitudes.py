"""Servicios de solicitudes: alta, consulta, programación, historial y cierre.

Los servicios son la única implementación de las reglas RN-01 a RN-07 y se
comparten entre la API HTTP y el webhook de WhatsApp. Cada operación de
escritura confirma su propia transacción; ante un error hace rollback y lanza
un :class:`ErrorDominio` con un código estable para los consumidores.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import date
from datetime import time as hora_del_dia
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import HistorialEstado, ReglaPuntos, Solicitud, Usuario
from app.schemas import (
    AsignarSolicitud,
    CancelarSolicitud,
    CerrarSolicitud,
    ProgramarSolicitud,
    RevisarSolicitud,
    SolicitudCrear,
)
from app.services.errors import (
    Conflicto,
    ErrorDominio,
    NoEncontrado,
    PermisoDenegado,
    Validacion,
)
from app.whatsapp.notificaciones import encolar
from app.tiempo import ahora_bogota, hoy_bogota

COORDINADOR_POR_FLUJO: dict[str, str] = {
    "ORGANICO": "COORD_HUERTEROS",
    "RECICLABLE": "COORD_RECICLADORES",
}
RECOLECTOR_POR_FLUJO: dict[str, str] = {
    "ORGANICO": "HUERTERO",
    "RECICLABLE": "RECICLADOR",
}
TIPO_GENERADOR_POR_ROL: dict[str, str] = {
    "HOGAR": "HOGAR",
    "UNIDAD_PRODUCTIVA": "UNIDAD_PRODUCTIVA",
}
ESTADOS_ACTIVOS: frozenset[str] = frozenset(
    {"RECIBIDA", "EN_REVISION", "ASIGNADA", "PROGRAMADA"}
)
ESTADOS_CANCELABLES_POR_SOLICITANTE: frozenset[str] = frozenset(
    {"RECIBIDA", "EN_REVISION"}
)
ESTADOS_CANCELABLES_POR_COORDINACION: frozenset[str] = frozenset(
    {"RECIBIDA", "EN_REVISION", "ASIGNADA", "PROGRAMADA"}
)
CENTAVOS = Decimal("0.01")
_SQLSTATES_REINTENTABLES = frozenset({"40001", "40P01"})
_MAX_INTENTOS_CIERRE = 3


@dataclass(frozen=True)
class ResultadoCierre:
    solicitud: Solicitud
    regla_puntos_id: int
    flujo: str
    tipo_generador: str
    puntos_base_solicitud: Decimal
    puntos_por_kg: Decimal
    cantidad_real_kg: Decimal
    puntos_otorgados: Decimal
    puntos_acumulados_solicitante: Decimal
    formula: str


def _cuantizar(valor: Decimal) -> Decimal:
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _sqlstate(exc: DBAPIError) -> str | None:
    original = getattr(exc, "orig", None)
    return getattr(original, "sqlstate", None)


def _reintentable(exc: DBAPIError) -> bool:
    return _sqlstate(exc) in _SQLSTATES_REINTENTABLES


def es_coordinador_de_flujo(usuario: Usuario, flujo: str) -> bool:
    return usuario.rol == COORDINADOR_POR_FLUJO.get(flujo)


def puede_ver_solicitud(usuario: Usuario, solicitud: Solicitud) -> bool:
    """Aplica visibilidad por propiedad, flujo y asignación (RN-07)."""
    if usuario.rol == "ADMIN":
        return True
    if solicitud.solicitante_id == usuario.id:
        return True
    if es_coordinador_de_flujo(usuario, solicitud.flujo):
        return True
    return solicitud.recolector_id is not None and solicitud.recolector_id == usuario.id


def solicitud_activa_del_solicitante(
    db: Session,
    solicitante: Usuario,
) -> Solicitud | None:
    return db.scalar(
        select(Solicitud)
        .where(
            Solicitud.solicitante_id == solicitante.id,
            Solicitud.estado.in_(ESTADOS_ACTIVOS),
        )
        .order_by(Solicitud.creado_en.desc(), Solicitud.id.desc())
        .options(
            selectinload(Solicitud.solicitante),
            selectinload(Solicitud.coordinador),
            selectinload(Solicitud.recolector),
            selectinload(Solicitud.mensajes_whatsapp),
        )
        .limit(1)
    )


def _cargar_solicitud(
    db: Session,
    solicitud_id: int,
    *,
    bloquear: bool = False,
) -> Solicitud:
    stmt = (
        select(Solicitud)
        .where(Solicitud.id == solicitud_id)
        .options(selectinload(Solicitud.mensajes_whatsapp))
    )
    if bloquear:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    solicitud = db.scalars(stmt).first()
    if solicitud is None:
        raise NoEncontrado("Solicitud no encontrada.")
    return solicitud


def _cargar_solicitud_visible(
    db: Session,
    usuario: Usuario,
    solicitud_id: int,
    *,
    bloquear: bool = False,
) -> Solicitud:
    solicitud = _cargar_solicitud(db, solicitud_id, bloquear=bloquear)
    if not puede_ver_solicitud(usuario, solicitud):
        # 404 para no revelar la existencia de solicitudes de otros usuarios.
        raise NoEncontrado("Solicitud no encontrada.")
    return solicitud


def _verificar_coordinador(usuario: Usuario, flujo: str) -> None:
    if not es_coordinador_de_flujo(usuario, flujo):
        rol_requerido = COORDINADOR_POR_FLUJO.get(flujo, "coordinador del flujo")
        raise PermisoDenegado(
            f"Solo {rol_requerido} puede gestionar el flujo {flujo}.",
            codigo="FLUJO_NO_AUTORIZADO",
        )


def _verificar_admin(usuario: Usuario) -> None:
    if usuario.rol != "ADMIN":
        raise PermisoDenegado(
            "Esta operación requiere el rol ADMIN.",
            codigo="ROL_NO_AUTORIZADO",
        )


def _validar_recolector(
    db: Session,
    recolector_id: uuid.UUID,
    flujo: str,
) -> Usuario:
    recolector = db.get(Usuario, recolector_id)
    if recolector is None:
        raise Validacion(
            "RECOLECTOR_INVALIDO",
            "El recolector indicado no existe.",
        )
    if not recolector.activo:
        raise Validacion(
            "RECOLECTOR_INACTIVO",
            "El recolector indicado está inactivo.",
        )
    rol_esperado = RECOLECTOR_POR_FLUJO[flujo]
    if recolector.rol != rol_esperado:
        raise Validacion(
            "RECOLECTOR_INCOMPATIBLE",
            f"El flujo {flujo} requiere un recolector con rol {rol_esperado}.",
        )
    return recolector


def _validar_fecha_hora_programada(fecha: date, hora: hora_del_dia) -> None:
    ahora = ahora_bogota()
    if fecha < ahora.date():
        raise Validacion(
            "FECHA_PROGRAMADA_INVALIDA",
            "La fecha programada no puede estar en el pasado.",
        )
    if fecha == ahora.date() and hora <= ahora.time().replace(tzinfo=None):
        raise Validacion(
            "HORA_PROGRAMADA_INVALIDA",
            "La hora programada ya pasó para la fecha de hoy.",
        )


def _registrar_historial(
    db: Session,
    solicitud: Solicitud,
    *,
    estado_anterior: str | None,
    estado_nuevo: str,
    actor_id: uuid.UUID | None,
    nota: str | None,
) -> HistorialEstado:
    registro = HistorialEstado(
        solicitud_id=solicitud.id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        cambiado_por=actor_id,
        nota_operativa=nota,
    )
    db.add(registro)
    return registro


def _codigo_publico(solicitud_id: int) -> str:
    return f"ECO-{hoy_bogota().year}-{solicitud_id:06d}"


def crear_solicitud(
    db: Session,
    solicitante: Usuario,
    datos: SolicitudCrear,
    *,
    commit: bool = True,
) -> Solicitud:
    """Crea una solicitud RECIBIDA y enruta su flujo (RN-01)."""
    if solicitante.rol not in TIPO_GENERADOR_POR_ROL:
        raise PermisoDenegado(
            "Solo hogares y unidades productivas pueden crear solicitudes.",
            codigo="ROL_NO_AUTORIZADO",
        )
    if not solicitante.activo:
        raise PermisoDenegado(
            "La cuenta está inactiva y no puede crear solicitudes.",
            codigo="USUARIO_INACTIVO",
        )

    solicitud = Solicitud(
        codigo_publico=f"TMP-{uuid.uuid4().hex[:16]}",
        solicitante_id=solicitante.id,
        flujo=datos.flujo,
        subtipo_material=datos.subtipo_material,
        cantidad_estimada_kg=datos.cantidad_estimada_kg,
        disponibilidad_usuario=datos.disponibilidad_usuario,
        observaciones=datos.observaciones,
        estado="RECIBIDA",
    )
    db.add(solicitud)
    try:
        db.flush()
        solicitud.codigo_publico = _codigo_publico(solicitud.id)
        _registrar_historial(
            db,
            solicitud,
            estado_anterior=None,
            estado_nuevo="RECIBIDA",
            actor_id=solicitante.id,
            nota=f"Solicitud creada para el flujo {datos.flujo}.",
        )
        if commit:
            db.commit()
        else:
            db.flush()
    except IntegrityError as exc:
        if commit:
            db.rollback()
        raise Conflicto(
            "CONFLICTO_CREACION",
            "No fue posible crear la solicitud por un conflicto de datos.",
        ) from exc
    except Exception:
        if commit:
            db.rollback()
        raise

    if commit:
        db.refresh(solicitud)
    return solicitud


def listar_solicitudes(
    db: Session,
    usuario: Usuario,
    *,
    flujo: str | None = None,
    estado: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Solicitud], int]:
    """Lista solicitudes aplicando aislamiento por rol y flujo (RN-01, RN-07)."""
    filtros: list[Any] = []

    if usuario.rol == "ADMIN":
        if flujo is not None:
            filtros.append(Solicitud.flujo == flujo)
    elif usuario.rol in COORDINADOR_POR_FLUJO.values():
        flujo_propio = next(
            candidato
            for candidato, rol in COORDINADOR_POR_FLUJO.items()
            if rol == usuario.rol
        )
        if flujo is not None and flujo != flujo_propio:
            raise PermisoDenegado(
                f"El rol {usuario.rol} solo puede consultar el flujo {flujo_propio}.",
                codigo="FLUJO_NO_AUTORIZADO",
            )
        filtros.append(Solicitud.flujo == flujo_propio)
    elif usuario.rol in RECOLECTOR_POR_FLUJO.values():
        filtros.append(Solicitud.recolector_id == usuario.id)
        if flujo is not None:
            filtros.append(Solicitud.flujo == flujo)
    else:
        filtros.append(Solicitud.solicitante_id == usuario.id)
        if flujo is not None:
            filtros.append(Solicitud.flujo == flujo)

    if estado is not None:
        filtros.append(Solicitud.estado == estado)

    total = db.scalar(select(func.count(Solicitud.id)).where(*filtros)) or 0
    stmt = (
        select(Solicitud)
        .where(*filtros)
        .options(
            selectinload(Solicitud.solicitante),
            selectinload(Solicitud.coordinador),
            selectinload(Solicitud.recolector),
            selectinload(Solicitud.mensajes_whatsapp),
        )
        .order_by(Solicitud.creado_en.desc(), Solicitud.id.desc())
        .limit(limit)
        .offset(offset)
    )
    solicitudes = list(db.scalars(stmt).all())
    return solicitudes, total


def obtener_solicitud(db: Session, usuario: Usuario, solicitud_id: int) -> Solicitud:
    return _cargar_solicitud_visible(db, usuario, solicitud_id)


def revisar_solicitud(
    db: Session,
    coordinador: Usuario,
    solicitud_id: int,
    datos: RevisarSolicitud,
) -> Solicitud:
    """Pasa una solicitud de RECIBIDA a EN_REVISION."""
    solicitud = _cargar_solicitud(db, solicitud_id, bloquear=True)
    _verificar_coordinador(coordinador, solicitud.flujo)
    if solicitud.estado != "RECIBIDA":
        raise Conflicto(
            "ESTADO_INVALIDO",
            f"No se puede revisar una solicitud en estado {solicitud.estado}.",
        )
    solicitud.estado = "EN_REVISION"
    _registrar_historial(
        db,
        solicitud,
        estado_anterior="RECIBIDA",
        estado_nuevo="EN_REVISION",
        actor_id=coordinador.id,
        nota=datos.nota_operativa or "Solicitud tomada para revisión humana.",
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(solicitud)
    return solicitud


def asignar_solicitud(
    db: Session,
    coordinador: Usuario,
    solicitud_id: int,
    datos: AsignarSolicitud,
) -> Solicitud:
    """Asigna un recolector compatible y registra coordinador (RN-03)."""
    solicitud = _cargar_solicitud(db, solicitud_id, bloquear=True)
    _verificar_coordinador(coordinador, solicitud.flujo)
    if solicitud.estado not in {"RECIBIDA", "EN_REVISION"}:
        raise Conflicto(
            "ESTADO_INVALIDO",
            f"No se puede asignar una solicitud en estado {solicitud.estado}.",
        )
    recolector = _validar_recolector(db, datos.recolector_id, solicitud.flujo)

    anterior = solicitud.estado
    solicitud.estado = "ASIGNADA"
    solicitud.coordinador_id = coordinador.id
    solicitud.recolector_id = recolector.id
    _registrar_historial(
        db,
        solicitud,
        estado_anterior=anterior,
        estado_nuevo="ASIGNADA",
        actor_id=coordinador.id,
        nota=datos.nota_operativa
        or f"Asignada al recolector {recolector.nombre} ({recolector.rol}).",
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(solicitud)
    return solicitud


def programar_solicitud(
    db: Session,
    coordinador: Usuario,
    solicitud_id: int,
    datos: ProgramarSolicitud,
) -> Solicitud:
    """Programa fecha, hora y recolector; única vía humana a PROGRAMADA (RN-02)."""
    solicitud = _cargar_solicitud(db, solicitud_id, bloquear=True)
    _verificar_coordinador(coordinador, solicitud.flujo)
    if solicitud.estado not in {"RECIBIDA", "EN_REVISION", "ASIGNADA", "PROGRAMADA"}:
        raise Conflicto(
            "ESTADO_INVALIDO",
            f"No se puede programar una solicitud en estado {solicitud.estado}.",
        )
    _validar_fecha_hora_programada(datos.fecha_programada, datos.hora_programada)
    recolector = _validar_recolector(db, datos.recolector_id, solicitud.flujo)

    campos = datos.model_fields_set
    nuevo_material = (
        datos.subtipo_material
        if "subtipo_material" in campos
        else solicitud.subtipo_material
    )
    nueva_cantidad = (
        datos.cantidad_estimada_kg
        if "cantidad_estimada_kg" in campos
        else solicitud.cantidad_estimada_kg
    )
    nueva_disponibilidad = (
        datos.disponibilidad_usuario
        if "disponibilidad_usuario" in campos and datos.disponibilidad_usuario is not None
        else solicitud.disponibilidad_usuario
    )
    nuevas_observaciones = (
        datos.observaciones
        if "observaciones" in campos
        else solicitud.observaciones
    )

    if (
        solicitud.estado == "PROGRAMADA"
        and solicitud.recolector_id == recolector.id
        and solicitud.fecha_programada == datos.fecha_programada
        and solicitud.hora_programada == datos.hora_programada
        and solicitud.subtipo_material == nuevo_material
        and solicitud.cantidad_estimada_kg == nueva_cantidad
        and solicitud.disponibilidad_usuario == nueva_disponibilidad
        and solicitud.observaciones == nuevas_observaciones
    ):
        return solicitud
    anterior = solicitud.estado
    solicitud.estado = "PROGRAMADA"
    solicitud.coordinador_id = coordinador.id
    solicitud.recolector_id = recolector.id
    solicitud.fecha_programada = datos.fecha_programada
    solicitud.hora_programada = datos.hora_programada
    solicitud.subtipo_material = nuevo_material
    solicitud.cantidad_estimada_kg = nueva_cantidad
    solicitud.disponibilidad_usuario = nueva_disponibilidad
    solicitud.observaciones = nuevas_observaciones
    accion = "Reprogramada" if anterior == "PROGRAMADA" else "Programada"
    historial = _registrar_historial(
        db,
        solicitud,
        estado_anterior=anterior,
        estado_nuevo="PROGRAMADA",
        actor_id=coordinador.id,
        nota=datos.nota_operativa
        or (
            f"{accion} para {datos.fecha_programada.isoformat()} "
            f"{datos.hora_programada.strftime('%H:%M')} con "
            f"{recolector.nombre} ({recolector.rol})."
        ),
    )
    try:
        encolar(db, historial, solicitud, recolector)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(solicitud)
    return solicitud


def cancelar_solicitud(
    db: Session,
    usuario: Usuario,
    solicitud_id: int,
    datos: CancelarSolicitud,
) -> Solicitud:
    """Cancela una solicitud sin acreditar puntos."""
    solicitud = _cargar_solicitud(db, solicitud_id, bloquear=True)
    es_propietario = solicitud.solicitante_id == usuario.id
    es_coordinacion = (
        es_coordinador_de_flujo(usuario, solicitud.flujo) or usuario.rol == "ADMIN"
    )

    if not (es_propietario or es_coordinacion):
        raise PermisoDenegado("No puedes cancelar esta solicitud.")

    if es_propietario and not es_coordinacion:
        if solicitud.estado not in ESTADOS_CANCELABLES_POR_SOLICITANTE:
            raise Conflicto(
                "ESTADO_INVALIDO",
                "La solicitud ya fue asignada o programada; contacta a la coordinación.",
            )
    elif solicitud.estado not in ESTADOS_CANCELABLES_POR_COORDINACION:
        raise Conflicto(
            "ESTADO_INVALIDO",
            f"No se puede cancelar una solicitud en estado {solicitud.estado}.",
        )

    anterior = solicitud.estado
    solicitud.estado = "CANCELADA"
    _registrar_historial(
        db,
        solicitud,
        estado_anterior=anterior,
        estado_nuevo="CANCELADA",
        actor_id=usuario.id,
        nota=f"Cancelada: {datos.motivo}",
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(solicitud)
    return solicitud


def _verificar_puede_cerrar(
    actor_id: uuid.UUID,
    actor_rol: str,
    solicitud: Solicitud,
) -> None:
    if actor_rol == "ADMIN":
        return
    if actor_rol == COORDINADOR_POR_FLUJO.get(solicitud.flujo):
        return
    if (
        solicitud.recolector_id is not None
        and solicitud.recolector_id == actor_id
        and actor_rol == RECOLECTOR_POR_FLUJO.get(solicitud.flujo)
    ):
        return
    raise PermisoDenegado(
        "Solo el coordinador del flujo, el recolector asignado o un administrador "
        "pueden cerrar la solicitud.",
        codigo="CIERRE_NO_AUTORIZADO",
    )


def verificar_puede_cerrar(usuario: Usuario, solicitud: Solicitud) -> None:
    _verificar_puede_cerrar(usuario.id, usuario.rol, solicitud)


def _cerrar_intento(
    db: Session,
    *,
    actor_id: uuid.UUID,
    actor_rol: str,
    solicitud_id: int,
    cantidad_real_kg: Decimal,
    nota_operativa: str | None,
) -> ResultadoCierre:
    solicitud = _cargar_solicitud(db, solicitud_id, bloquear=True)
    _verificar_puede_cerrar(actor_id, actor_rol, solicitud)

    if solicitud.estado == "RECOLECTADA":
        raise Conflicto(
            "SOLICITUD_YA_CERRADA",
            "La solicitud ya fue cerrada; no se acreditaron puntos nuevamente.",
        )
    if solicitud.estado != "PROGRAMADA":
        raise Conflicto(
            "ESTADO_INVALIDO",
            f"Solo se puede cerrar una solicitud PROGRAMADA; estado actual: {solicitud.estado}.",
        )

    cantidad = Decimal(cantidad_real_kg)
    if not cantidad.is_finite() or cantidad <= 0:
        raise Validacion(
            "CANTIDAD_INVALIDA",
            "El peso real debe ser un número mayor que cero.",
        )
    cantidad = _cuantizar(cantidad)

    solicitante = db.scalars(
        select(Usuario)
        .where(Usuario.id == solicitud.solicitante_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if solicitante is None:
        raise Conflicto(
            "SOLICITANTE_INEXISTENTE",
            "La solicitud no tiene un solicitante válido.",
        )
    tipo_generador = TIPO_GENERADOR_POR_ROL.get(solicitante.rol)
    if tipo_generador is None:
        raise Conflicto(
            "GENERADOR_INVALIDO",
            "El tipo de generador de la solicitud no permite acreditar puntos.",
        )

    regla = db.scalars(
        select(ReglaPuntos)
        .where(
            ReglaPuntos.flujo == solicitud.flujo,
            ReglaPuntos.tipo_generador == tipo_generador,
            ReglaPuntos.activa.is_(True),
        )
        .order_by(ReglaPuntos.id.desc())
        .limit(1)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if regla is None:
        raise Conflicto(
            "REGLA_PUNTOS_NO_DISPONIBLE",
            "No hay una regla de puntos activa para el flujo y tipo de generador. "
            "Un administrador debe configurarla antes del cierre.",
        )

    base = _cuantizar(regla.puntos_base_solicitud)
    por_kg = _cuantizar(regla.puntos_por_kg)
    puntos = _cuantizar(base + por_kg * cantidad)
    nuevo_acumulado = _cuantizar(Decimal(solicitante.puntos_acumulados or 0) + puntos)

    solicitud.cantidad_real_kg = cantidad
    solicitud.puntos_otorgados = puntos
    solicitud.regla_puntos_id = regla.id
    solicitud.estado = "RECOLECTADA"
    solicitante.puntos_acumulados = nuevo_acumulado

    formula = (
        f"{base:.2f} base + {cantidad:.2f} kg × {por_kg:.2f} puntos/kg "
        f"= {puntos:.2f} EcoPuntos"
    )
    nota = (
        f"Cierre con {cantidad:.2f} kg. Regla #{regla.id} "
        f"({regla.flujo}/{regla.tipo_generador}): {formula}. "
        "Cálculo parametrizable sujeto a validación FSD."
    )
    if nota_operativa:
        nota = f"{nota} Nota de campo: {nota_operativa}"
    historial = _registrar_historial(
        db,
        solicitud,
        estado_anterior="PROGRAMADA",
        estado_nuevo="RECOLECTADA",
        actor_id=actor_id,
        nota=nota,
    )
    encolar(db, historial, solicitud, solicitud.recolector)
    db.commit()
    db.refresh(solicitud)

    return ResultadoCierre(
        solicitud=solicitud,
        regla_puntos_id=regla.id,
        flujo=regla.flujo,
        tipo_generador=regla.tipo_generador,
        puntos_base_solicitud=base,
        puntos_por_kg=por_kg,
        cantidad_real_kg=cantidad,
        puntos_otorgados=puntos,
        puntos_acumulados_solicitante=nuevo_acumulado,
        formula=formula,
    )


def cerrar_solicitud(
    db: Session,
    usuario: Usuario,
    solicitud_id: int,
    datos: CerrarSolicitud,
) -> ResultadoCierre:
    """Cierra en una transacción con bloqueo de fila y acredita puntos (RN-05/RN-06).

    Si dos cierres llegan a la vez, el segundo espera el bloqueo y recibe
    ``SOLICITUD_YA_CERRADA``; los puntos se acreditan una sola vez. Se reintenta
    ante errores de serialización o interbloqueo de PostgreSQL.
    """
    if usuario is None:
        raise PermisoDenegado(
            "El remitente no está autorizado para cerrar la solicitud.",
            codigo="CIERRE_NO_AUTORIZADO",
        )
    actor_id = usuario.id
    actor_rol = usuario.rol
    for intento in range(1, _MAX_INTENTOS_CIERRE + 1):
        try:
            resultado = _cerrar_intento(
                db,
                actor_id=actor_id,
                actor_rol=actor_rol,
                solicitud_id=solicitud_id,
                cantidad_real_kg=datos.cantidad_real_kg,
                nota_operativa=datos.nota_operativa,
            )
            return resultado
        except IntegrityError as exc:
            db.rollback()
            raise Conflicto(
                "CONFLICTO_DATOS",
                "El cierre entra en conflicto con una restricción de la base de datos.",
            ) from exc
        except DBAPIError as exc:
            db.rollback()
            if _reintentable(exc) and intento < _MAX_INTENTOS_CIERRE:
                time.sleep(0.05 * intento)
                continue
            if _reintentable(exc):
                raise Conflicto(
                    "CIERRE_CONCURRENTE",
                    "No fue posible completar el cierre por concurrencia. "
                    "Reintenta la operación.",
                ) from exc
            raise ErrorDominio(
                503,
                "ERROR_PERSISTENCIA",
                "No fue posible guardar el cierre por un problema temporal de la base de datos.",
            ) from exc
        except Exception:
            db.rollback()
            raise
    raise Conflicto(
        "CIERRE_CONCURRENTE",
        "No fue posible completar el cierre por concurrencia. Reintenta la operación.",
    )


def buscar_solicitud_por_codigo(db: Session, codigo_publico: str) -> Solicitud:
    """Busca una solicitud por su código público (uso interno de WhatsApp)."""
    codigo = (codigo_publico or "").strip().upper()
    if not codigo:
        raise Validacion("CODIGO_INVALIDO", "El código de solicitud es obligatorio.")
    solicitud = db.scalar(
        select(Solicitud)
        .where(Solicitud.codigo_publico == codigo)
        .options(
            selectinload(Solicitud.solicitante),
            selectinload(Solicitud.coordinador),
            selectinload(Solicitud.recolector),
            selectinload(Solicitud.mensajes_whatsapp),
        )
    )
    if solicitud is None:
        raise NoEncontrado("No existe una solicitud con ese código.")
    return solicitud


def cerrar_solicitud_por_codigo(
    db: Session,
    usuario: Usuario,
    codigo_publico: str,
    datos: CerrarSolicitud,
) -> ResultadoCierre:
    """Cierre compartido para el webhook: resuelve el código y delega en el servicio."""
    solicitud = buscar_solicitud_por_codigo(db, codigo_publico)
    return cerrar_solicitud(db, usuario, solicitud.id, datos)


def obtener_historial(
    db: Session,
    usuario: Usuario,
    solicitud_id: int,
) -> list[HistorialEstado]:
    """Devuelve el historial visible de una solicitud ordenado por fecha (RN-04)."""
    _cargar_solicitud_visible(db, usuario, solicitud_id)
    stmt = (
        select(HistorialEstado)
        .where(HistorialEstado.solicitud_id == solicitud_id)
        .options(joinedload(HistorialEstado.actor))
        .order_by(HistorialEstado.fecha_cambio.asc(), HistorialEstado.id.asc())
    )
    return list(db.scalars(stmt).all())


__all__ = [
    "COORDINADOR_POR_FLUJO",
    "ESTADOS_ACTIVOS",
    "RECOLECTOR_POR_FLUJO",
    "ResultadoCierre",
    "asignar_solicitud",
    "buscar_solicitud_por_codigo",
    "cancelar_solicitud",
    "cerrar_solicitud",
    "cerrar_solicitud_por_codigo",
    "crear_solicitud",
    "es_coordinador_de_flujo",
    "listar_solicitudes",
    "obtener_historial",
    "obtener_solicitud",
    "programar_solicitud",
    "puede_ver_solicitud",
    "revisar_solicitud",
    "solicitud_activa_del_solicitante",
    "verificar_puede_cerrar",
]
