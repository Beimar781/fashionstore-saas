"""Ayudante de las pruebas de la Fase A: arma un catálogo de una empresa usando la propia API (rol Administrador)."""
from datetime import date

from app.modules.inventario.models import Existencia

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # firma PNG mínima para probar la subida de imágenes


class Catalogo:
    def __init__(self, client, headers, db=None):
        self.client, self.h, self.db = client, headers, db

    def _crear(self, ruta, cuerpo, esperado=201):
        r = self.client.post(ruta, json=cuerpo, headers=self.h)
        assert r.status_code == esperado, r.text
        return r.json()

    def grupo(self, nombre, codigos):
        grupo = self._crear("/api/grupos-talla", {"nombre": nombre})
        for orden, codigo in codigos:  # (orden, código): se pueden crear desordenadas
            self._crear("/api/tallas", {"grupo_id": grupo["id"], "codigo": codigo, "orden": orden})
        return next(g for g in self.client.get("/api/grupos-talla", headers=self.h).json() if g["id"] == grupo["id"])

    def categoria(self, nombre, grupo_id=None, padre_id=None):
        return self._crear("/api/categorias", {"nombre": nombre, "grupo_talla_id": grupo_id, "padre_id": padre_id})

    def color(self, nombre, hex_="#AA0000"):
        return self._crear("/api/colores", {"nombre": nombre, "codigo_hex": hex_})

    def temporada(self, codigo="PV26", nombre="Primavera-Verano 2026"):
        return self._crear("/api/temporadas", {
            "nombre": nombre, "codigo": codigo, "tipo": "PRIMAVERA_VERANO",
            "inicio": date(2026, 9, 1).isoformat(), "fin": date(2027, 3, 1).isoformat()})

    def coleccion(self, temporada_id, nombre="Colección Urbana"):
        return self._crear("/api/colecciones", {"nombre": nombre, "temporada_id": temporada_id})

    def producto(self, nombre, categoria_id, coleccion_id, tallas, colores, precio="100.00", **extra):
        cuerpo = {
            "nombre": nombre, "categoria_id": categoria_id, "coleccion_id": coleccion_id, "genero": "UNISEX",
            "precio_base": precio, "tallas_ids": tallas, "colores_ids": colores, **extra}
        return self._crear("/api/productos", cuerpo)

    def stock(self, empresa_id, sucursal_id, variante_id, disponible):
        self.db.add(Existencia(empresa_id=empresa_id, sucursal_id=sucursal_id, variante_id=variante_id, disponible=disponible))
        self.db.commit()


def tienda(client, headers, db):
    """Mundo mínimo de una empresa: tallas alfabéticas y numéricas, 3 colores, una temporada y una colección."""
    c = Catalogo(client, headers, db)
    c.alfa = c.grupo("Ropa superior", [(3, "L"), (2, "M"), (1, "S"), (4, "XL")])  # creadas desordenadas a propósito
    c.numerico = c.grupo("Pantalones", [(1, "28"), (2, "30"), (3, "32")])
    c.camisas = c.categoria("Camisas", c.alfa["id"])
    c.pantalones = c.categoria("Pantalones", c.numerico["id"])
    c.rojo, c.azul, c.verde = c.color("Rojo", "#CC0000"), c.color("Azul", "#0000CC"), c.color("Verde", "#00AA00")
    c.temp = c.temporada()
    c.col = c.coleccion(c.temp["id"])
    return c


def talla_id(grupo, codigo):
    return next(t["id"] for t in grupo["tallas"] if t["codigo"] == codigo)


def cabecera_cliente(datos, empresa):
    """Sesión de un Cliente de la empresa (se crea la primera vez)."""
    from app.modules.acceso.models import Usuario

    usuario = datos.db.query(Usuario).filter_by(empresa_id=empresa.id, email="cliente@tienda.com").first() or datos.usuario(
        empresa, "Cliente", email="cliente@tienda.com")
    return datos.login(usuario, empresa)


def por_variante(producto):
    """{(talla, color): variante} de un producto devuelto por la API."""
    return {(v["talla"], v["color"]): v for v in producto["variantes"]}


def entrar(client, empresa, email, password="Clave1234"):
    """Cabecera de sesión iniciando sesión por la API con código de empresa, correo y contraseña."""
    r = client.post("/api/auth/login", json={"codigo_empresa": empresa.codigo, "email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def crear_proveedor(client, h_admin, nombre="Textiles Sur", con_acceso=True, **extra):
    """Proveedor por la API; con acceso crea la cuenta del portal (<correo>/Clave1234)."""
    cuerpo = {"razon_social": nombre, "email": f"{nombre.split()[0].lower()}@proveedor.com", "telefono": "70000000", **extra}
    r = client.post("/api/proveedores", json=cuerpo, headers=h_admin)
    assert r.status_code == 201, r.text
    proveedor = r.json()
    if con_acceso:
        r = client.post(f"/api/proveedores/{proveedor['id']}/acceso", json={"email": cuerpo["email"], "password": "Clave1234"}, headers=h_admin)
        assert r.status_code == 201, r.text
    return proveedor
