"""CU-07 Asistente y recomendador de prendas — interpretación por reglas y por IA (doble en memoria), búsqueda con stock, recomendaciones, plan y aislamiento."""
import json
from decimal import Decimal

from app.core.ia import ClienteIA
from app.primer_parcial.ia.cu07_asistente import service
from app.primer_parcial.ia.cu07_asistente.intencion import combinar, parsear_con_reglas
from tests.catalogo_util import talla_id
from tests.compras_util import comprar, stock_listo
from tests.reportes_util import con_ia
from tests.test_cu23_reportes_generativos import ApiFalsa

COLORES, CATEGORIAS = ["Rojo", "Azul", "Verde"], ["Camisas", "Pantalones"]
MSG_PLAN = "Su plan no incluye esta funcionalidad. Cambie al plan Profesional."
SIN_RESULTADOS = "No encontré prendas disponibles con esas características. Pruebe con otro color, otra categoría o un precio mayor."


def _chat(client, h, *textos, **extra):
    """Una conversación: los textos alternan cliente y asistente empezando por el cliente."""
    mensajes = [{"rol": "usuario" if i % 2 == 0 else "asistente", "texto": t} for i, t in enumerate(textos)]
    return client.post("/api/asistente/chat", json={"mensajes": mensajes, **extra}, headers=h)


def _ia(monkeypatch, api):
    monkeypatch.setattr(service, "obtener_ia", lambda: ClienteIA("clave-de-prueba", "modelo", http=api))


def test_01_las_reglas_entienden_color_categoria_talla_y_precio():
    i = parsear_con_reglas("Busco una camisa azul talla M de menos de 200 bs para hombre", COLORES, CATEGORIAS)
    assert (i.categorias, i.colores, i.talla, i.precio_max, i.genero) == (["Camisas"], ["Azul"], "M", Decimal("200"), "MASCULINO")
    i = parsear_con_reglas("pantalones entre 150 y 80", COLORES, CATEGORIAS)
    assert (i.precio_min, i.precio_max) == (Decimal("80"), Decimal("150"))
    i = parsear_con_reglas("algo formal alrededor de 100", COLORES, CATEGORIAS)
    assert (i.ocasion, i.precio_min, i.precio_max) == ("formal", Decimal("80.00"), Decimal("120.00"))
    assert parsear_con_reglas("arma un outfit con ofertas", COLORES, CATEGORIAS).outfit and parsear_con_reglas("hay descuentos?", COLORES, CATEGORIAS).ofertas
    assert parsear_con_reglas("¡Hola!", COLORES, CATEGORIAS).saludo and not parsear_con_reglas("hola quiero una camisa", COLORES, CATEGORIAS).saludo


def test_02_lo_nuevo_completa_lo_anterior():
    antes = parsear_con_reglas("quiero una camisa", COLORES, CATEGORIAS)
    ahora = parsear_con_reglas("y en azul", COLORES, CATEGORIAS)
    i = combinar(antes, ahora)
    assert (i.categorias, i.colores) == (["Camisas"], ["Azul"])
    assert combinar(antes, parsear_con_reglas("mejor roja", COLORES, CATEGORIAS)).colores == ["Rojo"]


def test_03_el_asistente_encuentra_prendas_con_stock(inv, mundo, db, client):
    con_ia(db, mundo)
    stock_listo(inv, mundo)
    r = _chat(client, inv.h_cliente, "Quiero una camisa azul")
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["origen"] == "REGLAS" and [p["nombre"] for p in c["productos"]] == ["Camisa Oxford"] and c["filtros"]["colores"] == ["Azul"]
    assert c["respuesta"] == "Encontré 1 prenda(s) disponible(s) (Camisas, Azul)." and len(c["sugerencias"]) == 3


def test_04_sin_stock_no_se_ofrece_la_prenda(inv, mundo, db, client):
    con_ia(db, mundo)  # el catálogo existe pero no hay existencias en ninguna sucursal
    c = _chat(client, inv.h_cliente, "una camisa roja").json()
    assert c["productos"] == [] and c["respuesta"] == SIN_RESULTADOS
    stock_listo(inv, mundo, centro=10, norte=0)
    assert _chat(client, inv.h_cliente, "una camisa roja", sucursal_id=inv.norte.id).json()["productos"] == []  # en Norte no hay
    assert len(_chat(client, inv.h_cliente, "una camisa roja", sucursal_id=inv.centro.id).json()["productos"]) == 1


def test_05_si_no_hay_con_todo_lo_pedido_se_suelta_un_filtro_y_se_avisa(inv, mundo, db, client):
    con_ia(db, mundo)
    stock_listo(inv, mundo)
    c = _chat(client, inv.h_cliente, "una camisa roja de menos de 50").json()  # la camisa cuesta Bs 100
    assert [p["nombre"] for p in c["productos"]] == ["Camisa Oxford"]
    assert "amplié la búsqueda sin el filtro de precio" in c["respuesta"]


def test_06_la_conversacion_da_contexto(inv, mundo, db, client):
    con_ia(db, mundo)
    stock_listo(inv, mundo)
    c = _chat(client, inv.h_cliente, "quiero una camisa", "Encontré 1 prenda disponible.", "y en azul").json()
    assert (c["filtros"]["categorias"], c["filtros"]["colores"]) == (["Camisas"], ["Azul"]) and len(c["productos"]) == 1


def test_07_saludo_vacio_y_ofertas(inv, mundo, db, client):
    con_ia(db, mundo)
    stock_listo(inv, mundo)
    saludo = _chat(client, inv.h_cliente, "Hola").json()
    assert saludo["productos"] == [] and saludo["respuesta"].startswith("¡Hola! Soy el asistente de la tienda.")
    r = _chat(client, inv.h_cliente, "   ")
    assert r.status_code == 422 and r.json()["detail"] == "Escriba su consulta para el asistente."
    r = client.post("/api/asistente/chat", json={"mensajes": [{"rol": "usuario", "texto": "hola"}, {"rol": "asistente", "texto": "hola"}]}, headers=inv.h_cliente)
    assert r.status_code == 422 and r.json()["detail"] == "Escriba su consulta para el asistente."
    assert _chat(client, inv.h_cliente, "muéstrame las ofertas").json()["respuesta"] == "No encontré ofertas con esas características."


def test_08_un_outfit_junta_prendas_de_distintas_categorias(inv, mundo, db, client):
    con_ia(db, mundo)
    stock_listo(inv, mundo)
    jean = inv.producto("Jean Slim", inv.pantalones["id"], inv.col["id"], [talla_id(inv.numerico, "30")], [inv.azul["id"]], precio="180.00")
    inv.stock(mundo.a.id, inv.centro.id, jean["variantes"][0]["id"], 5)
    c = _chat(client, inv.h_cliente, "arma un outfit azul").json()
    assert {p["categoria"] for p in c["productos"]} == {"Camisas", "Pantalones"} and c["respuesta"].startswith("Le armé un outfit de 2 prenda(s)")


def test_09_con_clave_la_ia_interpreta_y_lo_inventado_se_descarta(inv, mundo, db, client, monkeypatch):
    con_ia(db, mundo)
    stock_listo(inv, mundo)
    api = ApiFalsa(json.dumps({"colores": ["Rojo", "Fucsia"], "categorias": ["Camisas", "Abrigos"], "outfit": False}))
    _ia(monkeypatch, api)
    c = _chat(client, inv.h_cliente, "algo rojo para la oficina").json()
    assert c["origen"] == "IA" and c["filtros"]["colores"] == ["Rojo"] and c["filtros"]["categorias"] == ["Camisas"]  # «Fucsia» y «Abrigos» no existen en la tienda
    contenido = api.llamadas[0][2]["messages"][0]["content"]
    assert "Rojo" in contenido and "Camisas" in contenido and "algo rojo para la oficina" in contenido
    _ia(monkeypatch, ApiFalsa("no es json"))
    assert _chat(client, inv.h_cliente, "camisa roja").json()["origen"] == "REGLAS"


def test_10_recomendaciones_de_lo_mas_vendido_si_no_compro(inv, mundo, db, client):
    con_ia(db, mundo)
    stock_listo(inv, mundo)
    r = client.get("/api/asistente/recomendaciones", headers=inv.h_cliente)
    assert r.status_code == 200, r.text
    rec = r.json()
    assert (rec["personalizada"], rec["motivo"], [p["nombre"] for p in rec["productos"]]) == (False, "Lo más vendido de la tienda.", ["Camisa Oxford"])


def test_11_recomendaciones_segun_lo_que_compro(inv, mundo, db, client):
    con_ia(db, mundo)
    stock_listo(inv, mundo)
    lino = inv.producto("Camisa Lino", inv.camisas["id"], inv.col["id"], [talla_id(inv.alfa, "M")], [inv.rojo["id"]])
    inv.stock(mundo.a.id, inv.centro.id, lino["variantes"][0]["id"], 5)
    comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1)
    rec = client.get("/api/asistente/recomendaciones", headers=inv.h_cliente).json()
    assert rec["personalizada"] is True and "Camisas" in rec["motivo"] and "Rojo" in rec["motivo"]
    assert [p["nombre"] for p in rec["productos"]] == ["Camisa Lino"]  # lo que ya compró no se recomienda
    assert client.get("/api/asistente/recomendaciones", params={"sucursal_id": 99999}, headers=inv.h_cliente).status_code == 404
    assert client.get("/api/asistente/recomendaciones", params={"limite": 0}, headers=inv.h_cliente).status_code == 422


def test_12_plan_roles_y_aislamiento(inv, mundo, tienda_b, db, datos, client):
    stock_listo(inv, mundo)
    r = _chat(client, inv.h_cliente, "una camisa")  # EMP-A tiene plan Básico
    assert r.status_code == 403 and r.json()["detail"] == MSG_PLAN
    assert client.get("/api/asistente/recomendaciones", headers=inv.h_cliente).status_code == 403
    con_ia(db, mundo)
    for h in (inv.h_admin, inv.h_cajero, inv.h_enc_centro):
        assert _chat(client, h, "una camisa").status_code == 403  # es del cliente
    assert client.post("/api/asistente/chat", json={"mensajes": [{"rol": "usuario", "texto": "hola"}]}).status_code == 401
    from tests.catalogo_util import cabecera_cliente
    h_b = cabecera_cliente(datos, mundo.b)  # cliente de EMP-B: tiene IA, pero el catálogo de EMP-A no existe para él
    c = _chat(client, h_b, "una camisa").json()
    assert c["productos"] == [] and c["respuesta"] == SIN_RESULTADOS
    assert client.get("/api/asistente/recomendaciones", headers=h_b).json()["productos"] == []
