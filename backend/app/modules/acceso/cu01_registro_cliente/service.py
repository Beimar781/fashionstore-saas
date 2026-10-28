"""CU-01 · Registrar cuenta de cliente (RN02, RN05, RN09, RN10). Capa de negocio."""
from sqlalchemy.orm import Session

from app.core.constantes import CLIENTE, EMPRESA_ACTIVA, MSG_EMPRESA_INACTIVA, MSG_SUSCRIPCION_NO_VIGENTE, SUS_ACTIVA
from app.core.errors import Conflicto, Prohibido
from app.core.security import hash_password
from app.modules.acceso.cu01_registro_cliente import schemas
from app.modules.acceso.cu02_login import schemas as login
from app.modules.acceso.cu02_login.service import AutenticacionService
from app.modules.acceso.cu13_usuarios.repository import RolRepository, UsuarioRepository
from app.modules.acceso.models import Usuario
from app.modules.plataforma.cu33_empresas.repository import EmpresaRepository
from app.modules.plataforma.publico import suscripcion_de


class RegistroClienteService:
    def __init__(self, db: Session):
        self.db = db

    def registrar(self, datos: schemas.RegistroClienteIn) -> login.TokenOut:
        empresa = EmpresaRepository(self.db).por_codigo(datos.codigo_empresa.strip())
        if empresa is None or empresa.estado != EMPRESA_ACTIVA:
            raise Prohibido(MSG_EMPRESA_INACTIVA)
        sus = suscripcion_de(self.db, empresa.id)
        if sus is None or sus.estado != SUS_ACTIVA:  # RN05: sin suscripción vigente no se opera
            raise Prohibido(MSG_SUSCRIPCION_NO_VIGENTE)

        usuarios = UsuarioRepository(self.db, empresa.id)  # a partir de aquí todo queda dentro de esa empresa
        email = str(datos.email).lower()
        if usuarios.existe_email(email):
            raise Conflicto("Este correo ya está en uso.")  # RN09: único dentro de la empresa
        rol = RolRepository(self.db).por_nombre(CLIENTE)
        usuarios.agregar(Usuario(
            rol_id=rol.id, nombre=datos.nombre.strip(), apellidos=datos.apellidos.strip(), email=email,
            password_hash=hash_password(datos.password), activo=True,
        ))
        self.db.commit()
        # La cuenta queda lista: se inicia sesión con los mismos datos (mismo resultado que CU-02).
        return AutenticacionService(self.db).iniciar_sesion(
            login.LoginIn(codigo_empresa=empresa.codigo, email=email, password=datos.password)
        )
