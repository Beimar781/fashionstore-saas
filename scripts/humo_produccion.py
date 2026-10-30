"""Prueba de humo del sistema desplegado: inicia sesión con las cuentas de demostración y revisa lo esencial.

Uso:  python scripts/humo_produccion.py https://fashionstore-saas-production.up.railway.app

Las contraseñas de las cuentas demo están en backend/app/seed.py; se pueden cambiar con las variables CLAVE_DEMO y CLAVE_SUPERADMIN.
Sale con código 1 si algo falla. Nunca imprime tokens.
"""
import os
import sys

import httpx

CLAVE_DEMO = os.environ.get("CLAVE_DEMO", "Demo2026*")
CLAVE_SUPERADMIN = os.environ.get("CLAVE_SUPERADMIN", "Super2026*")
CUENTAS = {
    "superadmin": (None, "superadmin@fashionstore.com", CLAVE_SUPERADMIN),
    "admin EMP-A": ("EMP-A", "admin@modaurbana.com", CLAVE_DEMO),
    "cliente EMP-A": ("EMP-A", "cliente@emp-a.com", CLAVE_DEMO),
    "admin EMP-B": ("EMP-B", "admin@estiloandino.com", CLAVE_DEMO),
    "cliente EMP-B": ("EMP-B", "cliente@emp-b.com", CLAVE_DEMO),
}
PEDIDO_ASISTENTE = {"mensajes": [{"rol": "usuario", "texto": "Busco una camisa para el trabajo"}]}

resultados: list[tuple[bool, str]] = []


def anotar(ok: bool, nombre: str, detalle: str = "") -> bool:
    resultados.append((ok, nombre))
    print(f"{'✔' if ok else '✘'} {nombre}" + (f" — {detalle}" if detalle else ""))
    return ok


def revisar(nombre: str, accion) -> object:
    """Ejecuta una comprobación; si lanza un error de red o de formato, la marca como fallida y sigue con la siguiente."""
    try:
        return accion()
    except Exception as error:  # noqa: BLE001 - la prueba de humo nunca debe cortarse a la mitad
        anotar(False, nombre, type(error).__name__)
        return None


def iniciar_sesion(http: httpx.Client, nombre: str) -> dict | None:
    codigo, email, clave = CUENTAS[nombre]
    r = http.post("/api/auth/login", json={"codigo_empresa": codigo, "email": email, "password": clave})
    if not anotar(r.status_code == 200, f"Inicio de sesión: {nombre}", f"HTTP {r.status_code}"):
        return None
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main(url_api: str) -> int:
    with httpx.Client(base_url=url_api.rstrip("/").removesuffix("/api"), timeout=60) as http:
        r = revisar("Salud", lambda: http.get("/salud"))
        if r is not None:
            anotar(r.status_code == 200 and r.json().get("estado") == "ok", "Salud del API (/salud)", f"HTTP {r.status_code}")

        sesiones = {nombre: revisar(f"Inicio de sesión: {nombre}", lambda n=nombre: iniciar_sesion(http, n)) for nombre in CUENTAS}

        for empresa in ("EMP-A", "EMP-B"):
            h = sesiones.get(f"cliente {empresa}")
            if h:
                r = revisar(f"Catálogo {empresa}", lambda: http.get("/api/catalogo/productos", headers=h))
                if r is not None:
                    total = r.json().get("total", 0) if r.status_code == 200 else 0
                    anotar(r.status_code == 200 and total > 0, f"Catálogo de {empresa} con prendas", f"HTTP {r.status_code}, total {total}")

        h = sesiones.get("cliente EMP-A")
        if h:
            r = revisar("Pagos", lambda: http.get("/api/pagos/config", headers=h))
            if r is not None:
                modo = r.json().get("modo") if r.status_code == 200 else None
                anotar(modo == "stripe", "Pagos en modo Stripe (/api/pagos/config)", f"HTTP {r.status_code}, modo {modo}")

            r = revisar("Asistente EMP-A", lambda: http.post("/api/asistente/chat", json=PEDIDO_ASISTENTE, headers=h))
            if r is not None:
                detalle = str(r.json().get("detail", "")) if r.status_code == 403 else ""
                anotar(r.status_code == 403 and detalle.startswith("Su plan no incluye esta funcionalidad"), "Asistente de EMP-A bloqueado por plan (403)", f"HTTP {r.status_code}")

        h = sesiones.get("cliente EMP-B")
        if h:
            r = revisar("Asistente EMP-B", lambda: http.post("/api/asistente/chat", json=PEDIDO_ASISTENTE, headers=h))
            if r is not None:
                origen = r.json().get("origen") if r.status_code == 200 else None
                anotar(r.status_code == 200 and origen == "IA", "Asistente de EMP-B responde con la IA (origen IA)", f"HTTP {r.status_code}, origen {origen}")

    fallidas = [n for ok, n in resultados if not ok]
    print(f"\n{len(resultados) - len(fallidas)} de {len(resultados)} comprobaciones correctas.")
    return 1 if fallidas else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows (cp1252) no puede imprimir ✔ ni ✘
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
