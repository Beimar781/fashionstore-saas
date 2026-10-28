"""CU-16 · Gestionar categorías, tallas y colores (RN01, RN02). Capa de negocio."""
from sqlalchemy.orm import Session

from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.core.texto import codigo_corto, slugify
from app.primer_parcial.catalogo.cu16_categorias_tallas_colores import schemas
from app.primer_parcial.catalogo.cu16_categorias_tallas_colores.repository import (
    CategoriaRepository, ColorRepository, GrupoTallaRepository, MarcaRepository, TallaRepository,
)
from app.primer_parcial.catalogo.models import Categoria, Color, GrupoTalla, Marca, Talla

MSG_DUPLICADO = "Este atributo ya existe en el sistema."  # excepción de la ficha CU-16
MSG_EN_USO = "No se puede eliminar: el atributo está en uso."


class AtributoService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.categorias = CategoriaRepository(db, empresa_id)
        self.grupos = GrupoTallaRepository(db, empresa_id)
        self.tallas = TallaRepository(db, empresa_id)
        self.colores = ColorRepository(db, empresa_id)
        self.marcas = MarcaRepository(db, empresa_id)

    # ---- categorías ----
    def listar_categorias(self, solo_activas: bool) -> list[Categoria]:
        return self.categorias.ordenadas(solo_activas)

    def crear_categoria(self, datos: schemas.CategoriaIn) -> Categoria:
        nombre = datos.nombre.strip()
        self._verificar_categoria(nombre, datos.padre_id, datos.grupo_talla_id)
        categoria = self.categorias.agregar(Categoria(
            nombre=nombre, slug=slugify(nombre), padre_id=datos.padre_id, grupo_talla_id=datos.grupo_talla_id,
            orden=datos.orden, activa=datos.activa,
        ))
        self.db.commit()
        return categoria

    def editar_categoria(self, categoria_id: int, datos: schemas.CategoriaUpdate) -> Categoria:
        categoria = self._obtener(self.categorias, categoria_id, "Categoría")
        cambios = datos.model_dump(exclude_unset=True)
        nombre = cambios["nombre"].strip() if cambios.get("nombre") else categoria.nombre
        padre_id = cambios["padre_id"] if "padre_id" in cambios else categoria.padre_id
        grupo_id = cambios["grupo_talla_id"] if "grupo_talla_id" in cambios else categoria.grupo_talla_id
        self._verificar_categoria(nombre, padre_id, grupo_id, categoria)
        categoria.nombre, categoria.slug = nombre, slugify(nombre)
        categoria.padre_id, categoria.grupo_talla_id = padre_id, grupo_id
        for campo in ("orden", "activa"):
            if cambios.get(campo) is not None:
                setattr(categoria, campo, cambios[campo])
        self.db.commit()
        return categoria

    def eliminar_categoria(self, categoria_id: int) -> None:
        self._eliminar(self.categorias, categoria_id, "Categoría")

    def _verificar_categoria(self, nombre: str, padre_id: int | None, grupo_id: int | None, actual: Categoria | None = None) -> None:
        if self.categorias.existe(actual.id if actual else None, slug=slugify(nombre)):
            raise Conflicto(MSG_DUPLICADO)
        if padre_id is not None:
            self._obtener(self.categorias, padre_id, "Categoría padre")
            if actual and self._es_descendiente(padre_id, actual.id):
                raise DatosInvalidos("Una categoría no puede ser hija de sí misma ni de sus descendientes.")
        if grupo_id is not None:
            self._obtener(self.grupos, grupo_id, "Grupo de tallas")

    def _es_descendiente(self, categoria_id: int | None, ancestro_id: int) -> bool:
        while categoria_id is not None:
            if categoria_id == ancestro_id:
                return True
            categoria_id = self.categorias.obtener(categoria_id).padre_id
        return False

    # ---- grupos de talla y tallas ----
    def listar_grupos(self) -> list[schemas.GrupoTallaOut]:
        tallas = self.tallas.ordenadas()
        return [
            schemas.GrupoTallaOut(
                id=g.id, nombre=g.nombre, descripcion=g.descripcion,
                tallas=[schemas.TallaOut.model_validate(t) for t in tallas if t.grupo_id == g.id],
            )
            for g in self.grupos.listar()
        ]

    def crear_grupo(self, datos: schemas.GrupoTallaIn) -> schemas.GrupoTallaOut:
        nombre = datos.nombre.strip()
        if self.grupos.existe(nombre=nombre):
            raise Conflicto(MSG_DUPLICADO)
        grupo = self.grupos.agregar(GrupoTalla(nombre=nombre, descripcion=datos.descripcion))
        self.db.commit()
        return schemas.GrupoTallaOut(id=grupo.id, nombre=grupo.nombre, descripcion=grupo.descripcion, tallas=[])

    def eliminar_grupo(self, grupo_id: int) -> None:
        self._eliminar(self.grupos, grupo_id, "Grupo de tallas")

    def crear_talla(self, datos: schemas.TallaIn) -> Talla:
        self._obtener(self.grupos, datos.grupo_id, "Grupo de tallas")
        codigo = datos.codigo.strip().upper()
        if self.tallas.existe_codigo(datos.grupo_id, codigo):
            raise Conflicto(MSG_DUPLICADO)
        orden = datos.orden if datos.orden is not None else self.tallas.siguiente_orden(datos.grupo_id)
        talla = self.tallas.agregar(Talla(grupo_id=datos.grupo_id, codigo=codigo, orden=orden))
        self.db.commit()
        return talla

    def editar_talla(self, talla_id: int, datos: schemas.TallaUpdate) -> Talla:
        talla = self._obtener(self.tallas, talla_id, "Talla")
        if datos.codigo is not None:
            codigo = datos.codigo.strip().upper()
            if self.tallas.existe_codigo(talla.grupo_id, codigo, excluir_id=talla.id):
                raise Conflicto(MSG_DUPLICADO)
            talla.codigo = codigo
        if datos.orden is not None:
            talla.orden = datos.orden
        self.db.commit()
        return talla

    def eliminar_talla(self, talla_id: int) -> None:
        self._eliminar(self.tallas, talla_id, "Talla")

    # ---- colores ----
    def listar_colores(self) -> list[Color]:
        return self.colores.ordenados()

    def crear_color(self, datos: schemas.ColorIn) -> Color:
        nombre = datos.nombre.strip()
        if self.colores.existe(slug=slugify(nombre)):
            raise Conflicto(MSG_DUPLICADO)
        codigo = codigo_corto(nombre, lambda c: self.colores.existe(codigo=c))  # el SKU usa este código, no el slug
        color = self.colores.agregar(Color(nombre=nombre, slug=slugify(nombre), codigo=codigo, codigo_hex=datos.codigo_hex.upper()))
        self.db.commit()
        return color

    def editar_color(self, color_id: int, datos: schemas.ColorUpdate) -> Color:
        color = self._obtener(self.colores, color_id, "Color")
        if datos.nombre is not None:
            nombre = datos.nombre.strip()
            if self.colores.existe(color.id, slug=slugify(nombre)):
                raise Conflicto(MSG_DUPLICADO)
            color.nombre, color.slug = nombre, slugify(nombre)  # el código corto del SKU no cambia
        if datos.codigo_hex is not None:
            color.codigo_hex = datos.codigo_hex.upper()
        self.db.commit()
        return color

    def eliminar_color(self, color_id: int) -> None:
        self._eliminar(self.colores, color_id, "Color")

    # ---- marcas ----
    def listar_marcas(self) -> list[Marca]:
        return self.marcas.ordenadas()

    def crear_marca(self, datos: schemas.MarcaIn) -> Marca:
        nombre = datos.nombre.strip()
        if self.marcas.existe(slug=slugify(nombre)):
            raise Conflicto(MSG_DUPLICADO)
        marca = self.marcas.agregar(Marca(nombre=nombre, slug=slugify(nombre)))
        self.db.commit()
        return marca

    def eliminar_marca(self, marca_id: int) -> None:
        self._eliminar(self.marcas, marca_id, "Marca")

    # ---- auxiliares ----
    def _obtener(self, repo, id_: int, nombre: str):
        entidad = repo.obtener(id_)
        if entidad is None:
            raise NoEncontrado(f"{nombre} no encontrada.")  # también si es de otra empresa
        return entidad

    def _eliminar(self, repo, id_: int, nombre: str) -> None:
        entidad = self._obtener(repo, id_, nombre)
        if repo.en_uso(entidad.id):
            raise Conflicto(MSG_EN_USO)
        self.db.delete(entidad)
        self.db.commit()
