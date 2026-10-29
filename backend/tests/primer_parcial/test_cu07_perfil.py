"""CU-07 Perfil de gustos del cliente — aprende de compras, búsquedas, prendas vistas y pedidos al asistente; recomienda con motivo, ofertas y outfits; el cliente controla su privacidad."""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text

from app.core.ia import ClienteIA
from app.primer_parcial.ia.cu07_asistente import recomendador
from app.primer_parcial.ia.cu07_asistente.perfil import construir_perfil, puntuar
from tests.catalogo_util import cabecera_cliente, por_variante, talla_id
from tests.compras_util import comprar, stock_listo
from tests.primer_parcial.test_cu07_asistente import _chat
from tests.reportes_util import con_ia
from tests.test_cu23_reportes_generativos import ApiFalsa

AHORA = datetime(2026, 10, 29, tzinfo=timezone.utc)


def _catalogo(inv, mundo):
    """Camisa Oxford (Camisas, Rojo/Azul, Bs 100) + Jean Slim (Pantalones, Azul, Bs 180) + Camisa Lino (Camisas, Azul, Bs 90), todo con stock."""
    stock_listo(inv, mundo)
    jean = inv.producto("Jean Slim", inv.pantalones["id"], inv.col["id"], [talla_id(inv.numerico, "30")], [inv.azul["id"]], precio="180.00")
    lino = inv.producto("Camisa Lino", inv.camisas["id"], inv.col["id"], [talla_id(inv.alfa, "M")], [inv.azul["id"]], precio="90.00")
    for p in (jean, lino):
        inv.stock(mundo.a.id, inv.centro.id, p["variantes"][0]["id"], 5)
    return jean, lino


def _interaccion(client, h, **cuerpo):
    return client.post("/api/asistente/interacciones", json=cuerpo, headers=h)


def _nombres(rec):
    return [p["nombre"] for p in rec["productos"]]


def test_01_el_perfil_pondera_compras_busquedas_y_lo_reciente():
    compras = [(1, 10, 100, "M", Decimal("100"), 2, AHORA)]
    interacciones = [("BUSQUEDA", None, 20, 200, "L", Decimal("240"), "pantalón azul", AHORA), ("VISTA", 5, 20, None, None, None, None, AHORA - timedelta(days=60))]
    p = construir_perfil(compras, interacciones, AHORA)
    assert p.compras == 1 and p.senales == 3 and p.comprados == {1} and p.vistos == {5} and p.busquedas == ["pantalón azul"]
    assert p.categorias[10] == 6.0 and p.categorias[20] == 2.0 + 0.25  # compra 3×2 u.; búsqueda 2 + vista de hace 60 días (1 × ¼)
    assert p.colores == {100: 6.0, 200: 2.0} and max(p.tallas, key=p.tallas.get) == "M"
    rango = p.rango_de_precio()
    assert rango == (Decimal("60.00"), Decimal("140.00"))  # el precio típico (Bs 100) ± 40 %


def test_02_la_puntuacion_premia_lo_que_encaja_con_el_perfil():
    p = construir_perfil([(1, 10, 100, "M", Decimal("100"), 1, AHORA)], [], AHORA)
    encaja, razones = puntuar(p, 10, [100], ["M"], Decimal("110"), 2, False)
    otra, _ = puntuar(p, 99, [300], ["XL"], Decimal("900"), 3, False)
    assert encaja > 8 and otra == 0 and razones["categoria"] and razones["color"] and razones["talla"] and razones["precio"]
    assert puntuar(p, 99, [300], ["XL"], Decimal("900"), 3, True)[0] == 0  # una oferta que no le interesa no suma


def test_03_sin_historial_se_muestra_lo_mas_vendido(inv, mundo, db, client):
    con_ia(db, mundo)
    _catalogo(inv, mundo)
    rec = client.get("/api/asistente/recomendaciones", headers=inv.h_cliente).json()
    assert rec["personalizada"] is False and rec["motivo"] == "Lo más vendido de la tienda." and rec["origen"] == "REGLAS" and rec["ofertas"] == []
    assert client.get("/api/asistente/privacidad", headers=inv.h_cliente).json() == {"personalizar": True, "interacciones": 0}


def test_04_aprende_de_las_busquedas_y_prendas_vistas(inv, mundo, db, client):
    con_ia(db, mundo)
    jean, lino = _catalogo(inv, mundo)
    assert _interaccion(client, inv.h_cliente, tipo="BUSQUEDA", texto="pantalón azul", categoria_id=inv.pantalones["id"], color_id=inv.azul["id"]).json() == {"registrada": True}
    assert _interaccion(client, inv.h_cliente, tipo="VISTA", producto_id=jean["id"]).status_code == 201
    rec = client.get("/api/asistente/recomendaciones", headers=inv.h_cliente).json()
    assert rec["personalizada"] is True and _nombres(rec)[0] == "Jean Slim" and rec["motivo"] == "Porque ha buscado prendas de Pantalones en color Azul."
    motivo = rec["motivos"][str(jean["id"])]
    assert "es de Pantalones, que le interesa" in motivo and "ya la miró" in motivo and "color que suele elegir" in motivo
    assert client.get("/api/asistente/privacidad", headers=inv.h_cliente).json()["interacciones"] == 2


def test_05_lo_comprado_pesa_mas_y_no_se_recomienda_de_nuevo(inv, mundo, db, client):
    con_ia(db, mundo)
    jean, lino = _catalogo(inv, mundo)
    _interaccion(client, inv.h_cliente, tipo="BUSQUEDA", categoria_id=inv.pantalones["id"])  # busca pantalones (peso 2)…
    comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1)  # …pero compró una camisa roja (peso 3)
    rec = client.get("/api/asistente/recomendaciones", headers=inv.h_cliente).json()
    nombres = _nombres(rec)
    assert "Camisa Oxford" not in nombres and nombres[0] == "Camisa Lino"  # la camisa que ya compró no se repite; otra camisa va primero
    assert "Jean Slim" in nombres and rec["motivo"].startswith("Porque compró prendas de Camisas")


def test_06_las_ofertas_son_las_que_encajan_con_sus_gustos(inv, mundo, db, client):
    con_ia(db, mundo)
    jean, lino = _catalogo(inv, mundo)
    hoy = datetime.now().date()
    r = client.post("/api/promociones", json={"nombre": "Jeans -20 %", "tipo_descuento": "PORCENTAJE", "valor": "20", "inicia": str(hoy - timedelta(days=1)),
                                              "termina": str(hoy + timedelta(days=5)), "productos_ids": [jean["id"]]}, headers=inv.h_admin)
    assert r.status_code == 201, r.text
    _interaccion(client, inv.h_cliente, tipo="BUSQUEDA", categoria_id=inv.pantalones["id"])
    rec = client.get("/api/asistente/recomendaciones", headers=inv.h_cliente).json()
    assert [p["nombre"] for p in rec["ofertas"]] == ["Jean Slim"] and "está en oferta" in rec["motivos"][str(jean["id"])]


def test_07_el_asistente_recuerda_lo_que_pidio_y_recomienda_si_se_lo_piden(inv, mundo, db, client):
    con_ia(db, mundo)
    _catalogo(inv, mundo)
    antes = _chat(client, inv.h_cliente, "recomiéndame algo").json()
    assert antes["respuesta"].startswith("Todavía no conozco sus gustos") and antes["filtros"].get("recomendar") is True
    _chat(client, inv.h_cliente, "busco un pantalón azul de menos de 250")
    assert client.get("/api/asistente/privacidad", headers=inv.h_cliente).json()["interacciones"] == 1
    c = _chat(client, inv.h_cliente, "¿qué me recomiendas?").json()
    assert c["respuesta"].startswith("Estas prendas le pueden gustar. Porque ha buscado prendas de Pantalones en color Azul.") and c["productos"][0]["nombre"] == "Jean Slim"


def test_08_un_outfit_combina_prendas_de_otras_categorias(inv, mundo, db, client):
    con_ia(db, mundo)
    jean, lino = _catalogo(inv, mundo)
    o = client.get("/api/asistente/outfit", params={"producto_id": lino["id"]}, headers=inv.h_cliente).json()
    assert o["base"]["nombre"] == "Camisa Lino" and [p["nombre"] for p in o["prendas"]] == ["Jean Slim"] and o["origen"] == "REGLAS"
    assert o["motivos"][str(jean["id"])] == "Combina en tono con la prenda base." and o["motivo"] == "Outfit armado alrededor de Camisa Lino: Jean Slim."
    sin_base = client.get("/api/asistente/outfit", headers=inv.h_cliente).json()
    assert sin_base["base"] is not None and sin_base["prendas"]
    r = client.get("/api/asistente/outfit", params={"producto_id": 99999}, headers=inv.h_cliente)
    assert r.status_code == 404 and r.json()["detail"] == "Prenda no encontrada o sin stock."


def test_09_con_ia_elige_entre_las_candidatas_y_se_valida(inv, mundo, db, client, monkeypatch):
    con_ia(db, mundo)
    jean, lino = _catalogo(inv, mundo)
    _interaccion(client, inv.h_cliente, tipo="BUSQUEDA", categoria_id=inv.camisas["id"], color_id=inv.azul["id"])
    api = ApiFalsa(json.dumps({"seleccion": [{"id": lino["id"], "motivo": "Una camisa azul fresca, como las que busca."}, {"id": 99999, "motivo": "inventada"}, {"id": lino["id"], "motivo": "repetida"}]}))
    monkeypatch.setattr(recomendador, "obtener_ia", lambda: ClienteIA("clave-de-prueba", "modelo", http=api))
    rec = client.get("/api/asistente/recomendaciones", params={"limite": 1}, headers=inv.h_cliente).json()
    assert rec["origen"] == "IA" and _nombres(rec) == ["Camisa Lino"] and rec["motivos"][str(lino["id"])] == "Una camisa azul fresca, como las que busca."
    enviado = json.loads(api.llamadas[0][2]["messages"][0]["content"].split("\n", 1)[1])  # lo que se le dio a la IA: perfil y candidatas reales
    assert enviado["perfil"]["categorias_favoritas"] == ["Camisas"] and enviado["perfil"]["colores_favoritos"] == ["Azul"]
    assert {c["nombre"] for c in enviado["candidatas"]} <= {"Camisa Oxford", "Camisa Lino", "Jean Slim"}
    monkeypatch.setattr(recomendador, "obtener_ia", lambda: ClienteIA("clave", "m", http=ApiFalsa(json.dumps({"seleccion": [{"id": 99999, "motivo": "x"}]}))))
    assert client.get("/api/asistente/recomendaciones", headers=inv.h_cliente).json()["origen"] == "REGLAS"  # lo inventado se descarta


def test_10_con_ia_arma_el_outfit(inv, mundo, db, client, monkeypatch):
    con_ia(db, mundo)
    jean, lino = _catalogo(inv, mundo)
    api = ApiFalsa(json.dumps({"seleccion": [{"id": jean["id"], "motivo": "El denim azul equilibra la camisa."}]}))
    monkeypatch.setattr(recomendador, "obtener_ia", lambda: ClienteIA("clave-de-prueba", "modelo", http=api))
    o = client.get("/api/asistente/outfit", params={"producto_id": lino["id"]}, headers=inv.h_cliente).json()
    assert o["origen"] == "IA" and o["motivos"][str(jean["id"])] == "El denim azul equilibra la camisa."
    assert "Camisa Lino" in api.llamadas[0][2]["messages"][0]["content"]


def test_11_el_cliente_controla_su_privacidad(inv, mundo, db, client):
    con_ia(db, mundo)
    jean, lino = _catalogo(inv, mundo)
    _interaccion(client, inv.h_cliente, tipo="BUSQUEDA", categoria_id=inv.pantalones["id"])
    assert client.delete("/api/asistente/historial", headers=inv.h_cliente).json() == {"personalizar": True, "interacciones": 0}
    assert client.get("/api/asistente/recomendaciones", headers=inv.h_cliente).json()["personalizada"] is False  # olvidó lo aprendido
    _interaccion(client, inv.h_cliente, tipo="BUSQUEDA", categoria_id=inv.pantalones["id"])
    assert client.put("/api/asistente/privacidad", json={"personalizar": False}, headers=inv.h_cliente).json() == {"personalizar": False, "interacciones": 0}
    assert _interaccion(client, inv.h_cliente, tipo="BUSQUEDA", categoria_id=inv.pantalones["id"]).json() == {"registrada": False}  # ya no aprende
    comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1)
    assert client.get("/api/asistente/recomendaciones", headers=inv.h_cliente).json()["personalizada"] is False  # ni usa lo comprado
    _chat(client, inv.h_cliente, "una camisa azul")
    assert client.get("/api/asistente/privacidad", headers=inv.h_cliente).json()["interacciones"] == 0
    assert client.put("/api/asistente/privacidad", json={"personalizar": True}, headers=inv.h_cliente).json()["personalizar"] is True
    assert client.get("/api/asistente/recomendaciones", headers=inv.h_cliente).json()["personalizada"] is True  # vuelve a usar lo comprado


def test_12_las_interacciones_se_validan_y_se_recortan(inv, mundo, db, client):
    con_ia(db, mundo)
    jean, lino = _catalogo(inv, mundo)
    r = _interaccion(client, inv.h_cliente, tipo="VISTA")
    assert r.status_code == 422 and r.json()["detail"] == "Indique la prenda que miró."
    r = _interaccion(client, inv.h_cliente, tipo="VISTA", producto_id=99999)
    assert r.status_code == 404 and r.json()["detail"] == "Prenda no encontrada."
    r = _interaccion(client, inv.h_cliente, tipo="BUSQUEDA")
    assert r.status_code == 422 and r.json()["detail"] == "La búsqueda no tiene datos de los que aprender."
    assert _interaccion(client, inv.h_cliente, tipo="OTRA", texto="x").status_code == 422
    for i in range(205):
        db.execute(text("INSERT INTO interacciones_cliente (empresa_id, cliente_id, tipo, texto) SELECT empresa_id, id, 'BUSQUEDA', 'x' FROM usuarios WHERE email = 'cliente@tienda.com' AND empresa_id = :e"), {"e": mundo.a.id})
    db.commit()
    _interaccion(client, inv.h_cliente, tipo="BUSQUEDA", texto="nueva")
    assert client.get("/api/asistente/privacidad", headers=inv.h_cliente).json()["interacciones"] == 200  # solo se recuerda lo último


def test_13_plan_roles_y_aislamiento(inv, mundo, tienda_b, db, datos, client):
    jean, lino = _catalogo(inv, mundo)
    for ruta in ("outfit", "privacidad"):
        r = client.get(f"/api/asistente/{ruta}", headers=inv.h_cliente)  # EMP-A tiene plan Básico
        assert r.status_code == 403 and r.json()["detail"] == "Su plan no incluye esta funcionalidad. Cambie al plan Profesional."
    assert _interaccion(client, inv.h_cliente, tipo="BUSQUEDA", texto="x").status_code == 403
    con_ia(db, mundo)
    for h in (inv.h_admin, inv.h_cajero, inv.h_enc_centro):
        assert client.get("/api/asistente/privacidad", headers=h).status_code == 403
    _interaccion(client, inv.h_cliente, tipo="BUSQUEDA", categoria_id=inv.pantalones["id"])
    h_b = cabecera_cliente(datos, mundo.b)  # cliente de EMP-B: no ve el perfil ni los productos de EMP-A
    assert client.get("/api/asistente/privacidad", headers=h_b).json()["interacciones"] == 0
    assert _interaccion(client, h_b, tipo="VISTA", producto_id=jean["id"]).status_code == 404
    assert client.get("/api/asistente/outfit", params={"producto_id": jean["id"]}, headers=h_b).status_code == 404
    assert client.get("/api/asistente/recomendaciones", headers=h_b).json()["productos"] == []
