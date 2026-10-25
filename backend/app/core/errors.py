"""Errores de negocio con mensaje controlado (los textos provienen de las fichas de CU)."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str, *, extra: dict | None = None):
        super().__init__(message)
        self.message = message
        self.extra = extra or {}


class NoAutenticado(AppError):
    status_code = 401


class Prohibido(AppError):
    status_code = 403


class NoEncontrado(AppError):
    status_code = 404


class Conflicto(AppError):
    status_code = 409


class DatosInvalidos(AppError):
    status_code = 422


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, **exc.extra})

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errores = exc.errors()
        primero = errores[0] if errores else {}
        msg = str(primero.get("msg", "Datos inválidos"))
        if primero.get("type") == "value_error":
            msg = msg.removeprefix("Value error, ")
        else:
            campo = ".".join(str(p) for p in primero.get("loc", ())[1:])
            msg = f"{campo}: {msg}" if campo else msg
        return JSONResponse(status_code=422, content={"detail": msg})
