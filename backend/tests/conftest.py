"""Pruebas automatizadas (RNF11): pytest + TestClient (HTTPX) contra PostgreSQL real.
El esquema se crea con la migración Alembic 0001, de modo que también se prueba el script del 3.5.4."""
import os
from datetime import date, timedelta

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from sqlalchemy.engine import make_url  # noqa: E402
from app.core.config import get_settings  # noqa: E402

# Por defecto usa el usuario y la clave del .env, con una base aparte para pruebas.
TEST_URL = os.environ.get("TEST_DATABASE_URL") or make_url(get_settings().database_url).set(database="fashionstore_test").render_as_string(hide_password=False)
os.environ["ALEMBIC_DATABASE_URL"] = TEST_URL

from app.core.constantes import ADMIN, CAJERO, CLIENTE, ENCARGADO, SUPERADMIN  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.acceso.models import Rol, Usuario  # noqa: E402
from app.modules.plataforma.models import Empresa, Plan, Suscripcion  # noqa: E402
from app.modules.sucursales.models import Ciudad, Sucursal  # noqa: E402

CLAVE = "Clave1234"

# Las pruebas crean decenas de usuarios: se abarata el hash (solo aquí; en producción se usa la configuración segura por defecto).
from argon2 import PasswordHasher  # noqa: E402
from app.core import security  # noqa: E402

security._hasher = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)


def _crear_bd_si_no_existe():
    """Crea la base de pruebas si no existe (se conecta a la base 'postgres' con las mismas credenciales)."""
    from sqlalchemy.engine import make_url
    url = make_url(TEST_URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as con:
        if not con.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}).scalar():
            con.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine():
    _crear_bd_si_no_existe()
    eng = create_engine(TEST_URL)
    with eng.begin() as con:
        con.execute(text("DROP SCHEMA public CASCADE"))
        con.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config("alembic.ini"), "head")
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    with engine.begin() as con:
        con.execute(text(
            "TRUNCATE usuarios, sucursales, ciudades, suscripciones, empresas, planes RESTART IDENTITY CASCADE"
        ))
    sesion = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield sesion
    sesion.close()


@pytest.fixture
def client(engine, db):
    fabrica = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _get_db():
        s = fabrica()
        try:
            yield s
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


class Datos:
    """Fábrica de datos de prueba directamente sobre la base."""

    def __init__(self, db, client):
        self.db, self.client = db, client
        self._rol = {r.nombre: r.id for r in db.query(Rol)}

    def plan(self, nombre="Básico", max_sucursales=2, ia=False, activo=True, precio=100):
        p = Plan(nombre=nombre, precio=precio, max_sucursales=max_sucursales, reportes_ia=ia, activo=activo)
        self.db.add(p); self.db.commit()
        return p

    def empresa(self, codigo="EMP-A", plan=None, estado="ACTIVA", sus_estado="ACTIVA", inicio=None, venc=None, nit=None):
        e = Empresa(codigo=codigo, razon_social=f"Empresa {codigo}", nit=nit or f"NIT-{codigo}", estado=estado)
        self.db.add(e); self.db.flush()
        if plan is not None:
            self.db.add(Suscripcion(
                empresa_id=e.id, plan_id=plan.id, estado=sus_estado,
                fecha_inicio=inicio or date.today() - timedelta(days=10),
                fecha_vencimiento=venc or date.today() + timedelta(days=355), monto=100))
        self.db.commit()
        return e

    def ciudad(self, empresa, nombre="Santa Cruz"):
        c = Ciudad(empresa_id=empresa.id, nombre=nombre); self.db.add(c); self.db.commit()
        return c

    def sucursal(self, empresa, nombre, activa=True, ciudad=None):
        ciudad = ciudad or self.db.query(Ciudad).filter_by(empresa_id=empresa.id).first() or self.ciudad(empresa)
        s = Sucursal(empresa_id=empresa.id, ciudad_id=ciudad.id, nombre=nombre, activa=activa)
        self.db.add(s); self.db.commit()
        return s

    def usuario(self, empresa, rol=ADMIN, email=None, sucursal=None, activo=True, password=CLAVE):
        u = Usuario(
            empresa_id=empresa.id if empresa else None, rol_id=self._rol[rol],
            sucursal_id=sucursal.id if sucursal else None, nombre=rol, apellidos="Prueba",
            email=email or f"{rol.lower()}@{(empresa.codigo if empresa else 'plataforma').lower()}.com",
            password_hash=hash_password(password), activo=activo)
        self.db.add(u); self.db.commit()
        return u

    def login(self, usuario, empresa=None, password=CLAVE):
        r = self.client.post("/api/auth/login", json={
            "codigo_empresa": empresa.codigo if empresa else None, "email": usuario.email, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def superadmin(self):
        u = self.usuario(None, SUPERADMIN, email="super@plataforma.com")
        return self.login(u)


@pytest.fixture
def datos(db, client):
    return Datos(db, client)


@pytest.fixture
def mundo(datos):
    """Dos empresas independientes (RN18): A con plan Básico, B con plan Profesional."""
    basico = datos.plan("Básico", 2, ia=False)
    pro = datos.plan("Profesional", 10, ia=True)
    a, b = datos.empresa("EMP-A", basico), datos.empresa("EMP-B", pro)
    datos.ciudad(a); datos.ciudad(b)
    return type("Mundo", (), dict(basico=basico, pro=pro, a=a, b=b,
                                  admin_a=datos.usuario(a, ADMIN), admin_b=datos.usuario(b, ADMIN)))


@pytest.fixture
def tienda_a(datos, mundo, client, db):
    """Catálogo base de EMP-A (la API, como Administrador) y su cabecera de sesión."""
    from tests.catalogo_util import tienda
    h = datos.login(mundo.admin_a, mundo.a)
    t = tienda(client, h, db)
    t.h_admin = h
    return t


@pytest.fixture
def tienda_b(datos, mundo, client, db):
    from tests.catalogo_util import tienda
    h = datos.login(mundo.admin_b, mundo.b)
    t = tienda(client, h, db)
    t.h_admin = h
    return t


@pytest.fixture
def inv(datos, mundo, tienda_a, client, db):
    """Fase B sobre EMP-A: dos sucursales con Encargado cada una, una camisa (S, M × Rojo, Azul), un proveedor con portal y un Cajero."""
    from tests.catalogo_util import cabecera_cliente, crear_proveedor, entrar, por_variante, talla_id
    t = tienda_a
    t.centro, t.norte = datos.sucursal(mundo.a, "Centro"), datos.sucursal(mundo.a, "Norte")
    t.camisa = t.producto("Camisa Oxford", t.camisas["id"], t.col["id"], [talla_id(t.alfa, "S"), talla_id(t.alfa, "M")], [t.rojo["id"], t.azul["id"]])
    t.var = por_variante(t.camisa)
    t.v_sm_rojo = t.var[("S", "Rojo")]
    for nombre, suc in (("enc_centro", t.centro), ("enc_norte", t.norte)):
        datos.usuario(mundo.a, "Encargado", email=f"{nombre}@a.com", sucursal=suc)
        setattr(t, "h_" + nombre, entrar(client, mundo.a, f"{nombre}@a.com"))
    datos.usuario(mundo.a, "Cajero", email="cajero@a.com", sucursal=t.centro)
    t.h_cajero = entrar(client, mundo.a, "cajero@a.com")
    t.h_cliente = cabecera_cliente(datos, mundo.a)
    t.proveedor = crear_proveedor(client, t.h_admin)
    t.h_prov = entrar(client, mundo.a, "textiles@proveedor.com")
    return t
