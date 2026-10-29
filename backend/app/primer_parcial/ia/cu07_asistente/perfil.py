"""CU-07 · Perfil de gustos del cliente y puntuación de prendas. Todo esto es local (sin IA): la IA externa solo elige entre lo mejor puntuado y lo explica.

El perfil suma lo que el cliente compró (peso 3), buscó o le pidió al asistente (peso 2) y miró (peso 1); lo reciente pesa más (la mitad cada 30 días).
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

PESOS = {"COMPRA": 3.0, "BUSQUEDA": 2.0, "ASISTENTE": 2.0, "VISTA": 1.0}
VIDA_MEDIA_DIAS = 30


@dataclass
class Perfil:
    categorias: dict[int, float] = field(default_factory=dict)
    colores: dict[int, float] = field(default_factory=dict)
    tallas: dict[str, float] = field(default_factory=dict)
    precios: list[tuple[Decimal, float]] = field(default_factory=list)  # (precio, peso)
    comprados: set[int] = field(default_factory=set)
    vistos: set[int] = field(default_factory=set)
    busquedas: list[str] = field(default_factory=list)  # lo último que escribió, de lo más nuevo a lo más viejo
    compras: int = 0
    senales: int = 0

    def vacio(self) -> bool:
        return self.senales == 0

    def rango_de_precio(self) -> tuple[Decimal, Decimal] | None:
        """Lo que suele gastar: el precio típico (mediana ponderada) ± 40 %."""
        if not self.precios:
            return None
        ordenados = sorted(self.precios)
        mitad, acumulado = sum(p for _, p in ordenados) / 2, 0.0
        for precio, peso in ordenados:
            acumulado += peso
            if acumulado >= mitad:
                return (precio * Decimal("0.6")).quantize(Decimal("0.01")), (precio * Decimal("1.4")).quantize(Decimal("0.01"))
        return None


def _peso(tipo: str, momento: datetime | None, ahora: datetime, cantidad: int = 1) -> float:
    dias = max((ahora - momento).days, 0) if momento else 0
    return PESOS[tipo] * min(cantidad, 3) * 0.5 ** (dias / VIDA_MEDIA_DIAS)


def construir_perfil(compras: list[tuple], interacciones: list[tuple], ahora: datetime) -> Perfil:
    """compras: (producto_id, categoria_id, color_id, talla, precio, cantidad, fecha).
    interacciones: (tipo, producto_id, categoria_id, color_id, talla, precio_max, texto, fecha)."""
    p = Perfil()
    for producto_id, categoria_id, color_id, talla, precio, cantidad, fecha in compras:
        w = _peso("COMPRA", fecha, ahora, cantidad)
        p.categorias[categoria_id] = p.categorias.get(categoria_id, 0) + w
        p.colores[color_id] = p.colores.get(color_id, 0) + w
        p.tallas[talla] = p.tallas.get(talla, 0) + w
        p.precios.append((Decimal(precio), w))
        p.comprados.add(producto_id)
        p.compras += 1
        p.senales += 1
    for tipo, producto_id, categoria_id, color_id, talla, precio_max, texto, fecha in interacciones:
        w = _peso(tipo, fecha, ahora)
        if categoria_id:
            p.categorias[categoria_id] = p.categorias.get(categoria_id, 0) + w
        if color_id:
            p.colores[color_id] = p.colores.get(color_id, 0) + w
        if talla:
            p.tallas[talla] = p.tallas.get(talla, 0) + w
        if precio_max:
            p.precios.append((Decimal(precio_max) / Decimal("1.2"), w))  # lo que busca «hasta X» suele ser algo menos que X
        if tipo == "VISTA" and producto_id:
            p.vistos.add(producto_id)
        if texto and tipo != "VISTA" and texto not in p.busquedas:
            p.busquedas.append(texto)
        p.senales += 1
    return p


def puntuar(perfil: Perfil, categoria_id: int | None, colores: list[int], tallas: list[str], precio: Decimal, producto_id: int, en_oferta: bool) -> tuple[float, dict[str, bool]]:
    """Qué tanto encaja una prenda con el perfil (0 a ~10) y por qué: categoría que prefiere, color, talla, precio, oferta o algo que ya miró."""
    maximo = lambda d: max(d.values(), default=0) or 1  # noqa: E731
    por_categoria = perfil.categorias.get(categoria_id, 0) / maximo(perfil.categorias)
    por_color = max((perfil.colores.get(c, 0) for c in colores), default=0) / maximo(perfil.colores)
    por_talla = 1.0 if any(perfil.tallas.get(t, 0) >= maximo(perfil.tallas) * 0.5 for t in tallas) else 0.0
    rango = perfil.rango_de_precio()
    por_precio = 1.0 if rango and rango[0] <= precio <= rango[1] else 0.0
    visto = producto_id in perfil.vistos
    puntos = 4 * por_categoria + 3 * por_color + por_talla + por_precio + (1.0 if visto else 0.0) + (0.5 if en_oferta and (por_categoria or por_color) else 0.0)
    return puntos, {"categoria": por_categoria > 0, "color": por_color > 0, "talla": por_talla > 0, "precio": por_precio > 0, "visto": visto, "oferta": en_oferta}
