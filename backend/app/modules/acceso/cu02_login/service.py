"""CU-02 · Iniciar sesión (RN02, RN05, RN09, RN10). Capa de negocio."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.constantes import (
    ADMIN,
    EMPRESA_ACTIVA,
    MSG_EMPRESA_INACTIVA,
    MSG_SUSCRIPCION_NO_VIGENTE,
    PANEL_POR_ROL,
    SUPERADMIN,
    SUS_ACTIVA,
)
from app.core.config import get_settings
from app.core.correo import enviar_correo
from app.core.errors import DatosInvalidos, NoAutenticado, Prohibido
from app.core.security import crear_token, decodificar_token, hash_password, verify_password
from app.modules.acceso.cu02_login import schemas
from app.modules.acceso.cu02_login.repository import AutenticacionRepository
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.models import Usuario
from app.modules.plataforma.cu33_empresas.repository import EmpresaRepository
from app.modules.plataforma.models import Empresa, Suscripcion
from app.modules.plataforma.publico import suscripcion_de

MSG_CREDENCIALES = "Código de empresa, correo o contraseña inválidos."
MSG_CUENTA_INACTIVA = "Cuenta inactiva. Contacte a su administrador."
MSG_RECUPERACION_ENVIADA = "Si los datos corresponden a una cuenta activa, enviamos un enlace para restablecer la contraseña a su correo."
MSG_ENLACE_INVALIDO = "El enlace no es válido o ya venció. Solicite uno nuevo."
MSG_PASSWORD_ACTUALIZADA = "Contraseña actualizada. Ya puede iniciar sesión."


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _sesion(usuario: Usuario, empresa: Empresa | None, sus: Suscripcion | None) -> dict:
    """Arma el contexto de sesión (usuario, empresa, plan) que consumen la web y el móvil."""
    rol = usuario.rol.nombre
    vigente = sus is not None and sus.estado == SUS_ACTIVA
    restringido = empresa is not None and not vigente  # solo llega aquí el Administrador (ver iniciar_sesion)
    return {
        "usuario": schemas.UsuarioSesion(
            id=usuario.id, nombre=usuario.nombre, apellidos=usuario.apellidos, email=usuario.email, rol=rol,
            sucursal_id=usuario.sucursal_id, sucursal_nombre=usuario.sucursal.nombre if usuario.sucursal else None,
        ),
        "empresa": (
            schemas.EmpresaSesion(id=empresa.id, codigo=empresa.codigo, razon_social=empresa.razon_social, estado=empresa.estado)
            if empresa else None
        ),
        "suscripcion": (
            schemas.SuscripcionSesion(
                estado=sus.estado, fecha_inicio=sus.fecha_inicio, fecha_vencimiento=sus.fecha_vencimiento,
                plan=schemas.PlanSesion(
                    nombre=sus.plan.nombre, max_sucursales=sus.plan.max_sucursales, reportes_ia=sus.plan.reportes_ia,
                    offline=sus.plan.offline, reportes_convencionales=sus.plan.reportes_convencionales,
                ),
            )
            if sus else None
        ),
        "panel": PANEL_POR_ROL.get(rol, "catalogo"),
        "restringido": restringido,
    }


def _claims(usuario: Usuario, restringido: bool) -> dict:
    return {
        "sub": str(usuario.id),
        "rol": usuario.rol.nombre,
        "empresa_id": usuario.empresa_id,
        "sucursal_id": usuario.sucursal_id,
        "restringido": restringido,
    }


class AutenticacionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AutenticacionRepository(db)

    def iniciar_sesion(self, datos: schemas.LoginIn) -> schemas.TokenOut:
        codigo = (datos.codigo_empresa or "").strip()
        email = datos.email.strip().lower()
        empresa: Empresa | None = None

        if codigo:
            empresa = EmpresaRepository(self.db).por_codigo(codigo)
            if empresa is None or empresa.estado != EMPRESA_ACTIVA:  # inexistente, suspendida o cancelada
                raise Prohibido(MSG_EMPRESA_INACTIVA)
            usuario = self.repo.usuario_de_empresa(empresa.id, email)
        else:
            usuario = self.repo.usuario_de_plataforma(email)  # SuperAdministrador

        if usuario is None or not verify_password(usuario.password_hash if usuario else None, datos.password):
            raise NoAutenticado(MSG_CREDENCIALES)  # mensaje único: no indica cuál dato falla
        if not usuario.activo:
            raise Prohibido(MSG_CUENTA_INACTIVA)

        sus = suscripcion_de(self.db, empresa.id) if empresa else None
        vigente = sus is not None and sus.estado == SUS_ACTIVA
        if empresa is not None and not vigente and usuario.rol.nombre != ADMIN:
            raise Prohibido(MSG_SUSCRIPCION_NO_VIGENTE)  # el Administrador entra en modo restringido

        usuario.ultimo_acceso = datetime.now(timezone.utc)
        self.db.commit()
        return self._tokens(usuario, empresa, sus)

    def renovar(self, refresh_token: str) -> schemas.TokenOut:
        claims = decodificar_token(refresh_token, "refresh")
        usuario = self.db.get(Usuario, int(claims["sub"]))
        if usuario is None or not usuario.activo:
            raise NoAutenticado("Sesión inválida o vencida. Inicie sesión nuevamente.")
        empresa = self.db.get(Empresa, usuario.empresa_id) if usuario.empresa_id else None
        if empresa is not None and empresa.estado != EMPRESA_ACTIVA:
            raise Prohibido(MSG_EMPRESA_INACTIVA)
        sus = suscripcion_de(self.db, empresa.id) if empresa else None
        if empresa is not None and (sus is None or sus.estado != SUS_ACTIVA) and usuario.rol.nombre != ADMIN:
            raise Prohibido(MSG_SUSCRIPCION_NO_VIGENTE)
        return self._tokens(usuario, empresa, sus)

    def sesion_actual(self, ctx: Contexto) -> schemas.SesionOut:
        empresa = self.db.get(Empresa, ctx.empresa_id) if ctx.empresa_id else None
        sus = suscripcion_de(self.db, empresa.id) if empresa else None
        return schemas.SesionOut(**_sesion(ctx.usuario, empresa, sus))

    def _tokens(self, usuario: Usuario, empresa: Empresa | None, sus: Suscripcion | None) -> schemas.TokenOut:
        sesion = _sesion(usuario, empresa, sus)
        claims = _claims(usuario, sesion["restringido"])
        return schemas.TokenOut(
            **sesion, access_token=crear_token(claims, "access"), refresh_token=crear_token(claims, "refresh")
        )

    # --- recuperación de contraseña (extensión de CU-02) ---
    def solicitar_restablecimiento(self, datos: schemas.OlvidePasswordIn) -> schemas.MensajeOut:
        """Siempre responde igual: no revela si el correo o el código de empresa existen."""
        codigo = (datos.codigo_empresa or "").strip()
        email = datos.email.strip().lower()
        usuario: Usuario | None = None
        if codigo:
            empresa = EmpresaRepository(self.db).por_codigo(codigo)
            if empresa is not None and empresa.estado == EMPRESA_ACTIVA:
                usuario = self.repo.usuario_de_empresa(empresa.id, email)
        else:
            usuario = self.repo.usuario_de_plataforma(email)

        if usuario is not None and usuario.activo:
            cfg = get_settings()
            token = secrets.token_urlsafe(32)
            self.repo.invalidar_pendientes(usuario.id)  # solo el enlace más reciente sirve
            self.repo.crear_restablecimiento(
                usuario.id, _hash_token(token), datetime.now(timezone.utc) + timedelta(minutes=cfg.reset_token_minutes)
            )
            self.db.commit()
            enlace = f"{cfg.frontend_url.rstrip('/')}/restablecer-password?token={token}"
            enviar_correo(
                usuario.email, "Restablecer su contraseña · FashionStore",
                f"<p>Hola {usuario.nombre},</p><p>Recibimos una solicitud para restablecer su contraseña. "
                f"Use este enlace (vence en {cfg.reset_token_minutes} minutos y sirve una sola vez):</p>"
                f'<p><a href="{enlace}">Restablecer contraseña</a></p>'
                "<p>Si usted no lo solicitó, ignore este mensaje.</p>",
                texto_consola=f"Enlace para restablecer: {enlace}",
            )
        return schemas.MensajeOut(detail=MSG_RECUPERACION_ENVIADA)

    def restablecer_password(self, datos: schemas.RestablecerPasswordIn) -> schemas.MensajeOut:
        fila = self.repo.restablecimiento_vigente(_hash_token(datos.token), datetime.now(timezone.utc))
        if fila is None:
            raise DatosInvalidos(MSG_ENLACE_INVALIDO)
        usuario = self.db.get(Usuario, fila.usuario_id)
        if usuario is None or not usuario.activo:
            raise DatosInvalidos(MSG_ENLACE_INVALIDO)
        usuario.password_hash = hash_password(datos.password)
        fila.usado = True
        self.db.commit()
        return schemas.MensajeOut(detail=MSG_PASSWORD_ACTUALIZADA)
