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
            r"(?i)\b(calle|carrera|cra\.?|cll\.?|avenida|av\.?|diagonal|transversal|manzana|mz\.?|casa)\s+[^\n,;]{1,60}"
        ),
        "[DIRECCION]",
    ),
    (
        re.compile(r"(?i)\b(señor|señora|sr\.?|sra\.?)\s+[A-Za-zÁÉÍÓÚáéíóúÑñ]+"),
        "[NOMBRE]",
    ),
)


def anonimizar(
    texto: str | None,
    *,
    nombre: str | None = None,
    telefono: str | None = None,
    direccion: str | None = None,
) -> str:
    limpio = (texto or "").strip()[:2000]
    if direccion and len(direccion.strip()) >= 4:
        limpio = re.sub(re.escape(direccion.strip()), "[DIRECCION]", limpio, flags=re.I)
    if nombre and len(nombre.strip()) >= 3:
        limpio = re.sub(re.escape(nombre.strip()), "[NOMBRE]", limpio, flags=re.I)
    if telefono:
        digitos = re.sub(r"\D", "", telefono)
        variantes = {telefono.strip()}
        if digitos:
            variantes.add(digitos)
            if len(digitos) == 12 and digitos.startswith("57"):
                variantes.add(digitos[2:])
        for variante in sorted(variantes, key=len, reverse=True):
            if len(variante) >= 7:
                limpio = re.sub(re.escape(variante), "[TELEFONO]", limpio, flags=re.I)
    for patron, reemplazo in _PATRONES:
        limpio = patron.sub(reemplazo, limpio)
    return limpio


__all__ = ["anonimizar"]
