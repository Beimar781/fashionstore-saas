"""CU-15 · Gestionar proveedores (RN01, RN02). Capa de negocio."""
from sqlalchemy.orm import Session

from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.modules.acceso.publico import crear_usuario_proveedor
from app.primer_parcial.catalogo.publico import asignar_proveedor_a_coleccion
from app.primer_parcial.proveedores.cu15_proveedores import schemas
from app.primer_parcial.proveedores.cu15_proveedores.repository import ProveedorRepository
from app.primer_parcial.proveedores.models import Proveedor


class ProveedorService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.proveedores = ProveedorRepository(db, empresa_id)
        self.empresa_id = empresa_id

    def listar(self, solo_activos: bool, q: str | None) -> list[schemas.ProveedorOut]:
        return [schemas.ProveedorOut.desde(p) for p in self.proveedores.ordenados(solo_activos, q)]

    def obtener(self, proveedor_id: int) -> schemas.ProveedorOut:
        return schemas.ProveedorOut.desde(self._proveedor(proveedor_id))

    def crear(self, datos: schemas.ProveedorIn) -> schemas.ProveedorOut:
        if datos.nit and self.proveedores.existe_nit(datos.nit):
            raise Conflicto("Ya existe un proveedor con ese NIT.")
        proveedor = self.proveedores.agregar(Proveedor(
            razon_social=datos.razon_social.strip(), nombre_comercial=datos.nombre_comercial.strip(), nit=datos.nit,
            email=str(datos.email).lower() if datos.email else None, telefono=datos.telefono, direccion=datos.direccion,
        ))
        self.db.commit()
        return schemas.ProveedorOut.desde(proveedor)

    def editar(self, proveedor_id: int, datos: schemas.ProveedorUpdate) -> schemas.ProveedorOut:
        proveedor = self._proveedor(proveedor_id)
        cambios = datos.model_dump(exclude_unset=True)
        nuevo = {c: cambios.get(c, getattr(proveedor, c)) for c in ("razon_social", "email", "telefono")}
        if not nuevo["razon_social"] or not (nuevo["email"] or nuevo["telefono"]):
            raise DatosInvalidos(schemas.MSG_DATOS)  # la ficha: nombre de la empresa e información de contacto
        if cambios.get("nit") and self.proveedores.existe_nit(cambios["nit"], excluir_id=proveedor.id):
            raise Conflicto("Ya existe un proveedor con ese NIT.")
        for campo, valor in cambios.items():
            if campo == "email" and valor:
                valor = str(valor).lower()
            if valor is None and campo in ("nombre_comercial", "direccion"):
                valor = ""
            setattr(proveedor, campo, valor)
        self.db.commit()
        return schemas.ProveedorOut.desde(proveedor)

    def cambiar_estado(self, proveedor_id: int, activo: bool) -> schemas.ProveedorOut:
        proveedor = self._proveedor(proveedor_id)
        if not activo and self.proveedores.tiene_lotes_en_transito(proveedor.id):
            raise Conflicto("El proveedor tiene lotes en tránsito. Reciba o cancele esos lotes antes de desactivarlo.")
        proveedor.activo = activo
        self.db.commit()
        return schemas.ProveedorOut.desde(proveedor)

    def crear_acceso(self, proveedor_id: int, datos: schemas.AccesoIn) -> schemas.ProveedorOut:
        """Cuenta del portal de proveedores: con ella el proveedor envía avisos de remisión y propuestas (CU-31)."""
        proveedor = self._proveedor(proveedor_id)
        if proveedor.usuario_id is not None:
            raise Conflicto("El proveedor ya tiene una cuenta de acceso.")
        proveedor.usuario_id = crear_usuario_proveedor(
            self.db, self.empresa_id, datos.nombre or proveedor.nombre_comercial or proveedor.razon_social, str(datos.email), datos.password
        )
        self.db.commit()
        return schemas.ProveedorOut.desde(proveedor)

    def vincular_coleccion(self, coleccion_id: int, proveedor_id: int | None):
        if proveedor_id is not None:
            self._proveedor(proveedor_id)
        return asignar_proveedor_a_coleccion(self.db, self.empresa_id, coleccion_id, proveedor_id)

    def _proveedor(self, proveedor_id: int) -> Proveedor:
        proveedor = self.proveedores.obtener(proveedor_id)
        if proveedor is None:
            raise NoEncontrado("Proveedor no encontrado.")  # también si es de otra empresa
        return proveedor
