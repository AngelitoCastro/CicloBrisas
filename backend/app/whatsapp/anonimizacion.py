"""Limpieza de datos personales antes de consultar al proveedor de IA."""

from __future__ import annotations

import re

_PATRONES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?<!\w)(?:\+?57[\s.-]?)?3\d{2}[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)"),
        "[TELEFONO]",
    ),
    (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"), "[CORREO]"),
    (
        re.compile(
            r"(?i)\b(calle|carrera|avenida|av\.?|diagonal|transversal)\s+[^\n,;]{1,60}"
        ),
        "[DIRECCION]",
    ),
    (
        re.compile(r"(?i)\b(señor|señora|sr\.?|sra\.?)\s+[A-Za-zÁÉÍÓÚáéíóúÑñ]+"),
        "[NOMBRE]",
    ),
)


def anonimizar(texto: str | None) -> str:
    limpio = (texto or "").strip()[:2000]
    for patron, reemplazo in _PATRONES:
        limpio = patron.sub(reemplazo, limpio)
    return limpio


__all__ = ["anonimizar"]
