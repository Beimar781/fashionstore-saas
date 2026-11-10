"""Puebla una instalación de FashionStore SOLO por la API (no importa nada de app/*): crea 4 empresas nuevas con sus sucursales,
copia el catálogo de EMP-B (plantilla) con fotos, PNG del vestidor y existencias, y deja todo idempotente (se puede correr varias veces).

Uso:
  python scripts/poblar_via_api.py --url http://localhost:8000 --super-email superadmin@fashionstore.com --super-pass '...'
  python scripts/poblar_via_api.py --url https://fashionstore-saas-production.up.railway.app --super-email ... --super-pass '...'

Necesita:  pip install requests pillow   (ya están en backend/requirements.txt)
Las contraseñas de las cuentas demo siguen la misma convención que scripts/humo_produccion.py (variable CLAVE_DEMO).
Nada de lo que imprime se guarda en archivos: las credenciales salen solo por consola. Nunca se imprimen tokens.
"""
import argparse
import io
import os
import sys
import unicodedata
from datetime import date

import requests
from PIL import Image

CLAVE_DEMO = os.environ.get("CLAVE_DEMO", "Demo2026*")
NOTA_STOCK = "Stock inicial de demostración"

# código sugerido, razón social, NIT, ciudad, plan, correo y teléfono de contacto, administrador y sucursales (nombre, dirección, teléfono, horario)
EMPRESAS_NUEVAS = [
    dict(codigo="EMP-D", razon="Boutique Altiplano S.A.", nit="1023456017", ciudad="Cochabamba", plan="Profesional",
         correo="contacto@boutiquealtiplano.com.bo", telefono="4-4251100", admin=("Valeria", "Camacho", "admin@boutiquealtiplano.com.bo"),
         sucursales=[("Sucursal Cala Cala", "Av. Ramón Rivero 540, Cala Cala", "4-4284410", "Lun a Sáb 10:00 - 20:00"),
                     ("Sucursal Centro", "Calle España 245, Centro", "4-4225566", "Lun a Sáb 09:30 - 20:30"),
                     ("Sucursal Sacaba", "Av. Villazón km 6, Sacaba", "4-4701234", "Lun a Sáb 10:00 - 19:30")]),
    dict(codigo="EMP-E", razon="Ropa Valle Dorado Ltda.", nit="1034567028", ciudad="Tarija", plan="Básico",
         correo="ventas@valledorado.com.bo", telefono="4-6641200", admin=("Rodrigo", "Vaca", "admin@valledorado.com.bo"),
         sucursales=[("Sucursal Centro", "Calle Sucre 480, Centro", "4-6642233", "Lun a Sáb 09:00 - 20:00"),
                     ("Sucursal Aranjuez", "Av. Las Américas 1230, Aranjuez", "4-6645544", "Lun a Sáb 10:00 - 19:00")]),
    dict(codigo="EMP-F", razon="Textiles del Oriente S.R.L.", nit="1045678039", ciudad="Santa Cruz", plan="Básico",
         correo="info@textilesdeloriente.com.bo", telefono="3-3361500", admin=("Daniela", "Suárez", "admin@textilesdeloriente.com.bo"),
         sucursales=[("Sucursal Equipetrol", "Av. San Martín 1580, Equipetrol", "3-3412200", "Lun a Sáb 10:00 - 21:00"),
                     ("Sucursal Plan 3000", "Av. Che Guevara 305, Plan 3000", "3-3478800", "Lun a Sáb 09:00 - 19:00")]),
    dict(codigo="EMP-G", razon="Moda Sucre Express", nit="1056789040", ciudad="Sucre", plan="Prueba gratuita",
         correo="hola@modasucreexpress.com.bo", telefono="4-6441800", admin=("Gabriela", "Terrazas", "admin@modasucreexpress.com.bo"),
         sucursales=[("Sucursal Plaza 25 de Mayo", "Calle Nicolás Ortiz 60, Plaza 25 de Mayo", "4-6443300", "Lun a Sáb 09:30 - 19:30")]),
]


class ErrorApi(Exception):
    def __init__(self, estado: int, detalle: str, ruta: str):
        super().__init__(f"{estado} en {ruta}: {detalle}")
        self.estado, self.detalle, self.ruta = estado, detalle, ruta


class Api:
    """Cliente de una sesión (SuperAdministrador, administrador o encargado). Vuelve a iniciar sesión si el token vence."""

    def __init__(self, base: str, email: str, clave: str, codigo: str | None = None):
        self.base, self.email, self.clave, self.codigo = base.rstrip("/"), email, clave, codigo
        self.http = requests.Session()
        self.token = ""
        self.entrar()

    def entrar(self):
        r = self.http.post(f"{self.base}/api/auth/login", json={"codigo_empresa": self.codigo, "email": self.email, "password": self.clave}, timeout=60)
        if r.status_code != 200:
            raise ErrorApi(r.status_code, _detalle(r), "/auth/login")
        self.token = r.json()["access_token"]

    def pedir(self, metodo: str, ruta: str, **kw):
        for intento in (1, 2):
            r = self.http.request(metodo, f"{self.base}/api{ruta}", headers={"Authorization": f"Bearer {self.token}"}, timeout=120, **kw)
            if r.status_code == 401 and intento == 1:
                self.entrar()
                continue
            break
        if r.status_code >= 400:
            raise ErrorApi(r.status_code, _detalle(r), ruta)
        return r.json() if r.content and "json" in r.headers.get("content-type", "") else None

    def get(self, ruta, **params):
        return self.pedir("GET", ruta, params=params or None)

    def post(self, ruta, cuerpo=None, **kw):
        return self.pedir("POST", ruta, json=cuerpo, **kw) if not kw else self.pedir("POST", ruta, **kw)

    def put(self, ruta, cuerpo=None, **kw):
        return self.pedir("PUT", ruta, json=cuerpo, **kw) if not kw else self.pedir("PUT", ruta, **kw)

    def paginas(self, ruta, **params):
        """Recorre un listado paginado ({items, total, pagina, tamano}) y devuelve todas las filas."""
        filas, pagina = [], 1
        while True:
            r = self.get(ruta, pagina=pagina, tamano=100, **params)
            filas += r["items"]
            if len(filas) >= r["total"] or not r["items"]:
                return filas
            pagina += 1


def _detalle(r: requests.Response) -> str:
    try:
        d = r.json().get("detail", r.text)
        return d if isinstance(d, str) else str(d)
    except ValueError:
        return r.text[:200]


def sin_tilde(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower().strip()


# ---------- el mismo método que seed_prendas.py / cu06_vestidor (copiado: este script no importa app/*) ----------
def preparar_png(contenido: bytes) -> tuple[bytes, int, int]:
    """PNG RGBA de hasta 800 px de ancho; rechaza lo que no es PNG o no tiene fondo transparente."""
    if contenido[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("no es PNG")
    imagen = Image.open(io.BytesIO(contenido)).convert("RGBA")
    alfa = imagen.getchannel("A")
    if sum(1 for v in alfa.getdata() if v < 255) < imagen.width * imagen.height * 0.02:
        raise ValueError("sin fondo transparente")
    if imagen.width > 800:
        imagen = imagen.resize((800, max(1, round(imagen.height * 800 / imagen.width))), Image.LANCZOS)
    salida = io.BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return salida.getvalue(), imagen.width, imagen.height


def anclaje_desde_png(contenido: bytes) -> dict:
    with Image.open(io.BytesIO(contenido)) as imagen:
        alfa = imagen.convert("RGBA").getchannel("A").point(lambda v: 255 if v > 16 else 0)
    ancho, alto = alfa.size
    izq, sup, der, inf = alfa.getbbox()
    y_hombros = sup + 0.08 * (inf - sup)
    y_fila = int(sup + 0.12 * (inf - sup))
    fila = alfa.crop((0, y_fila, ancho, y_fila + 1)).getbbox()
    ancho_fila = (fila[2] - fila[0]) if fila else (der - izq)
    return {
        "y_hombros": round(min(0.5, y_hombros / alto), 3),
        "ancho_hombros": round(max(0.3, min(1.0, ancho_fila / ancho)), 3),
        "y_cadera": round(max(0.4, min(1.0, (sup + 0.95 * (inf - sup)) / alto)), 3),
        "ajuste": 1.0,
    }


def descargar(api: Api, url: str) -> bytes:
    destino = url if url.startswith("http") else f"{api.base}{url}"
    r = requests.get(destino, timeout=120)
    if r.status_code != 200:
        raise ErrorApi(r.status_code, "no se pudo descargar la imagen", url)
    return r.content


def tipo_imagen(contenido: bytes) -> tuple[str, str]:
    if contenido[:8] == b"\x89PNG\r\n\x1a\n":
        return "foto.png", "image/png"
    if contenido[:3] == b"\xff\xd8\xff":
        return "foto.jpg", "image/jpeg"
    return "foto.webp", "image/webp"


# ---------- lectura de la plantilla (EMP-B) ----------
class Plantilla:
    def __init__(self, api: Api):
        self.api = api
        self.grupos = api.get("/grupos-talla")
        self.colores = api.get("/colores")
        self.marcas = api.get("/marcas")
        self.categorias = api.get("/categorias")
        self.temporadas = api.get("/temporadas")
        self.colecciones = api.get("/colecciones")
        self.sucursales = [s for s in api.get("/sucursales")["sucursales"] if s["activa"]]
        self.productos = []
        for resumen in api.paginas("/productos"):
            detalle = api.get(f"/productos/{resumen['id']}")
            detalle["vestidor"] = api.get(f"/vestidor/productos/{resumen['id']}")
            detalle["tiene_foto"] = any(i["principal"] for i in detalle["imagenes"]) or bool(detalle["imagenes"])
            self.productos.append(detalle)
        self.stock = self._leer_stock()

    def _leer_stock(self) -> dict[int, dict[int, int]]:
        """variante_id → {sucursal_id: disponible} en la plantilla."""
        stock: dict[int, dict[int, int]] = {}
        for s in self.sucursales:
            for fila in self.api.paginas("/inventario/global", sucursal=s["id"]):
                stock.setdefault(fila["variante_id"], {})[s["id"]] = fila["disponible"]
        return stock

    def imprimir(self):
        print("\nPlantilla (EMP-B): productos, foto principal y PNG del vestidor")
        print(f"{'Producto':44} {'Activo':7} {'Foto':6} Vestidor")
        for p in self.productos:
            v = p["vestidor"]
            if not v["admite"]:
                vestidor = "no admite"
            else:
                listos = sum(1 for c in v["colores"] if c["listo"])
                vestidor = f"{listos}/{len(v['colores'])} colores"
            print(f"{p['nombre'][:44]:44} {'sí' if p['activo'] else 'no':7} {'sí' if p['tiene_foto'] else 'NO':6} {vestidor}")


# ---------- creación de empresas y sucursales ----------
def asegurar_empresas(sup: Api, avisos: list[str]) -> list[dict]:
    planes = {sin_tilde(p["nombre"]): p for p in sup.get("/plataforma/planes")}
    existentes = sup.get("/plataforma/empresas")
    por_nit = {e["nit"]: e for e in existentes}
    usados = {e["codigo"] for e in existentes}
    resultado = []
    for e in EMPRESAS_NUEVAS:
        plan = planes.get(sin_tilde(e["plan"]))
        if plan is None:
            avisos.append(f"{e['razon']}: no existe el plan «{e['plan']}»; no se creó la empresa.")
            continue
        if e["nit"] in por_nit:
            codigo = por_nit[e["nit"]]["codigo"]
            print(f"= {e['razon']} ya existe ({codigo})")
        else:
            codigo = e["codigo"]
            while codigo in usados:  # si el código ya lo usa otra empresa, se toma el siguiente libre
                codigo = f"EMP-{chr(ord(codigo[-1]) + 1)}"
            hoy = date.today().isoformat()
            suscripcion = {"plan_id": plan["id"], "fecha_inicio": hoy, "forma_pago": "TRANSFERENCIA"}
            if not plan.get("es_prueba"):
                suscripcion["duracion_meses"] = 12
            try:
                sup.post("/plataforma/empresas", {
                    "codigo": codigo, "razon_social": e["razon"], "nit": e["nit"], "email_contacto": e["correo"], "telefono": e["telefono"],
                    "administrador": {"nombre": e["admin"][0], "apellidos": e["admin"][1], "email": e["admin"][2], "password": CLAVE_ADMIN[0]},
                    "suscripcion": suscripcion,
                })
                print(f"+ Empresa creada: {e['razon']} ({codigo}), plan {plan['nombre']}")
                usados.add(codigo)
            except ErrorApi as err:
                avisos.append(f"{e['razon']}: no se pudo crear la empresa ({err}).")
                continue
        resultado.append({**e, "codigo": codigo, "plan_nombre": plan["nombre"]})
    return resultado


def asegurar_sucursales(admin: Api, e: dict, avisos: list[str]) -> list[dict]:
    r = admin.get("/sucursales")
    existentes = {s["nombre"]: s for s in r["sucursales"]}
    limite = r["uso_plan"]["limite"]
    for nombre, direccion, telefono, horario in e["sucursales"]:
        if nombre in existentes:
            continue
        activas = sum(1 for s in existentes.values() if s["activa"])
        if limite is not None and activas >= limite:
            avisos.append(f"{e['razon']}: el plan permite {limite} sucursal(es); no se creó «{nombre}».")
            continue
        try:
            s = admin.post("/sucursales", {"ciudad_nombre": _ciudad_de(nombre, e), "nombre": nombre, "direccion": direccion, "telefono": telefono, "horario": horario})
            existentes[nombre] = s
            print(f"  + {e['razon']}: {nombre}")
        except ErrorApi as err:
            avisos.append(f"{e['razon']}: no se pudo crear la sucursal «{nombre}» ({err}).")
    return [s for s in admin.get("/sucursales")["sucursales"] if s["activa"]]


def _ciudad_de(nombre: str, e: dict) -> str:
    return e["ciudad"]


# ---------- copia del catálogo ----------
class Mapas:
    def __init__(self):
        self.grupo, self.talla, self.color, self.marca, self.categoria, self.temporada, self.coleccion = {}, {}, {}, {}, {}, {}, {}


def copiar_atributos(destino: Api, pl: Plantilla) -> Mapas:
    m = Mapas()
    grupos = {sin_tilde(g["nombre"]): g for g in destino.get("/grupos-talla")}
    for g in pl.grupos:
        d = grupos.get(sin_tilde(g["nombre"])) or destino.post("/grupos-talla", {"nombre": g["nombre"], "descripcion": g["descripcion"]})
        grupos[sin_tilde(g["nombre"])] = d
        m.grupo[g["id"]] = d["id"]
        codigos = {t["codigo"]: t for t in d["tallas"]}
        for t in g["tallas"]:
            dt = codigos.get(t["codigo"]) or destino.post("/tallas", {"grupo_id": d["id"], "codigo": t["codigo"], "orden": t["orden"]})
            m.talla[t["id"]] = dt["id"]
    colores = {sin_tilde(c["nombre"]): c for c in destino.get("/colores")}
    for c in pl.colores:
        d = colores.get(sin_tilde(c["nombre"])) or destino.post("/colores", {"nombre": c["nombre"], "codigo_hex": c["codigo_hex"]})
        m.color[c["id"]] = d["id"]
    marcas = {sin_tilde(x["nombre"]): x for x in destino.get("/marcas")}
    for x in pl.marcas:
        d = marcas.get(sin_tilde(x["nombre"])) or destino.post("/marcas", {"nombre": x["nombre"]})
        m.marca[x["id"]] = d["id"]
    categorias = {sin_tilde(c["nombre"]): c for c in destino.get("/categorias")}
    for c in sorted(pl.categorias, key=lambda c: c["padre_id"] is not None):  # primero las categorías raíz
        d = categorias.get(sin_tilde(c["nombre"])) or destino.post("/categorias", {
            "nombre": c["nombre"], "padre_id": m.categoria.get(c["padre_id"]), "grupo_talla_id": m.grupo.get(c["grupo_talla_id"]), "orden": c["orden"], "activa": c["activa"]})
        categorias[sin_tilde(c["nombre"])] = d
        m.categoria[c["id"]] = d["id"]
    temporadas = {t["codigo"]: t for t in destino.get("/temporadas")}
    for t in pl.temporadas:
        d = temporadas.get(t["codigo"]) or destino.post("/temporadas", {k: t[k] for k in ("nombre", "codigo", "tipo", "inicio", "fin", "activa")})
        m.temporada[t["id"]] = d["id"]
    colecciones = {sin_tilde(c["nombre"]): c for c in destino.get("/colecciones")}
    for c in pl.colecciones:
        d = colecciones.get(sin_tilde(c["nombre"])) or destino.post("/colecciones", {
            "nombre": c["nombre"], "temporada_id": m.temporada[c["temporada_id"]], "fecha_lanzamiento": c["fecha_lanzamiento"], "activa": c["activa"]})
        m.coleccion[c["id"]] = d["id"]
    return m


def copiar_producto(destino: Api, pl: Plantilla, p: dict, m: Mapas, existentes: dict[str, dict], avisos: list[str], etiqueta: str) -> dict | None:
    """Crea (o completa) el producto en la empresa destino con variantes, fotos y PNG del vestidor."""
    nuevo = existentes.get(sin_tilde(p["nombre"]))
    if nuevo is None:
        tallas = sorted({m.talla[v["talla_id"]] for v in p["variantes"]})
        colores = sorted({m.color[v["color_id"]] for v in p["variantes"]})
        nuevo = destino.post("/productos", {
            "nombre": p["nombre"], "descripcion": p["descripcion"], "categoria_id": m.categoria[p["categoria_id"]], "marca_id": m.marca.get(p["marca_id"]),
            "coleccion_id": m.coleccion[p["coleccion_id"]], "genero": p["genero"], "precio_base": str(p["precio_base"]), "material": p["material"],
            "cuidado": p["cuidado"], "tallas_ids": tallas, "colores_ids": colores})
        if not p["activo"]:
            nuevo = destino.post(f"/productos/{nuevo['id']}/desactivar")
        print(f"  + {etiqueta}: {p['nombre']}")
    else:
        nuevo = destino.get(f"/productos/{nuevo['id']}")
    _precios_de_variantes(destino, p, nuevo, m)
    _copiar_fotos(destino, pl, p, nuevo, m)
    _copiar_vestidor(destino, pl, p, nuevo, m, avisos, etiqueta)
    return destino.get(f"/productos/{nuevo['id']}")


def _precios_de_variantes(destino: Api, p: dict, nuevo: dict, m: Mapas):
    por_clave = {(v["talla"], v["color"]): v for v in nuevo["variantes"]}
    for v in p["variantes"]:
        d = por_clave.get((v["talla"], v["color"]))
        if d is None:
            continue
        cambios = {}
        if v["precio_especifico"] is not None and d["precio_especifico"] != v["precio_especifico"]:
            cambios["precio_especifico"] = v["precio_especifico"]
        if v["codigo_barras"] and not d["codigo_barras"]:
            cambios["codigo_barras"] = v["codigo_barras"]
        if d["activa"] != v["activa"]:
            cambios["activa"] = v["activa"]
        if cambios:
            destino.put(f"/productos/{nuevo['id']}/variantes/{d['id']}", cambios)


def _copiar_fotos(destino: Api, pl: Plantilla, p: dict, nuevo: dict, m: Mapas):
    if len(nuevo["imagenes"]) >= len(p["imagenes"]):
        return
    for img in p["imagenes"]:
        datos = descargar(pl.api, img["url"])
        nombre, tipo = tipo_imagen(datos)
        form = {"texto_alt": img["texto_alt"], "principal": "true" if img["principal"] else "false"}
        if img["color_id"] is not None:
            form["color_id"] = str(m.color[img["color_id"]])
        destino.pedir("POST", f"/productos/{nuevo['id']}/imagenes", files={"archivo": (nombre, datos, tipo)}, data=form)


def _copiar_vestidor(destino: Api, pl: Plantilla, p: dict, nuevo: dict, m: Mapas, avisos: list[str], etiqueta: str):
    origen = p["vestidor"]
    if not origen["admite"]:
        return
    destino_v = destino.get(f"/vestidor/productos/{nuevo['id']}")
    listos = {c["color_id"] for c in destino_v["colores"] if c["listo"]}
    foto_por_color = {i["color_id"]: i for i in p["imagenes"] if i["color_id"] is not None}
    for c in origen["colores"]:
        color_dest = m.color[c["color_id"]]
        if color_dest in listos:
            continue
        if c["listo"]:  # se baja el PNG de la plantilla con su anclaje
            png, anclaje = descargar(pl.api, c["imagen_url"]), c["anclaje"]
        else:  # a la plantilla le falta: se genera de la foto con el mismo método de seed_prendas.py
            foto = foto_por_color.get(c["color_id"]) or (p["imagenes"][0] if p["imagenes"] else None)
            if foto is None:
                continue
            try:
                png, _, _ = preparar_png(descargar(pl.api, foto["url"]))
            except ValueError as e:
                avisos.append(f"{etiqueta}: «{p['nombre']}» ({c['color']}) sin PNG de vestidor: la foto {e}.")
                continue
            anclaje = anclaje_desde_png(png)
        destino.pedir("PUT", f"/vestidor/productos/{nuevo['id']}/colores/{color_dest}", files={"archivo": ("vestidor.png", png, "image/png")},
                      data={k: str(anclaje[k]) for k in ("y_hombros", "ancho_hombros", "y_cadera", "ajuste")})


# ---------- existencias por sucursal (solo un Encargado puede registrar ajustes por la API) ----------
def poblar_existencias(sup_base: str, admin: Api, e: dict, sucursales: list[dict], pl: Plantilla, nuevos: list[tuple[dict, dict]], avisos: list[str]):
    dominio = e["admin"][2].split("@")[1]
    usuarios = {u["email"]: u for u in admin.get("/usuarios")}
    for i, suc in enumerate(sucursales):
        email = f"encargado{i + 1}@{dominio}"
        if email not in usuarios:
            try:
                admin.post("/usuarios", {"nombre": "Encargado", "apellidos": suc["nombre"].replace("Sucursal ", ""), "email": email, "password": CLAVE_ADMIN[0], "rol": "Encargado", "sucursal_id": suc["id"]})
                print(f"  + {e['razon']}: encargado de {suc['nombre']} ({email})")
            except ErrorApi as err:
                avisos.append(f"{e['razon']}: no se pudo crear el encargado de {suc['nombre']} ({err}); sin existencias en esa sucursal.")
                continue
        try:
            encargado = Api(sup_base, email, CLAVE_ADMIN[0], e["codigo"])
            actuales = {f["variante_id"]: f["disponible"] for f in encargado.paginas("/inventario/sucursal")}
            origen_sucursal = pl.sucursales[i % len(pl.sucursales)]["id"]  # la sucursal i usa el stock de la sucursal i de la plantilla (en círculo)
            for variante_p, variante_d in _pares_de_variantes(nuevos):
                objetivo = pl.stock.get(variante_p["id"], {}).get(origen_sucursal, 0)
                falta = objetivo - actuales.get(variante_d["id"], 0)
                if falta > 0:
                    encargado.post("/inventario/sucursal/movimientos", {"variante_id": variante_d["id"], "tipo": "AJUSTE_ENTRADA", "cantidad": falta, "nota": NOTA_STOCK})
        except ErrorApi as err:
            avisos.append(f"{e['razon']}: no se pudieron cargar existencias de {suc['nombre']} ({err}).")


def _pares_de_variantes(nuevos: list[tuple[dict, dict]]):
    for origen, destino in nuevos:
        claves = {(v["talla"], v["color"]): v for v in destino["variantes"]}
        for v in origen["variantes"]:
            d = claves.get((v["talla"], v["color"]))
            if d is not None:
                yield v, d


def copiar_a(destino: Api, base: str, e: dict, pl: Plantilla, sucursales: list[dict], avisos: list[str], sin_foto: set[str]) -> int:
    etiqueta = e["codigo"]
    mapas = copiar_atributos(destino, pl)
    existentes = {sin_tilde(r["nombre"]): r for r in destino.paginas("/productos")}
    nuevos = []
    for p in pl.productos:
        if not p["tiene_foto"]:
            sin_foto.add(p["nombre"])
            continue
        try:
            nuevos.append((p, copiar_producto(destino, pl, p, mapas, existentes, avisos, etiqueta)))
        except ErrorApi as err:
            avisos.append(f"{etiqueta}: no se pudo copiar «{p['nombre']}» ({err}).")
    if sucursales:
        poblar_existencias(base, destino, e, sucursales, pl, nuevos, avisos)
    return sum(1 for r in destino.paginas("/productos") if r["imagen_principal"])


CLAVE_ADMIN = [CLAVE_DEMO]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # tildes bien en la consola de Windows
    ap = argparse.ArgumentParser(description="Puebla FashionStore por la API (empresas, sucursales, catálogo con fotos y existencias).")
    ap.add_argument("--url", required=True, help="URL del backend, p. ej. http://localhost:8000")
    ap.add_argument("--super-email", required=True)
    ap.add_argument("--super-pass", required=True)
    ap.add_argument("--admin-pass", default=CLAVE_DEMO, help="contraseña de los administradores y encargados nuevos (por defecto CLAVE_DEMO)")
    ap.add_argument("--plantilla", default="EMP-B,admin@estiloandino.com", help="CODIGO,correo del administrador de la empresa plantilla")
    ap.add_argument("--plantilla-pass", default=CLAVE_DEMO)
    ap.add_argument("--destino-existente", action="append", default=[], metavar="CODIGO,correo,clave",
                    help="empresa que ya existe y también recibe el catálogo (p. ej. EMP-C,admin@correo.com,clave); se puede repetir")
    args = ap.parse_args()
    CLAVE_ADMIN[0] = args.admin_pass
    base = args.url.rstrip("/")
    avisos: list[str] = []
    try:
        sup = Api(base, args.super_email, args.super_pass)
    except ErrorApi as err:
        print(f"No se pudo iniciar sesión como SuperAdministrador: {err}")
        return 1
    planes = sup.get("/plataforma/planes")
    print("Planes:", ", ".join(f"{p['nombre']} ({p.get('precio_texto', p['precio'])}, hasta {p['max_sucursales']} sucursales)" for p in planes))
    print("Empresas actuales:", ", ".join(f"{e['codigo']} ({e['razon_social']})" for e in sup.get("/plataforma/empresas")))

    empresas = asegurar_empresas(sup, avisos)

    codigo_p, correo_p = args.plantilla.split(",")
    try:
        pl = Plantilla(Api(base, correo_p, args.plantilla_pass, codigo_p))
    except ErrorApi as err:
        print(f"No se pudo leer la plantilla {codigo_p}: {err}")
        return 1
    pl.imprimir()

    sin_foto: set[str] = set()
    resumen = []
    for e in empresas:
        try:
            admin = Api(base, e["admin"][2], args.admin_pass, e["codigo"])
        except ErrorApi as err:
            avisos.append(f"{e['razon']}: no se pudo entrar como administrador ({err}); ¿la empresa ya existía con otra contraseña?")
            continue
        sucursales = asegurar_sucursales(admin, e, avisos)
        con_foto = copiar_a(admin, base, e, pl, sucursales, avisos, sin_foto)
        resumen.append((e["codigo"], e["razon"], e["plan_nombre"], len(sucursales), con_foto, e["admin"][2], args.admin_pass))

    todas = {x["codigo"]: x for x in sup.get("/plataforma/empresas")}
    for dato in args.destino_existente:
        codigo, correo, clave = dato.split(",", 2)
        if codigo not in todas:
            avisos.append(f"{codigo}: no existe en esta instalación; no se copió el catálogo.")
            continue
        try:
            admin = Api(base, correo, clave, codigo)
            sucursales = [s for s in admin.get("/sucursales")["sucursales"] if s["activa"]]
            e = {"codigo": codigo, "razon": todas[codigo]["razon_social"], "admin": ("", "", correo)}
            con_foto = copiar_a(admin, base, e, pl, sucursales, avisos, sin_foto)
            resumen.append((codigo, e["razon"], todas[codigo]["plan"] or "—", len(sucursales), con_foto, correo, clave))
        except ErrorApi as err:
            avisos.append(f"{codigo}: no se pudo copiar el catálogo ({err}).")
    if not any(d.startswith("EMP-C") for d in args.destino_existente):
        if "EMP-C" in todas:
            avisos.append("EMP-C existe pero no se indicó --destino-existente EMP-C,correo,clave: no recibió el catálogo.")
        else:
            avisos.append("EMP-C no existe en esta instalación; no se copió el catálogo.")

    print("\nResumen (credenciales solo en consola)")
    print(f"{'Código':8} {'Empresa':30} {'Plan':16} {'Sucurs.':8} {'Prod. con foto':15} Administrador")
    for codigo, razon, plan, nsuc, nfoto, correo, clave in resumen:
        print(f"{codigo:8} {razon[:30]:30} {plan[:16]:16} {nsuc:<8} {nfoto:<15} {correo} / {clave}")
    if sin_foto:
        print("\nProductos de la plantilla SIN foto (no se copiaron):", ", ".join(sorted(sin_foto)))
    if avisos:
        print("\nAvisos:")
        for a in avisos:
            print(" -", a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
