"""CU-13 · Gestionar usuarios y roles (RN02, RN03, RN09, RN10). Capa de negocio."""
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, MSG_RECURSO_AJENO, ROLES_CON_SUCURSAL, ROLES_INTERNOS
from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado, Prohibido
from app.core.security import hash_password
from app.modules.acceso.cu13_usuarios import schemas
from app.modules.acceso.cu13_usuarios.repository import RolRepository, UsuarioRepository
from app.modules.acceso.models import Usuario
from app.modules.sucursales.cu14_sucursales.repository import SucursalRepository

MSG_ROL = "No tiene permisos para asignar este rol."


class UsuarioService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self.repo = UsuarioRepository(db, empresa_id)
        self.sucursales = SucursalRepository(db, empresa_id)
        self.roles = RolRepository(db)

    def listar(self) -> list[schemas.UsuarioOut]:
        return [schemas.UsuarioOut.desde(u) for u in self.repo.listar_internos()]

    def registrar(self, datos: schemas.UsuarioCreate) -> schemas.UsuarioOut:
        rol = self._rol_permitido(datos.rol)
        self._validar_sucursal(rol.nombre, datos.sucursal_id)
        email = str(datos.email).lower()
        if self.repo.existe_email(email):
            raise Conflicto("Este correo ya está en uso.")
        usuario = Usuario(
            rol_id=rol.id,
            sucursal_id=datos.sucursal_id,
            nombre=datos.nombre.strip(),
            apellidos=datos.apellidos.strip(),
            email=email,
            password_hash=hash_password(datos.password),
            activo=True,
        )
        self.repo.agregar(usuario)  # TenantRepository fija empresa_id con la empresa del token
        self.db.commit()
        self.db.refresh(usuario)
        return schemas.UsuarioOut.desde(usuario)

    def editar(self, usuario_id: int, datos: schemas.UsuarioUpdate) -> schemas.UsuarioOut:
        usuario = self._obtener(usuario_id)
        cambios = datos.model_dump(exclude_unset=True)

        nuevo_rol = usuario.rol.nombre
        if cambios.get("rol") is not None:
            rol = self._rol_permitido(cambios["rol"])
            nuevo_rol = rol.nombre
            usuario.rol_id = rol.id
            usuario.rol = rol
        sucursal_id = cambios["sucursal_id"] if "sucursal_id" in cambios else usuario.sucursal_id
        self._validar_sucursal(nuevo_rol, sucursal_id)

        quedara_activo = cambios["activo"] if cambios.get("activo") is not None else usuario.activo
        era_admin_activo = self._es_admin(usuario) and usuario.activo
        sigue_admin_activo = nuevo_rol == ADMIN and quedara_activo
        if era_admin_activo and not sigue_admin_activo and self.repo.contar_administradores_activos() <= 1:
            self.db.rollback()
            raise Conflicto("La empresa debe tener al menos un administrador activo.")  # RN03

        for campo in ("nombre", "apellidos"):
            if cambios.get(campo) is not None:
                setattr(usuario, campo, cambios[campo].strip())
        usuario.sucursal_id = sucursal_id
        if cambios.get("activo") is not None:
            usuario.activo = cambios["activo"]
        if cambios.get("password"):
            usuario.password_hash = hash_password(cambios["password"])
        self.db.commit()
        self.db.refresh(usuario)
        return schemas.UsuarioOut.desde(usuario)

    def desactivar(self, usuario_id: int) -> schemas.UsuarioOut:
        return self.editar(usuario_id, schemas.UsuarioUpdate(activo=False))

    # ---- auxiliares ----
    def _obtener(self, usuario_id: int) -> Usuario:
        usuario = self.repo.obtener_interno(usuario_id)
        if usuario is None:
            raise NoEncontrado("Usuario no encontrado.")  # no se revela si existe en otra empresa
        return usuario

    @staticmethod
    def _es_admin(usuario: Usuario) -> bool:
        return usuario.rol.nombre == ADMIN

    def _rol_permitido(self, nombre: str):
        if nombre not in ROLES_INTERNOS:
            raise Prohibido(MSG_ROL)  # p. ej. SuperAdministrador o Cliente
        return self.roles.por_nombre(nombre)

    def _validar_sucursal(self, rol: str, sucursal_id: int | None) -> None:
        if rol in ROLES_CON_SUCURSAL and sucursal_id is None:
            raise DatosInvalidos("Debe asignar una sucursal.")
        if sucursal_id is not None and self.sucursales.obtener(sucursal_id) is None:
            raise NoEncontrado(MSG_RECURSO_AJENO)  # la sucursal no existe en ESTA empresa (RN02)
