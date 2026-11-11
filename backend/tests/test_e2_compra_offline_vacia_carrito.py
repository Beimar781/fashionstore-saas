"""Segunda ronda E2 · Una compra hecha sin conexión sale del carrito del servidor: si no, al volver la red el cliente la vería otra vez y podría pagarla dos veces."""
import uuid

from tests.compras_util import agregar_ok, stock_listo
from tests.offline_util import ahora_iso, sincronizar_ok


def _compra(inv, cantidad):
    payload = {"sucursal_id": inv.centro.id, "items": [{"variante_id": inv.v_sm_rojo["id"], "cantidad": cantidad}], "tipo_entrega": "RETIRO", "nit_ci": "1234567", "razon_social": "Cliente Prueba"}
    return {"id": str(uuid.uuid4()), "tipo": "COMPRA", "creada_en": ahora_iso(), "payload": payload, "sucursal_id": inv.centro.id}


def test_01_lo_comprado_sin_conexion_sale_del_carrito_y_lo_demas_se_conserva(inv, mundo, client):
    stock_listo(inv, mundo)
    h = inv.h_cliente
    agregar_ok(client, h, inv.v_sm_rojo, inv.centro, 3)
    agregar_ok(client, h, inv.var[("M", "Azul")], inv.centro, 1)
    r = sincronizar_ok(client, h, _compra(inv, 2))[0]
    assert r["estado"] == "CONFIRMADA"
    items = {i["variante_id"]: i["cantidad"] for i in client.get("/api/carrito", headers=h).json()["items"]}
    assert items == {inv.v_sm_rojo["id"]: 1, inv.var[("M", "Azul")]["id"]: 1}  # de 3 camisas quedó 1; la otra prenda no se tocó


def test_02_si_compra_todo_lo_del_carrito_este_queda_vacio_y_sin_carrito_no_falla(inv, mundo, client):
    stock_listo(inv, mundo)
    h = inv.h_cliente
    agregar_ok(client, h, inv.v_sm_rojo, inv.centro, 2)
    sincronizar_ok(client, h, _compra(inv, 2))
    assert client.get("/api/carrito", headers=h).json()["items"] == []
    sincronizar_ok(client, h, _compra(inv, 1))  # sin carrito ni prendas por descontar: la compra se confirma igual


def test_03_el_catalogo_descargado_trae_las_fotos_con_la_misma_ruta_que_el_catalogo_en_linea(inv, mundo, client, tmp_path, monkeypatch):
    """Antes traía la ruta de la base sin «/media/»: en la Caja y en el catálogo sin conexión las fotos salían rotas."""
    from app.core.config import get_settings
    from tests.catalogo_util import PNG
    monkeypatch.setattr(get_settings(), "media_dir", str(tmp_path))
    stock_listo(inv, mundo)
    camisa_id = client.get("/api/offline/catalogo", headers=inv.h_cajero).json()["productos"][0]["id"]
    assert client.post(f"/api/productos/{camisa_id}/imagenes", headers=inv.h_admin, files={"archivo": ("a.png", PNG, "image/png")}).status_code == 201
    producto = next(p for p in client.get("/api/offline/catalogo", headers=inv.h_cajero).json()["productos"] if p["id"] == camisa_id)
    assert producto["imagen"].startswith("/media/") and all(i["url"].startswith("/media/") for i in producto["imagenes"])
    en_linea = client.get(f"/api/catalogo/productos/{camisa_id}", headers=inv.h_cliente).json()
    assert producto["imagen"] == en_linea["imagen"]
