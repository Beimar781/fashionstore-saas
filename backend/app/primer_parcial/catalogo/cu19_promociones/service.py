"""CU-19 · Gestionar promociones y descuentos (RN01, RN02). Capa de negocio."""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.primer_parcial.catalogo.cu16_categorias_tallas_colores.repository import CategoriaRepository
from app.primer_parcial.catalogo.cu17_temporadas_colecciones.repository import ColeccionRepository
from app.primer_parcial.catalogo.cu18_productos.repository import ProductoRepository
from app.primer_parcial.catalogo.cu19_promociones import schemas
from app.primer_parcial.catalogo.cu19_promociones.repository import PromocionRepository
from app.primer_parcial.catalogo.models import Producto, Promocion

CENTAVO = Decimal("0.01")


def aplicar_descuento(promocion: Promocion, precio: Decimal) -> Decimal:
    if promocion.tipo_descuento == "PORCENTAJE":
        return (precio * (100 - promocion.valor) / 100).quantize(CENTAVO, ROUND_HALF_UP)
    return max(precio - promocion.valor, Decimal(0)).quantize(CENTAVO, ROUND_HALF_UP)


class Descuentos:
    """Promociones automáticas vigentes de una empresa: el catálogo (CU-03) y el POS calculan el precio con ellas."""

    def __init__(self, promociones: list[Promocion], padres: dict[int, int | None]):
        self.promociones = promociones
        self.padres = padres

    def _categorias_de(self, categoria_id: int) -> set[int]:
        cadena = set()
        while categoria_id is not None and categoria_id not in cadena:
            cadena.add(categoria_id)
            categoria_id = self.padres.get(categoria_id)
        return cadena

    def _aplica(self, promo: Promocion, producto: Producto) -> bool:
        if not (promo.categorias or promo.colecciones or promo.productos):
            return True
        return (
            producto.id in {p.id for p in promo.productos}
            or producto.coleccion_id in {c.id for c in promo.colecciones}
            or bool(self._categorias_de(producto.categoria_id) & {c.id for c in promo.categorias})
        )

    def precio_final(self, producto: Producto, precio: Decimal) -> tuple[Decimal, Promocion | None]:
        """Precio con la mejor promoción que le aplica (la que deja el precio más bajo)."""
        opciones = [(aplicar_descuento(p, precio), p) for p in self.promociones if self._aplica(p, producto)]
        return min(opciones, key=lambda o: o[0], default=(precio, None))


def descuentos_vigentes(db: Session, empresa_id: int, hoy: date | None = None) -> Descuentos:
    repo = PromocionRepository(db, empresa_id)
    return Descuentos(repo.automaticas_vigentes(hoy or date.today()), repo.padres_de_categorias())


class PromocionService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.promociones = PromocionRepository(db, empresa_id)
        self.categorias = CategoriaRepository(db, empresa_id)
        self.colecciones = ColeccionRepository(db, empresa_id)
        self.productos = ProductoRepository(db, empresa_id)

    def listar(self, solo_vigentes: bool) -> list[schemas.PromocionOut]:
        hoy = date.today()
        return [schemas.PromocionOut.desde(p, hoy) for p in self.promociones.ordenadas(solo_vigentes, hoy)]

    def crear(self, datos: schemas.PromocionIn) -> schemas.PromocionOut:
        codigo = datos.codigo.strip().upper() if datos.codigo else None
        if codigo and self.promociones.existe_codigo(codigo):
            raise Conflicto("Ya existe una promoción con ese código.")
        promocion = self.promociones.agregar(Promocion(
            nombre=datos.nombre.strip(), codigo=codigo, tipo_descuento=datos.tipo_descuento, valor=datos.valor,
            inicia=datos.inicia, termina=datos.termina, monto_minimo=datos.monto_minimo, usos_maximos=datos.usos_maximos,
            activa=datos.activa,
        ))
        self._asignar_alcance(promocion, datos.categorias_ids, datos.colecciones_ids, datos.productos_ids)
        self.db.commit()
        return schemas.PromocionOut.desde(promocion, date.today())

    def editar(self, promocion_id: int, datos: schemas.PromocionUpdate) -> schemas.PromocionOut:
        promocion = self._promocion(promocion_id)
        cambios = datos.model_dump(exclude_unset=True, exclude_none=True)
        tipo = cambios.get("tipo_descuento", promocion.tipo_descuento)
        valor = cambios.get("valor", promocion.valor)
        if cambios.get("termina", promocion.termina) <= cambios.get("inicia", promocion.inicia):
            raise DatosInvalidos(schemas.MSG_FECHAS)
        if tipo == "PORCENTAJE" and valor > 100:
            raise DatosInvalidos(schemas.MSG_PORCENTAJE)
        if "codigo" in cambios:
            cambios["codigo"] = cambios["codigo"].strip().upper()
            if self.promociones.existe_codigo(cambios["codigo"], excluir_id=promocion.id):
                raise Conflicto("Ya existe una promoción con ese código.")
        alcance = {c: cambios.pop(c, None) for c in ("categorias_ids", "colecciones_ids", "productos_ids")}
        for campo, valor_nuevo in cambios.items():
            setattr(promocion, campo, valor_nuevo.strip() if campo == "nombre" else valor_nuevo)
        self._asignar_alcance(
            promocion,
            alcance["categorias_ids"] if alcance["categorias_ids"] is not None else [c.id for c in promocion.categorias],
            alcance["colecciones_ids"] if alcance["colecciones_ids"] is not None else [c.id for c in promocion.colecciones],
            alcance["productos_ids"] if alcance["productos_ids"] is not None else [p.id for p in promocion.productos],
        )
        self.db.commit()
        return schemas.PromocionOut.desde(promocion, date.today())

    def eliminar(self, promocion_id: int) -> None:
        promocion = self._promocion(promocion_id)
        if promocion.usos > 0:
            raise Conflicto("No se puede eliminar: la promoción ya fue usada. Desactívela.")
        self.db.delete(promocion)
        self.db.commit()

    def _promocion(self, promocion_id: int) -> Promocion:
        promocion = self.promociones.obtener(promocion_id)
        if promocion is None:
            raise NoEncontrado("Promoción no encontrada.")  # también si es de otra empresa
        return promocion

    def _asignar_alcance(self, promocion: Promocion, categorias: list[int], colecciones: list[int], productos: list[int]) -> None:
        """Categorías, colecciones y productos afectados; deben pertenecer a la empresa (si no, 404)."""
        promocion.categorias = [self._existente(self.categorias, i, "Categoría") for i in dict.fromkeys(categorias)]
        promocion.colecciones = [self._existente(self.colecciones, i, "Colección") for i in dict.fromkeys(colecciones)]
        promocion.productos = [self._existente(self.productos, i, "Producto") for i in dict.fromkeys(productos)]

    def _existente(self, repo, id_: int, nombre: str):
        entidad = repo.obtener(id_)
        if entidad is None:
            raise NoEncontrado(f"{nombre} no encontrada.")
        return entidad
