"""Errores específicos del adaptador de WhatsApp."""

from __future__ import annotations

from app.services.errors import ErrorDominio


class ErrorWhatsApp(ErrorDominio):
    def __init__(self, codigo: str, mensaje: str, status_code: int = 502) -> None:
        super().__init__(status_code, codigo, mensaje)


class FirmaInvalida(ErrorWhatsApp):
    def __init__(self) -> None:
        super().__init__(
            "WEBHOOK_FIRMA_INVALIDA",
            "La firma del webhook de Twilio no es válida.",
            status_code=403,
        )


class CuentaTwilioInvalida(ErrorWhatsApp):
    def __init__(self) -> None:
        super().__init__(
            "WEBHOOK_CUENTA_INVALIDA",
            "La cuenta de Twilio del webhook no es válida.",
            status_code=403,
        )


class ConfiguracionIncompleta(ErrorWhatsApp):
    def __init__(self, variable: str) -> None:
        super().__init__(
            "WHATSAPP_CONFIGURACION_INCOMPLETA",
            f"Falta configurar {variable}.",
            status_code=503,
        )


class ProveedorNoDisponible(ErrorWhatsApp):
    def __init__(self, proveedor: str) -> None:
        super().__init__(
            "IA_PROVEEDOR_NO_DISPONIBLE",
            f"No fue posible consultar al proveedor {proveedor}.",
            status_code=502,
        )


class SalidaIAInvalida(ErrorWhatsApp):
    def __init__(self) -> None:
        super().__init__(
            "IA_SALIDA_INVALIDA",
            "La respuesta de la IA no tuvo el formato esperado.",
            status_code=502,
        )


class MultimediaNoDisponible(ErrorWhatsApp):
    def __init__(self) -> None:
        super().__init__(
            "MULTIMEDIA_NO_DISPONIBLE",
            "No fue posible descargar el archivo enviado.",
            status_code=502,
        )


__all__ = [
    "ConfiguracionIncompleta",
    "CuentaTwilioInvalida",
    "ErrorWhatsApp",
    "FirmaInvalida",
    "MultimediaNoDisponible",
    "ProveedorNoDisponible",
    "SalidaIAInvalida",
]
