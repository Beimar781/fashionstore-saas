"""CU-03 Consultar catálogo de prendas — caja negra, errores del primer parcial (sección 9 del plan) y aislamiento."""
import pytest
from sqlalchemy import event

from tests.catalogo_util import PNG, cabecera_cliente, por_variante, talla_id


@pytest.fixture
def surtido(datos, mundo, tienda_a, client, db):
    """Camisa en tallas S, M, L, XL × rojo y azul, con stock en dos sucursales de EMP-A."""
    t = tienda_a
    todas = [talla_id(t.alfa, c) for c in ("S", "M", "L", "XL")]
    t.camisa = t.producto("Camisa Oxford", t.camisas["id"], t.col["id"], todas, [t.rojo["id"], t.azul["id"]])
    t.centro, t.norte = datos.sucursal(mundo.a, "Centro"), datos.sucursal(mundo.a, "Norte")
    t.var = por_variante(t.camisa)
    t.h_cliente = cabecera_cliente(datos, mundo.a)
    return t


def _stock(t, mundo, sucursal, talla, color, cantidad):
    t.stock(mundo.a.id, sucursal.id, t.var[(talla, color)]["id"], cantidad)


def test_01_el_cliente_ve_solo_prendas_activas_con_variantes(mundo, surtido, client):
    t = surtido
    oculto = t.producto("Oculta", t.camisas["id"], t.col["id"], [talla_id(t.alfa, "M")], [t.rojo["id"]])
    client.post(f"/api/productos/{oculto['id']}/desactivar", headers=t.h_admin)
    sin_activas = t.producto("Sin variantes activas", t.camisas["id"], t.col["id"], [talla_id(t.alfa, "M")], [t.rojo["id"]])
    client.put(f"/api/productos/{sin_activas['id']}/variantes/{sin_activas['variantes'][0]['id']}", json={"activa": False}, headers=t.h_admin)
    r = client.get("/api/catalogo/productos", headers=t.h_cliente)
    assert r.status_code == 200 and [p["nombre"] for p in r.json()["items"]] == ["Camisa Oxford"] and r.json()["total"] == 1


def test_02_la_tarjeta_resume_tallas_colores_y_precio(mundo, surtido, client):
    t = surtido
    client.put(f"/api/productos/{t.camisa['id']}/variantes/{t.var[('S', 'Azul')]['id']}", json={"precio_especifico": "85"}, headers=t.h_admin)
    item = client.get("/api/catalogo/productos", headers=t.h_cliente).json()["items"][0]
    assert item["tallas"] == ["S", "M", "L", "XL"]  # por display_order, no por orden de creación (L, M, S, XL)
    assert [c["nombre"] for c in item["colores"]] == ["Azul", "Rojo"]
    assert (item["precio"], item["precio_final"], item["promocion"], item["imagen"]) == ("85.00", "85.00", None, None)
    assert item["disponible"] is False  # todavía no hay stock en ninguna sucursal


def test_03_detalle_de_la_prenda_con_imagenes(mundo, surtido, client, tmp_path, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "media_dir", str(tmp_path))
    t = surtido
    client.post(f"/api/productos/{t.camisa['id']}/imagenes", headers=t.h_admin, files={"archivo": ("a.png", PNG, "image/png")}, data={"color_id": t.rojo["id"]})
    r = client.get(f"/api/catalogo/productos/{t.camisa['id']}", headers=t.h_cliente)
    assert r.status_code == 200
    assert r.json()["nombre"] == "Camisa Oxford" and r.json()["imagenes"][0]["color_id"] == t.rojo["id"] and r.json()["imagen"]
    assert client.get("/api/catalogo/productos/999999", headers=t.h_cliente).status_code == 404


def test_04_opciones_matriz_color_talla_con_orden_y_disponibilidad(mundo, surtido, client):
    t = surtido
    _stock(t, mundo, t.centro, "M", "Rojo", 5)
    _stock(t, mundo, t.norte, "M", "Rojo", 2)
    _stock(t, mundo, t.centro, "S", "Azul", 1)
    r = client.get(f"/api/catalogo/productos/{t.camisa['id']}/opciones", headers=t.h_cliente)
    assert r.status_code == 200
    op = r.json()
    assert [x["codigo"] for x in op["tallas"]] == ["S", "M", "L", "XL"]  # siempre por display_order (nunca L, M, S, XL)
    assert [x["orden"] for x in op["variantes"]] == sorted(x["orden"] for x in op["variantes"])
    celda = {(v["talla"], v["color"]): v for v in op["variantes"]}
    assert len(celda) == 8
    assert (celda[("M", "Rojo")]["cantidad"], celda[("M", "Rojo")]["disponible"]) == (7, True)  # suma de todas las sucursales
    assert (celda[("L", "Rojo")]["cantidad"], celda[("L", "Rojo")]["disponible"]) == (0, False)


def test_05_opciones_por_sucursal(mundo, surtido, client):
    t = surtido
    _stock(t, mundo, t.centro, "M", "Rojo", 5)
    _stock(t, mundo, t.norte, "M", "Rojo", 2)
    _stock(t, mundo, t.norte, "XL", "Azul", 4)
    op = client.get(f"/api/catalogo/productos/{t.camisa['id']}/opciones?sucursal={t.norte.id}", headers=t.h_cliente).json()
    celda = {(v["talla"], v["color"]): v for v in op["variantes"]}
    assert op["sucursal_id"] == t.norte.id
    assert celda[("M", "Rojo")]["cantidad"] == 2 and celda[("XL", "Azul")]["disponible"] is True
    azul = next(c for c in op["colores"] if c["nombre"] == "Azul")
    assert azul["disponible"] is True and next(x for x in op["tallas"] if x["codigo"] == "S")["disponible"] is False


def test_06_una_variante_agotada_o_desactivada_no_se_ofrece_como_disponible(mundo, surtido, client):
    t = surtido
    _stock(t, mundo, t.centro, "M", "Rojo", 3)
    _stock(t, mundo, t.centro, "L", "Rojo", 9)
    client.put(f"/api/productos/{t.camisa['id']}/variantes/{t.var[('L', 'Rojo')]['id']}", json={"activa": False}, headers=t.h_admin)
    op = client.get(f"/api/catalogo/productos/{t.camisa['id']}/opciones", headers=t.h_cliente).json()
    celda = {(v["talla"], v["color"]): v for v in op["variantes"]}
    assert ("L", "Rojo") not in celda and len(celda) == 7  # la desactivada no sale aunque tenga stock
    assert celda[("M", "Rojo")]["disponible"] is True
    rojo = next(c for c in op["colores"] if c["nombre"] == "Rojo")
    azul = next(c for c in op["colores"] if c["nombre"] == "Azul")
    assert rojo["disponible"] is True and azul["disponible"] is False  # un color sin stock llega marcado para deshabilitarlo


def test_07_disponibilidad_en_una_sola_consulta_agrupada(datos, mundo, surtido, client, engine):
    t = surtido
    chico = t.producto("Polo", t.camisas["id"], t.col["id"], [talla_id(t.alfa, "S")], [t.rojo["id"]])
    amarillo = t.color("Amarillo")
    grande = t.producto("Polo grande", t.camisas["id"], t.col["id"], [talla_id(t.alfa, c) for c in ("S", "M", "L", "XL")],
                        [t.rojo["id"], t.azul["id"], t.verde["id"], amarillo["id"]])
    consultas = []
    contar = lambda conn, cursor, statement, *a: consultas.append(statement)  # noqa: E731
    event.listen(engine, "before_cursor_execute", contar)
    try:
        for producto in (chico, grande):
            consultas.clear()
            assert client.get(f"/api/catalogo/productos/{producto['id']}/opciones", headers=t.h_cliente).status_code == 200
            if producto is chico:
                con_pocas = len(consultas)
    finally:
        event.remove(engine, "before_cursor_execute", contar)
    assert len(consultas) == con_pocas  # 1 variante o 16: mismo número de consultas (nada de una por variante)
    assert sum("existencias" in c for c in consultas) <= 1


def test_08_sucursal_de_otra_empresa_o_inexistente(mundo, surtido, tienda_b, client, datos):
    t = surtido
    ajena = datos.sucursal(mundo.b, "Ajena")
    for url in (f"/api/catalogo/productos?sucursal={ajena.id}", f"/api/catalogo/productos/{t.camisa['id']}/opciones?sucursal={ajena.id}",
                f"/api/catalogo/productos/{t.camisa['id']}?sucursal=99999"):
        r = client.get(url, headers=t.h_cliente)
        assert r.status_code == 404 and r.json()["detail"] == "Sucursal no encontrada."


def test_09_categoria_con_subcategorias_y_paginacion(mundo, surtido, client):
    t = surtido
    sub = t.categoria("Camisas formales", padre_id=t.camisas["id"])
    for i in range(3):
        t.producto(f"Formal {i}", sub["id"], t.col["id"], [talla_id(t.alfa, "M")], [t.rojo["id"]])
    t.producto("Jean", t.pantalones["id"], t.col["id"], [talla_id(t.numerico, "30")], [t.azul["id"]])
    r = client.get(f"/api/catalogo/productos?categoria_id={t.camisas['id']}", headers=t.h_cliente).json()
    assert r["total"] == 4  # la camisa de la categoría padre + 3 de la subcategoría; el jean no
    pagina = client.get("/api/catalogo/productos?pagina=2&tamano=2", headers=t.h_cliente).json()
    assert (pagina["total"], pagina["pagina"], len(pagina["items"])) == (5, 2, 2)


def test_10_roles_y_sesion(datos, mundo, surtido, client):
    t = surtido
    assert client.get("/api/catalogo/productos").status_code == 401
    assert client.get("/api/catalogo/productos", headers=datos.superadmin()).status_code == 403  # el SuperAdmin no opera datos comerciales
    for rol in ("Encargado", "Cajero"):
        usuario = datos.usuario(mundo.a, rol, email=f"{rol.lower()}@a.com", sucursal=t.centro)
        assert client.get("/api/catalogo/productos", headers=datos.login(usuario, mundo.a)).status_code == 200


def test_11_aislamiento_entre_empresas(datos, mundo, surtido, tienda_b, client):
    t = surtido
    h_b = cabecera_cliente(datos, mundo.b)
    assert client.get("/api/catalogo/productos", headers=h_b).json()["total"] == 0
    assert client.get(f"/api/catalogo/productos/{t.camisa['id']}", headers=h_b).status_code == 404
    assert client.get(f"/api/catalogo/productos/{t.camisa['id']}/opciones", headers=h_b).status_code == 404


def test_12_sucursales_activas_para_elegir_donde_consultar(datos, mundo, surtido, client):
    t = surtido
    datos.sucursal(mundo.a, "Cerrada", activa=False)
    datos.sucursal(mundo.b, "De otra empresa")
    nombres = [s["nombre"] for s in client.get("/api/catalogo/sucursales", headers=t.h_cliente).json()]
    assert nombres == ["Centro", "Norte"]  # solo las activas de su empresa
