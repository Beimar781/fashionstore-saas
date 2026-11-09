"""CU-21 · Reportes de ventas y reservas (RN07: plan con reportes convencionales). Capa de negocio.

Ventas digitales y presenciales netas de devoluciones (CU-41), reservas con su conversión, y una vista de pagos tomada de la tabla `pagos`:
aprobados, rechazados y pendientes de confirmación.
"""
import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from app.core.errors import DatosInvalidos
from app.core.exportar import FORMATOS, exportar as armar_archivo
from app.core.tiempo import a_local
from app.modules.plataforma.publico import datos_de_empresa
from app.modules.reportes.base import ReportesBase
from app.modules.reportes.cu21_ventas_y_reservas import schemas
from app.modules.reportes.repository import CERO

TIPOS_EXPORTACION = ("ventas", "reservas", "pagos", "inventario")
MSG_TIPO = "Tipo de exportación no soportado. Use ventas, reservas, pagos o inventario."
MSG_FORMATO = "Formato de exportación no válido. Use csv, xlsx o pdf."
TITULOS = {"ventas": "Reporte de ventas", "reservas": "Reporte de reservas", "pagos": "Reporte de pagos", "inventario": "Reporte de inventario por sucursal"}
LIMITE_INVENTARIO = 5000


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

    def _tabla(self, tipo: str, d, h, sucursal: int | None, categoria: int | None) -> tuple[list[str], list[list]]:
        """Columnas y filas de un reporte convencional: de aquí salen el CSV, el Excel y el PDF."""
        nombres = self.nombres()
        if tipo == "ventas":
            columnas = ["comprobante", "pedido", "fecha", "canal", "sucursal", "total"]
            filas = [[p.comprobante_numero or "", p.codigo, a_local(p.pagado_en).strftime("%Y-%m-%d %H:%M"), p.canal, nombres.get(p.sucursal_id, ""), p.total] for p in self.repo.tickets(d, h, sucursal)]
        elif tipo == "reservas":
            columnas = ["codigo", "sucursal", "estado", "programada_para", "creada_en"]
            filas = [[r.codigo, nombres.get(r.sucursal_id, ""), r.estado, a_local(r.programada_para).strftime("%Y-%m-%d %H:%M"), a_local(r.creada_en).strftime("%Y-%m-%d %H:%M")] for r in self.repo.reservas(d, h, sucursal)]
        elif tipo == "pagos":
            columnas = ["estado", "metodo", "cantidad", "monto"]
            filas = [[estado, metodo, n, Decimal(total).quantize(Decimal("0.01"))] for estado, metodo, n, total in sorted(self.repo.pagos_por_estado(d, h, sucursal))]
        else:
            columnas = ["sucursal", "categoria", "producto", "sku", "talla", "color", "disponible", "reservada", "vendida", "minimo", "situacion"]
            _, detalle = self.repo.inventario_detalle(sucursal, categoria, LIMITE_INVENTARIO)
            filas = [[nombres.get(s, ""), c, p, k, t, col, disp, res, ven, u, self._situacion(disp, u)] for s, c, p, k, t, col, disp, res, ven, u in detalle]
        return columnas, filas

    @staticmethod
    def _situacion(disponible: int, umbral: int) -> str:
        return "Agotado" if disponible == 0 else ("Bajo stock" if umbral > 0 and disponible <= umbral else "Normal")

    def inventario(self, sucursal: int | None, categoria: int | None, pagina: int, tamano: int) -> dict:
        """Inventario por sucursal en pantalla (paginado): existencias por prenda, talla y color, con bajo stock y agotados."""
        sucursal = self.sucursal(sucursal)
        nombres = self.nombres()
        total, detalle = self.repo.inventario_detalle(sucursal, categoria, tamano, (pagina - 1) * tamano)
        return {
            "resumen": self.repo.inventario(sucursal), "total": total, "pagina": pagina, "tamano": tamano,
            "items": [
                {"sucursal": nombres.get(s, ""), "categoria": c, "producto": p, "sku": k, "talla": t, "color": col, "disponible": disp, "reservada": res, "vendida": ven, "minimo": u, "situacion": self._situacion(disp, u)}
                for s, c, p, k, t, col, disp, res, ven, u in detalle
            ],
        }

    def exportar(self, tipo: str, desde: date | None, hasta: date | None, sucursal: int | None, formato: str = "csv", categoria: int | None = None) -> tuple[bytes, str, str]:
        """CSV (con BOM para que Excel respete las tildes), Excel o PDF del reporte, con el mismo contenido en los tres."""
        if tipo not in TIPOS_EXPORTACION:
            raise DatosInvalidos(MSG_TIPO)
        if formato != "csv" and formato not in FORMATOS:
            raise DatosInvalidos(MSG_FORMATO)
        desde, hasta, d, h = self.periodo(desde, hasta)
        sucursal = self.sucursal(sucursal)
        columnas, filas = self._tabla(tipo, d, h, sucursal, categoria)
        nombre = f"{tipo}-{desde}-{hasta}.{formato}"
        if formato == "csv":
            salida = StringIO()
            escritor = csv.writer(salida)
            escritor.writerow(columnas)
            escritor.writerows(filas)
            return ("\ufeff" + salida.getvalue()).encode("utf-8"), "text/csv; charset=utf-8", nombre
        rep = {
            "empresa": datos_de_empresa(self.db, self.empresa_id)["razon_social"], "titulo": TITULOS[tipo],
            "filtros": [("Periodo", f"{desde} a {hasta}"), ("Sucursal", self.nombres().get(sucursal, "Todas") if sucursal else "Todas")],
            "tablas": [{"nombre": TITULOS[tipo], "columnas": [c.replace("_", " ").capitalize() for c in columnas], "filas": [[str(v) if isinstance(v, Decimal) else v for v in f] for f in filas]}],
            "grafico": None,
        }
        return armar_archivo(rep, formato), FORMATOS[formato], nombre
