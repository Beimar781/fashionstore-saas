"""CU-31 Gestionar información de productos y abastecimiento — caja negra (pasos de la ficha) + roles y aislamiento."""
from tests.catalogo_util import crear_proveedor, entrar

SKU_INEXISTENTE = "El código SKU ingresado no corresponde a ningún producto habilitado; solicite su creación primero."


def _aviso(inv, items, **extra):
    return {"sucursal_id": inv.centro.id, "referencia": "REM-001", "items": items, **extra}


def _item(variante, cantidad=10, **extra):
    return {"sku": variante["sku"], "cantidad": cantidad, **extra}


def test_01_acceder_al_submodulo_de_abastecimiento(inv, client):
    assert client.get("/api/abastecimiento/lotes", headers=inv.h_prov).json() == []
    mio = client.get("/api/abastecimiento/mi-proveedor", headers=inv.h_prov).json()
    assert mio["id"] == inv.proveedor["id"]


def test_02_asociar_el_aviso_a_productos_existentes(inv, client):
    r = client.post("/api/abastecimiento/lotes", json=_aviso(inv, [_item(inv.v_sm_rojo)]), headers=inv.h_prov)
    assert r.status_code == 201
    assert (r.json()["items"][0]["producto"], r.json()["items"][0]["sku"]) == ("Camisa Oxford", inv.v_sm_rojo["sku"])


def test_02b_seleccionar_el_producto_registrado_y_la_sucursal_de_destino(inv, datos, mundo, client):
    datos.sucursal(mundo.a, "Cerrada", activa=False)
    r = client.get("/api/abastecimiento/variantes?q=oxford", headers=inv.h_prov).json()
    assert len(r) == 4 and {"sku", "producto", "talla", "color"} == set(r[0])
    assert [v["sku"] for v in client.get(f"/api/abastecimiento/variantes?q={inv.v_sm_rojo['sku']}", headers=inv.h_prov).json()] == [inv.v_sm_rojo["sku"]]
    assert client.get("/api/abastecimiento/variantes?q=zapatilla", headers=inv.h_prov).json() == []
    assert [s["nombre"] for s in client.get("/api/abastecimiento/sucursales", headers=inv.h_prov).json()] == ["Centro", "Norte"]
    assert client.get("/api/abastecimiento/variantes", headers=inv.h_cliente).status_code == 403
    assert [c["nombre"] for c in client.get("/api/colecciones", headers=inv.h_prov).json()] == ["Colección Urbana"]  # el proveedor elige colección al proponer


def test_03_definir_cantidades_por_talla_y_color(inv, client):
    items = [_item(inv.var[("S", "Rojo")], 10), _item(inv.var[("M", "Azul")], 25, costo_unitario="45.50")]
    r = client.post("/api/abastecimiento/lotes", json=_aviso(inv, items), headers=inv.h_prov).json()
    detalle = {(i["talla"], i["color"]): (i["cantidad"], i["costo_unitario"]) for i in r["items"]}
    assert detalle == {("S", "Rojo"): (10, None), ("M", "Azul"): (25, "45.50")} and r["total_unidades"] == 35
    # el mismo SKU repetido se suma en una sola línea
    r = client.post("/api/abastecimiento/lotes", json=_aviso(inv, [_item(inv.v_sm_rojo, 4), _item(inv.v_sm_rojo, 6)]), headers=inv.h_prov).json()
    assert [(i["sku"], i["cantidad"]) for i in r["items"]] == [(inv.v_sm_rojo["sku"], 10)]


def test_04_confirmar_y_enviar_deja_el_lote_en_transito_y_avisa_a_la_administracion(inv, client):
    assert client.get("/api/abastecimiento/resumen", headers=inv.h_admin).json() == {"lotes_en_transito": 0, "propuestas_pendientes": 0}
    r = client.post("/api/abastecimiento/lotes", json=_aviso(inv, [_item(inv.v_sm_rojo)]), headers=inv.h_prov).json()
    assert r["estado"] == "EN_TRANSITO" and r["codigo"] == f"LOT-{r['id']:06d}" and r["sucursal"] == "Centro"
    assert client.get("/api/abastecimiento/resumen", headers=inv.h_admin).json()["lotes_en_transito"] == 1  # aviso para la administración
    assert [x["id"] for x in client.get("/api/abastecimiento/lotes?estado=EN_TRANSITO", headers=inv.h_admin).json()] == [r["id"]]


def test_05_sku_inexistente(inv, client):
    r = client.post("/api/abastecimiento/lotes", json=_aviso(inv, [{"sku": "NO-EXISTE", "cantidad": 3}]), headers=inv.h_prov)
    assert r.status_code == 422 and r.json()["detail"] == SKU_INEXISTENTE
    assert client.get("/api/abastecimiento/lotes", headers=inv.h_prov).json() == []  # no quedó nada a medias


def test_sku_de_producto_retirado_o_variante_inactiva_no_esta_habilitado(inv, client):
    client.put(f"/api/productos/{inv.camisa['id']}/variantes/{inv.var[('M', 'Azul')]['id']}", json={"activa": False}, headers=inv.h_admin)
    r = client.post("/api/abastecimiento/lotes", json=_aviso(inv, [_item(inv.var[("M", "Azul")])]), headers=inv.h_prov)
    assert r.status_code == 422 and r.json()["detail"] == SKU_INEXISTENTE
    client.post(f"/api/productos/{inv.camisa['id']}/desactivar", headers=inv.h_admin)
    r = client.post("/api/abastecimiento/lotes", json=_aviso(inv, [_item(inv.v_sm_rojo)]), headers=inv.h_prov)
    assert r.status_code == 422 and r.json()["detail"] == SKU_INEXISTENTE


def test_validaciones_del_aviso(datos, mundo, inv, client):
    r = client.post("/api/abastecimiento/lotes", json=_aviso(inv, []), headers=inv.h_prov)
    assert r.status_code == 422 and r.json()["detail"] == "Debe indicar al menos un producto en el aviso de remisión."
    ajena = datos.sucursal(mundo.b, "Ajena")
    r = client.post("/api/abastecimiento/lotes", json=_aviso(inv, [_item(inv.v_sm_rojo)], sucursal_id=ajena.id), headers=inv.h_prov)
    assert r.status_code == 404 and r.json()["detail"] == "Sucursal no encontrada."
    assert client.post("/api/abastecimiento/lotes", json=_aviso(inv, [_item(inv.v_sm_rojo, 0)]), headers=inv.h_prov).status_code == 422


def test_el_administrador_puede_enviar_en_nombre_del_proveedor(inv, client):
    cuerpo = _aviso(inv, [_item(inv.v_sm_rojo)])
    assert client.post("/api/abastecimiento/lotes", json=cuerpo, headers=inv.h_admin).status_code == 404  # debe indicar el proveedor
    r = client.post("/api/abastecimiento/lotes", json={**cuerpo, "proveedor_id": inv.proveedor["id"]}, headers=inv.h_admin)
    assert r.status_code == 201 and r.json()["proveedor"] == "Textiles Sur"


def test_cada_proveedor_ve_solo_lo_suyo(datos, mundo, inv, client):
    otro = crear_proveedor(client, inv.h_admin, "Hilos Norte")
    h_otro = entrar(client, mundo.a, "hilos@proveedor.com")
    lote = client.post("/api/abastecimiento/lotes", json=_aviso(inv, [_item(inv.v_sm_rojo)]), headers=inv.h_prov).json()
    assert client.get("/api/abastecimiento/lotes", headers=h_otro).json() == []
    assert client.get(f"/api/abastecimiento/lotes/{lote['id']}", headers=h_otro).status_code == 404
    assert client.post(f"/api/abastecimiento/lotes/{lote['id']}/cancelar", headers=h_otro).status_code == 404
    assert len(client.get("/api/abastecimiento/lotes", headers=inv.h_admin).json()) == 1
    assert client.get(f"/api/abastecimiento/lotes?proveedor_id={otro['id']}", headers=inv.h_admin).json() == []


def test_cancelar_un_lote_en_transito(inv, client):
    lote = client.post("/api/abastecimiento/lotes", json=_aviso(inv, [_item(inv.v_sm_rojo)]), headers=inv.h_prov).json()
    r = client.post(f"/api/abastecimiento/lotes/{lote['id']}/cancelar", headers=inv.h_prov)
    assert r.status_code == 200 and r.json()["estado"] == "CANCELADO"
    assert client.post(f"/api/abastecimiento/lotes/{lote['id']}/cancelar", headers=inv.h_prov).status_code == 409
    assert client.get("/api/abastecimiento/resumen", headers=inv.h_admin).json()["lotes_en_transito"] == 0


def test_propuestas_el_proveedor_propone_y_el_administrador_revisa(inv, client):
    cuerpo = {"nombre": "Chaqueta Impermeable", "coleccion_id": inv.col["id"], "genero": "UNISEX", "precio_base": "260", "material": "Poliéster"}
    p = client.post("/api/abastecimiento/propuestas", json=cuerpo, headers=inv.h_prov)
    assert p.status_code == 201 and (p.json()["estado"], p.json()["coleccion"]) == ("PENDIENTE", "Colección Urbana")
    assert client.get("/api/abastecimiento/resumen", headers=inv.h_admin).json()["propuestas_pendientes"] == 1
    # el Administrador no propone; el proveedor no revisa
    assert client.post("/api/abastecimiento/propuestas", json=cuerpo, headers=inv.h_admin).status_code == 403
    assert client.post(f"/api/abastecimiento/propuestas/{p.json()['id']}/aprobar", json={}, headers=inv.h_prov).status_code == 403
    r = client.post(f"/api/abastecimiento/propuestas/{p.json()['id']}/rechazar", json={"notas": "  "}, headers=inv.h_admin)
    assert r.status_code == 422 and r.json()["detail"] == "Indique el motivo del rechazo."
    r = client.post(f"/api/abastecimiento/propuestas/{p.json()['id']}/aprobar", json={"notas": "Adelante"}, headers=inv.h_admin)
    assert (r.json()["estado"], r.json()["notas_revision"]) == ("APROBADA", "Adelante")
    r = client.post(f"/api/abastecimiento/propuestas/{p.json()['id']}/rechazar", json={"notas": "tarde"}, headers=inv.h_admin)
    assert r.status_code == 409 and r.json()["detail"] == "La propuesta ya fue revisada."
    assert client.get("/api/abastecimiento/propuestas?estado=PENDIENTE", headers=inv.h_admin).json() == []


def test_propuestas_cada_proveedor_ve_las_suyas(datos, mundo, inv, client):
    crear_proveedor(client, inv.h_admin, "Hilos Norte")
    h_otro = entrar(client, mundo.a, "hilos@proveedor.com")
    cuerpo = {"nombre": "Gorra", "coleccion_id": inv.col["id"], "genero": "UNISEX", "precio_base": "40"}
    client.post("/api/abastecimiento/propuestas", json=cuerpo, headers=inv.h_prov)
    assert client.get("/api/abastecimiento/propuestas", headers=h_otro).json() == []
    assert len(client.get("/api/abastecimiento/propuestas", headers=inv.h_prov).json()) == 1
    assert client.post("/api/abastecimiento/propuestas", json={**cuerpo, "coleccion_id": 9999}, headers=inv.h_prov).status_code == 404


def test_roles_y_aislamiento(datos, mundo, inv, tienda_b, client):
    lote = client.post("/api/abastecimiento/lotes", json=_aviso(inv, [_item(inv.v_sm_rojo)]), headers=inv.h_prov).json()
    for cabecera in (inv.h_cliente, inv.h_cajero, inv.h_enc_centro):
        assert client.get("/api/abastecimiento/lotes", headers=cabecera).status_code == 403
    assert client.get("/api/abastecimiento/lotes", headers=tienda_b.h_admin).json() == []
    assert client.get(f"/api/abastecimiento/lotes/{lote['id']}", headers=tienda_b.h_admin).status_code == 404
    assert client.post(f"/api/abastecimiento/lotes/{lote['id']}/cancelar", headers=tienda_b.h_admin).status_code == 404
    # con un SKU de otra empresa no se puede armar un aviso
    pb = crear_proveedor(client, tienda_b.h_admin, "Proveedor B")
    h_pb = entrar(client, mundo.b, "proveedor@proveedor.com")
    suc_b = datos.sucursal(mundo.b, "Central B")
    r = client.post("/api/abastecimiento/lotes", json={"sucursal_id": suc_b.id, "items": [_item(inv.v_sm_rojo)]}, headers=h_pb)
    assert r.status_code == 422 and r.json()["detail"] == SKU_INEXISTENTE
    assert pb["id"]
