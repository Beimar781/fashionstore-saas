"""Comprobante de compra en PDF (CU-11 paso 5 y CU-12 paso 4)."""
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.primer_parcial.ventas.models import Pago, Pedido

ENTREGA = {"DELIVERY": "Entrega a domicilio", "RETIRO": "Retiro en sucursal", "EN_TIENDA": "Compra en tienda"}


def _fmt(n) -> str:
    return f"Bs {n:,.2f}"


def generar_pdf(empresa: dict, sucursal: dict, cliente: str, pedido: Pedido, pago: Pago | None, iva_porcentaje: int, atendio: str | None = None) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    ancho, alto = A4
    x, y = 20 * mm, alto - 22 * mm

    def linea(texto: str, tam: int = 10, negrita: bool = False, dx: float = 0, avance: float = 5.2):
        nonlocal y
        c.setFont("Helvetica-Bold" if negrita else "Helvetica", tam)
        c.drawString(x + dx, y, texto)
        y -= avance * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, empresa["razon_social"])
    c.setFont("Helvetica-Bold", 11)
    titulo = {"FACTURA": "FACTURA", "INTERNO_TEMPORAL": "COMPROBANTE INTERNO TEMPORAL"}.get(pedido.comprobante_tipo or "", "COMPROBANTE DE COMPRA")
    c.drawRightString(ancho - x, y, titulo)
    y -= 7 * mm
    linea(f"NIT {empresa['nit']}" + (f" · Tel. {empresa['telefono']}" if empresa["telefono"] else ""))
    linea(f"Sucursal {sucursal.get('nombre', '')} · {sucursal.get('direccion', '')} · {sucursal.get('ciudad', '')}")
    y -= 2 * mm
    c.line(x, y, ancho - x, y)
    y -= 7 * mm

    linea(f"N.° {pedido.comprobante_numero}      Pedido {pedido.codigo}", 11, True)
    fecha = pedido.pagado_en or pedido.creado_en
    linea(f"Fecha: {fecha.astimezone().strftime('%d/%m/%Y %H:%M')}")
    linea(f"Cliente: {cliente}" + (f" · Atendió: {atendio}" if atendio else ""))
    if pedido.autorizacion_fiscal:
        linea(f"Autorización: {pedido.autorizacion_fiscal}", 8.5)
    linea(f"Facturar a: {pedido.razon_social or cliente} · NIT/CI {pedido.nit_ci}")
    entrega = ENTREGA.get(pedido.tipo_entrega, pedido.tipo_entrega)
    linea(f"Entrega: {entrega}" + (f" · {pedido.direccion_entrega}" if pedido.direccion_entrega else ""))
    y -= 3 * mm

    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Descripción")
    c.drawRightString(ancho - x - 70 * mm, y, "Cant.")
    c.drawRightString(ancho - x - 38 * mm, y, "P. unit.")
    c.drawRightString(ancho - x, y, "Subtotal")
    y -= 2 * mm
    c.line(x, y, ancho - x, y)
    y -= 5 * mm
    for item in pedido.items:
        if y < 50 * mm:  # salto de página en pedidos largos
            c.showPage()
            y = alto - 25 * mm
        c.setFont("Helvetica", 9)
        c.drawString(x, y, f"{item.producto} · {item.talla} · {item.color}"[:60])
        c.drawRightString(ancho - x - 70 * mm, y, str(item.cantidad))
        c.drawRightString(ancho - x - 38 * mm, y, f"{item.precio_final:,.2f}")
        c.drawRightString(ancho - x, y, f"{item.subtotal:,.2f}")
        y -= 4.6 * mm
        c.setFont("Helvetica", 7.5)
        c.drawString(x, y, f"SKU {item.sku}")
        y -= 4.2 * mm
    c.line(x, y, ancho - x, y)
    y -= 6 * mm

    for texto, valor, negrita in (
        ("Subtotal", pedido.subtotal, False), ("Descuento", -pedido.descuento, False), ("TOTAL", pedido.total, True),
    ):
        c.setFont("Helvetica-Bold" if negrita else "Helvetica", 11 if negrita else 10)
        c.drawString(ancho - x - 70 * mm, y, texto)
        c.drawRightString(ancho - x, y, _fmt(valor))
        y -= 5.4 * mm
    c.setFont("Helvetica", 8.5)
    c.drawString(ancho - x - 70 * mm, y, f"IVA incluido ({iva_porcentaje}%)")
    c.drawRightString(ancho - x, y, _fmt(pedido.iva_incluido))
    y -= 9 * mm

    if pago is not None:
        medio = f"{pago.tarjeta_marca} terminada en {pago.tarjeta_ultimos4}" if pago.tarjeta_ultimos4 else {"EFECTIVO": "Efectivo"}.get(pago.metodo, pago.metodo.capitalize())
        linea(f"Pago: {medio} · {pago.estado.replace('_', ' ').capitalize()}", 10, True)
        if pago.monto_recibido is not None:
            linea(f"Recibido: {_fmt(pago.monto_recibido)} · Cambio: {_fmt(pago.cambio or 0)}", 9)
    if pedido.comprobante_tipo == "INTERNO_TEMPORAL":
        linea("El servicio de impuestos no respondió: este comprobante interno temporal se reemplazará por la factura.", 8.5)
    y -= 6 * mm
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(x, y, "Documento de prueba de un proyecto académico (pago en modo de prueba): no tiene validez fiscal.")
    c.showPage()
    c.save()
    return buf.getvalue()
