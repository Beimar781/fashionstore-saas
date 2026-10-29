"""Datos de ejemplo de la bitácora (Fase J): unas 40 filas repartidas entre EMP-A y EMP-B y las operaciones de la plataforma. Idempotente."""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, CAJERO, CLIENTE, ENCARGADO, SUPERADMIN
from app.core.tiempo import ahora
from app.modules.acceso.models import Rol, Usuario
from app.modules.plataforma.bitacora.models import Bitacora
from app.modules.plataforma.models import Empresa
from app.modules.plataforma.publico import registrar_en_bitacora

# (días atrás, hora, rol, acción, entidad, id de la entidad, detalle, IP)
EMPRESA = [
    (6, 8, ADMIN, "LOGIN", "sesión", None, "Inició sesión", "190.129.45.12"),
    (6, 8, ADMIN, "CREAR", "usuario", None, "Registró al usuario Luis Rojas (Encargado)", "190.129.45.12"),
    (6, 9, ADMIN, "CREAR", "producto", None, "Registró el producto Camisa Oxford", "190.129.45.12"),
    (5, 10, ADMIN, "CREAR", "promoción", None, "Registró la promoción Descuento de temporada", "190.129.45.12"),
    (5, 17, ADMIN, "LOGOUT", "sesión", None, "Cerró sesión", "190.129.45.12"),
    (4, 8, ENCARGADO, "LOGIN", "sesión", None, "Inició sesión", "181.115.20.7"),
    (4, 9, ENCARGADO, "RECIBIR", "lote", None, "Recibió el lote LOT-DEMO01 en la sucursal", "181.115.20.7"),
    (4, 11, ENCARGADO, "ATENDER", "reserva", None, "Preparó la reserva RSV-DEMO0001", "181.115.20.7"),
    (3, 9, CAJERO, "LOGIN", "sesión", None, "Inició sesión", "181.115.20.9"),
    (3, 10, CAJERO, "CREAR", "venta", None, "Registró la venta de caja PED-DEMO0001 por Bs 200.00", "181.115.20.9"),
    (3, 10, CAJERO, "COBRAR", "venta", None, "Cobró la venta PED-DEMO0001 por Bs 200.00 (EFECTIVO)", "181.115.20.9"),
    (2, 15, CAJERO, "DEVOLVER", "devolución", None, "Registró la nota de devolución o cambio NDV-DEMO por Bs 100.00", "181.115.20.9"),
    (2, 12, CLIENTE, "LOGIN", "sesión", None, "Inició sesión", "200.87.33.140"),
    (2, 12, CLIENTE, "CREAR", "reserva", None, "Registró la reserva RSV-DEMO0002", "200.87.33.140"),
    (1, 18, CLIENTE, "PAGAR", "pago", None, "Pagó el pedido PED-DEMO0002 por Bs 300.00 con tarjeta", "200.87.33.140"),
    (1, 19, CLIENTE, "CANCELAR", "reserva", None, "Canceló la reserva RSV-DEMO0002", "200.87.33.140"),
]
PLATAFORMA = [
    (7, 9, "LOGIN", "sesión", "Inició sesión"),
    (7, 9, "CREAR", "plan", "Creó el plan Profesional"),
    (6, 10, "CREAR", "empresa", "Registró la empresa {razon} ({codigo})"),
    (6, 10, "ASIGNAR", "suscripción", "Asignó el plan {plan} a la empresa"),
    (2, 16, "MODIFICAR", "plan", "Modificó el plan Básico"),
]


def cargar(db: Session) -> None:
    if db.scalar(select(Bitacora.id).limit(1)):
        return
    base = ahora()
    roles = {r.nombre: r.id for r in db.scalars(select(Rol))}
    planes = {"EMP-A": "Básico", "EMP-B": "Profesional"}
    super_ = db.scalar(select(Usuario).where(Usuario.rol_id == roles[SUPERADMIN]).limit(1))
    for empresa in db.scalars(select(Empresa).order_by(Empresa.id)):
        personas = {rol: db.scalar(select(Usuario).where(Usuario.empresa_id == empresa.id, Usuario.rol_id == roles[rol]).order_by(Usuario.id).limit(1)) for rol in (ADMIN, ENCARGADO, CAJERO, CLIENTE)}
        for dias, hora, rol, accion, entidad, entidad_id, detalle, ip in EMPRESA:
            u = personas[rol]
            if u is None:
                continue
            registrar_en_bitacora(
                db, empresa_id=empresa.id, usuario_id=u.id, usuario=f"{u.nombre} {u.apellidos}".strip(), rol=rol, accion=accion, entidad=entidad, entidad_id=entidad_id,
                detalle=detalle.replace("DEMO", empresa.codigo[-1]), ip=ip, creado_en=(base - timedelta(days=dias)).replace(hour=hora, minute=(dias * 7 + hora) % 60),
            )
        cliente = personas[CLIENTE]
        if cliente is not None:  # un intento de ingreso fallido, desde otra IP
            registrar_en_bitacora(
                db, empresa_id=empresa.id, usuario_id=None, usuario=cliente.email, rol=None, accion="LOGIN_FALLIDO", entidad="sesión", ip="45.230.12.88",
                detalle=f"Intento fallido de inicio de sesión con el correo {cliente.email} en la empresa {empresa.codigo}", creado_en=base - timedelta(days=1, hours=3),
            )
        if super_ is not None:  # operaciones de la plataforma sobre esta empresa
            for dias, hora, accion, entidad, texto in PLATAFORMA[2:4]:
                registrar_en_bitacora(
                    db, empresa_id=empresa.id, usuario_id=super_.id, usuario=f"{super_.nombre} {super_.apellidos}".strip(), rol=SUPERADMIN, accion=accion, entidad=entidad,
                    detalle=texto.format(razon=empresa.razon_social, codigo=empresa.codigo, plan=planes.get(empresa.codigo, "Básico")), ip="190.129.1.1",
                    creado_en=(base - timedelta(days=dias)).replace(hour=hora, minute=30),
                )
    if super_ is not None:
        for dias, hora, accion, entidad, texto in PLATAFORMA[:2] + PLATAFORMA[4:]:
            registrar_en_bitacora(
                db, empresa_id=None, usuario_id=super_.id, usuario=f"{super_.nombre} {super_.apellidos}".strip(), rol=SUPERADMIN, accion=accion, entidad=entidad, detalle=texto,
                ip="190.129.1.1", creado_en=(base - timedelta(days=dias)).replace(hour=hora, minute=5),
            )
