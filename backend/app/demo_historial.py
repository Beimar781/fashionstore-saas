"""Historial sintético de 3 meses para las demostraciones de reportes («ventas de septiembre», «los diez productos más vendidos este mes», «últimos tres meses por sucursal»).

Uso, a mano:  python -m app.demo_historial
No lo corren el arranque ni el seed. Es idempotente (una sucursal que ya tiene su historial no se toca), solo agrega pedidos cuyo código empieza con
«DEMO-» (datos de demostración) y no cambia nada de lo existente. No descuenta inventario: son ventas históricas.
"""
import random
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.tiempo import ahora
from app.modules.inventario.models import Existencia
from app.modules.plataforma.models import Empresa
from app.modules.sucursales.models import Sucursal
from app.primer_parcial.catalogo.publico import Producto, Variante
from app.primer_parcial.ventas.models import Pago, Pedido, PedidoItem

DIAS = 90
PREFIJO = "DEMO"


def _variantes_de(db: Session, empresa_id: int, sucursal_id: int) -> list[tuple[Variante, Producto]]:
    filas = db.execute(
        select(Variante, Producto).join(Producto, Producto.id == Variante.producto_id).join(Existencia, Existencia.variante_id == Variante.id)
        .where(Variante.empresa_id == empresa_id, Existencia.sucursal_id == sucursal_id).order_by(Producto.id, Variante.id)
    ).all()
    return [(v, p) for v, p in filas]


def generar_sucursal(db: Session, empresa: Empresa, sucursal: Sucursal) -> int:
    """Crea las ventas de los últimos 90 días de una sucursal. Devuelve cuántos pedidos agregó (0 si ya tenía historial)."""
    marca = f"{PREFIJO}-{empresa.id}-{sucursal.id}-"
    if db.scalar(select(Pedido.id).where(Pedido.empresa_id == empresa.id, Pedido.codigo.like(marca + "%")).limit(1)):
        return 0
    variantes = _variantes_de(db, empresa.id, sucursal.id)
    if not variantes:
        return 0
    azar = random.Random(empresa.id * 1000 + sucursal.id)  # siempre el mismo historial para la misma sucursal
    creados = 0
    for atras in range(DIAS, 0, -1):
        for _ in range(azar.choice([0, 1, 1, 2, 3])):
            canal = azar.choice(["PRESENCIAL", "PRESENCIAL", "DIGITAL"])
            momento = ahora() - timedelta(days=atras, hours=azar.randint(0, 9), minutes=azar.randint(0, 59))
            lineas = azar.sample(variantes, k=min(len(variantes), azar.randint(1, 3)))
            total = Decimal("0.00")
            creados += 1
            pedido = Pedido(
                empresa_id=empresa.id, codigo=f"{marca}{creados:04d}", sucursal_id=sucursal.id, canal=canal, tipo_entrega="EN_TIENDA" if canal == "PRESENCIAL" else "RETIRO",
                estado="PAGADO", subtotal=Decimal("0.00"), total=Decimal("0.00"), iva_incluido=Decimal("0.00"), pagado_en=momento,
            )
            for variante, producto in lineas:
                unidades, precio = azar.randint(1, 3), Decimal(variante.precio_especifico or producto.precio_base)
                total += precio * unidades
                pedido.items.append(PedidoItem(
                    empresa_id=empresa.id, variante_id=variante.id, sku=variante.sku, producto=producto.nombre, talla=variante.talla.codigo, color=variante.color.nombre,
                    cantidad=unidades, precio_unitario=precio, precio_final=precio, subtotal=precio * unidades,
                ))
            pedido.subtotal = pedido.total = total
            pedido.iva_incluido = (total * 13 / 113).quantize(Decimal("0.01"))
            db.add(pedido)
            db.flush()
            db.add(Pago(
                empresa_id=empresa.id, pedido_id=pedido.id, metodo="EFECTIVO" if canal == "PRESENCIAL" else "TARJETA", proveedor="CAJA" if canal == "PRESENCIAL" else "SIMULADO",
                estado="APROBADO", monto=total, creado_en=momento, referencia_externa=None if canal == "PRESENCIAL" else f"sim_demo_{empresa.id}_{pedido.id}",
                tarjeta_marca="" if canal == "PRESENCIAL" else "Visa", tarjeta_ultimos4="" if canal == "PRESENCIAL" else "4242", mensaje="Pago aprobado.",
            ))
    return creados


def generar(db: Session) -> dict[str, int]:
    """Historial para todas las empresas y sucursales activas. Devuelve {«empresa/sucursal»: pedidos agregados}."""
    resumen: dict[str, int] = {}
    for empresa in db.scalars(select(Empresa).order_by(Empresa.id)):
        for sucursal in db.scalars(select(Sucursal).where(Sucursal.empresa_id == empresa.id, Sucursal.activa.is_(True)).order_by(Sucursal.id)):
            resumen[f"{empresa.codigo}/{sucursal.nombre}"] = generar_sucursal(db, empresa, sucursal)
    db.commit()
    return resumen


if __name__ == "__main__":
    with SessionLocal() as sesion:
        for clave, n in generar(sesion).items():
            print(f"{clave}: {n} pedido(s) de demostración agregados" if n else f"{clave}: ya tenía historial, no se tocó")
