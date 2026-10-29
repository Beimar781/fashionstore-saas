"""Nota de devolución en PDF (RN15): respalda lo que volvió al inventario y el dinero que se movió."""
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.modules.ventas.models import Devolucion


def _fmt(n) -> str:
    return f"Bs {n:,.2f}"


def generar_nota(empresa: dict, sucursal: dict, devolucion: Devolucion, comprobante: str, registrada_por: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    ancho, alto = A4
    x, y = 20 * mm, alto - 22 * mm

    def linea(texto: str, tam: float = 10, negrita: bool = False, avance: float = 5.2):
        nonlocal y
        c.setFont("Helvetica-Bold" if negrita else "Helvetica", tam)
        c.drawString(x, y, texto)
        y -= avance * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, empresa["razon_social"])
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(ancho - x, y, "NOTA DE CAMBIO" if devolucion.tipo == "CAMBIO" else "NOTA DE DEVOLUCIÓN")
    y -= 7 * mm
    linea(f"NIT {empresa['nit']}")
    linea(f"Sucursal {sucursal.get('nombre', '')} · {sucursal.get('direccion', '')} · {sucursal.get('ciudad', '')}")
    y -= 2 * mm
    c.line(x, y, ancho - x, y)
    y -= 7 * mm
    linea(f"N.° {devolucion.numero}      Comprobante de la venta: {comprobante}", 11, True)
    linea(f"Fecha: {devolucion.creada_en.astimezone().strftime('%d/%m/%Y %H:%M')} · Registró: {registrada_por}")
    linea(f"Motivo: {devolucion.motivo}")
    y -= 3 * mm

    for sentido, titulo in (("DEVUELTA", "Prendas devueltas (vuelven al inventario)"), ("ENTREGADA", "Prendas entregadas en el cambio")):
        items = [i for i in devolucion.items if i.sentido == sentido]
        if not items:
            continue
        linea(titulo, 10, True)
        for i in items:
            c.setFont("Helvetica", 9)
            c.drawString(x, y, f"{i.cantidad} × {i.producto} · {i.talla} · {i.color}  (SKU {i.sku})"[:78])
            c.drawRightString(ancho - x, y, _fmt(i.subtotal))
            y -= 4.6 * mm
        y -= 3 * mm

    c.line(x, y, ancho - x, y)
    y -= 6 * mm
    linea(f"Valor devuelto: {_fmt(devolucion.monto_devuelto)}", 10)
    if devolucion.tipo == "CAMBIO":
        linea(f"Valor de las prendas nuevas: {_fmt(devolucion.monto_nuevo)}", 10)
    if devolucion.reembolso:
        medio = {"TARJETA": "a la misma tarjeta (reembolso en la pasarela)", "EFECTIVO": "en efectivo"}.get(devolucion.medio_reembolso or "", "")
        linea(f"Dinero devuelto al cliente: {_fmt(devolucion.reembolso)} {medio}", 11, True)
    if devolucion.cobro_adicional:
        if devolucion.medio_cobro == "TARJETA":
            detalle = f"con tarjeta {devolucion.cobro_tarjeta_marca} terminada en {devolucion.cobro_tarjeta_ultimos4}"
        else:
            detalle = f"en efectivo (recibido {_fmt(devolucion.monto_recibido)}, cambio {_fmt(devolucion.cambio_entregado or 0)})" if devolucion.monto_recibido is not None else "en efectivo"
        linea(f"Diferencia cobrada al cliente: {_fmt(devolucion.cobro_adicional)} {detalle}", 11, True)
    y -= 14 * mm
    c.line(x, y, x + 60 * mm, y)
    c.line(ancho - x - 60 * mm, y, ancho - x, y)
    y -= 4.5 * mm
    c.setFont("Helvetica", 8.5)
    c.drawString(x, y, "Firma del cliente")
    c.drawString(ancho - x - 60 * mm, y, "Firma del empleado")
    y -= 10 * mm
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(x, y, "Documento de prueba de un proyecto académico: no tiene validez fiscal.")
    c.showPage()
    c.save()
    return buf.getvalue()
