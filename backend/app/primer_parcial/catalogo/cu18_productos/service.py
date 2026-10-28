"""CU-18 · Gestionar productos (RN01, RN02). Capa de negocio."""
import uuid

from sqlalchemy.orm import Session

from app.core import almacenamiento
from app.core.config import get_settings
from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.core.texto import slugify
from app.primer_parcial.catalogo.cu16_categorias_tallas_colores.repository import (
    CategoriaRepository, ColorRepository, MarcaRepository, TallaRepository,
)
from app.primer_parcial.catalogo.cu17_temporadas_colecciones.repository import ColeccionRepository
from app.primer_parcial.catalogo.cu18_productos import schemas
from app.primer_parcial.catalogo.cu18_productos.repository import ImagenRepository, ProductoRepository, VarianteRepository
from app.primer_parcial.catalogo.models import Categoria, Color, ImagenProducto, Producto, Talla, Variante

MSG_SIN_VARIANTES = "Debe especificar al menos una talla y un color para el producto."  # excepción de la ficha CU-18
MSG_IMAGEN = "La imagen debe ser JPG, PNG o WEBP de hasta {mb} MB."


class ProductoService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self.productos = ProductoRepository(db, empresa_id)
        self.variantes = VarianteRepository(db, empresa_id)
        self.imagenes = ImagenRepository(db, empresa_id)
        self.categorias = CategoriaRepository(db, empresa_id)
        self.marcas = MarcaRepository(db, empresa_id)
        self.colecciones = ColeccionRepository(db, empresa_id)
        self.tallas = TallaRepository(db, empresa_id)
        self.colores = ColorRepository(db, empresa_id)

    # ---- consulta ----
    def listar(self, q: str | None, categoria_id: int | None, activo: bool | None, pagina: int, tamano: int) -> schemas.ProductosPagina:
        total, productos = self.productos.buscar(q, categoria_id, activo, pagina, tamano)
        items = []
        for p in productos:
            principal = next((i for i in sorted(p.imagenes, key=lambda i: (not i.principal, i.orden)) ), None)
            items.append(schemas.ProductoResumen(
                id=p.id, nombre=p.nombre, categoria=p.categoria.nombre, marca=p.marca.nombre if p.marca else None,
                coleccion=p.coleccion.nombre, precio_base=p.precio_base, activo=p.activo, variantes=len(p.variantes),
                imagen_principal=schemas.url_media(principal.ruta) if principal else None,
            ))
        return schemas.ProductosPagina(total=total, pagina=pagina, tamano=tamano, items=items)

    def obtener(self, producto_id: int) -> schemas.ProductoOut:
        return schemas.ProductoOut.desde(self._producto(producto_id))

    # ---- altas y cambios ----
    def crear(self, datos: schemas.ProductoIn) -> schemas.ProductoOut:
        if not datos.tallas_ids or not datos.colores_ids:
            raise DatosInvalidos(MSG_SIN_VARIANTES)
        categoria = self._buscar(self.categorias, datos.categoria_id, "Categoría")
        coleccion = self._buscar(self.colecciones, datos.coleccion_id, "Colección")
        if datos.marca_id is not None:
            self._buscar(self.marcas, datos.marca_id, "Marca")
        tallas, colores = self._validar_variantes(categoria, datos.tallas_ids, datos.colores_ids)

        nombre = datos.nombre.strip()
        producto = self.productos.agregar(Producto(
            publico_id=uuid.uuid4(), categoria_id=categoria.id, marca_id=datos.marca_id, coleccion_id=coleccion.id,
            nombre=nombre, slug=self.productos.slug_libre(slugify(nombre)), descripcion=datos.descripcion, genero=datos.genero,
            precio_base=datos.precio_base, material=datos.material, cuidado=datos.cuidado, activo=True,
        ))
        self._crear_variantes(producto, tallas, colores)
        self.db.commit()
        return self.obtener(producto.id)

    def editar(self, producto_id: int, datos: schemas.ProductoUpdate) -> schemas.ProductoOut:
        producto = self._producto(producto_id)
        cambios = datos.model_dump(exclude_unset=True)
        if cambios.get("categoria_id") not in (None, producto.categoria_id):
            categoria = self._buscar(self.categorias, cambios["categoria_id"], "Categoría")
            grupo_id = self._grupo_de(categoria)
            if any(v.talla.grupo_id != grupo_id for v in producto.variantes):
                raise Conflicto("La nueva categoría usa otro grupo de tallas que las variantes existentes del producto.")
            producto.categoria_id = categoria.id
        if cambios.get("coleccion_id") is not None:
            producto.coleccion_id = self._buscar(self.colecciones, cambios["coleccion_id"], "Colección").id
        if cambios.get("marca_id") is not None:
            producto.marca_id = self._buscar(self.marcas, cambios["marca_id"], "Marca").id
        elif "marca_id" in cambios:
            producto.marca_id = None
        for campo in ("nombre", "descripcion", "genero", "precio_base", "material", "cuidado"):
            if cambios.get(campo) is not None:
                setattr(producto, campo, cambios[campo].strip() if campo == "nombre" else cambios[campo])
        self.db.commit()
        self.db.expire(producto)
        return self.obtener(producto.id)

    def activar(self, producto_id: int) -> schemas.ProductoOut:
        producto = self._producto(producto_id)
        if not any(v.activa for v in producto.variantes):
            raise DatosInvalidos(MSG_SIN_VARIANTES)  # no se publica un producto sin variantes
        producto.activo = True
        self.db.commit()
        return schemas.ProductoOut.desde(producto)

    def desactivar(self, producto_id: int) -> schemas.ProductoOut:
        producto = self._producto(producto_id)
        producto.activo = False  # retirarlo del catálogo no lo borra: otras pantallas lo referencian
        self.db.commit()
        return schemas.ProductoOut.desde(producto)

    # ---- variantes ----
    def generar_variantes(self, producto_id: int, datos: schemas.VariantesIn) -> schemas.VariantesGeneradasOut:
        if not datos.tallas_ids or not datos.colores_ids:
            raise DatosInvalidos(MSG_SIN_VARIANTES)
        producto = self._producto(producto_id)
        tallas, colores = self._validar_variantes(producto.categoria, datos.tallas_ids, datos.colores_ids)
        creadas = self._crear_variantes(producto, tallas, colores)
        self.db.commit()
        return schemas.VariantesGeneradasOut(
            creadas=len(creadas), omitidas=len(tallas) * len(colores) - len(creadas),
            variantes=[schemas.VarianteOut.desde(v) for v in creadas],
        )

    def editar_variante(self, producto_id: int, variante_id: int, datos: schemas.VarianteUpdate) -> schemas.VarianteOut:
        producto = self._producto(producto_id)
        variante = next((v for v in producto.variantes if v.id == variante_id), None)
        if variante is None:
            raise NoEncontrado("Variante no encontrada.")
        cambios = datos.model_dump(exclude_unset=True)
        if "precio_especifico" in cambios:
            variante.precio_especifico = cambios["precio_especifico"]
        if cambios.get("codigo_barras"):
            if self.variantes.existe_barras(cambios["codigo_barras"], variante.id):
                raise Conflicto("Ese código de barras ya está en uso.")
            variante.codigo_barras = cambios["codigo_barras"]
        elif "codigo_barras" in cambios:
            variante.codigo_barras = None
        if cambios.get("activa") is not None:
            variante.activa = cambios["activa"]
        self.db.commit()
        return schemas.VarianteOut.desde(variante)

    # ---- imágenes ----
    def subir_imagen(self, producto_id: int, contenido: bytes, color_id: int | None, texto_alt: str, principal: bool) -> schemas.ImagenOut:
        producto = self._producto(producto_id)
        maximo_mb = get_settings().media_max_mb
        extension = almacenamiento.tipo_imagen(contenido)
        if extension is None or len(contenido) > maximo_mb * 1024 * 1024:
            raise DatosInvalidos(MSG_IMAGEN.format(mb=maximo_mb))
        if color_id is not None:
            self._buscar(self.colores, color_id, "Color")
        ruta = almacenamiento.guardar_imagen(self.empresa_id, producto.id, contenido, extension)
        es_primera = not producto.imagenes
        imagen = self.imagenes.agregar(ImagenProducto(
            producto_id=producto.id, color_id=color_id, ruta=ruta, texto_alt=texto_alt,
            principal=False, orden=self.imagenes.siguiente_orden(producto.id),
        ))
        if principal or es_primera:
            self.db.refresh(producto, ["imagenes"])
            self._marcar_principal(producto, imagen)
        self.db.commit()
        return schemas.ImagenOut.desde(imagen)

    def marcar_principal(self, producto_id: int, imagen_id: int) -> schemas.ProductoOut:
        producto = self._producto(producto_id)
        self._marcar_principal(producto, self._imagen(producto, imagen_id))
        self.db.commit()
        return schemas.ProductoOut.desde(producto)

    def eliminar_imagen(self, producto_id: int, imagen_id: int) -> None:
        producto = self._producto(producto_id)
        imagen = self._imagen(producto, imagen_id)
        era_principal, ruta = imagen.principal, imagen.ruta
        producto.imagenes.remove(imagen)
        self.db.flush()
        if era_principal and producto.imagenes:
            producto.imagenes[0].principal = True
        self.db.commit()
        almacenamiento.borrar_imagen(ruta)

    # ---- auxiliares ----
    def _producto(self, producto_id: int) -> Producto:
        producto = self.productos.obtener_completo(producto_id)
        if producto is None:
            raise NoEncontrado("Producto no encontrado.")  # también si es de otra empresa
        return producto

    def _buscar(self, repo, id_: int, nombre: str):
        entidad = repo.obtener(id_)
        if entidad is None:
            raise NoEncontrado(f"{nombre} no encontrada.")
        return entidad

    def _imagen(self, producto: Producto, imagen_id: int) -> ImagenProducto:
        imagen = next((i for i in producto.imagenes if i.id == imagen_id), None)
        if imagen is None:
            raise NoEncontrado("Imagen no encontrada.")
        return imagen

    def _marcar_principal(self, producto: Producto, imagen: ImagenProducto) -> None:
        for otra in producto.imagenes:
            otra.principal = otra.id == imagen.id

    def _grupo_de(self, categoria: Categoria) -> int | None:
        """Grupo de tallas de la categoría; si no tiene, el de su categoría padre."""
        while categoria is not None:
            if categoria.grupo_talla_id is not None:
                return categoria.grupo_talla_id
            categoria = self.categorias.obtener(categoria.padre_id) if categoria.padre_id else None
        return None

    def _validar_variantes(self, categoria: Categoria, tallas_ids: list[int], colores_ids: list[int]) -> tuple[list[Talla], list[Color]]:
        grupo_id = self._grupo_de(categoria)
        if grupo_id is None:
            raise DatosInvalidos("La categoría no tiene grupo de tallas. Asígnele uno antes de crear variantes.")
        tallas = [self._buscar(self.tallas, i, "Talla") for i in dict.fromkeys(tallas_ids)]
        for talla in tallas:
            if talla.grupo_id != grupo_id:  # no se mezclan S/M con 28/30
                raise DatosInvalidos(f"La talla {talla.codigo} no pertenece al grupo de tallas de la categoría.")
        colores = [self._buscar(self.colores, i, "Color") for i in dict.fromkeys(colores_ids)]
        return tallas, colores

    def _crear_variantes(self, producto: Producto, tallas: list[Talla], colores: list[Color]) -> list[Variante]:
        existentes = {(v.talla_id, v.color_id) for v in producto.variantes}
        creadas = []
        for talla in tallas:
            for color in colores:
                if (talla.id, color.id) in existentes:
                    continue
                sku = f"P{producto.id}-{talla.codigo}-{color.codigo}".upper()  # corto: no depende de nombres editables
                if self.variantes.existe_sku(sku):
                    raise Conflicto(f"El SKU {sku} ya existe en su empresa.")
                creadas.append(self.variantes.agregar(Variante(producto_id=producto.id, talla_id=talla.id, color_id=color.id, sku=sku)))
        self.db.refresh(producto, ["variantes"])
        return creadas
