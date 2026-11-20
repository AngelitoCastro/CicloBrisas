"""Utilidades de tiempo para la operación en Villas de San Pablo (Colombia)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

# Colombia no aplica horario de verano; un desplazamiento fijo evita depender de tzdata.
ZONA_BOGOTA = timezone(timedelta(hours=-5), name="America/Bogota")


def ahora_bogota() -> datetime:
    """Devuelve la fecha y hora actual en la zona horaria de Colombia."""
    return datetime.now(ZONA_BOGOTA)


def hoy_bogota() -> date:
    """Devuelve la fecha actual en la zona horaria de Colombia."""
    return ahora_bogota().date()


__all__ = ["ZONA_BOGOTA", "ahora_bogota", "hoy_bogota"]
