"""CU-23 · Reportes generativos: el Administrador escribe o dicta una petición y el sistema la interpreta y genera el reporte (RN07: plan con IA).

Pasos: interpretar la petición (IA externa o reglas de respaldo) → consultar los datos con las consultas de CU-21 → redactar el reporte →
dejar constancia del reporte y del uso de la IA.
"""
from decimal import Decimal

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.errors import DatosInvalidos, NoEncontrado
from app.core.ia import obtener_ia
from app.modules.acceso.dependencias import Contexto
from app.modules.ia.cu23_reportes_generativos import schemas
from app.modules.ia.cu23_reportes_generativos.interprete import EspecReporte, interpretar_con_ia, interpretar_con_reglas
from app.modules.ia.cu23_reportes_generativos.repository import ReporteRepository
from app.modules.ia.models import ReporteGenerado
from app.modules.ia.publico import registrar_uso_ia
from app.modules.reportes.publico import ReportesBase, hoy_local

MSG_PROMPT = "Escriba o dicte lo que desea consultar."


def _a_json(valor):
    """Para guardar las cifras: importes con dos decimales como texto (nunca float) y fechas en ISO."""
    if isinstance(valor, Decimal):
        return f"{valor:.2f}"
    if isinstance(valor, dict):
        return {k: _a_json(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_a_json(v) for v in valor]
    return jsonable_encoder(valor)


def _bs(valor) -> str:
    return f"Bs {Decimal(valor):,.2f}"


class ReporteGenerativoService(ReportesBase):
    def __init__(self, db: Session, ctx: Contexto):
        super().__init__(db, ctx)
        self.reportes = ReporteRepository(db, ctx.empresa_id)

    def generar(self, datos: schemas.PromptIn) -> schemas.ReporteGenerativoOut:
        prompt = datos.prompt.strip()
        if not prompt:
            raise DatosInvalidos(MSG_PROMPT)
        sucursales = sorted(self.nombres().items())
        espec, origen = interpretar_con_ia(obtener_ia(), prompt, hoy_local(), sucursales), "IA"
        if espec is None:
            espec, origen = interpretar_con_reglas(prompt, hoy_local(), sucursales), "REGLAS"
        self.sucursal(espec.sucursal_id)
        cifras = self._datos(espec)
        fila = self.reportes.agregar(ReporteGenerado(
            usuario_id=self.ctx.usuario.id, prompt=prompt, especificacion=jsonable_encoder(espec), resultado={"texto": self._redactar(prompt, espec, cifras), "datos": _a_json(cifras)}, origen=origen,
        ))
        registrar_uso_ia(self.db, self.empresa_id, self.ctx.usuario.id, "REPORTE", origen)
        self.db.commit()
        return self._salida(fila)

    def listar(self) -> list[schemas.ReporteGenerativoOut]:
        return [self._salida(r) for r in self.reportes.recientes()]

    def obtener(self, reporte_id: int) -> schemas.ReporteGenerativoOut:
        fila = self.reportes.con_id(reporte_id)
        if fila is None:
            raise NoEncontrado("Reporte no encontrado.")  # también si es de otra empresa
        return self._salida(fila)

    # ---- datos y redacción ----
    def _datos(self, e: EspecReporte) -> dict:
        _, _, d, h = self.periodo(e.desde, e.hasta)
        suc, cifras = e.sucursal_id, {}
        if e.ventas or e.ranking:
            cifras["ventas"] = self.totales(d, h, suc)
        if e.detalle_ventas and e.limite_detalle:
            cifras["detalle_ventas"] = [
                {"pedido": p.codigo, "comprobante": p.comprobante_numero, "canal": p.canal, "total": p.total, "fecha": p.pagado_en}
                for p in self.repo.tickets(d, h, suc, None, e.limite_detalle)
            ]
        if e.ranking:
            cifras["ranking"] = self.ranking(d, h, suc, None, e.orden_ranking == "mejores", e.limite_ranking)
        if e.reservas:
            por_estado = self.repo.reservas_por_estado(d, h, suc)
            total = sum(por_estado.values())
            cifras["reservas"] = {"total": total, "completadas": por_estado.get("COMPLETADA", 0), "por_estado": por_estado,
                                  "conversion": round(por_estado.get("COMPLETADA", 0) / total * 100, 1) if total else 0.0}
        if e.pagos:
            cifras["pagos"] = {estado: {"cantidad": n, "monto": t} for estado, n, t in self._pagos_por_estado(d, h, suc)}
        if e.inventario or e.stock_bajo:
            cifras["inventario"] = self.repo.inventario(suc)
            if e.stock_bajo:
                cifras["stock_bajo"] = [{"sucursal": self.nombres().get(s, ""), "producto": p, "sku": k, "disponible": disp, "umbral": u} for s, p, k, disp, u in self.repo.stock_bajo(suc, 10)]
        return cifras

    def _pagos_por_estado(self, d, h, suc) -> list[tuple[str, int, Decimal]]:
        acumulado: dict[str, list] = {}
        for estado, _, n, t in self.repo.pagos_por_estado(d, h, suc):
            fila = acumulado.setdefault(estado, [0, Decimal("0.00")])
            fila[0] += n
            fila[1] += t
        return [(e, v[0], v[1]) for e, v in sorted(acumulado.items())]

    def _redactar(self, prompt: str, e: EspecReporte, c: dict) -> str:
        lineas = [f"Consulta: {prompt}", f"Periodo: {e.etiqueta_periodo} ({e.desde} a {e.hasta})", f"Ámbito: {e.etiqueta_ambito}", ""]
        if "ventas" in c and e.ventas:
            v = c["ventas"]
            lineas.append(f"Ventas: {_bs(v['ventas_netas'])} netas en {v['ventas']} venta(s), {v['unidades']} prenda(s); ticket promedio {_bs(v['ticket_promedio'])}.")
            if v["devoluciones"]:
                lineas.append(f"  Incluye {v['devoluciones']} devolución(es)/cambio(s): se descontaron {_bs(v['devuelto'])} y se sumaron {_bs(v['entregado_en_cambios'])} entregados en cambios.")
        for fila in c.get("detalle_ventas", []):
            lineas.append(f"  • {fila['comprobante'] or fila['pedido']} | {fila['canal']} | {_bs(fila['total'])} | {fila['fecha']:%d/%m/%Y}")
        if c.get("ranking"):
            lineas += ["", "Productos con menor venta:" if e.orden_ranking == "peores" else "Productos más vendidos:"]
            lineas += [f"  {i}. {p['producto']} — {p['unidades']} u., {_bs(p['ingresos'])}" for i, p in enumerate(c["ranking"], 1)]
        elif e.ranking:
            lineas += ["", "No hubo ventas de productos en el periodo."]
        if "reservas" in c:
            r = c["reservas"]
            estados = ", ".join(f"{k}: {n}" for k, n in sorted(r["por_estado"].items(), key=lambda x: -x[1]))
            lineas += ["", f"Reservas: {r['total']} en total, {r['completadas']} completadas (conversión {r['conversion']}%)." + (f" Por estado: {estados}." if estados else "")]
        if "pagos" in c:
            p = c["pagos"]
            nombres = {"APROBADO": "aprobados", "RECHAZADO": "rechazados", "PENDIENTE_CONFIRMACION": "pendientes de confirmación"}
            partes = [f"{p[k]['cantidad']} {nombres[k]} ({_bs(p[k]['monto'])})" for k in nombres if k in p]
            lineas += ["", "Pagos: " + (", ".join(partes) if partes else "sin pagos en el periodo") + "."]
        if "inventario" in c and e.inventario:
            i = c["inventario"]
            lineas += ["", f"Inventario: {i['disponibles']} prendas disponibles, {i['reservadas']} reservadas, {i['agotadas']} variantes agotadas."]
        if e.stock_bajo:
            lineas.append("")
            if c.get("stock_bajo"):
                lineas.append("Alertas de stock bajo:")
                lineas += [f"  • {s['sucursal']} | {s['producto']} ({s['sku']}) — {s['disponible']} u. (mínimo {s['umbral']})" for s in c["stock_bajo"]]
            else:
                lineas.append("Alertas de stock bajo: ninguna.")
        return "\n".join(lineas)

    @staticmethod
    def _salida(f: ReporteGenerado) -> schemas.ReporteGenerativoOut:
        return schemas.ReporteGenerativoOut(id=f.id, prompt=f.prompt, origen=f.origen, especificacion=f.especificacion, texto=f.resultado["texto"], datos=f.resultado["datos"], creado_en=f.creado_en)
