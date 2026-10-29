"""Bitácora del sistema (función transversal). Capa de negocio: registrar (lo llama el middleware y, por `publico.py`, cualquier paquete) y consultar.

Nunca se guardan contraseñas, tokens ni datos de tarjeta: el detalle se arma solo con los datos que nombra la tabla de etiquetas.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import DatosInvalidos
from app.modules.plataforma.bitacora import acciones, schemas
from app.modules.plataforma.bitacora.models import Bitacora
from app.modules.plataforma.bitacora.repository import BitacoraRepository

MSG_PAGINA = "La página y el tamaño deben ser números positivos (tamaño máximo 100)."


def registrar(
    db: Session, *, empresa_id: int | None, usuario_id: int | None, usuario: str, rol: str | None, accion: str, entidad: str, detalle: str,
    ip: str | None = None, entidad_id: int | None = None, creado_en: datetime | None = None,
) -> None:
    """Agrega un registro y lo confirma (es independiente de la operación que lo origina)."""
    registro = Bitacora(
        empresa_id=empresa_id, usuario_id=usuario_id, usuario=usuario[:150], rol=rol, accion=accion, entidad=entidad[:40], entidad_id=entidad_id,
        detalle=detalle[:400], ip=(ip or None) and ip[:45],
    )
    if creado_en is not None:
        registro.creado_en = creado_en
    BitacoraRepository(db).agregar(registro)
    db.commit()


class BitacoraService:
    def __init__(self, db: Session, empresa_id: int | None):
        self.repo = BitacoraRepository(db, empresa_id)
        self.general = empresa_id is None  # SuperAdministrador: todas las empresas

    def consultar(self, f: schemas.Filtros) -> schemas.PaginaBitacoraOut:
        if f.pagina < 1 or not 1 <= f.tamano <= 100:
            raise DatosInvalidos(MSG_PAGINA)
        total, filas = self.repo.buscar(f)
        return schemas.PaginaBitacoraOut(
            total=total, pagina=f.pagina, tamano=f.tamano,
            items=[
                schemas.RegistroOut(
                    id=b.id, fecha=b.creado_en, empresa_id=b.empresa_id, empresa=(razon or "Plataforma") if self.general else None, usuario=b.usuario, rol=b.rol, accion=b.accion,
                    accion_texto=acciones.texto_de(b.accion), tono=acciones.tono_de(b.accion), entidad=b.entidad, entidad_id=b.entidad_id, detalle=b.detalle, ip=b.ip,
                )
                for b, razon in filas
            ],
        )

    def opciones(self) -> schemas.OpcionesOut:
        return schemas.OpcionesOut(
            usuarios=self.repo.usuarios(), entidades=self.repo.entidades(), acciones=[schemas.AccionOut(codigo=c, texto=t) for c, (t, _) in acciones.ACCIONES.items()],
            empresas=[schemas.EmpresaOpcionOut(id=i, nombre=n) for i, n in self.repo.empresas()] if self.general else [],
        )
