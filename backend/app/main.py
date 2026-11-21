"""Punto de entrada FastAPI de EcoConecta (`app.main:app`)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import admin, auth, catalogos, solicitudes, whatsapp
from app.schemas import HealthResponse
from app.services import eventos
from app.services.errors import ErrorDominio
from app.whatsapp.notificaciones import manejar_evento

logger = logging.getLogger("ecoconecta.api")
eventos.suscribir(manejar_evento)


def _detalle_error(codigo: str, mensaje: str, **extra: Any) -> dict[str, Any]:
    detalle: dict[str, Any] = {"codigo": codigo, "mensaje": mensaje}
    detalle.update(extra)
    return {"detail": detalle}


def crear_app() -> FastAPI:
    app = FastAPI(
        title="EcoConecta API",
        version="0.1.0",
        description=(
            "API del MVP comunitario de EcoConecta (Villas de San Pablo). "
            "Gestiona solicitudes de recolección orgánica y reciclable, "
            "programación humana, historial auditable, cierre transaccional con "
            "puntos parametrizables y administración de reglas y cuentas piloto. "
            "Los datos de contacto se devuelven únicamente al propietario, al "
            "coordinador del flujo, al recolector asignado y al administrador (RN-07)."
        ),
        openapi_tags=[
            {
                "name": "Autenticación",
                "description": "Login con bcrypt y JWT; consulta de la cuenta.",
            },
            {
                "name": "Solicitudes",
                "description": "Alta, consulta, programación, historial y cierre.",
            },
            {
                "name": "Catálogo",
                "description": "Reglas de puntos activas para mostrar al usuario.",
            },
            {
                "name": "Administración",
                "description": "Reglas de puntos y modo piloto (solo ADMIN).",
            },
            {
                "name": "WhatsApp",
                "description": "Webhook firmado de WhatsApp con Twilio y asistente OpenAI o Azure OpenAI.",
            },
            {
                "name": "Salud",
                "description": "Verificación de disponibilidad de la API.",
            },
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
    app.include_router(
        solicitudes.router, prefix="/api/solicitudes", tags=["Solicitudes"]
    )
    app.include_router(catalogos.router, prefix="/api", tags=["Catálogo"])
    app.include_router(admin.router, prefix="/api/admin", tags=["Administración"])
    app.include_router(whatsapp.router)

    @app.get("/health", response_model=HealthResponse, tags=["Salud"])
    def health() -> HealthResponse:
        return HealthResponse(estado="ok", servicio="ecoconecta-api")

    @app.get("/api/health", response_model=HealthResponse, tags=["Salud"])
    def health_api() -> HealthResponse:
        return HealthResponse(estado="ok", servicio="ecoconecta-api")

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "servicio": "EcoConecta API",
            "version": "0.1.0",
            "documentacion": "/docs",
            "salud": "/health",
        }

    @app.exception_handler(ErrorDominio)
    async def manejar_error_dominio(
        request: Request,
        exc: ErrorDominio,
    ) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=exc.status_code,
            content=_detalle_error(exc.codigo, exc.mensaje),
            headers=exc.headers or None,
        )

    @app.exception_handler(RequestValidationError)
    async def manejar_validacion(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        del request
        errores = []
        for error in exc.errors():
            ubicacion = [
                str(parte)
                for parte in error.get("loc", ())
                if parte not in {"body", "query", "path", "header"}
            ]
            errores.append(
                {
                    "campo": ".".join(ubicacion) or "cuerpo",
                    "mensaje": str(error.get("msg", "Valor inválido.")),
                    "tipo": str(error.get("type", "valor_invalido")),
                }
            )
        return JSONResponse(
            status_code=422,
            content=_detalle_error(
                "VALIDACION",
                "La petición contiene datos inválidos.",
                errores=errores,
            ),
        )

    @app.exception_handler(IntegrityError)
    async def manejar_integridad(
        request: Request,
        exc: IntegrityError,
    ) -> JSONResponse:
        del request
        # No se registra el detalle SQL para no filtrar datos personales.
        logger.warning(
            "Conflicto de integridad en base de datos: %s", type(exc).__name__
        )
        return JSONResponse(
            status_code=409,
            content=_detalle_error(
                "CONFLICTO_DATOS",
                "La operación entra en conflicto con datos existentes.",
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def manejar_http(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        del request
        if isinstance(exc.detail, dict):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers or None,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=_detalle_error(
                "ERROR_HTTP",
                str(exc.detail),
            ),
            headers=exc.headers or None,
        )

    @app.exception_handler(Exception)
    async def manejar_inesperado(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Error no controlado en %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content=_detalle_error(
                "ERROR_INTERNO",
                "Ocurrió un error interno. Intenta nuevamente más tarde.",
            ),
        )

    return app


app = crear_app()

__all__ = ["app", "crear_app"]
