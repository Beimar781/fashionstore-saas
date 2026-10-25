"""Crea la base de datos del proyecto en tu PostgreSQL local (la misma que ves en pgAdmin) si no existe.
Lee DATABASE_URL del archivo .env.  Uso:  python scripts/crear_bd.py"""
import sys

import psycopg
from psycopg.conninfo import make_conninfo
from sqlalchemy.engine import make_url

sys.path.insert(0, ".")
from app.core.config import get_settings  # noqa: E402

url = make_url(get_settings().database_url)
conninfo = make_conninfo(host=url.host, port=url.port or 5432, user=url.username, password=url.password, dbname="postgres")
with psycopg.connect(conninfo, autocommit=True) as con:
    existe = con.execute("SELECT 1 FROM pg_database WHERE datname = %s", (url.database,)).fetchone()
    if existe:
        print(f"La base '{url.database}' ya existe.")
    else:
        con.execute(f'CREATE DATABASE "{url.database}"')
        print(f"Base '{url.database}' creada.")
