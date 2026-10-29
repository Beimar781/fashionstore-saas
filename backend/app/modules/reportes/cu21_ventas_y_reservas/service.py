"""CU-21 · Reportes de ventas y reservas (RN07: plan con reportes convencionales). Capa de negocio.

Ventas digitales y presenciales netas de devoluciones (CU-41), reservas con su conversión, y una vista de pagos tomada de la tabla `pagos`:
aprobados, rechazados y pendientes de confirmación.
"""
import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from app.core.errors import DatosInvalidos
from app.core.tiempo import a_local
from app.modules.reportes.base import ReportesBase
from app.modules.reportes.cu21_ventas_y_reservas import schemas
from app.modules.reportes.repository import CERO

TIPOS_EXPORTACION = ("ventas", "reservas", "pagos")
MSG_TIPO = "Tipo de exportación no soportado. Use ventas, reservas o pagos."


class VentasYReservasService(ReportesBase):
    def ventas(self, desde: date | None, hasta: date | None, sucursal: int | None, canal: str | None) -> schemas.VentasReporteOut:
        desde, hasta, d, h = self.periodo(desde, hasta)
        sucursal = self.sucursal(sucursal)
        nombres = self.nombres()
        return schemas.VentasReporteOut(
            desde=desde, hasta=hasta, sucursal_id=sucursal, canal=canal, totales=schemas.TotalesOut(**self.totales(d, h, sucursal, canal)),
            por_canal=[schemas.CanalOut(canal=c, ventas=n, unidades=u, total=t) for c, (n, u, t) in sorted(self.repo.por_canal(d, h, sucursal, canal).items())],
            por_sucursal=[schemas.SucursalVentasOut(sucursal_id=s, sucursal=nombres.get(s, ""), ventas=n, total=t) for s, n, t in self.repo.por_sucursal(d, h, sucursal, canal)],
            por_dia=[schemas.DiaOut(**dia) for dia in self.ventas_por_dia(desde, hasta, d, h, sucursal, canal)],
            por_metodo=[schemas.MetodoOut(metodo=m, cobros=n, total=t) for m, n, t in self.repo.por_metodo_de_pago(d, h, sucursal, canal)],
            mas_vendidos=[schemas.ProductoVendidoOut(**p) for p in self.ranking(d, h, sucursal, canal, True, 10)],
            menos_vendidos=[schemas.ProductoVendidoOut(**p) for p in self.ranking(d, h, sucursal, canal, False, 5)],
        )

    def reservas(self, desde: date | None, hasta: date | None, sucursal: int | None) -> schemas.ReservasReporteOut:
        desde, hasta, d, h = self.periodo(desde, hasta)
        sucursal = self.sucursal(sucursal)
        nombres = self.nombres()
        por_estado = self.repo.reservas_por_estado(d, h, sucursal)
        total, completadas = sum(por_estado.values()), por_estado.get("COMPLETADA", 0)
        dias: dict[date, list[int]] = {}
        for momento, estado in self.repo.reservas_con_fecha(d, h, sucursal):
            fila = dias.setdefault(a_local(momento).date(), [0, 0])
            fila[0] += 1
            fila[1] += estado == "COMPLETADA"
        return schemas.ReservasReporteOut(
            desde=desde, hasta=hasta, sucursal_id=sucursal, total=total, completadas=completadas, conversion=round(completadas / total * 100, 1) if total else 0.0,
            por_estado=[schemas.EstadoReservaOut(estado=e, cantidad=n) for e, n in sorted(por_estado.items(), key=lambda x: -x[1])],
            por_sucursal=[schemas.SucursalReservasOut(sucursal_id=s, sucursal=nombres.get(s, ""), reservas=n, completadas=c) for s, n, c in self.repo.reservas_por_sucursal(d, h, sucursal)],
            por_dia=[{"fecha": dia, "reservas": v[0], "completadas": v[1]} for dia, v in sorted(dias.items())],
        )

    def pagos(self, desde: date | None, hasta: date | None, sucursal: int | None) -> schemas.PagosReporteOut:
        desde, hasta, d, h = self.periodo(desde, hasta)
        sucursal = self.sucursal(sucursal)
        nombres = self.nombres()
        filas = self.repo.pagos_por_estado(d, h, sucursal)

        def suma(estado: str) -> schemas.ResumenEstadoPagoOut:
            return schemas.ResumenEstadoPagoOut(cantidad=sum(n for e, _, n, _ in filas if e == estado), monto=sum((t for e, _, _, t in filas if e == estado), CERO))

        return schemas.PagosReporteOut(
            desde=desde, hasta=hasta, sucursal_id=sucursal, aprobados=suma("APROBADO"), rechazados=suma("RECHAZADO"), pendientes_confirmacion=suma("PENDIENTE_CONFIRMACION"),
            por_metodo=[schemas.PagoPorMetodoOut(metodo=m, estado=e, cantidad=n, monto=t) for e, m, n, t in sorted(filas, key=lambda f: (f[1], f[0]))],
            con_problemas=[
                schemas.PagoProblemaOut(
                    id=p.id, pedido=codigo, sucursal_id=s, sucursal=nombres.get(s, ""), metodo=p.metodo, estado=p.estado, monto=p.monto,
                    motivo=p.motivo or p.mensaje, tarjeta=f"{p.tarjeta_marca} ****{p.tarjeta_ultimos4}" if p.tarjeta_ultimos4 else "", fecha=p.creado_en,
                )
                for p, codigo, s in self.repo.pagos_con_problemas(d, h, sucursal)
            ],
        )

    def exportar(self, tipo: str, desde: date | None, hasta: date | None, sucursal: int | None) -> tuple[str, str]:
        """CSV del reporte (separado por comas, con BOM para que Excel respete las tildes)."""
        if tipo not in TIPOS_EXPORTACION:
            raise DatosInvalidos(MSG_TIPO)
        desde, hasta, d, h = self.periodo(desde, hasta)
        sucursal = self.sucursal(sucursal)
        nombres = self.nombres()
        salida = StringIO()
        escritor = csv.writer(salida)
        if tipo == "ventas":
            escritor.writerow(["comprobante", "pedido", "fecha", "canal", "sucursal", "total"])
            for p in self.repo.tickets(d, h, sucursal):
                escritor.writerow([p.comprobante_numero or "", p.codigo, a_local(p.pagado_en).strftime("%Y-%m-%d %H:%M"), p.canal, nombres.get(p.sucursal_id, ""), p.total])
        elif tipo == "reservas":
            escritor.writerow(["codigo", "sucursal", "estado", "programada_para", "creada_en"])
            for r in self.repo.reservas(d, h, sucursal):
                escritor.writerow([r.codigo, nombres.get(r.sucursal_id, ""), r.estado, a_local(r.programada_para).strftime("%Y-%m-%d %H:%M"), a_local(r.creada_en).strftime("%Y-%m-%d %H:%M")])
        else:
            escritor.writerow(["estado", "metodo", "cantidad", "monto"])
            for estado, metodo, n, total in sorted(self.repo.pagos_por_estado(d, h, sucursal)):
                escritor.writerow([estado, metodo, n, Decimal(total).quantize(Decimal("0.01"))])
        return "﻿" + salida.getvalue(), f"{tipo}-{desde}-{hasta}.csv"
