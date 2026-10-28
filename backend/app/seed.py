"""Datos iniciales (seed) — CU/RN18: planes, SuperAdministrador y dos empresas de prueba independientes.

Uso:  python -m app.seed
Es idempotente: se puede ejecutar varias veces.
"""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.core.constantes import ADMIN, CAJERO, CLIENTE, ENCARGADO, SUPERADMIN
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.acceso.models import Rol, Usuario
from app.modules.plataforma.models import Empresa, Plan, Suscripcion
from app.modules.sucursales.models import Ciudad, Sucursal
from app.seed_catalogo import cargar as cargar_catalogo

SUPER_EMAIL, SUPER_PASS = "superadmin@fashionstore.com", "Super2026*"
CLAVE = "Demo2026*"

PLANES = [
    dict(nombre="Básico", descripcion="Hasta 2 sucursales activas, reportes convencionales y operación offline.",
         precio=150, periodicidad="mensual", max_sucursales=2, reportes_ia=False),
    dict(nombre="Profesional", descripcion="Hasta 10 sucursales activas, reportes generativos con IA y analítica ML.",
         precio=350, periodicidad="mensual", max_sucursales=10, reportes_ia=True),
]

EMPRESAS = [
    dict(codigo="EMP-A", razon_social="Moda Urbana S.R.L.", nit="1020304011", plan="Básico", ciudad="Santa Cruz",
         depto="Santa Cruz", admin=("Carla", "Mendoza", "admin@modaurbana.com"),
         sucursales=[("Sucursal Centro", "Av. Cañoto 120", "3-3322110")],
         otros=[(ENCARGADO, "Luis", "Rojas", "encargado@tienda.com", "Sucursal Centro"),
                (CAJERO, "Ana", "Suárez", "cajero@tienda.com", "Sucursal Centro")]),
    dict(codigo="EMP-B", razon_social="Estilo Andino Ltda.", nit="2030405022", plan="Profesional", ciudad="La Paz",
         depto="La Paz", admin=("Diego", "Quispe", "admin@estiloandino.com"),
         sucursales=[("Sucursal Sopocachi", "Av. 20 de Octubre 2050", "2-2411100"),
                     ("Sucursal Calacoto", "Calle 21 de Calacoto 300", "2-2799000")],
         otros=[(ENCARGADO, "Marta", "Condori", "encargado@tienda.com", "Sucursal Sopocachi"),
                (CAJERO, "Pedro", "Mamani", "cajero@tienda.com", "Sucursal Calacoto")]),
]


def _usuario(db: Session, empresa_id, rol_id, nombre, apellidos, email, password, sucursal_id=None):
    existente = db.scalar(select(Usuario).where(Usuario.empresa_id.is_(empresa_id) if empresa_id is None else Usuario.empresa_id == empresa_id, Usuario.email == email))
    if existente:
        return existente
    u = Usuario(empresa_id=empresa_id, rol_id=rol_id, sucursal_id=sucursal_id, nombre=nombre, apellidos=apellidos,
                email=email, password_hash=hash_password(password), activo=True)
    db.add(u)
    db.flush()
    return u


def ejecutar(db: Session) -> None:
    roles = {r.nombre: r.id for r in db.scalars(select(Rol))}
    planes = {}
    for p in PLANES:
        plan = db.scalar(select(Plan).where(Plan.nombre == p["nombre"])) or Plan(**p)
        db.add(plan)
        planes[p["nombre"]] = plan
    db.flush()

    _usuario(db, None, roles[SUPERADMIN], "Super", "Administrador", SUPER_EMAIL, SUPER_PASS)

    for e in EMPRESAS:
        empresa = db.scalar(select(Empresa).where(Empresa.codigo == e["codigo"]))
        if empresa is None:
            empresa = Empresa(codigo=e["codigo"], razon_social=e["razon_social"], nit=e["nit"],
                              email_contacto=e["admin"][2], telefono="70000000")
            db.add(empresa)
            db.flush()
            hoy = date.today()
            db.add(Suscripcion(empresa_id=empresa.id, plan_id=planes[e["plan"]].id, fecha_inicio=hoy,
                               fecha_vencimiento=hoy + timedelta(days=365), forma_pago="QR",
                               monto=planes[e["plan"]].precio * 12))
        ciudad = db.scalar(select(Ciudad).where(Ciudad.empresa_id == empresa.id, Ciudad.nombre == e["ciudad"]))
        if ciudad is None:
            ciudad = Ciudad(empresa_id=empresa.id, nombre=e["ciudad"], departamento=e["depto"])
            db.add(ciudad)
            db.flush()
        sucs = {}
        for nombre, direccion, tel in e["sucursales"]:
            s = db.scalar(select(Sucursal).where(Sucursal.empresa_id == empresa.id, Sucursal.nombre == nombre))
            if s is None:
                s = Sucursal(empresa_id=empresa.id, ciudad_id=ciudad.id, nombre=nombre, direccion=direccion,
                             telefono=tel, horario="Lun-Sáb 9:00-20:00", activa=True)
                db.add(s)
                db.flush()
            sucs[nombre] = s
        _usuario(db, empresa.id, roles[ADMIN], e["admin"][0], e["admin"][1], e["admin"][2], CLAVE)
        for rol, nom, ape, email, suc in e["otros"]:
            _usuario(db, empresa.id, roles[rol], nom, ape, email, CLAVE, sucs[suc].id)
        _usuario(db, empresa.id, roles[CLIENTE], "Cliente", "Demo", f"cliente@{e['codigo'].lower()}.com", CLAVE)
        db.flush()
        cargar_catalogo(db, empresa)
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as sesion:
        ejecutar(sesion)
    print("Seed aplicado.\n")
    print("SuperAdministrador (código de empresa vacío): ", SUPER_EMAIL, "/", SUPER_PASS)
    for e in EMPRESAS:
        print(f"{e['codigo']} · {e['razon_social']} (plan {e['plan']}):")
        print(f"   Administrador: {e['admin'][2]} / {CLAVE}")
        print(f"   Encargado y Cajero: encargado@tienda.com, cajero@tienda.com / {CLAVE}  (el mismo correo existe en ambas empresas)")
