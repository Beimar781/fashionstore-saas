"""Cierre H · scripts/poblar_via_api.py: si la categoría del destino tiene otro grupo de tallas (EMP-C), el producto se crea con las tallas de ESE grupo (antes: 422 «La talla S no pertenece al grupo de tallas de la categoría»)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
import poblar_via_api as poblar  # noqa: E402


class DestinoFalso:
    def __init__(self, grupo_tallas):
        self.grupo_tallas = grupo_tallas

    def get(self, ruta, **kw):
        if ruta == "/categorias":
            return [{"id": 50, "grupo_talla_id": 9}]
        assert ruta == "/grupos-talla"
        return [{"id": 9, "tallas": self.grupo_tallas}]


def _producto():
    return {"categoria_id": 1, "variantes": [{"talla": "S"}, {"talla": "M"}]}


def _mapas():
    m = poblar.Mapas()
    m.categoria[1] = 50
    return m


def test_01_si_las_tallas_ya_son_del_grupo_de_la_categoria_no_cambian():
    destino = DestinoFalso([{"id": 1, "codigo": "S", "orden": 1}, {"id": 2, "codigo": "M", "orden": 2}])
    assert poblar.tallas_de_la_categoria(destino, _mapas(), _producto(), [1, 2]) == [1, 2]


def test_02_con_otro_grupo_usa_las_tallas_del_mismo_codigo_o_las_tres_primeras():
    mismo_codigo = DestinoFalso([{"id": 11, "codigo": "S", "orden": 1}, {"id": 12, "codigo": "M", "orden": 2}, {"id": 13, "codigo": "L", "orden": 3}])
    assert poblar.tallas_de_la_categoria(mismo_codigo, _mapas(), _producto(), [101, 102]) == [11, 12]
    numerico = DestinoFalso([{"id": 21, "codigo": "38", "orden": 1}, {"id": 22, "codigo": "40", "orden": 2}, {"id": 23, "codigo": "42", "orden": 3}, {"id": 24, "codigo": "44", "orden": 4}])
    assert poblar.tallas_de_la_categoria(numerico, _mapas(), _producto(), [101, 102]) == [21, 22, 23]
