"""Servicios de administración de usuarios y modo piloto (RN-08)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Usuario
from app.services.errors import NoEncontrado, PermisoDenegado, Validacion

ROLES_EXTERNOS = frozenset({"HOGAR", "UNIDAD_PRODUCTIVA"})
ROL_RECOLECTOR_POR_FLUJO: dict[str, str] = {
    "ORGANICO": "HUERTERO",
    "RECICLABLE": "RECICLADOR",
}
FLUJO_POR_COORDINADOR: dict[str, str] = {
    "COORD_HUERTEROS": "ORGANICO",
    "COORD_RECICLADORES": "RECICLABLE",
}


def _verificar_admin(usuario: Usuario) -> None:
    if usuario.rol != "ADMIN":
        raise PermisoDenegado(
            "Solo el administrador puede gestionar cuentas y el modo piloto.",
            codigo="ROL_NO_AUTORIZADO",
        )


def listar_usuarios_admin(
    db: Session,
    admin: Usuario,
    *,
    rol: str | None = None,
    es_piloto: bool | None = None,
    activo: bool | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Usuario], int]:
    _verificar_admin(admin)
    filtros = []
    if rol is not None:
        filtros.append(Usuario.rol == rol)
    if es_piloto is not None:
        filtros.append(Usuario.es_piloto.is_(es_piloto))
    if activo is not None:
        filtros.append(Usuario.activo.is_(activo))
    if q:
        patron = f"%{q.strip().lower()}%"
        filtros.append(
            or_(
                func.lower(Usuario.nombre).like(patron),
                func.lower(Usuario.telefono).like(patron),
                func.lower(func.coalesce(Usuario.sector_manzana, "")).like(patron),
            )
        )

    total = db.scalar(select(func.count(Usuario.id)).where(*filtros)) or 0
    usuarios = list(
        db.scalars(
            select(Usuario)
            .where(*filtros)
            .order_by(Usuario.rol.asc(), Usuario.nombre.asc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return usuarios, total


def cambiar_modo_piloto(
    db: Session,
    admin: Usuario,
    usuario_id: uuid.UUID,
    es_piloto: bool,
) -> Usuario:
    """Activa o desactiva la etiqueta piloto de hogares y unidades productivas.

    ``es_piloto`` documenta la población piloto FSD; por sí solo no restringe
    acceso ni funcionalidades (RN-08).
    """
    _verificar_admin(admin)
    usuario = db.scalars(
        select(Usuario)
        .where(Usuario.id == usuario_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if usuario is None:
        raise NoEncontrado("Usuario no encontrado.")
    if usuario.rol not in ROLES_EXTERNOS:
        raise Validacion(
            "USUARIO_NO_APLICA_PILOTO",
            "El modo piloto solo aplica a HOGAR y UNIDAD_PRODUCTIVA.",
        )
    usuario.es_piloto = es_piloto
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(usuario)
    return usuario


def listar_recolectores_activos(
    db: Session,
    usuario: Usuario,
    *,
    flujo: str | None = None,
) -> list[Usuario]:
    """Lista recolectores activos permitidos para coordinadores y administración.

    Respeta la separación de flujos (RN-01): un coordinador solo consulta los
    recolectores de su colectivo; solicitar el otro flujo responde 403.
    """
    if usuario.rol in FLUJO_POR_COORDINADOR:
        flujo_propio = FLUJO_POR_COORDINADOR[usuario.rol]
        if flujo is not None and flujo != flujo_propio:
            raise PermisoDenegado(
                f"Tu coordinación solo puede consultar recolectores del flujo {flujo_propio}.",
                codigo="FLUJO_NO_AUTORIZADO",
            )
        roles = [ROL_RECOLECTOR_POR_FLUJO[flujo_propio]]
    elif usuario.rol == "ADMIN":
        if flujo is not None:
            roles = [ROL_RECOLECTOR_POR_FLUJO[flujo]]
        else:
            roles = ["HUERTERO", "RECICLADOR"]
    else:
        raise PermisoDenegado(
            "Solo coordinadores y administradores pueden consultar el catálogo de recolectores.",
            codigo="ROL_NO_AUTORIZADO",
        )

    return list(
        db.scalars(
            select(Usuario)
            .where(Usuario.activo.is_(True), Usuario.rol.in_(roles))
            .order_by(Usuario.rol.asc(), Usuario.nombre.asc())
        ).all()
    )


__all__ = [
    "FLUJO_POR_COORDINADOR",
    "ROLES_EXTERNOS",
    "ROL_RECOLECTOR_POR_FLUJO",
    "cambiar_modo_piloto",
    "listar_recolectores_activos",
    "listar_usuarios_admin",
]
