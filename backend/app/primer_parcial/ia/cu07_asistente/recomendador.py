"""CU-07 · Recomendador personalizado y armado de outfits.

Compara las prendas con stock contra el perfil de gustos del cliente (compras, búsquedas, prendas que miró y lo que pidió al asistente) y se queda con las mejor puntuadas.
Con IA externa (si hay clave), la IA elige entre las mejores y explica por qué le gustarán; sin ella, el motivo se redacta con reglas. La IA nunca inventa prendas: solo puede
elegir entre las candidatas que el servidor le da.
"""
import json
from decimal import Decimal

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.errors import NoEncontrado
from app.core.ia import ClienteIA, obtener_ia
from app.core.tiempo import ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.catalogo.publico import BusquedaService, FiltrosBusqueda, PrendaOut
from app.primer_parcial.ia.cu07_asistente import schemas
from app.primer_parcial.ia.cu07_asistente.perfil import Perfil, construir_perfil, puntuar
from app.primer_parcial.ia.cu07_asistente.repository import AsistenteRepository, InteraccionRepository

SISTEMA_RECOMENDAR = (
    "Eres el estilista de una tienda de ropa. Recibes el perfil de gustos de un cliente y prendas candidatas con stock. Elige las que más le gustarán (máximo el número pedido) "
    "y explica cada una en una frase corta, en español y dirigida al cliente. Responde SOLO un JSON: {\"seleccion\": [{\"id\": <id de una candidata>, \"motivo\": \"...\"}]}."
)
SISTEMA_OUTFIT = (
    "Eres el estilista de una tienda de ropa. Recibes una prenda base y prendas candidatas con stock. Elige hasta el número pedido de candidatas, de categorías distintas, que armen "
    "un outfit con la prenda base y con los gustos del cliente (colores que combinen). Responde SOLO un JSON: {\"seleccion\": [{\"id\": <id de una candidata>, \"motivo\": \"...\"}]}."
)


class Candidata:
    def __init__(self, prenda: PrendaOut, categoria_id: int | None, puntos: float, razones: dict[str, bool]):
        self.prenda, self.categoria_id, self.puntos, self.razones = prenda, categoria_id, puntos, razones


def elegir_con_ia(ia: ClienteIA, sistema: str, contexto: dict, validas: set[int], limite: int) -> list[tuple[int, str]] | None:
    """La selección que propone la IA, validada (solo ids candidatos, sin repetir, motivo corto). None si no hay IA, falló o no propuso nada válido."""
    crudo = ia.json_estructurado(sistema, f"Número de prendas a elegir: {limite}\n{json.dumps(contexto, ensure_ascii=False)}")
    if crudo is None or not isinstance(crudo.get("seleccion"), list):
        return None
    elegidas: list[tuple[int, str]] = []
    for fila in crudo["seleccion"]:
        try:
            pid, motivo = int(fila["id"]), str(fila.get("motivo", "")).strip()[:200]
        except (KeyError, TypeError, ValueError):
            continue
        if pid in validas and all(pid != e[0] for e in elegidas):
            elegidas.append((pid, motivo))
    return elegidas[:limite] or None


class Recomendador:
    def __init__(self, db: Session, ctx: Contexto, catalogo: BusquedaService, repo: AsistenteRepository):
        self.db, self.ctx, self.empresa_id = db, ctx, ctx.empresa_id
        self.catalogo, self.repo = catalogo, repo
        self.interacciones = InteraccionRepository(db, ctx.empresa_id)
        self.categorias = {n: i for i, n in repo.nombres_de_categorias()}
        self.nombre_categoria = dict(repo.nombres_de_categorias())
        self.nombre_color = dict(repo.nombres_de_colores())

    # ---- perfil ----
    def perfil(self) -> Perfil:
        """El perfil de gustos; vacío si el cliente apagó la personalización."""
        if not self.interacciones.personaliza(self.ctx.usuario.id):
            return Perfil()
        return construir_perfil(self.repo.compras_del_cliente(self.ctx.usuario.id), self.interacciones.del_cliente(self.ctx.usuario.id), ahora())

    # ---- recomendaciones ----
    def recomendar(self, sucursal: int | None, limite: int) -> schemas.RecomendacionesOut:
        perfil = self.perfil()
        pool = self._puntuadas(perfil, sucursal)
        candidatas = [c for c in pool if c.prenda.id not in perfil.comprados] if not perfil.vacio() else []
        seleccion: list[tuple[PrendaOut, str]] = []
        origen = "REGLAS"
        if candidatas:
            top = candidatas[: max(limite * 2, 10)]
            ia = elegir_con_ia(obtener_ia(), SISTEMA_RECOMENDAR, self._contexto(perfil, top), {c.prenda.id for c in top}, limite)
            if ia:
                origen, por_id = "IA", {c.prenda.id: c for c in top}
                seleccion = [(por_id[i].prenda, m or self._motivo_prenda(por_id[i])) for i, m in ia]
            else:
                seleccion = [(c.prenda, self._motivo_prenda(c)) for c in candidatas if c.puntos > 0][:limite]
        personalizada = bool(seleccion)
        if len(seleccion) < limite:  # se completa con lo más vendido
            ranking = self.repo.mas_vendidos()
            ya = {p.id for p, _ in seleccion}
            for c in sorted(pool, key=lambda c: ranking.index(c.prenda.id) if c.prenda.id in ranking else len(ranking)):
                if c.prenda.id not in perfil.comprados and c.prenda.id not in ya and len(seleccion) < limite:
                    seleccion.append((c.prenda, "Es de lo más vendido de la tienda."))
        ofertas = [c.prenda for c in candidatas if c.prenda.promocion and c.puntos > 0][:4]
        return schemas.RecomendacionesOut(
            motivo=self._motivo_general(perfil, [p for p, _ in seleccion]) if personalizada else "Lo más vendido de la tienda.", personalizada=personalizada,
            productos=[p for p, _ in seleccion], motivos={p.id: m for p, m in seleccion}, ofertas=ofertas, origen=origen,
        )

    # ---- outfit ----
    def outfit(self, producto_id: int | None, sucursal: int | None) -> schemas.OutfitOut:
        perfil = self.perfil()
        pool = self._puntuadas(perfil, sucursal)
        if producto_id is not None:
            base = next((c for c in pool if c.prenda.id == producto_id), None)
            if base is None:
                raise NoEncontrado("Prenda no encontrada o sin stock.")  # también si es de otra empresa
            complementos = self._complementos(base, pool)
        else:  # la prenda que mejor encaja con sus gustos y que tenga con qué combinarse
            base, complementos = None, []
            for c in [*(c for c in pool if c.prenda.id not in perfil.comprados), *(c for c in pool if c.prenda.id in perfil.comprados)]:
                complementos = self._complementos(c, pool)
                if complementos:
                    base = c
                    break
            base = base or (pool[0] if pool else None)
        if base is None:
            return schemas.OutfitOut(base=None, prendas=[], motivo="Todavía no hay prendas con stock para armar un outfit.", motivos={}, origen="REGLAS")
        if not complementos:
            return schemas.OutfitOut(base=base.prenda, prendas=[], motivo="No hay prendas de otras categorías con stock para completar el outfit.", motivos={}, origen="REGLAS")
        colores_base = {c.id for c in base.prenda.colores}
        ia = elegir_con_ia(obtener_ia(), SISTEMA_OUTFIT, {**self._contexto(perfil, complementos), "prenda_base": self._resumen(base)}, {c.prenda.id for c in complementos}, 3)
        if ia:
            origen, por_id = "IA", {c.prenda.id: c for c in complementos}
            elegidas = [(por_id[i].prenda, m or "Combina con la prenda base.") for i, m in ia]
        else:
            origen = "REGLAS"
            elegidas = [(c.prenda, "Combina en tono con la prenda base." if colores_base & {x.id for x in c.prenda.colores} else "Completa el outfit con otra categoría.") for c in complementos[:3]]
        return schemas.OutfitOut(
            base=base.prenda, prendas=[p for p, _ in elegidas], motivos={p.id: m for p, m in elegidas},
            motivo=f"Outfit armado alrededor de {base.prenda.nombre}: " + ", ".join(p.nombre for p, _ in elegidas) + ".", origen=origen,
        )

    def _complementos(self, base: Candidata, pool: list[Candidata]) -> list[Candidata]:
        """Lo mejor de cada otra categoría para el mismo público, con preferencia por un tono que combine con la prenda base."""
        colores_base = {c.id for c in base.prenda.colores}

        def encaja(c: Candidata) -> float:
            if c.categoria_id == base.categoria_id or (c.prenda.genero not in (base.prenda.genero, "UNISEX") and base.prenda.genero != "UNISEX"):
                return -1
            return c.puntos + (2 if colores_base & {x.id for x in c.prenda.colores} else 0)

        mejor_por_categoria: dict[int | None, Candidata] = {}
        for c in sorted(pool, key=lambda c: (-encaja(c), c.prenda.nombre)):
            if encaja(c) >= 0 and c.categoria_id not in mejor_por_categoria:
                mejor_por_categoria[c.categoria_id] = c
        return list(mejor_por_categoria.values())[:6]

    # ---- auxiliares ----
    def _puntuadas(self, perfil: Perfil, sucursal: int | None) -> list[Candidata]:
        """Prendas con stock (de la sucursal, si se pide), de la que más encaja con el perfil a la que menos."""
        vistas: dict[int, PrendaOut] = {}
        consultas = [None, *[c for c, _ in sorted(perfil.categorias.items(), key=lambda x: -x[1])[:2]]]
        for categoria_id in consultas:
            for p in self.catalogo.buscar(FiltrosBusqueda(categoria_id=categoria_id, sucursal=sucursal, solo_disponibles=True, tamano=50)).items:
                vistas.setdefault(p.id, p)
        salida = []
        for p in vistas.values():
            categoria_id = self.categorias.get(p.categoria)
            puntos, razones = puntuar(perfil, categoria_id, [c.id for c in p.colores], p.tallas, Decimal(p.precio_final), p.id, bool(p.promocion))
            salida.append(Candidata(p, categoria_id, puntos, razones))
        return sorted(salida, key=lambda c: (-c.puntos, c.prenda.nombre))

    def _motivo_prenda(self, c: Candidata) -> str:
        r, p = c.razones, c.prenda
        partes = []
        if r["categoria"]:
            partes.append(f"es de {p.categoria}, que le interesa")
        if r["color"]:
            partes.append("viene en un color que suele elegir")
        if r["precio"]:
            partes.append("está dentro de lo que suele gastar")
        if r["visto"]:
            partes.append("ya la miró")
        if r["oferta"] and p.promocion:
            partes.append(f"está en oferta ({p.promocion})")
        return "Se la recomendamos porque " + ", ".join(partes) + "." if partes else "Es de lo más vendido de la tienda."

    def _motivo_general(self, perfil: Perfil, elegidas: list[PrendaOut]) -> str:
        """La categoría y el color que más le interesan *entre lo que se le recomienda*."""
        categorias = {self.categorias.get(p.categoria) for p in elegidas}
        colores = {c.id for p in elegidas for c in p.colores}
        categoria = next((k for k, _ in sorted(perfil.categorias.items(), key=lambda x: -x[1]) if k in categorias), None)
        color = next((k for k, _ in sorted(perfil.colores.items(), key=lambda x: -x[1]) if k in colores), None)
        inicio = "Porque compró prendas" if perfil.compras else "Porque ha buscado prendas"
        return inicio + (f" de {self.nombre_categoria.get(categoria)}" if categoria else "") + (f" en color {self.nombre_color.get(color)}" if color else "") + "."

    def _resumen(self, c: Candidata) -> dict:
        p = c.prenda
        return {"id": p.id, "nombre": p.nombre, "categoria": p.categoria, "genero": p.genero, "colores": [x.nombre for x in p.colores], "precio": str(p.precio_final), "oferta": p.promocion}

    def _contexto(self, perfil: Perfil, candidatas: list[Candidata]) -> dict:
        rango = perfil.rango_de_precio()
        top = lambda d, nombres: [nombres.get(k) for k, _ in sorted(d.items(), key=lambda x: -x[1])[:3] if nombres.get(k)]  # noqa: E731
        return jsonable_encoder({
            "perfil": {
                "categorias_favoritas": top(perfil.categorias, self.nombre_categoria), "colores_favoritos": top(perfil.colores, self.nombre_color),
                "tallas": [t for t, _ in sorted(perfil.tallas.items(), key=lambda x: -x[1])[:2]], "rango_de_precio": [rango[0], rango[1]] if rango else None,
                "ultimas_busquedas": perfil.busquedas[:5], "compras": perfil.compras,
            },
            "candidatas": [self._resumen(c) for c in candidatas],
        })
