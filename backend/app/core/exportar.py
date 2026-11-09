"""Exportación de reportes a Excel y PDF con formato de reporte convencional (§8.1 del enunciado, RF23).

Un reporte se describe con un diccionario simple y de ahí salen los dos formatos, sin duplicar código:
    {"empresa": ..., "titulo": ..., "filtros": [("Periodo", "..."), ...], "tablas": [{"nombre", "columnas", "filas"}], "grafico": {"titulo", "categorias", "valores"} | None}
"""
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PIE = "Generado por FashionStore"
FORMATOS = {"xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "pdf": "application/pdf"}
VINO = "7A1F3D"


def _ahora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _hoja(nombre: str, usados: set[str]) -> str:
    """Nombre de hoja válido para Excel (máximo 31 caracteres, sin símbolos prohibidos y sin repetirse)."""
    limpio = "".join(c for c in nombre if c not in '[]:*?/\\')[:31] or "Hoja"
    base, n = limpio, 2
    while limpio in usados:
        limpio = f"{base[:28]}_{n}"
        n += 1
    usados.add(limpio)
    return limpio


def a_excel(rep: dict) -> bytes:
    libro = Workbook()
    libro.remove(libro.active)
    usados: set[str] = set()
    tablas = rep["tablas"] or [{"nombre": "Resumen", "columnas": ["Dato"], "filas": [["Sin datos en el periodo"]]}]
    for t in tablas:
        hoja = libro.create_sheet(_hoja(t["nombre"], usados))
        hoja["A1"] = rep["empresa"]
        hoja["A1"].font = Font(bold=True, size=14, color=VINO)
        hoja["A2"] = rep["titulo"]
        hoja["A2"].font = Font(bold=True, size=12)
        fila = 3
        for etiqueta, valor in rep["filtros"]:
            hoja.cell(fila, 1, f"{etiqueta}:").font = Font(bold=True)
            hoja.cell(fila, 2, str(valor))
            fila += 1
        hoja.cell(fila, 1, "Fecha y hora:").font = Font(bold=True)
        hoja.cell(fila, 2, _ahora())
        fila += 2
        cabecera = fila
        for j, nombre in enumerate(t["columnas"], 1):
            c = hoja.cell(cabecera, j, nombre)
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor=VINO)
            c.alignment = Alignment(horizontal="center")
        for i, datos in enumerate(t["filas"], cabecera + 1):
            for j, valor in enumerate(datos, 1):
                hoja.cell(i, j, valor)
        for j, nombre in enumerate(t["columnas"], 1):
            ancho = max([len(str(nombre))] + [len(str(f[j - 1])) for f in t["filas"] if len(f) >= j])
            hoja.column_dimensions[hoja.cell(cabecera, j).column_letter].width = min(ancho + 3, 50)
        ultima = cabecera + len(t["filas"])
        g = rep.get("grafico")
        if g and t is tablas[0] and g["categorias"]:  # el gráfico nativo va en la primera hoja, con sus propios datos
            base = ultima + 3
            hoja.cell(base - 1, 1, g["titulo"]).font = Font(bold=True)
            for i, (cat, val) in enumerate(zip(g["categorias"], g["valores"]), base):
                hoja.cell(i, 1, cat)
                hoja.cell(i, 2, val)
            grafico = BarChart()
            grafico.title = g["titulo"]
            grafico.add_data(Reference(hoja, min_col=2, min_row=base, max_row=base + len(g["valores"]) - 1), titles_from_data=False)
            grafico.set_categories(Reference(hoja, min_col=1, min_row=base, max_row=base + len(g["valores"]) - 1))
            grafico.legend = None
            hoja.add_chart(grafico, f"D{cabecera}")
            ultima = base + len(g["valores"])
        hoja.cell(ultima + 2, 1, PIE).font = Font(italic=True, color="888888")
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


def a_pdf(rep: dict) -> bytes:
    estilos = getSampleStyleSheet()
    salida = BytesIO()
    doc = SimpleDocTemplate(salida, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm, bottomMargin=1.8 * cm, title=rep["titulo"])
    partes = [Paragraph(rep["empresa"], estilos["Title"]), Paragraph(rep["titulo"], estilos["Heading2"])]
    for etiqueta, valor in rep["filtros"]:
        partes.append(Paragraph(f"<b>{etiqueta}:</b> {valor}", estilos["Normal"]))
    partes += [Paragraph(f"<b>Fecha y hora:</b> {_ahora()}", estilos["Normal"]), Spacer(1, 0.5 * cm)]
    for t in rep["tablas"]:
        partes.append(Paragraph(t["nombre"], estilos["Heading3"]))
        filas = [t["columnas"]] + [[Paragraph(str(v), estilos["BodyText"]) if isinstance(v, str) and len(v) > 28 else v for v in f] for f in t["filas"]]
        if len(filas) == 1:
            filas.append(["Sin datos"] + [""] * (len(t["columnas"]) - 1))
        tabla = Table(filas, repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{VINO}")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4EEF0")]),
        ]))
        partes += [tabla, Spacer(1, 0.4 * cm)]
    g = rep.get("grafico")
    if g and g["categorias"]:
        dibujo = Drawing(440, 200)
        barras = VerticalBarChart()
        barras.x, barras.y, barras.width, barras.height = 40, 30, 380, 140
        barras.data = [[float(v) for v in g["valores"]]]
        barras.categoryAxis.categoryNames = [str(c)[:14] for c in g["categorias"]]
        barras.categoryAxis.labels.fontSize = 7
        barras.bars[0].fillColor = colors.HexColor(f"#{VINO}")
        dibujo.add(barras)
        partes += [Paragraph(g["titulo"], estilos["Heading3"]), dibujo]

    def pie(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Oblique", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(1.8 * cm, 1 * cm, PIE)
        canvas.drawRightString(A4[0] - 1.8 * cm, 1 * cm, f"Página {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(partes, onFirstPage=pie, onLaterPages=pie)
    return salida.getvalue()


def exportar(rep: dict, formato: str) -> bytes:
    return a_excel(rep) if formato == "xlsx" else a_pdf(rep)
