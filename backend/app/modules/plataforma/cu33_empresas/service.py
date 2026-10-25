"""CU-33 · Gestionar empresas (tenants) (RN01, RN03, RN04, RN09, RN18). Capa de negocio."""
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, EMPRESA_ACTIVA, EMPRESA_CANCELADA, EMPRESA_SUSPENDIDA
from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.core.security import hash_password
from app.modules.acceso.cu13_usuarios.repository import RolRepository
from app.modules.acceso.models import Usuario
from app.modules.plataforma.cu33_empresas import schemas
from app.modules.plataforma.cu33_empresas.repository import EmpresaRepository
from app.modules.plataforma.cu34_planes.repository import PlanRepository
from app.modules.plataforma.cu35_suscripciones.service import SuscripcionService, resolver_vigencia
from app.modules.plataforma.models import Empresa, Suscripcion


def _salida(empresa: Empresa, sus: Suscripcion | None) -> schemas.EmpresaOut:
    out = schemas.EmpresaOut.model_validate(empresa)
    if sus is not None:
        out.plan = sus.plan.nombre
        out.suscripcion_estado = sus.estado
        out.fecha_vencimiento = sus.fecha_vencimiento
    return out


class EmpresaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmpresaRepository(db)

    def listar(self) -> list[schemas.EmpresaOut]:
        self._sincronizar_vencimientos()
        return [_salida(e, s) for e, s in self.repo.listar_con_suscripcion()]

    def registrar(self, datos: schemas.EmpresaCreate) -> schemas.EmpresaRegistradaOut:
        """Crea empresa + Administrador + suscripción inicial en UNA transacción (CU-33, paso 8):
        si falla cualquiera de los tres registros se revierte todo."""
        if datos.administrador is None:
            raise DatosInvalidos("Debe registrar un administrador para la empresa.")
        if datos.suscripcion is None:
            raise DatosInvalidos("Debe seleccionar el plan inicial de la empresa.")
        codigo = datos.codigo.strip().upper()
        if self.repo.existe_codigo_o_nit(codigo, datos.nit.strip()):
            raise Conflicto("Ya existe una empresa con ese código/NIT.")
        plan = PlanRepository(self.db).obtener(datos.suscripcion.plan_id)
        if plan is None:
            raise NoEncontrado("Plan no encontrado.")
        if not plan.activo:
            raise Conflicto("El plan no está disponible para nuevas contrataciones.")
        vencimiento = resolver_vigencia(
            datos.suscripcion.fecha_inicio, datos.suscripcion.fecha_vencimiento, datos.suscripcion.duracion_meses
        )
        rol_admin = RolRepository(self.db).por_nombre(ADMIN)
        try:
            empresa = self.repo.agregar(
                Empresa(
                    codigo=codigo,
                    razon_social=datos.razon_social.strip(),
                    nit=datos.nit.strip(),
                    email_contacto=datos.email_contacto,
                    telefono=datos.telefono,
                    estado=EMPRESA_ACTIVA,
                )
            )
            admin = Usuario(
                empresa_id=empresa.id,
                rol_id=rol_admin.id,
                nombre=datos.administrador.nombre.strip(),
                apellidos=datos.administrador.apellidos.strip(),
                email=str(datos.administrador.email).lower(),
                password_hash=hash_password(datos.administrador.password),
                activo=True,
            )
            self.db.add(admin)
            self.db.flush()
            SuscripcionService(self.db).crear_registro(
                empresa.id, plan, datos.suscripcion.fecha_inicio, vencimiento, datos.suscripcion.forma_pago
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        sus = SuscripcionService(self.db).repo.ultima(empresa.id)
        base = _salida(empresa, sus)
        return schemas.EmpresaRegistradaOut(**base.model_dump(), administrador_email=admin.email)

    def editar(self, empresa_id: int, datos: schemas.EmpresaUpdate) -> schemas.EmpresaOut:
        empresa = self._obtener(empresa_id)
        cambios = datos.model_dump(exclude_unset=True)
        if cambios.get("nit") and self.repo.existe_nit(cambios["nit"], empresa.id):
            raise Conflicto("Ya existe una empresa con ese código/NIT.")
        for campo, valor in cambios.items():
            if valor is not None:
                setattr(empresa, campo, valor)
        self.db.commit()
        return _salida(empresa, SuscripcionService(self.db).repo.ultima(empresa.id))

    def suspender(self, empresa_id: int) -> schemas.EmpresaOut:
        """Sus usuarios dejan de poder iniciar sesión y se bloquean sus operaciones; los datos se conservan."""
        empresa = self._obtener(empresa_id)
        if empresa.estado != EMPRESA_ACTIVA:
            raise Conflicto("La empresa ya está suspendida o cancelada.")
        empresa.estado = EMPRESA_SUSPENDIDA
        self.db.commit()
        return _salida(empresa, SuscripcionService(self.db).repo.ultima(empresa.id))

    def reactivar(self, empresa_id: int) -> schemas.EmpresaOut:
        empresa = self._obtener(empresa_id)
        if empresa.estado == EMPRESA_CANCELADA:
            raise Conflicto("Una empresa cancelada no puede reactivarse.")
        if empresa.estado == EMPRESA_ACTIVA:
            raise Conflicto("La empresa ya está activa.")
        empresa.estado = EMPRESA_ACTIVA
        self.db.commit()
        return _salida(empresa, SuscripcionService(self.db).repo.ultima(empresa.id))

    def eliminar(self, empresa_id: int) -> None:
        self._obtener(empresa_id)
        raise Conflicto("No se permite eliminar una empresa con datos; use la suspensión o cancelación (baja lógica).")

    # ---- auxiliares ----
    def _obtener(self, empresa_id: int) -> Empresa:
        empresa = self.repo.obtener(empresa_id)
        if empresa is None:
            raise NoEncontrado("Empresa no encontrada.")
        return empresa

    def _sincronizar_vencimientos(self) -> None:
        if SuscripcionService(self.db).repo.marcar_vencidas():
            self.db.commit()
