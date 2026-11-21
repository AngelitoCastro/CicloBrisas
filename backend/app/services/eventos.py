"""Registro liviano de eventos de dominio posteriores al commit."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("ecoconecta.eventos")

Oyente = Callable[[str, Any], None]
_oyentes: list[Oyente] = []


def suscribir(oyente: Oyente) -> None:
    if oyente not in _oyentes:
        _oyentes.append(oyente)


def emitir(evento: str, carga: Any) -> None:
    for oyente in tuple(_oyentes):
        try:
            oyente(evento, carga)
        except Exception:
            logger.exception("Falló el oyente del evento %s", evento)


def reiniciar() -> None:
    _oyentes.clear()


__all__ = ["emitir", "reiniciar", "suscribir"]
