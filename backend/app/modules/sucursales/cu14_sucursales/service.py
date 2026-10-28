"""CU-14 · Gestionar ciudades y sucursales (RN01, RN02, RN05, RN06). Capa de negocio."""
from sqlalchemy.orm import Session

from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.modules.plataforma.publico import suscripcion_activa_de
from app.modules.sucursales.cu14_sucursales import schemas
from app.modules.sucursales.cu14_sucursales.repository import CiudadRepository, SucursalRepository
from app.modules.sucursales.models import Ciudad, Sucursal
from app.modules.sucursales.publico import tiene_pendientes


class SucursalService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self.sucursales = SucursalRepository(db, empresa_id)
        self.ciudades = CiudadRepository(db, empresa_id)

    # ---- consulta ----
    def listar(self) -> schemas.SucursalesOut:
        return schemas.SucursalesOut(
            uso_plan=self.uso_plan(), sucursales=[schemas.SucursalOut.desde(s) for s in self.sucursales.listar()]
        )

    def uso_plan(self) -> schemas.UsoPlanOut:
        sus = suscripcion_activa_de(self.db, self.empresa_id)
        activas = self.sucursales.contar_activas()
        limite = sus.plan.max_sucursales if sus else None
        return schemas.UsoPlanOut(
            plan=sus.plan.nombre if sus else None,
            activas=activas,
            limite=limite,
            disponibles=None if limite is None else max(limite - activas, 0),
        )

    # ---- altas y cambios ----
    def crear(self, datos: schemas.SucursalCreate) -> schemas.SucursalOut:
        ciudad = self._resolver_ciudad(datos.ciudad_id, datos.ciudad_nombre)
        if self.sucursales.existe_nombre(datos.nombre.strip()):
            raise Conflicto("Ya existe una sucursal con ese nombre.")
        self._verificar_cupo()  # RN06
        sucursal = self.sucursales.agregar(
            Sucursal(
                ciudad_id=ciudad.id,
                nombre=datos.nombre.strip(),
                direccion=datos.direccion,
                telefono=datos.telefono,
                horario=datos.horario,
                activa=True,
            )
        )
        self.db.commit()
        self.db.refresh(sucursal)
        return schemas.SucursalOut.desde(sucursal)

    def editar(self, sucursal_id: int, datos: schemas.SucursalUpdate) -> schemas.SucursalOut:
        sucursal = self._obtener(sucursal_id)
        cambios = datos.model_dump(exclude_unset=True)
        if cambios.get("nombre") and self.sucursales.existe_nombre(cambios["nombre"].strip(), excluir_id=sucursal.id):
            raise Conflicto("Ya existe una sucursal con ese nombre.")
        if cambios.get("ciudad_id") is not None:
            ciudad = self.ciudades.obtener(cambios["ciudad_id"])
            if ciudad is None:
                raise NoEncontrado("Ciudad no encontrada.")
            sucursal.ciudad_id = ciudad.id
            sucursal.ciudad = ciudad
        for campo in ("nombre", "direccion", "telefono", "horario"):
            if campo in cambios and cambios[campo] is not None:
                setattr(sucursal, campo, cambios[campo].strip() if campo == "nombre" else cambios[campo])
        self.db.commit()
        self.db.refresh(sucursal)
        return schemas.SucursalOut.desde(sucursal)

    def activar(self, sucursal_id: int) -> schemas.SucursalOut:
        sucursal = self._obtener(sucursal_id)
        if not sucursal.activa:
            self._verificar_cupo()  # reactivar también respeta el límite del plan
            sucursal.activa = True
            self.db.commit()
        return schemas.SucursalOut.desde(sucursal)

    def desactivar(self, sucursal_id: int) -> schemas.SucursalOut:
        sucursal = self._obtener(sucursal_id)
        if sucursal.activa:
            if tiene_pendientes(self.db, self.empresa_id, sucursal.id):  # reservas activas u operaciones sin sincronizar (CU-14, excepción 5)
                raise Conflicto("La sucursal tiene reservas pendientes u operaciones sin sincronizar. Resuélvalas antes de desactivarla.")
            sucursal.activa = False
            self.db.commit()
        return schemas.SucursalOut.desde(sucursal)

    # ---- ciudades ----
    def listar_ciudades(self) -> list[Ciudad]:
        return self.ciudades.listar()

    def crear_ciudad(self, datos: schemas.CiudadCreate) -> Ciudad:
        if self.ciudades.por_nombre(datos.nombre.strip()):
            raise Conflicto("Ya existe una ciudad con ese nombre.")
        ciudad = self.ciudades.agregar(Ciudad(nombre=datos.nombre.strip(), departamento=datos.departamento))
        self.db.commit()
        return ciudad

    # ---- auxiliares ----
    def _obtener(self, sucursal_id: int) -> Sucursal:
        sucursal = self.sucursales.obtener(sucursal_id)
        if sucursal is None:
            raise NoEncontrado("Sucursal no encontrada.")  # también si es de otra empresa
        return sucursal

    def _verificar_cupo(self) -> None:
        uso = self.uso_plan()
        if uso.limite is not None and uso.activas >= uso.limite:
            raise Conflicto(f"Su plan permite hasta {uso.limite} sucursales activas. Desactive una sucursal o cambie de plan.")

    def _resolver_ciudad(self, ciudad_id: int | None, ciudad_nombre: str | None) -> Ciudad:
        if ciudad_id is not None:
            ciudad = self.ciudades.obtener(ciudad_id)
            if ciudad is None:
                raise NoEncontrado("Ciudad no encontrada.")
            return ciudad
        nombre = (ciudad_nombre or "").strip()
        if not nombre:
            raise DatosInvalidos("Seleccione o ingrese la ciudad de la sucursal.")
        return self.ciudades.por_nombre(nombre) or self.ciudades.agregar(Ciudad(nombre=nombre))
