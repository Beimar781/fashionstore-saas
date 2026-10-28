"""Arquitectura (RNF07/RNF12): los paquetes se hablan por `publico.py` y no hay dependencias circulares."""
import ast
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / "app"
ZONAS = ("modules", "primer_parcial")
# Núcleo del lote 1: acceso, plataforma y sucursales se usan entre sí (token, empresa y suscripción).
NUCLEO_LOTE_1 = {"modules.acceso", "modules.plataforma", "modules.sucursales"}
PERMITIDOS = {"publico", "dependencias"}  # módulos que un paquete ajeno puede importar


def _paquete_de(modulo: str) -> str | None:
    m = re.match(r"app\.(modules|primer_parcial)\.([a-z_]+)(?:\.(.*))?$", modulo)
    return f"{m.group(1)}.{m.group(2)}" if m else None


def _importaciones() -> list[tuple[str, str, str]]:
    """(paquete origen, paquete destino, módulo importado) de todo `app/modules` y `app/primer_parcial`."""
    salida = []
    for zona in ZONAS:
        for archivo in (RAIZ / zona).rglob("*.py"):
            rel = archivo.relative_to(RAIZ).with_suffix("").parts
            origen = f"{rel[0]}.{rel[1]}" if len(rel) > 2 else None
            if origen is None:
                continue
            for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
                if isinstance(nodo, ast.ImportFrom) and nodo.module:
                    destino = _paquete_de(nodo.module)
                    if destino and destino != origen:
                        salida.append((origen, destino, nodo.module))
    return salida


def _ciclos(aristas: dict[str, set[str]]) -> list[list[str]]:
    encontrados, pila = [], []

    def visitar(nodo, visitados):
        if nodo in pila:
            encontrados.append(pila[pila.index(nodo):] + [nodo])
            return
        if nodo in visitados:
            return
        visitados.add(nodo)
        pila.append(nodo)
        for vecino in sorted(aristas.get(nodo, ())):
            visitar(vecino, visitados)
        pila.pop()

    visitados: set[str] = set()
    for nodo in sorted(aristas):
        visitar(nodo, visitados)
    return encontrados


def test_paquetes_nuevos_no_forman_ciclos():
    aristas: dict[str, set[str]] = {}
    for origen, destino, _ in _importaciones():
        aristas.setdefault(origen, set()).add(destino)
    # El núcleo se trata como un solo bloque: lo que importa es que nada vuelva hacia un paquete nuevo.
    bloque = {n: ("nucleo" if n in NUCLEO_LOTE_1 else n) for n in set(aristas) | {d for v in aristas.values() for d in v}}
    contraido: dict[str, set[str]] = {}
    for origen, destinos in aristas.items():
        for destino in destinos:
            if bloque[origen] != bloque[destino]:
                contraido.setdefault(bloque[origen], set()).add(bloque[destino])
    assert _ciclos(contraido) == []


def test_paquetes_nuevos_solo_importan_publico_de_otros_paquetes():
    infracciones = [
        f"{origen} importa {modulo}"
        for origen, destino, modulo in _importaciones()
        if origen not in NUCLEO_LOTE_1 and modulo.split(".")[-1] not in PERMITIDOS
    ]
    assert infracciones == []
