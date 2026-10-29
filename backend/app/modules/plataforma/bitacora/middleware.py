"""Middleware de la bitácora: registra, sin tocar cada caso de uso, los inicios y cierres de sesión, los intentos de ingreso fallidos y toda operación de escritura
(POST, PUT, PATCH, DELETE) terminada con éxito por un usuario con sesión. Las consultas (GET) no se registran.

Quién la hizo sale del token (o de la respuesta, en el login y el registro); qué hizo, de la tabla de etiquetas. Un fallo al registrar nunca rompe la operación.
Nunca se guardan contraseñas, tokens ni datos de tarjeta: el cuerpo de la petición solo se usa para completar el texto del detalle.
"""
import json
import logging

from fastapi import FastAPI, Request, Response
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import get_db
from app.core.security import decodificar_token
from app.modules.acceso.models import Usuario
from app.modules.plataforma.bitacora import etiquetas
from app.modules.plataforma.bitacora.service import registrar
from app.modules.plataforma.models import Empresa

logger = logging.getLogger(__name__)
ESCRITURA = {"POST", "PUT", "PATCH", "DELETE"}
MAX_RESPUESTA = 1_000_000  # no se analizan respuestas más grandes que 1 MB
POR_METODO = {"POST": "CREAR", "PUT": "MODIFICAR", "PATCH": "MODIFICAR", "DELETE": "ELIMINAR"}


def ip_del_cliente(request: Request) -> str | None:
    """La IP real: con proxy (nube) viene en X-Forwarded-For; el primer valor es el cliente."""
    reenviada = request.headers.get("x-forwarded-for", "")
    if reenviada.strip():
        return reenviada.split(",")[0].strip()[:45]
    return request.client.host[:45] if request.client else None


def _json(texto: bytes | str) -> dict:
    try:
        dato = json.loads(texto)
        return dato if isinstance(dato, dict) else {}
    except (ValueError, TypeError):
        return {}


class BitacoraMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in ESCRITURA or not request.url.path.startswith("/api/"):
            return await call_next(request)
        cuerpo = {}
        if "json" in request.headers.get("content-type", ""):  # los archivos (imágenes) no se leen
            cuerpo = _json(await request.body())
        respuesta = await call_next(request)
        contenido = b"".join([parte async for parte in respuesta.body_iterator])
        nueva = Response(contenido, status_code=respuesta.status_code, headers=dict(respuesta.headers), media_type=respuesta.media_type)
        try:
            datos = _json(contenido) if len(contenido) <= MAX_RESPUESTA and "json" in respuesta.headers.get("content-type", "") else {}
            token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
            await run_in_threadpool(_registrar, request.app, request.method, request.url.path, respuesta.status_code, cuerpo, datos, token, ip_del_cliente(request))
        except Exception:  # noqa: BLE001  la bitácora nunca deshace ni rompe la operación
            logger.exception("No se pudo registrar en la bitácora %s %s", request.method, request.url.path)
        return nueva


def _abrir(app: FastAPI):
    """La misma sesión de base de datos que usa la aplicación (las pruebas la reemplazan con `dependency_overrides`)."""
    generador = app.dependency_overrides.get(get_db, get_db)()
    return next(generador), generador


def _registrar(app: FastAPI, metodo: str, ruta: str, estado: int, cuerpo: dict, respuesta: dict, token: str, ip: str | None) -> None:
    exito = 200 <= estado < 300
    es_login = ruta == "/api/auth/login"
    if not exito and not (es_login and estado in (401, 403, 429)):
        return  # solo lo que terminó bien; y el ingreso fallido
    db, generador = _abrir(app)
    try:
        if es_login and not exito:
            _login_fallido(db, cuerpo, ip)
            return
        hallada = etiquetas.buscar(metodo, ruta)
        etiqueta, parametros = hallada if hallada else (None, {})
        if etiqueta is not None and etiqueta.accion is None:
            return  # consultas disfrazadas de POST y operaciones sin valor de auditoría
        actor = _actor(db, etiqueta.sesion if etiqueta else "token", token, respuesta, cuerpo)
        if actor is None:
            return  # sin sesión válida no hay a quién atribuirle la operación
        if isinstance(cuerpo.get("operaciones"), list):
            cuerpo = {**cuerpo, "n_operaciones": len(cuerpo["operaciones"])}
        if etiqueta is None:
            accion, entidad, detalle, regla_empresa = POR_METODO[metodo], etiquetas.GENERICA[1], etiquetas.GENERICA[0], "usuario"
        else:
            accion, entidad, regla_empresa = etiqueta.accion, etiqueta.entidad, etiqueta.empresa
            detalle = etiquetas.construir_detalle(etiqueta.detalle, parametros, cuerpo, respuesta)
        entidad_id = respuesta.get("id") if isinstance(respuesta.get("id"), int) else next((int(v) for v in parametros.values() if v.isdigit()), None)
        registrar(
            db, empresa_id=etiquetas.resolver_empresa(regla_empresa, actor["empresa_id"], parametros, respuesta), usuario_id=actor["id"], usuario=actor["nombre"], rol=actor["rol"],
            accion=accion, entidad=entidad, detalle=detalle, ip=ip, entidad_id=entidad_id,
        )
    finally:
        generador.close()


def _actor(db, sesion: str, token: str, respuesta: dict, cuerpo: dict) -> dict | None:
    if sesion == "visitante":
        return {"id": None, "nombre": str(cuerpo.get("email") or "Visitante"), "rol": None, "empresa_id": None}
    if sesion == "respuesta":  # login y registro: el usuario viene en la respuesta
        u, e = respuesta.get("usuario") or {}, respuesta.get("empresa") or {}
        if not u.get("id"):
            return None
        return {"id": u["id"], "nombre": f"{u.get('nombre', '')} {u.get('apellidos', '')}".strip() or u.get("email", ""), "rol": u.get("rol"), "empresa_id": e.get("id")}
    try:
        usuario = db.get(Usuario, int(decodificar_token(token, "access")["sub"]))
    except Exception:  # noqa: BLE001  token inválido o vencido
        return None
    if usuario is None:
        return None
    return {"id": usuario.id, "nombre": f"{usuario.nombre} {usuario.apellidos}".strip(), "rol": usuario.rol.nombre, "empresa_id": usuario.empresa_id}


def _login_fallido(db, cuerpo: dict, ip: str | None) -> None:
    """Un intento de ingreso que no prosperó. Se guarda el correo y el código de empresa que se intentó, NUNCA la contraseña."""
    email = str(cuerpo.get("email") or "").strip().lower()[:150] or "(sin correo)"
    codigo = str(cuerpo.get("codigo_empresa") or "").strip()
    empresa_id = db.scalar(select(Empresa.id).where(Empresa.codigo == codigo)) if codigo else None
    detalle = f"Intento fallido de inicio de sesión con el correo {email}" + (f" en la empresa {codigo}" if codigo else "")
    registrar(db, empresa_id=empresa_id, usuario_id=None, usuario=email, rol=None, accion="LOGIN_FALLIDO", entidad="sesión", detalle=detalle, ip=ip)
