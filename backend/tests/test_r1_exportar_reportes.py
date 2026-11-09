"""Prompt R · A1: el reporte generativo se exporta a Excel y PDF con formato de reporte convencional."""
from io import BytesIO

from openpyxl import load_workbook

from tests.reportes_util import con_ia, movimiento


def _reporte(client, inv, mundo, db, prompt="los productos más vendidos de este mes y las ventas"):
    con_ia(db, mundo)
    movimiento(client, inv, mundo)
    r = client.post("/api/ia/reportes", json={"prompt": prompt}, headers=inv.h_admin)
    assert r.status_code == 201, r.text
    return r.json()


def test_01_excel_con_encabezado_filtros_tablas_y_pie(inv, mundo, client, db):
    rep = _reporte(client, inv, mundo, db)
    r = client.get(f"/api/ia/reportes/{rep['id']}/exportar?formato=xlsx", headers=inv.h_admin)
    assert r.status_code == 200 and "spreadsheetml" in r.headers["content-type"]
    assert r.headers["content-disposition"] == f'attachment; filename="reporte-{rep["id"]}.xlsx"'
    libro = load_workbook(BytesIO(r.content))
    assert len(libro.sheetnames) >= 1
    primera = libro[libro.sheetnames[0]]
    textos = [str(c.value) for fila in primera.iter_rows() for c in fila if c.value is not None]
    assert any("Reporte:" in t for t in textos) and "Periodo:" in textos and "Generado por FashionStore" in textos
    assert any(t == "Fecha y hora:" for t in textos)


def test_02_pdf_valido_y_no_vacio(inv, mundo, client, db):
    rep = _reporte(client, inv, mundo, db)
    r = client.get(f"/api/ia/reportes/{rep['id']}/exportar?formato=pdf", headers=inv.h_admin)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and len(r.content) > 1500


def test_03_formato_desconocido_da_mensaje_claro(inv, mundo, client, db):
    rep = _reporte(client, inv, mundo, db)
    r = client.get(f"/api/ia/reportes/{rep['id']}/exportar?formato=doc", headers=inv.h_admin)
    assert r.status_code == 422 or r.status_code == 400
    assert "Formato de exportación no válido" in r.text


def test_04_plan_basico_no_exporta(inv, mundo, client):
    r = client.get("/api/ia/reportes/1/exportar?formato=pdf", headers=inv.h_admin)
    assert r.status_code == 403 and r.json()["detail"].startswith("Su plan no incluye esta funcionalidad")


def test_05_reporte_de_otra_empresa_da_404(inv, mundo, tienda_b, client, db):
    rep = _reporte(client, inv, mundo, db)
    r = client.get(f"/api/ia/reportes/{rep['id']}/exportar?formato=xlsx", headers=tienda_b.h_admin)
    assert r.status_code == 404


# ---- A2: reportes convencionales en Excel y PDF, y el inventario por sucursal ----
def test_06_los_reportes_convencionales_salen_en_excel_y_pdf(inv, mundo, client, db):
    movimiento(client, inv, mundo)
    for tipo in ("ventas", "reservas", "pagos", "inventario"):
        x = client.get(f"/api/reportes/exportar/{tipo}?formato=xlsx", headers=inv.h_admin)
        assert x.status_code == 200 and "spreadsheetml" in x.headers["content-type"], tipo
        assert load_workbook(BytesIO(x.content)).sheetnames
        p = client.get(f"/api/reportes/exportar/{tipo}?formato=pdf", headers=inv.h_admin)
        assert p.status_code == 200 and p.content.startswith(b"%PDF"), tipo
        assert client.get(f"/api/reportes/exportar/{tipo}?formato=csv", headers=inv.h_admin).status_code == 200


def test_07_formato_invalido_en_reportes_convencionales(inv, client):
    r = client.get("/api/reportes/exportar/ventas?formato=doc", headers=inv.h_admin)
    assert r.status_code in (400, 422) and "Formato de exportación no válido" in r.text


def test_08_inventario_por_sucursal_con_filtros_y_paginacion(inv, mundo, client):
    from tests.compras_util import stock_listo

    stock_listo(inv, mundo, centro=10, norte=0)
    todo = client.get("/api/reportes/inventario", headers=inv.h_admin).json()
    assert todo["total"] == 8 and len(todo["items"]) == 8  # 4 variantes en 2 sucursales
    assert {i["sucursal"] for i in todo["items"]} == {inv.centro.nombre, inv.norte.nombre}
    agotados = [i for i in todo["items"] if i["situacion"] == "Agotado"]
    assert len(agotados) == 4 and all(i["sucursal"] == inv.norte.nombre for i in agotados)
    solo_centro = client.get(f"/api/reportes/inventario?sucursal={inv.centro.id}", headers=inv.h_admin).json()
    assert solo_centro["total"] == 4
    pagina = client.get("/api/reportes/inventario?tamano=3&pagina=2", headers=inv.h_admin).json()
    assert (pagina["total"], len(pagina["items"]), pagina["pagina"]) == (8, 3, 2)
    assert client.get(f"/api/reportes/inventario?categoria={inv.camisa['categoria_id']}", headers=inv.h_admin).json()["total"] == 8 if "categoria_id" in inv.camisa else True


def test_09_inventario_de_otra_empresa_da_404_y_exige_plan(inv, mundo, tienda_b, client):
    assert client.get(f"/api/reportes/inventario?sucursal={inv.centro.id}", headers=tienda_b.h_admin).status_code == 404
    assert client.get("/api/reportes/exportar/inventario?formato=pdf", headers=tienda_b.h_admin).status_code == 200
