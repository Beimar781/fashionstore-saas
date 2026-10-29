"""CU-22 · Indicadores empresariales (dashboard del Administrador). Capa de negocio.

Cada indicador se compara con el periodo anterior de la misma duración. Las ventas son netas de devoluciones (CU-41).
"""
from datetime import timedelta

from app.core.errors import DatosInvalidos
from app.modules.reportes.base import ReportesBase, hoy_local, inicio_del_dia
from app.modules.reportes.cu21_ventas_y_reservas import schemas as comunes
from app.modules.reportes.cu22_indicadores import schemas

PERIODOS = (7, 14, 30, 90)
MSG_PERIODO = "El periodo debe ser de 7, 14, 30 o 90 días."


def _indicador(valor, anterior) -> schemas.IndicadorOut:
    valor, anterior = float(valor), float(anterior)
    return schemas.IndicadorOut(valor=round(valor, 2), anterior=round(anterior, 2), variacion=round((valor - anterior) / anterior * 100, 1) if anterior else None)


class IndicadoresService(ReportesBase):
    def indicadores(self, dias: int, sucursal: int | None) -> schemas.IndicadoresOut:
        if dias not in PERIODOS:
            raise DatosInvalidos(MSG_PERIODO)
        sucursal = self.sucursal(sucursal)
        nombres = self.nombres()
        hasta = hoy_local()
        desde = hasta - timedelta(days=dias - 1)
        d, h = inicio_del_dia(desde), inicio_del_dia(hasta + timedelta(days=1))
        d0, h0 = d - timedelta(days=dias), d  # el periodo anterior, de la misma duración

        ahora_, antes = self.totales(d, h, sucursal), self.totales(d0, h0, sucursal)
        reservas_ahora, reservas_antes = self.repo.reservas_por_estado(d, h, sucursal), self.repo.reservas_por_estado(d0, h0, sucursal)

        def conversion(por_estado: dict[str, int]) -> float:
            total = sum(por_estado.values())
            return por_estado.get("COMPLETADA", 0) / total * 100 if total else 0.0

        return schemas.IndicadoresOut(
            dias=dias, desde=desde, hasta=hasta, sucursal_id=sucursal,
            ventas_netas=_indicador(ahora_["ventas_netas"], antes["ventas_netas"]), ventas=_indicador(ahora_["ventas"], antes["ventas"]),
            ticket_promedio=_indicador(ahora_["ticket_promedio"], antes["ticket_promedio"]),
            reservas=_indicador(sum(reservas_ahora.values()), sum(reservas_antes.values())), conversion_reservas=_indicador(conversion(reservas_ahora), conversion(reservas_antes)),
            stock=schemas.StockOut(**self.repo.inventario(sucursal)), productos_activos=self.repo.productos_activos(),
            ventas_por_dia=[comunes.DiaOut(**dia) for dia in self.ventas_por_dia(desde, hasta, d, h, sucursal)],
            por_canal=[comunes.CanalOut(canal=c, ventas=n, unidades=u, total=t) for c, (n, u, t) in sorted(self.repo.por_canal(d, h, sucursal).items())],
            por_sucursal=[comunes.SucursalVentasOut(sucursal_id=s, sucursal=nombres.get(s, ""), ventas=n, total=t) for s, n, t in self.repo.por_sucursal(d, h, sucursal)],
            reservas_por_estado=[comunes.EstadoReservaOut(estado=e, cantidad=n) for e, n in sorted(reservas_ahora.items(), key=lambda x: -x[1])],
            mas_vendidos=[comunes.ProductoVendidoOut(**p) for p in self.ranking(d, h, sucursal, None, True, 6)],
            stock_bajo_items=[schemas.StockBajoOut(sucursal_id=s, sucursal=nombres.get(s, ""), producto=p, sku=k, disponible=disp, umbral=u) for s, p, k, disp, u in self.repo.stock_bajo(sucursal, 8)],
            ultimas_ventas=[
                schemas.UltimaVentaOut(id=p.id, codigo=p.codigo, comprobante=p.comprobante_numero, sucursal=nombres.get(p.sucursal_id, ""), canal=p.canal, total=p.total, fecha=p.pagado_en)
                for p in self.repo.tickets(d, h, sucursal, None, 8)
            ],
        )
