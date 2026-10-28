"""CU-17 · Gestionar temporadas y colecciones (RN01, RN02). Capa de negocio."""
from sqlalchemy.orm import Session

from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.core.texto import slugify
from app.primer_parcial.catalogo.cu17_temporadas_colecciones import schemas
from app.primer_parcial.catalogo.cu17_temporadas_colecciones.repository import ColeccionRepository, TemporadaRepository
from app.primer_parcial.catalogo.models import Coleccion, Temporada


class TemporadaService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.temporadas = TemporadaRepository(db, empresa_id)
        self.colecciones = ColeccionRepository(db, empresa_id)

    # ---- temporadas ----
    def listar_temporadas(self, solo_activas: bool) -> list[Temporada]:
        return self.temporadas.ordenadas(solo_activas)

    def crear_temporada(self, datos: schemas.TemporadaIn) -> Temporada:
        codigo = datos.codigo.strip().upper()
        if self.temporadas.existe_codigo(codigo):
            raise Conflicto("Ya existe una temporada con ese código.")
        temporada = self.temporadas.agregar(Temporada(
            nombre=datos.nombre.strip(), codigo=codigo, tipo=datos.tipo, inicio=datos.inicio, fin=datos.fin, activa=datos.activa,
        ))
        self.db.commit()
        return temporada

    def editar_temporada(self, temporada_id: int, datos: schemas.TemporadaUpdate) -> Temporada:
        temporada = self._temporada(temporada_id)
        cambios = datos.model_dump(exclude_unset=True, exclude_none=True)
        inicio, fin = cambios.get("inicio", temporada.inicio), cambios.get("fin", temporada.fin)
        if fin <= inicio:
            raise DatosInvalidos(schemas.MSG_FECHAS)
        if "codigo" in cambios:
            cambios["codigo"] = cambios["codigo"].strip().upper()
            if self.temporadas.existe_codigo(cambios["codigo"], excluir_id=temporada.id):
                raise Conflicto("Ya existe una temporada con ese código.")
        for campo, valor in cambios.items():
            setattr(temporada, campo, valor.strip() if campo == "nombre" else valor)
        self.db.commit()
        return temporada

    def eliminar_temporada(self, temporada_id: int) -> None:
        temporada = self._temporada(temporada_id)
        if self.temporadas.en_uso(temporada.id):
            raise Conflicto("No se puede eliminar: la temporada tiene colecciones asociadas.")
        self.db.delete(temporada)
        self.db.commit()

    # ---- colecciones ----
    def listar_colecciones(self, solo_activas: bool, temporada_id: int | None) -> list[schemas.ColeccionOut]:
        return [schemas.ColeccionOut.desde(c) for c in self.colecciones.ordenadas(solo_activas, temporada_id)]

    def crear_coleccion(self, datos: schemas.ColeccionIn) -> schemas.ColeccionOut:
        self._temporada(datos.temporada_id)
        nombre = datos.nombre.strip()
        self._verificar_nombre(nombre)
        coleccion = self.colecciones.agregar(Coleccion(
            nombre=nombre, slug=slugify(nombre), temporada_id=datos.temporada_id,
            fecha_lanzamiento=datos.fecha_lanzamiento, activa=datos.activa,
        ))
        self.db.commit()
        self.db.refresh(coleccion)
        return schemas.ColeccionOut.desde(coleccion)

    def editar_coleccion(self, coleccion_id: int, datos: schemas.ColeccionUpdate) -> schemas.ColeccionOut:
        coleccion = self._coleccion(coleccion_id)
        cambios = datos.model_dump(exclude_unset=True)
        if cambios.get("temporada_id") is not None:
            coleccion.temporada = self._temporada(cambios["temporada_id"])
            coleccion.temporada_id = coleccion.temporada.id
        if cambios.get("nombre"):
            nombre = cambios["nombre"].strip()
            self._verificar_nombre(nombre, coleccion.id)
            coleccion.nombre, coleccion.slug = nombre, slugify(nombre)
        if "fecha_lanzamiento" in cambios:
            coleccion.fecha_lanzamiento = cambios["fecha_lanzamiento"]
        if cambios.get("activa") is not None:
            coleccion.activa = cambios["activa"]
        self.db.commit()
        return schemas.ColeccionOut.desde(coleccion)

    def eliminar_coleccion(self, coleccion_id: int) -> None:
        coleccion = self._coleccion(coleccion_id)
        if self.colecciones.en_uso(coleccion.id):
            raise Conflicto("No se puede eliminar: la colección tiene productos asociados.")
        self.db.delete(coleccion)
        self.db.commit()

    # ---- auxiliares ----
    def _temporada(self, temporada_id: int) -> Temporada:
        temporada = self.temporadas.obtener(temporada_id)
        if temporada is None:
            raise NoEncontrado("Temporada no encontrada.")  # también si es de otra empresa
        return temporada

    def _coleccion(self, coleccion_id: int) -> Coleccion:
        coleccion = self.colecciones.obtener(coleccion_id)
        if coleccion is None:
            raise NoEncontrado("Colección no encontrada.")
        return coleccion

    def _verificar_nombre(self, nombre: str, excluir_id: int | None = None) -> None:
        if self.colecciones.existe_slug(slugify(nombre), excluir_id):
            raise Conflicto("Ya existe una colección con ese nombre.")
