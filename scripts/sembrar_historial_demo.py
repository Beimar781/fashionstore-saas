"""Siembra un historial de ventas de demostración en EMP-B (Estilo Andino) para probar el reporte «top 10 de productos más vendidos de los últimos 3 meses por sucursal» (CU-23).

Uso (desde la raíz del proyecto; lee DATABASE_URL del entorno o de backend/.env, igual que el backend):
    python scripts/sembrar_historial_demo.py --dry-run     # solo muestra el plan, no escribe nada
    python scripts/sembrar_historial_demo.py               # siembra
    python scripts/sembrar_historial_demo.py --borrar      # elimina únicamente lo sembrado

Qué hace
- 60 a 90 ventas PAGADAS con comprobante CMP-<sucursal>-<número> (el número sigue al último de cada sucursal), entre hace 120 días y hace 3 días, nunca en el futuro.
  Una cuarta parte es más antigua que 3 meses (así «últimos 6 meses» muestra más ventas que «últimos 3 meses»).
- Reparte las ventas entre todas las sucursales activas con existencias, con el cajero o encargado de cada una; cada sucursal tiene su propio ranking de productos.
- Total e IVA incluido coherentes (total × 13 / 113); mezcla de efectivo, QR y tarjeta.
- NO toca el inventario (no hay movimientos): antes de guardar se comprueba que las existencias siguen idénticas.
- Marca: los pedidos tienen código «DH-0001…» y sus pagos la referencia «demo-hist-DH-…». --borrar elimina solo eso.
- Idempotente: si ya hay filas «DH-», no vuelve a sembrar. Solo EMP-B (otra empresa exige --empresa a propósito).
"""
import argparse
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import delete, func, select  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

import app.db_models  # noqa: E402,F401  (registra TODOS los modelos: sin esto SQLAlchemy no resuelve claves foráneas como pedidos.reserva_id)
from app.core.database import SessionLocal  # noqa: E402
from app.core.tiempo import a_local, ahora  # noqa: E402
from app.core.tipos import iva_incluido  # noqa: E402
from app.modules.acceso.models import Rol, Usuario  # noqa: E402
from app.modules.inventario.models import Existencia  # noqa: E402
from app.modules.plataforma.models import Empresa  # noqa: E402
from app.modules.sucursales.models import Sucursal  # noqa: E402
from app.primer_parcial.catalogo.publico import Producto, Variante  # noqa: E402
from app.primer_parcial.ventas.models import Pago, Pedido, PedidoItem, SecuenciaComprobante  # noqa: E402

EMPRESA_POR_DEFECTO = "EMP-B"
PREFIJO = "DH-"
REFERENCIA = "demo-hist-"
MINIMO, MAXIMO = 60, 90
DIAS_MAS_RECIENTE, DIAS_LIMITE_3_MESES, DIAS_MAS_ANTIGUA = 3, 89, 120
FRACCION_ANTIGUA = 0.25
METODOS = [("EFECTIVO", 50), ("QR", 20), ("TARJETA", 30)]


def _existencias(db, empresa_id: int) -> list[tuple]:
    """Foto del inventario de la empresa: (sucursal, variante, disponible, reservada, vendida) ordenada; sirve para comprobar que no cambió."""
    return [tuple(f) for f in db.execute(
        select(Existencia.sucursal_id, Existencia.variante_id, Existencia.disponible, Existencia.reservada, Existencia.vendida)
        .where(Existencia.empresa_id == empresa_id).order_by(Existencia.sucursal_id, Existencia.variante_id)
    )]


def _personal(db, empresa_id: int) -> dict[int, int]:
    """Un usuario (cajero, si no encargado) por sucursal para registrarlo como quien vendió."""
    filas = db.execute(
        select(Usuario.id, Usuario.sucursal_id, Rol.nombre).join(Rol, Rol.id == Usuario.rol_id)
        .where(Usuario.empresa_id == empresa_id, Usuario.activo.is_(True), Usuario.sucursal_id.is_not(None), Rol.nombre.in_(["Cajero", "Encargado"])).order_by(Usuario.id)
    ).all()
    elegido: dict[int, int] = {}
    for usuario_id, sucursal_id, rol in filas:
        if rol == "Cajero" or sucursal_id not in elegido:  # el cajero tiene prioridad; si no hay, el encargado
            elegido[sucursal_id] = usuario_id
    return elegido


def _catalogo_por_sucursal(db, empresa_id: int) -> dict[int, list[tuple[Producto, list[Variante]]]]:
    """Por sucursal activa: los productos que allí tienen existencias, con sus variantes."""
    filas = db.execute(
        select(Existencia.sucursal_id, Variante, Producto).join(Variante, Variante.id == Existencia.variante_id).join(Producto, Producto.id == Variante.producto_id)
        .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
        .where(Existencia.empresa_id == empresa_id, Sucursal.activa.is_(True), Producto.activo.is_(True)).order_by(Existencia.sucursal_id, Producto.id, Variante.id)
    ).all()
    por_sucursal: dict[int, dict[int, tuple[Producto, list[Variante]]]] = defaultdict(dict)
    for sucursal_id, variante, producto in filas:
        por_sucursal[sucursal_id].setdefault(producto.id, (producto, []))[1].append(variante)
    return {s: list(d.values()) for s, d in por_sucursal.items()}


def _momentos(azar: random.Random, cantidad: int) -> list:
    """Fechas entre hace 120 y hace 3 días (nunca futuras): una cuarta parte más antigua que 3 meses, el resto en los últimos 3 meses."""
    base = ahora()
    antiguas = round(cantidad * FRACCION_ANTIGUA)
    fechas = []
    for i in range(cantidad):
        dias = azar.randint(DIAS_LIMITE_3_MESES + 2, DIAS_MAS_ANTIGUA) if i < antiguas else azar.randint(DIAS_MAS_RECIENTE, DIAS_LIMITE_3_MESES)
        hora_local = azar.randint(9, 20)
        momento = (base - timedelta(days=dias)).astimezone(a_local(base).tzinfo).replace(hour=hora_local, minute=azar.randint(0, 59), second=azar.randint(0, 59), microsecond=0)
        fechas.append(min(momento, base - timedelta(days=DIAS_MAS_RECIENTE - 1)))
    return sorted(fechas)


def _metodo(azar: random.Random) -> str:
    return azar.choices([m for m, _ in METODOS], weights=[p for _, p in METODOS])[0]


def planear(db, empresa: Empresa) -> list[dict]:
    """Arma todas las ventas en memoria (sin escribir). Cada sucursal tiene su propio ranking: sus productos se ordenan al azar con un peso que baja rápido."""
    azar = random.Random(20260101 + empresa.id)
    catalogo = _catalogo_por_sucursal(db, empresa.id)
    personal = _personal(db, empresa.id)
    if not catalogo:
        raise SystemExit(f"{empresa.codigo}: no hay sucursales activas con existencias; no hay con qué sembrar.")
    total = azar.randint(MINIMO, MAXIMO)
    sucursales = sorted(catalogo)
    reparto = {s: max(8, round(total * peso)) for s, peso in zip(sucursales, _pesos(azar, len(sucursales)))}
    ventas: list[dict] = []
    for sucursal_id in sucursales:
        productos = catalogo[sucursal_id][:]
        azar.shuffle(productos)  # ranking distinto en cada sucursal
        pesos = [1 / (i + 1) ** 1.25 for i in range(len(productos))]
        for momento in _momentos(azar, reparto[sucursal_id]):
            lineas, usados = [], set()
            for _ in range(azar.choices([1, 2, 3], weights=[50, 35, 15])[0]):
                producto, variantes = azar.choices(productos, weights=pesos)[0]
                variante = azar.choice(variantes)
                if variante.id in usados:
                    continue
                usados.add(variante.id)
                precio = Decimal(variante.precio_especifico or producto.precio_base).quantize(Decimal("0.01"))
                lineas.append({"variante": variante, "producto": producto, "cantidad": azar.choices([1, 2, 3, 4], weights=[55, 25, 12, 8])[0], "precio": precio})
            ventas.append({"sucursal_id": sucursal_id, "momento": momento, "lineas": lineas, "metodo": _metodo(azar), "vendedor": personal.get(sucursal_id)})
    ventas.sort(key=lambda v: v["momento"])
    for numero, venta in enumerate(ventas, 1):
        venta["codigo"] = f"{PREFIJO}{numero:04d}"
        venta["total"] = sum((l["precio"] * l["cantidad"] for l in venta["lineas"]), Decimal("0.00"))
        venta["iva"] = iva_incluido(venta["total"])
    return ventas


def _pesos(azar: random.Random, n: int) -> list[float]:
    crudos = [azar.uniform(0.7, 1.3) for _ in range(n)]
    return [c / sum(crudos) for c in crudos]


def aplicar(db, empresa: Empresa, ventas: list[dict]) -> None:
    """Escribe las ventas: pedido + detalle + pago + número de comprobante correlativo por sucursal (en orden de fecha)."""
    secuencias = {s.sucursal_id: s for s in db.scalars(select(SecuenciaComprobante).where(SecuenciaComprobante.empresa_id == empresa.id))}
    for venta in ventas:  # ya vienen ordenadas por fecha
        sucursal_id, momento = venta["sucursal_id"], venta["momento"]
        secuencia = secuencias.get(sucursal_id)
        if secuencia is None:
            secuencia = secuencias[sucursal_id] = SecuenciaComprobante(empresa_id=empresa.id, sucursal_id=sucursal_id, ultimo=0)
            db.add(secuencia)
        secuencia.ultimo += 1
        comprobante = f"CMP-{sucursal_id:03d}-{secuencia.ultimo:06d}"
        digital = venta["metodo"] == "TARJETA" and venta["total"] % 2 == 0  # unas pocas compras con tarjeta fueron por la web
        pedido = Pedido(
            empresa_id=empresa.id, codigo=venta["codigo"], sucursal_id=sucursal_id, canal="DIGITAL" if digital else "PRESENCIAL", tipo_entrega="RETIRO" if digital else "EN_TIENDA",
            estado="PAGADO", subtotal=venta["total"], descuento=Decimal("0.00"), iva_incluido=venta["iva"], total=venta["total"], comprobante_numero=comprobante, comprobante_tipo="FACTURA",
            autorizacion_fiscal=f"DEMO-{venta['codigo']}", creado_por=None if digital else venta["vendedor"], creado_en=momento - timedelta(minutes=3), pagado_en=momento,
        )
        for l in venta["lineas"]:
            pedido.items.append(PedidoItem(
                empresa_id=empresa.id, variante_id=l["variante"].id, sku=l["variante"].sku, producto=l["producto"].nombre, talla=l["variante"].talla.codigo, color=l["variante"].color.nombre,
                cantidad=l["cantidad"], precio_unitario=l["precio"], precio_final=l["precio"], subtotal=l["precio"] * l["cantidad"],
            ))
        db.add(pedido)
        db.flush()
        efectivo = venta["metodo"] == "EFECTIVO"
        recibido = (venta["total"] / 10).to_integral_value(rounding="ROUND_CEILING") * 10 if efectivo else None
        db.add(Pago(
            empresa_id=empresa.id, pedido_id=pedido.id, metodo=venta["metodo"], proveedor="SIMULADO" if venta["metodo"] == "TARJETA" else "CAJA", estado="APROBADO", monto=venta["total"],
            referencia_externa=REFERENCIA + venta["codigo"], monto_recibido=recibido, cambio=(recibido - venta["total"]) if efectivo else None,
            tarjeta_marca="Visa" if venta["metodo"] == "TARJETA" else "", tarjeta_ultimos4="4242" if venta["metodo"] == "TARJETA" else "", mensaje="Pago aprobado.",
            usuario_id=None if digital else venta["vendedor"], creado_en=momento, actualizado_en=momento,
        ))


def borrar(db, empresa: Empresa) -> int:
    """Elimina solo lo sembrado (pedidos «DH-», su detalle y sus pagos) y deja la secuencia de comprobantes en el último número que sigue existiendo."""
    ids = list(db.scalars(select(Pedido.id).where(Pedido.empresa_id == empresa.id, Pedido.codigo.like(PREFIJO + "%"))))
    if not ids:
        return 0
    db.execute(delete(Pago).where(Pago.pedido_id.in_(ids), Pago.referencia_externa.like(REFERENCIA + "%")))
    db.execute(delete(PedidoItem).where(PedidoItem.pedido_id.in_(ids)))
    db.execute(delete(Pedido).where(Pedido.id.in_(ids)))
    db.flush()
    for secuencia in db.scalars(select(SecuenciaComprobante).where(SecuenciaComprobante.empresa_id == empresa.id)):
        numeros = [int(m.group(1)) for c in db.scalars(select(Pedido.comprobante_numero).where(Pedido.empresa_id == empresa.id, Pedido.sucursal_id == secuencia.sucursal_id, Pedido.comprobante_numero.is_not(None)))
                   if (m := re.fullmatch(r"CMP-\d+-(\d+)", c))]
        secuencia.ultimo = max(numeros, default=0)
    return len(ids)


def resumen(db, empresa: Empresa, ventas: list[dict]) -> str:
    nombres = {s.id: s.nombre for s in db.scalars(select(Sucursal).where(Sucursal.empresa_id == empresa.id))}
    por_sucursal, por_mes = Counter(), Counter()
    top: dict[int, Counter] = defaultdict(Counter)
    for v in ventas:
        por_sucursal[v["sucursal_id"]] += 1
        por_mes[a_local(v["momento"]).strftime("%Y-%m")] += 1
        for l in v["lineas"]:
            top[v["sucursal_id"]][l["producto"].nombre] += l["cantidad"]
    meses = {}
    for v in ventas:
        meses.setdefault(a_local(v["momento"]).strftime("%Y-%m"), Counter())[v["sucursal_id"]] += 1
    L = [f"Ventas: {len(ventas)} · total Bs {sum(v['total'] for v in ventas):.2f} · IVA incluido Bs {sum(v['iva'] for v in ventas):.2f}",
         f"Fechas: {a_local(ventas[0]['momento']):%d/%m/%Y} a {a_local(ventas[-1]['momento']):%d/%m/%Y} · más antiguas que 3 meses: {sum(1 for v in ventas if (ahora() - v['momento']).days > 90)}",
         "", "Ventas por sucursal:"]
    L += [f"  {nombres.get(s, s)}: {n}" for s, n in sorted(por_sucursal.items())]
    L += ["", "Ventas por mes:"] + [f"  {mes}: {n}  ({', '.join(f'{nombres.get(s, s)} {c}' for s, c in sorted(meses[mes].items()))})" for mes, n in sorted(por_mes.items())]
    L += ["", "Top 5 por sucursal (unidades):"]
    for s in sorted(top):
        L.append(f"  {nombres.get(s, s)}: " + " · ".join(f"{p} {u}" for p, u in top[s].most_common(5)))
    L += ["", "Métodos: " + ", ".join(f"{m} {n}" for m, n in Counter(v["metodo"] for v in ventas).most_common())]
    return "\n".join(L)


def totales_de_la_empresa(db, empresa: Empresa) -> tuple[int, Decimal]:
    n, total = db.execute(select(func.count(Pedido.id), func.coalesce(func.sum(Pedido.total), 0)).where(Pedido.empresa_id == empresa.id, Pedido.estado == "PAGADO")).one()
    return n, Decimal(total)


def principal(argumentos=None) -> int:
    ap = argparse.ArgumentParser(description="Siembra historial de ventas de demostración en EMP-B.")
    ap.add_argument("--dry-run", action="store_true", help="solo muestra el plan; no escribe nada")
    ap.add_argument("--borrar", action="store_true", help="elimina únicamente lo sembrado por este script")
    ap.add_argument("--empresa", default=EMPRESA_POR_DEFECTO, help="código de la empresa (por defecto EMP-B; no uses otra salvo en pruebas)")
    args = ap.parse_args(argumentos)
    with SessionLocal() as db:
        empresa = db.scalar(select(Empresa).where(Empresa.codigo == args.empresa))
        if empresa is None:
            print(f"No existe la empresa {args.empresa}.")
            return 1
        antes = _existencias(db, empresa.id)
        ya = db.scalar(select(func.count(Pedido.id)).where(Pedido.empresa_id == empresa.id, Pedido.codigo.like(PREFIJO + "%"))) or 0
        n0, t0 = totales_de_la_empresa(db, empresa)
        if args.borrar:
            n = borrar(db, empresa) if not args.dry_run else ya
            if args.dry_run:
                db.rollback()
                print(f"[dry-run] se eliminarían {n} ventas sembradas de {empresa.codigo}.")
                return 0
            assert _existencias(db, empresa.id) == antes, "el inventario cambió: se cancela"
            db.commit()
            n1, t1 = totales_de_la_empresa(db, empresa)
            print(f"Eliminadas {n} ventas sembradas de {empresa.codigo}. Ventas pagadas ahora: {n1} · Bs {t1:.2f}")
            return 0
        if ya:
            print(f"{empresa.codigo} ya tiene {ya} ventas sembradas (códigos {PREFIJO}…): no se vuelve a sembrar. Use --borrar para quitarlas.")
            return 0
        ventas = planear(db, empresa)
        print(("[dry-run] Plan para " if args.dry_run else "Sembrando en ") + f"{empresa.codigo}:\n")
        print(resumen(db, empresa, ventas))
        if args.dry_run:
            db.rollback()
            print(f"\n[dry-run] no se escribió nada. Hoy {empresa.codigo} tiene {n0} ventas pagadas por Bs {t0:.2f}.")
            return 0
        aplicar(db, empresa, ventas)
        if _existencias(db, empresa.id) != antes:
            db.rollback()
            print("El inventario cambió: se canceló todo (no debería pasar).")
            return 1
        db.commit()
        n1, t1 = totales_de_la_empresa(db, empresa)
        print(f"\nListo. {empresa.codigo}: de {n0} ventas pagadas (Bs {t0:.2f}) a {n1} (Bs {t1:.2f}). El inventario no cambió.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(principal())
    except OperationalError:
        print("No se pudo conectar a la base de datos. Defina DATABASE_URL (la de Railway o la local) en el entorno o en backend/.env y vuelva a intentar.")
        sys.exit(2)
