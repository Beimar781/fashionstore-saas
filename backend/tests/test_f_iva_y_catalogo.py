"""Tercera ronda F · El IVA incluido se calcula sin conexión con la misma fórmula que el servidor: la tabla de abajo es la MISMA que usan las pruebas de la web (iva.spec.ts) y del móvil (iva_test.dart)."""
from decimal import Decimal

from app.core.tipos import iva_incluido

TABLA = [("0.00", "0.00"), ("0.50", "0.06"), ("1.00", "0.12"), ("9.99", "1.15"), ("100.00", "11.50"), ("235.00", "27.04"), ("300.00", "34.51"), ("1250.50", "143.86"), ("8.69", "1.00"), ("4.35", "0.50")]


def test_01_la_tabla_de_referencia_coincide_con_el_servidor():
    for total, esperado in TABLA:
        assert str(iva_incluido(Decimal(total))) == esperado, total


def test_02_el_catalogo_descargado_trae_la_tasa_de_iva_para_calcularla_sin_conexion(inv, client):
    r = client.get("/api/offline/catalogo", headers=inv.h_cajero)
    assert r.status_code == 200 and r.json()["iva_porcentaje"] == 13
