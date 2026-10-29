"""Lo que comparten los reportes (CU-21, CU-22) y el reporte generativo (CU-23): periodo, sucursal y totales netos de devoluciones."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import DatosInvalidos, NoEncontrado
from app.core.tiempo import a_local, zona_local
from app.modules.acceso.dependencias import Contexto
from app.modules.reportes.repository import CERO, ReportesRepository
from app.modules.sucursales.publico import nombres_de_sucursales, sucursal_de_empresa

MSG_PERIODO = "La fecha inicial no puede ser posterior a la final."
MSG_PERIODO_LARGO = "El periodo no puede superar 366 días."
MSG_SUCURSAL = "Sucursal no encontrada."


def hoy_local() -> date:
    return a_local(datetime.now(zona_local())).date()


def inicio_del_dia(dia: date) -> datetime:
    return datetime.combine(dia, time.min, tzinfo=zona_local())


class ReportesBase:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id
        self.repo = ReportesRepository(db, ctx.empresa_id)

    def periodo(self, desde: date | None, hasta: date | None, dias_por_defecto: int = 30) -> tuple[date, date, datetime, datetime]:
        """Fechas locales inclusivas (por defecto, los últimos 30 días) y los instantes que las acotan."""
        hasta = hasta or hoy_local()
        desde = desde or hasta - timedelta(days=dias_por_defecto - 1)
        if desde > hasta:
            raise DatosInvalidos(MSG_PERIODO)
        if (hasta - desde).days > 365:
            raise DatosInvalidos(MSG_PERIODO_LARGO)
        return desde, hasta, inicio_del_dia(desde), inicio_del_dia(hasta + timedelta(days=1))

    def sucursal(self, sucursal_id: int | None) -> int | None:
        if sucursal_id is not None and not sucursal_de_empresa(self.db, self.empresa_id, sucursal_id):
            raise NoEncontrado(MSG_SUCURSAL)  # también si es de otra empresa
        return sucursal_id

    def nombres(self) -> dict[int, str]:
        return nombres_de_sucursales(self.db, self.empresa_id)

    def totales(self, d: datetime, h: datetime, sucursal_id: int | None, canal: str | None = None) -> dict:
        """Ventas brutas del periodo y ventas netas: lo vendido, menos lo devuelto, más lo entregado en cambios (CU-41)."""
        canales = self.repo.por_canal(d, h, sucursal_id, canal)
        ventas = sum(n for n, _, _ in canales.values())
        unidades = sum(u for _, u, _ in canales.values())
        bruto = sum((t for _, _, t in canales.values()), CERO)
        notas, devuelto, nuevo = self.repo.devoluciones(d, h, sucursal_id, canal)
        return {
            "ventas": ventas, "unidades": unidades, "total_bruto": bruto, "devoluciones": notas, "devuelto": devuelto, "entregado_en_cambios": nuevo,
            "ventas_netas": bruto - devuelto + nuevo, "ticket_promedio": (bruto / ventas).quantize(Decimal("0.01")) if ventas else CERO,
        }

    def ventas_por_dia(self, desde: date, hasta: date, d: datetime, h: datetime, sucursal_id: int | None, canal: str | None = None) -> list[dict]:
        acumulado: dict[date, list] = {}
        for momento, total in self.repo.ventas_con_fecha(d, h, sucursal_id, canal):
            fila = acumulado.setdefault(a_local(momento).date(), [0, CERO])
            fila[0] += 1
            fila[1] += total
        dias = (hasta - desde).days + 1
        return [{"fecha": dia, "ventas": acumulado.get(dia, [0, CERO])[0], "total": acumulado.get(dia, [0, CERO])[1]} for dia in (desde + timedelta(days=i) for i in range(dias))]

    def ranking(self, d: datetime, h: datetime, sucursal_id: int | None, canal: str | None, mejores: bool, limite: int) -> list[dict]:
        filas = [(p, u, i) for p, u, i in self.repo.productos_netos(d, h, sucursal_id, canal) if u > 0]
        filas.sort(key=lambda f: (-f[1], -f[2]) if mejores else (f[1], f[2]))
        return [{"producto": p, "unidades": u, "ingresos": i} for p, u, i in filas[:limite]]
