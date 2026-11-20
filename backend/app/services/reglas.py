"""Servicios de administración de reglas de puntos adaptables (RN-06)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ReglaPuntos, Usuario
from app.schemas import ReglaPuntosActualizar, ReglaPuntosCrear
from app.services.errors import Conflicto, NoEncontrado, PermisoDenegado, Validacion


def _verificar_admin(usuario: Usuario) -> None:
    if usuario.rol != "ADMIN":
        raise PermisoDenegado(
            "Solo el administrador puede gestionar las reglas de puntos.",
            codigo="ROL_NO_AUTORIZADO",
        )


def _validar_no_negativos(datos: ReglaPuntosCrear) -> None:
    if min(
        datos.puntos_base_solicitud,
        datos.puntos_por_kg,
        datos.valor_referencia_kg_cop,
    ) < 0:
        raise Validacion(
            "VALORES_NO_NEGATIVOS",
            "Los parámetros de puntos y valor de referencia no pueden ser negativos.",
        )


def listar_reglas_admin(
    db: Session,
    usuario: Usuario,
    *,
    flujo: str | None = None,
    tipo_generador: str | None = None,
    activa: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[ReglaPuntos], int]:
    _verificar_admin(usuario)
    filtros = []
    if flujo is not None:
        filtros.append(ReglaPuntos.flujo == flujo)
    if tipo_generador is not None:
        filtros.append(ReglaPuntos.tipo_generador == tipo_generador)
    if activa is not None:
        filtros.append(ReglaPuntos.activa.is_(activa))

    total = db.scalar(select(func.count(ReglaPuntos.id)).where(*filtros)) or 0
    reglas = list(
        db.scalars(
            select(ReglaPuntos)
            .where(*filtros)
            .order_by(
                ReglaPuntos.flujo.asc(),
                ReglaPuntos.tipo_generador.asc(),
                ReglaPuntos.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return reglas, total


def listar_reglas_activas(db: Session) -> list[ReglaPuntos]:
    """Reglas activas legibles por cualquier usuario autenticado."""
    return list(
        db.scalars(
            select(ReglaPuntos)
            .where(ReglaPuntos.activa.is_(True))
            .order_by(
                ReglaPuntos.flujo.asc(),
                ReglaPuntos.tipo_generador.asc(),
                ReglaPuntos.id.desc(),
            )
        ).all()
    )


def crear_regla(
    db: Session,
    admin: Usuario,
    datos: ReglaPuntosCrear,
) -> ReglaPuntos:
    """Crea una regla; si se activa, reemplaza la activa del mismo par."""
    _verificar_admin(admin)
    _validar_no_negativos(datos)

    if datos.activa:
        activas = db.scalars(
            select(ReglaPuntos)
            .where(
                ReglaPuntos.flujo == datos.flujo,
                ReglaPuntos.tipo_generador == datos.tipo_generador,
                ReglaPuntos.activa.is_(True),
            )
            .with_for_update()
        ).all()
        for anterior in activas:
            anterior.activa = False
        if activas:
            db.flush()

    regla = ReglaPuntos(
        flujo=datos.flujo,
        tipo_generador=datos.tipo_generador,
        puntos_base_solicitud=datos.puntos_base_solicitud,
        puntos_por_kg=datos.puntos_por_kg,
        valor_referencia_kg_cop=datos.valor_referencia_kg_cop,
        descripcion_regla=datos.descripcion_regla,
        activa=datos.activa,
    )
    db.add(regla)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise Conflicto(
            "REGLA_ACTIVA_DUPLICADA",
            "Ya existe una regla activa para ese flujo y tipo de generador.",
        ) from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(regla)
    return regla


def actualizar_regla(
    db: Session,
    admin: Usuario,
    regla_id: int,
    datos: ReglaPuntosActualizar,
) -> ReglaPuntos:
    """Actualiza parámetros o activa una regla existente sin borrar historia."""
    _verificar_admin(admin)

    regla = db.scalars(
        select(ReglaPuntos)
        .where(ReglaPuntos.id == regla_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if regla is None:
        raise NoEncontrado("Regla de puntos no encontrada.")

    cambios = datos.model_dump(exclude_unset=True, exclude_none=True)
    if not cambios:
        raise Validacion(
            "SIN_CAMBIOS",
            "No se indicó ningún valor efectivo para actualizar.",
        )

    for campo in ("puntos_base_solicitud", "puntos_por_kg", "valor_referencia_kg_cop"):
        valor = cambios.get(campo)
        if valor is not None and valor < 0:
            raise Validacion(
                "VALORES_NO_NEGATIVOS",
                "Los parámetros de puntos y valor de referencia no pueden ser negativos.",
            )

    activando = cambios.get("activa") is True
    if activando:
        otras_activas = db.scalars(
            select(ReglaPuntos)
            .where(
                ReglaPuntos.flujo == regla.flujo,
                ReglaPuntos.tipo_generador == regla.tipo_generador,
                ReglaPuntos.activa.is_(True),
                ReglaPuntos.id != regla.id,
            )
            .with_for_update()
        ).all()
        for otra in otras_activas:
            otra.activa = False
        if otras_activas:
            db.flush()

    for campo, valor in cambios.items():
        setattr(regla, campo, valor)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise Conflicto(
            "REGLA_ACTIVA_DUPLICADA",
            "Ya existe otra regla activa para ese flujo y tipo de generador.",
        ) from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(regla)
    return regla


__all__ = [
    "actualizar_regla",
    "crear_regla",
    "listar_reglas_activas",
    "listar_reglas_admin",
]
