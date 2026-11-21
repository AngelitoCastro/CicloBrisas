"""Errores de dominio compartidos por HTTP y por los servicios de WhatsApp."""

from __future__ import annotations

from collections.abc import Mapping


class ErrorDominio(Exception):
    """Error esperado del dominio, traducible a una respuesta HTTP estable."""

    def __init__(
        self,
        status_code: int,
        codigo: str,
        mensaje: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.status_code = status_code
        self.codigo = codigo
        self.mensaje = mensaje
        self.headers = dict(headers or {})


class NoAutenticado(ErrorDominio):
    def __init__(self, mensaje: str = "Debes iniciar sesión para continuar.") -> None:
        super().__init__(
            401,
            "NO_AUTENTICADO",
            mensaje,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpirado(ErrorDominio):
    def __init__(self) -> None:
        super().__init__(
            401,
            "TOKEN_EXPIRADO",
            "El token de acceso expiró. Inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenInvalido(ErrorDominio):
    def __init__(self) -> None:
        super().__init__(
            401,
            "TOKEN_INVALIDO",
            "El token de acceso no es válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermisoDenegado(ErrorDominio):
    def __init__(
        self,
        mensaje: str = "No tienes permisos para realizar esta operación.",
        codigo: str = "PERMISO_DENEGADO",
    ) -> None:
        super().__init__(403, codigo, mensaje)


class NoEncontrado(ErrorDominio):
    def __init__(self, mensaje: str = "El recurso solicitado no existe.") -> None:
        super().__init__(404, "NO_ENCONTRADO", mensaje)


class Validacion(ErrorDominio):
    def __init__(
        self,
        codigo: str,
        mensaje: str,
        status_code: int = 422,
    ) -> None:
        super().__init__(status_code, codigo, mensaje)


class Conflicto(ErrorDominio):
    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(409, codigo, mensaje)


__all__ = [
    "Conflicto",
    "ErrorDominio",
    "NoAutenticado",
    "NoEncontrado",
    "PermisoDenegado",
    "TokenExpirado",
    "TokenInvalido",
    "Validacion",
]
