"""CU-23 · Interpreta lo que el Administrador escribe o dicta y lo convierte en la especificación de un reporte.

Dos caminos (regla 12): la IA externa (Claude, por API) devuelve la especificación en JSON; si no hay clave o falla, se usan las reglas locales
(basadas en `reports/prompt_interpreter.py` del primer parcial). Lo que devuelva la IA siempre se valida: nunca se ejecuta tal cual.
"""
import re
import unicodedata
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from app.core.ia import ClienteIA


class EspecReporte(BaseModel):
    ventas: bool = False
    detalle_ventas: bool = False
    ranking: bool = False
    orden_ranking: Literal["mejores", "peores"] = "mejores"
    reservas: bool = False
    pagos: bool = False
    inventario: bool = False
    stock_bajo: bool = False
    desde: date | None = None
    hasta: date | None = None
    sucursal_id: int | None = None
    limite_ranking: int = Field(default=5, ge=1, le=20)
    limite_detalle: int = Field(default=0, ge=0, le=100)
    etiqueta_periodo: str = "Últimos 30 días"
    etiqueta_ambito: str = "Todas las sucursales"


def normalizar(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto.lower().strip())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def _contiene(texto: str, frases: tuple[str, ...]) -> bool:
    return any(f in texto for f in frases)


def _coincide(texto: str, patrones: tuple[str, ...]) -> bool:
    return any(re.search(p, texto) for p in patrones)


def _periodo(texto: str, hoy: date) -> tuple[date, date, str]:
    if _contiene(texto, ("hoy", "dia de hoy")):
        return hoy, hoy, "Hoy"
    if "ayer" in texto:
        return hoy - timedelta(days=1), hoy - timedelta(days=1), "Ayer"
    if _contiene(texto, ("ultima semana", "semana pasada", "ultimos 7 dias", "ultimos siete dias")):
        return hoy - timedelta(days=6), hoy, "Últimos 7 días"
    if _contiene(texto, ("este mes", "mes actual", "mes en curso")):
        return hoy.replace(day=1), hoy, "Mes en curso"
    if _contiene(texto, ("mes pasado", "mes anterior")):
        fin = hoy.replace(day=1) - timedelta(days=1)
        return fin.replace(day=1), fin, "Mes anterior"
    if _contiene(texto, ("ultimo mes", "ultimos 30 dias", "ultimos treinta dias")):
        return hoy - timedelta(days=29), hoy, "Últimos 30 días"
    iso = re.search(r"(\d{4}-\d{2}-\d{2})\s*(?:a|hasta|-)\s*(\d{4}-\d{2}-\d{2})", texto)
    if iso:
        try:
            ini, fin = date.fromisoformat(iso.group(1)), date.fromisoformat(iso.group(2))
            if ini <= fin and (fin - ini).days <= 365:
                return ini, fin, f"{ini.isoformat()} → {fin.isoformat()}"
        except ValueError:
            pass
    return hoy - timedelta(days=29), hoy, "Últimos 30 días"


def _sucursal(texto: str, sucursales: list[tuple[int, str]]) -> tuple[int | None, str]:
    for sucursal_id, nombre in sucursales:
        palabras = [p for p in normalizar(nombre).split() if len(p) >= 4 and p != "sucursal"]
        if any(re.search(rf"\b{re.escape(p)}\b", texto) for p in palabras):
            return sucursal_id, f"Sucursal {nombre.removeprefix('Sucursal ').strip()}"
    return None, "Todas las sucursales"


def interpretar_con_reglas(prompt: str, hoy: date, sucursales: list[tuple[int, str]]) -> EspecReporte:
    """Modo de respaldo: reconoce temas (ventas, ranking, reservas, pagos, inventario), periodo y sucursal por palabras clave."""
    t = normalizar(prompt)
    ventas = _coincide(t, (r"\bventas?\b", r"\bvendid", r"\bingresos?\b", r"\bfactur", r"\bpedidos?\b", r"\btickets?\b", r"\bcobr"))
    detalle = _contiene(t, ("todas las ventas", "lista de ventas", "listado de ventas", "detalle de ventas", "desglose", "cada venta")) or ("todas" in t and "venta" in t)
    peores = _coincide(t, (r"\bmenos vend", r"\bvende menos\b", r"\bpeor producto\b", r"\bmenor venta\b", r"\bbottom\b"))
    mejores = _contiene(t, ("mejor producto", "mas vendido", "producto estrella", "top producto")) or ("mejor" in t and "producto" in t and not peores)
    ranking = mejores or peores or _contiene(t, ("ranking", "que producto", "cual producto"))
    reservas = _contiene(t, ("reserva", "probador"))
    pagos = _coincide(t, (r"\bpagos?\b", r"\brechazad", r"\bpendientes? de confirmacion"))
    inventario = _coincide(t, (r"\binventarios?\b", r"\bexistencias?\b", r"\bstock\b"))
    stock_bajo = _contiene(t, ("stock bajo", "reposicion", "alerta de stock", "minimo")) or inventario
    if not any((ventas, ranking, reservas, pagos, inventario)):  # no se reconoció un tema: se muestra un resumen general
        ventas = reservas = inventario = ranking = True
        stock_bajo = True
    desde, hasta, etiqueta = _periodo(t, hoy)
    sucursal_id, ambito = _sucursal(t, sucursales)
    limite = 10 if _contiene(t, ("top 10", "diez productos", "10 productos")) else 3 if _contiene(t, ("top 3", "tres productos", "3 productos")) else 5
    limite_detalle = (10 if "10 ventas" in t or "ultimas 10" in t else 20 if "20 ventas" in t or "ultimas 20" in t else 50) if detalle else 0
    return EspecReporte(
        ventas=ventas, detalle_ventas=detalle, ranking=ranking, orden_ranking="peores" if peores and not mejores else "mejores", reservas=reservas, pagos=pagos,
        inventario=inventario, stock_bajo=stock_bajo, desde=desde, hasta=hasta, sucursal_id=sucursal_id, limite_ranking=limite, limite_detalle=limite_detalle,
        etiqueta_periodo=etiqueta, etiqueta_ambito=ambito,
    )


SISTEMA_IA = (
    "Eres el intérprete de reportes de una tienda de ropa. Convierte la petición del administrador en una especificación JSON y responde SOLO el JSON, "
    "sin texto adicional. Campos: ventas, detalle_ventas, ranking, reservas, pagos, inventario, stock_bajo (booleanos); orden_ranking ('mejores' o 'peores'); "
    "desde y hasta (fechas AAAA-MM-DD o null); sucursal_id (uno de los ids dados o null); limite_ranking (1 a 20); limite_detalle (0 a 100); "
    "etiqueta_periodo y etiqueta_ambito (textos cortos en español). Si la petición no menciona un tema, activa ventas, reservas e inventario."
)


def interpretar_con_ia(ia: ClienteIA, prompt: str, hoy: date, sucursales: list[tuple[int, str]]) -> EspecReporte | None:
    """La especificación que propone la IA, validada; None si no hay IA, si falló o si propuso algo inválido (se usan las reglas)."""
    usuario = f"Hoy es {hoy.isoformat()}.\nSucursales: {[{'id': i, 'nombre': n} for i, n in sucursales]}\nPetición: {prompt}"
    crudo = ia.json_estructurado(SISTEMA_IA, usuario)
    if crudo is None:
        return None
    try:
        espec = EspecReporte.model_validate(crudo)
        if espec.sucursal_id is not None and espec.sucursal_id not in {i for i, _ in sucursales}:
            return None
        if espec.desde and espec.hasta and (espec.desde > espec.hasta or (espec.hasta - espec.desde).days > 365):
            return None
        if espec.desde is None or espec.hasta is None:
            espec.desde, espec.hasta = hoy - timedelta(days=29), hoy
        if not any((espec.ventas, espec.ranking, espec.reservas, espec.pagos, espec.inventario, espec.stock_bajo)):
            return None
        return espec
    except Exception:
        return None
