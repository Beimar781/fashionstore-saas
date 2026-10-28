"""CU-19 Gestionar promociones y descuentos — caja negra (pasos de la ficha) + aislamiento entre empresas."""
from datetime import date, timedelta
from decimal import Decimal

from app.core.constantes import CLIENTE
from app.modules.acceso.models import Usuario
from app.primer_parcial.catalogo.publico import Producto, descuentos_vigentes
from tests.catalogo_util import talla_id

MSG_FECHAS = "La fecha de finalización debe ser posterior a la fecha de inicio."


def _promo(**extra):
    hoy = date.today()
    return {"nombre": "Liquidación", "tipo_descuento": "PORCENTAJE", "valor": "20",
            "inicia": (hoy - timedelta(days=1)).isoformat(), "termina": (hoy + timedelta(days=10)).isoformat(), **extra}


def _camisa(t, precio="100.00"):
    return t.producto("Camisa", t.camisas["id"], t.col["id"], [talla_id(t.alfa, "M")], [t.rojo["id"]], precio=precio)


def _precio_en_catalogo(datos, mundo, client, empresa=None):
    empresa = empresa or mundo.a
    cliente = datos.db.query(Usuario).filter_by(empresa_id=empresa.id, email="cliente@tienda.com").first() or datos.usuario(
        empresa, CLIENTE, email="cliente@tienda.com")
    h = datos.login(cliente, empresa)
    return client.get("/api/catalogo/productos", headers=h).json()["items"][0]


def test_01_ingresar_al_modulo_de_promociones(tienda_a, client):
    r = client.get("/api/promociones", headers=tienda_a.h_admin)
    assert r.status_code == 200 and r.json() == []


def test_02_registrar_promocion_con_fechas_y_categorias(tienda_a, client):
    r = client.post("/api/promociones", json=_promo(categorias_ids=[tienda_a.camisas["id"]]), headers=tienda_a.h_admin)
    assert r.status_code == 201
    assert (r.json()["activa"], r.json()["vigente"], r.json()["categorias_ids"]) == (True, True, [tienda_a.camisas["id"]])


def test_03_fecha_de_fin_anterior_al_inicio(tienda_a, client):
    hoy = date.today()
    r = client.post("/api/promociones", json=_promo(inicia=hoy.isoformat(), termina=(hoy - timedelta(days=3)).isoformat()), headers=tienda_a.h_admin)
    assert r.status_code == 422 and r.json()["detail"] == MSG_FECHAS


def test_04_el_catalogo_muestra_el_precio_con_descuento(datos, mundo, tienda_a, client):
    _camisa(tienda_a)
    client.post("/api/promociones", json=_promo(categorias_ids=[tienda_a.camisas["id"]]), headers=tienda_a.h_admin)
    item = _precio_en_catalogo(datos, mundo, client)
    assert (item["precio"], item["precio_final"], item["promocion"]) == ("100.00", "80.00", "Liquidación")


def test_05_el_pos_calcula_el_mismo_precio(mundo, tienda_a, client, db):
    p = _camisa(tienda_a)
    client.post("/api/promociones", json=_promo(productos_ids=[p["id"]]), headers=tienda_a.h_admin)
    producto = db.get(Producto, p["id"])
    final, promo = descuentos_vigentes(db, mundo.a.id).precio_final(producto, Decimal("100.00"))  # lo que usará el POS (CU-29)
    assert (final, promo.nombre) == (Decimal("80.00"), "Liquidación")


def test_06_editar_una_promocion(tienda_a, client):
    h = tienda_a.h_admin
    promo = client.post("/api/promociones", json=_promo(), headers=h).json()
    r = client.put(f"/api/promociones/{promo['id']}", json={"nombre": "Liquidación total", "valor": "35"}, headers=h)
    assert (r.json()["nombre"], r.json()["valor"]) == ("Liquidación total", "35.00")
    r = client.put(f"/api/promociones/{promo['id']}", json={"termina": (date.today() - timedelta(days=30)).isoformat()}, headers=h)
    assert r.status_code == 422 and r.json()["detail"] == MSG_FECHAS


def test_monto_fijo_la_mejor_promocion_gana_y_no_baja_de_cero(datos, mundo, tienda_a, client):
    _camisa(tienda_a, precio="100.00")
    h = tienda_a.h_admin
    client.post("/api/promociones", json=_promo(nombre="10%", valor="10"), headers=h)
    client.post("/api/promociones", json=_promo(nombre="Bs 25 menos", tipo_descuento="MONTO", valor="25"), headers=h)
    item = _precio_en_catalogo(datos, mundo, client)
    assert (item["precio_final"], item["promocion"]) == ("75.00", "Bs 25 menos")
    client.post("/api/promociones", json=_promo(nombre="Regalo", tipo_descuento="MONTO", valor="500"), headers=h)
    assert _precio_en_catalogo(datos, mundo, client)["precio_final"] == "0.00"


def test_no_aplican_las_vencidas_inactivas_los_cupones_ni_otro_alcance(datos, mundo, tienda_a, client):
    _camisa(tienda_a)
    h = tienda_a.h_admin
    hoy = date.today()
    client.post("/api/promociones", json=_promo(nombre="Vencida", inicia=(hoy - timedelta(days=20)).isoformat(), termina=(hoy - timedelta(days=10)).isoformat()), headers=h)
    client.post("/api/promociones", json=_promo(nombre="Apagada", activa=False), headers=h)
    client.post("/api/promociones", json=_promo(nombre="Cupón", codigo="verano20"), headers=h)  # los cupones se aplican al pagar
    client.post("/api/promociones", json=_promo(nombre="Solo pantalones", categorias_ids=[tienda_a.pantalones["id"]]), headers=h)
    item = _precio_en_catalogo(datos, mundo, client)
    assert (item["precio_final"], item["promocion"]) == ("100.00", None)
    vigentes = client.get("/api/promociones?solo_vigentes=true", headers=h).json()
    assert {x["nombre"] for x in vigentes} == {"Cupón", "Solo pantalones"}


def test_el_alcance_incluye_subcategorias_y_colecciones(datos, mundo, tienda_a, client):
    sub = tienda_a.categoria("Camisas formales", padre_id=tienda_a.camisas["id"])
    tienda_a.producto("Formal", sub["id"], tienda_a.col["id"], [talla_id(tienda_a.alfa, "M")], [tienda_a.rojo["id"]])
    h = tienda_a.h_admin
    client.post("/api/promociones", json=_promo(categorias_ids=[tienda_a.camisas["id"]]), headers=h)  # la categoría padre
    assert _precio_en_catalogo(datos, mundo, client)["precio_final"] == "80.00"
    otra_col = tienda_a.coleccion(tienda_a.temp["id"], "Otra")
    client.post("/api/promociones", json=_promo(nombre="Otra colección", valor="50", colecciones_ids=[otra_col["id"]]), headers=h)
    assert _precio_en_catalogo(datos, mundo, client)["precio_final"] == "80.00"  # el producto no es de esa colección


def test_validaciones_de_valor_y_codigo(tienda_a, client):
    h = tienda_a.h_admin
    r = client.post("/api/promociones", json=_promo(valor="150"), headers=h)
    assert r.status_code == 422 and r.json()["detail"] == "El porcentaje de descuento debe estar entre 0 y 100."
    assert client.post("/api/promociones", json=_promo(codigo="oferta1"), headers=h).status_code == 201
    r = client.post("/api/promociones", json=_promo(codigo="OFERTA1"), headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "Ya existe una promoción con ese código."


def test_eliminar_promocion(tienda_a, client, db):
    h = tienda_a.h_admin
    a = client.post("/api/promociones", json=_promo(), headers=h).json()
    assert client.delete(f"/api/promociones/{a['id']}", headers=h).status_code == 204
    b = client.post("/api/promociones", json=_promo(codigo="usada"), headers=h).json()
    db.execute(__import__("sqlalchemy").text("UPDATE promociones SET usos = 3 WHERE id = :i"), {"i": b["id"]})
    db.commit()
    r = client.delete(f"/api/promociones/{b['id']}", headers=h)
    assert r.status_code == 409 and "ya fue usada" in r.json()["detail"]


def test_aislamiento_entre_empresas(datos, mundo, tienda_a, tienda_b, client):
    _camisa(tienda_a)
    tienda_b.producto("Camisa", tienda_b.camisas["id"], tienda_b.col["id"], [talla_id(tienda_b.alfa, "M")], [tienda_b.rojo["id"]])
    promo = client.post("/api/promociones", json=_promo(), headers=tienda_a.h_admin).json()
    assert _precio_en_catalogo(datos, mundo, client)["precio_final"] == "80.00"
    assert _precio_en_catalogo(datos, mundo, client, mundo.b)["precio_final"] == "100.00"  # el descuento de A no llega a B
    assert client.get("/api/promociones", headers=tienda_b.h_admin).json() == []
    assert client.put(f"/api/promociones/{promo['id']}", json={"nombre": "Robada"}, headers=tienda_b.h_admin).status_code == 404
    assert client.delete(f"/api/promociones/{promo['id']}", headers=tienda_b.h_admin).status_code == 404
    r = client.post("/api/promociones", json=_promo(categorias_ids=[tienda_a.camisas["id"]]), headers=tienda_b.h_admin)
    assert r.status_code == 404  # no se puede apuntar a la categoría de otra empresa
