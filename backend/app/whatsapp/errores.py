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
            "La firma del webhook no es válida.",
            status_code=403,
        )


class CuentaTwilioInvalida(ErrorWhatsApp):
    def __init__(self) -> None:
        super().__init__(
            "WEBHOOK_CUENTA_INVALIDA",
            "La cuenta de Twilio del webhook no es válida.",
            status_code=403,
        )


class NumeroMetaInvalido(ErrorWhatsApp):
    def __init__(self) -> None:
        super().__init__(
            "WEBHOOK_NUMERO_INVALIDO",
            "El identificador del número receptor de WhatsApp no es válido.",
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


class ErrorTransitorioIA(ProveedorNoDisponible):
    """Fallo transitorio del proveedor de IA susceptible de reintento."""

    def __init__(self, proveedor: str, detalle: str = "ERROR_TRANSITORIO") -> None:
        super().__init__(proveedor)
        self.codigo = f"IA_TRANSITORIO_{detalle}"[:50]


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


class ErrorMetaDefinitivo(ErrorWhatsApp):
    """Rechazo confirmado 4xx de Graph API: el envío no se aceptó y puede reintentarse."""

    def __init__(self, codigo: str, mensaje: str = "Graph API rechazó el aviso.") -> None:
        super().__init__(codigo[:80], mensaje, status_code=502)


class ErrorMetaIncierto(ErrorWhatsApp):
    """Resultado incierto (5xx/timeout/red): esperar conciliación antes de reenviar."""

    def __init__(self, codigo: str, mensaje: str = "Resultado incierto en Graph API.") -> None:
        super().__init__(codigo[:80], mensaje, status_code=502)


__all__ = [
    "ConfiguracionIncompleta",
    "CuentaTwilioInvalida",
    "ErrorMetaDefinitivo",
    "ErrorMetaIncierto",
    "ErrorTransitorioIA",
    "ErrorWhatsApp",
    "FirmaInvalida",
    "MultimediaNoDisponible",
    "NumeroMetaInvalido",
    "ProveedorNoDisponible",
    "SalidaIAInvalida",
]
