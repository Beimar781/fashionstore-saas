"""Deja listos los datos de la demostración sin conexión (EMP-B por defecto) usando solo la API. Es idempotente: se puede correr las veces que haga falta.

Asegura:
  1. un Encargado y existencias suficientes en cada sucursal (así la Caja no muestra todo «Sin stock»);
  2. dos Cajeros en la primera sucursal (para la demostración de «dos cajeros y la última unidad»);
  3. que el cliente de demostración tenga una tarjeta de prueba guardada (solo con la pasarela simulada; con Stripe se guarda desde la app);
  4. un catálogo mínimo en EMP-C (opcional, con --empresa-c) reutilizando scripts/poblar_via_api.py.

Las claves NO están en el código: se leen de CLAVE_DEMO y de los argumentos. Ejemplo contra el despliegue:
    python scripts/preparar_demo.py --url https://fashionstore-saas-production.up.railway.app
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from poblar_via_api import Api, ErrorApi  # noqa: E402  (mismo cliente de la API que usa el script de poblado)

CLAVE_DEMO = os.environ.get("CLAVE_DEMO", "Demo2026*")
NOTA = "Stock de demostración sin conexión"
TARJETA_PRUEBA = {"numero": "4242424242424242", "mes": 12, "anio": 2030, "cvc": "123", "titular": "Cliente Demo"}


def asegurar_usuario(admin, usuarios: dict, rol: str, email: str, sucursal: dict, nombre: str, avisos: list[str]) -> bool:
    """Crea el usuario si no existe. Devuelve True si quedó disponible."""
    if email in usuarios:
        return True
    try:
        admin.post("/usuarios", {"nombre": nombre, "apellidos": sucursal["nombre"].replace("Sucursal ", ""), "email": email, "password": CLAVE_DEMO, "rol": rol, "sucursal_id": sucursal["id"]})
        usuarios[email] = {"email": email, "rol": rol, "sucursal_id": sucursal["id"]}
        print(f"  + {rol}: {email} ({sucursal['nombre']})")
        return True
    except ErrorApi as e:
        avisos.append(f"No se pudo crear {rol} {email}: {e}")
        return False


def completar_stock(encargado, minimo: int) -> int:
    """Sube a `minimo` las existencias de la sucursal del encargado. Devuelve cuántas variantes se completaron."""
    completadas = 0
    for fila in encargado.paginas("/inventario/sucursal"):
        falta = minimo - fila["disponible"]
        if falta > 0:
            encargado.post("/inventario/sucursal/movimientos", {"variante_id": fila["variante_id"], "tipo": "AJUSTE_ENTRADA", "cantidad": falta, "nota": NOTA})
            completadas += 1
    return completadas


def preparar_sucursales(admin, url: str, codigo: str, minimo: int, avisos: list[str], crear_api=Api) -> dict:
    sucursales = [s for s in admin.get("/sucursales")["sucursales"] if s.get("activa", True)]
    usuarios = {u["email"]: u for u in admin.get("/usuarios")}
    dominio = admin.email.split("@")[1]
    resumen = {"sucursales": len(sucursales), "variantes_completadas": 0, "cajeros": 0}
    for i, suc in enumerate(sucursales, start=1):
        existente = next((u for u in usuarios.values() if u.get("rol") == "Encargado" and u.get("sucursal_id") == suc["id"] and u.get("activo", True)), None)
        email = existente["email"] if existente else f"encargado.demo{i}@{dominio}"
        if not existente and not asegurar_usuario(admin, usuarios, "Encargado", email, suc, "Encargado", avisos):
            continue
        try:
            resumen["variantes_completadas"] += completar_stock(crear_api(url, email, CLAVE_DEMO, codigo), minimo)
        except ErrorApi as e:
            avisos.append(f"{suc['nombre']}: no se pudo completar el stock con {email} ({e}). Si el encargado ya existía, su clave no es la de demostración.")
    primera = sucursales[0] if sucursales else None
    if primera:
        for n in (1, 2):
            if asegurar_usuario(admin, usuarios, "Cajero", f"cajero.demo{n}@{dominio}", primera, f"Cajero {n}", avisos):
                resumen["cajeros"] += 1
    return resumen


def tarjeta_de_prueba(url: str, codigo: str, correo: str, avisos: list[str], crear_api=Api) -> str:
    """Deja una tarjeta de prueba guardada para el cliente de demostración; solo es posible con la pasarela simulada."""
    cliente = crear_api(url, correo, CLAVE_DEMO, codigo)
    if cliente.get("/pagos/tarjetas"):
        return "ya tenía una tarjeta guardada"
    config = cliente.get("/pagos/config")
    if config.get("modo") == "stripe":
        avisos.append(f"{correo}: la pasarela está en modo Stripe; guarde la tarjeta 4242 4242 4242 4242 desde la app o la web al pagar una compra («Guardar esta tarjeta»).")
        return "pendiente (Stripe)"
    sucursal = cliente.get("/catalogo/sucursales")[0]["id"]
    prenda = next((p for p in cliente.get("/catalogo/buscar", sucursal=sucursal, solo_disponibles="true")["items"]), None)
    if prenda is None:
        avisos.append(f"{correo}: no hay prendas con stock para la compra que guarda la tarjeta.")
        return "pendiente (sin stock)"
    variante = cliente.get(f"/catalogo/productos/{prenda['id']}/opciones", sucursal=sucursal)["variantes"]
    elegida = next(v for v in variante if v["disponible"])
    cliente.post("/carrito/items", {"variante_id": elegida["variante_id"], "cantidad": 1, "sucursal_id": sucursal})
    pedido = cliente.post("/compras/checkout", {"tipo_entrega": "RETIRO", "direccion_entrega": "", "nit_ci": "1234567", "razon_social": "Cliente Demo"})
    pago = cliente.post(f"/pagos/pedidos/{pedido['id']}/iniciar", {"tarjeta_guardada_id": None, "guardar_tarjeta": True})
    cliente.post(f"/pagos/{pago.get('pago_id', pago.get('id'))}/confirmar", {"tarjeta": TARJETA_PRUEBA})
    return "tarjeta de prueba guardada"


def poblar_emp_c(url: str, argumento: str, super_email: str, avisos: list[str]) -> None:
    """EMP-C recibe el catálogo de EMP-B con el mismo script de poblado (necesita la clave del SuperAdministrador en CLAVE_SUPERADMIN)."""
    clave_super = os.environ.get("CLAVE_SUPERADMIN")
    if not clave_super:
        avisos.append("EMP-C: falta la variable CLAVE_SUPERADMIN; no se pobló. Ver docs/DESPLIEGUE.md.")
        return
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poblar_via_api.py")
    resultado = subprocess.run([sys.executable, script, "--url", url, "--super-email", super_email, "--super-pass", clave_super, "--plantilla-pass", CLAVE_DEMO, "--admin-pass", CLAVE_DEMO, "--destino-existente", argumento], check=False)
    if resultado.returncode != 0:
        avisos.append("EMP-C: el script de poblado terminó con errores (revise su salida).")


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepara los datos de la demostración sin conexión.")
    ap.add_argument("--url", required=True, help="URL del backend, p. ej. http://localhost:8000")
    ap.add_argument("--codigo", default="EMP-B")
    ap.add_argument("--admin", default="admin@estiloandino.com", help="correo del administrador de la empresa")
    ap.add_argument("--cliente", default="cliente@emp-b.com", help="cliente de demostración que debe tener una tarjeta guardada")
    ap.add_argument("--stock-minimo", type=int, default=12)
    ap.add_argument("--empresa-c", metavar="EMP-C,correo,clave", help="también copia el catálogo mínimo a EMP-C")
    ap.add_argument("--super-email", default="superadmin@fashionstore.com")
    a = ap.parse_args()
    avisos: list[str] = []
    admin = Api(a.url, a.admin, CLAVE_DEMO, a.codigo)
    resumen = preparar_sucursales(admin, a.url, a.codigo, a.stock_minimo, avisos)
    print(f"Sucursales: {resumen['sucursales']} · variantes con stock completado: {resumen['variantes_completadas']} · cajeros de demostración: {resumen['cajeros']}")
    try:
        print(f"Tarjeta del cliente de demostración: {tarjeta_de_prueba(a.url, a.codigo, a.cliente, avisos)}")
    except ErrorApi as e:
        avisos.append(f"{a.cliente}: no se pudo guardar la tarjeta de prueba ({e}).")
    if a.empresa_c:
        poblar_emp_c(a.url, a.empresa_c, a.super_email, avisos)
    if avisos:
        print("\nAvisos:")
        for texto in avisos:
            print(f" - {texto}")
    return 0 if not avisos else 1


if __name__ == "__main__":
    sys.exit(main())
