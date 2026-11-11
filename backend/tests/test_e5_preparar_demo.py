"""Segunda ronda E5 · scripts/preparar_demo.py deja los datos de la demostración sin conexión (stock, cajeros, tarjeta) y puede correrse varias veces.
Se prueba con una API falsa en memoria: el script solo usa get/post/paginas, igual que contra el despliegue."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
import preparar_demo as demo  # noqa: E402


class ApiFalsa:
    """Una empresa con dos sucursales; el stock y los usuarios viven en el propio objeto compartido."""

    mundo: dict = {}

    def __init__(self, base, email, clave, codigo=None):
        self.email, self.clave = email, clave

    @classmethod
    def nuevo_mundo(cls, **extra):
        cls.mundo = {
            "sucursales": [{"id": 1, "nombre": "Sucursal Centro", "activa": True}, {"id": 2, "nombre": "Sucursal Norte", "activa": True}],
            "usuarios": [{"email": "admin@estiloandino.com", "rol": "Administrador", "sucursal_id": None, "activo": True}],
            "stock": {1: {100: 0, 101: 3}, 2: {100: 12}}, "movimientos": [], "tarjetas": [], "modo": "simulado", **extra,
        }

    def _sucursal(self):
        u = next(u for u in self.mundo["usuarios"] if u["email"] == self.email)
        return u["sucursal_id"]

    def get(self, ruta, **params):
        m = self.mundo
        if ruta == "/sucursales":
            return {"sucursales": m["sucursales"]}
        if ruta == "/usuarios":
            return list(m["usuarios"])
        if ruta == "/pagos/tarjetas":
            return m["tarjetas"]
        if ruta == "/pagos/config":
            return {"modo": m["modo"]}
        if ruta == "/catalogo/sucursales":
            return [{"id": 1}]
        if ruta == "/catalogo/buscar":
            return {"items": [{"id": 10}]}
        if ruta.endswith("/opciones"):
            return {"variantes": [{"variante_id": 100, "disponible": True}]}
        raise AssertionError(ruta)

    def paginas(self, ruta, **params):
        assert ruta == "/inventario/sucursal"
        return [{"variante_id": v, "disponible": d} for v, d in self.mundo["stock"][self._sucursal()].items()]

    def post(self, ruta, cuerpo=None, **kw):
        m = self.mundo
        if ruta == "/usuarios":
            m["usuarios"].append({"email": cuerpo["email"], "rol": cuerpo["rol"], "sucursal_id": cuerpo["sucursal_id"], "activo": True})
            m["stock"].setdefault(cuerpo["sucursal_id"], {})
        elif ruta == "/inventario/sucursal/movimientos":
            m["stock"][self._sucursal()][cuerpo["variante_id"]] += cuerpo["cantidad"]
            m["movimientos"].append(cuerpo)
        elif ruta.endswith("/iniciar"):
            return {"pago_id": 5}
        elif ruta.endswith("/confirmar"):
            m["tarjetas"].append({"id": 1, "ultimos4": "4242"})
        elif ruta == "/compras/checkout":
            return {"id": 9}
        return {}


def test_01_completa_el_stock_de_cada_sucursal_y_crea_encargados_y_dos_cajeros():
    ApiFalsa.nuevo_mundo()
    avisos: list[str] = []
    admin = ApiFalsa("u", "admin@estiloandino.com", "x")
    r = demo.preparar_sucursales(admin, "u", "EMP-B", 12, avisos, crear_api=ApiFalsa)
    assert avisos == [] and r == {"sucursales": 2, "variantes_completadas": 2, "cajeros": 2}
    assert all(d >= 12 for sucursal in ApiFalsa.mundo["stock"].values() for d in sucursal.values())
    emails = {u["email"] for u in ApiFalsa.mundo["usuarios"]}
    assert {"encargado.demo1@estiloandino.com", "encargado.demo2@estiloandino.com", "cajero.demo1@estiloandino.com", "cajero.demo2@estiloandino.com"} <= emails
    cajeros = [u for u in ApiFalsa.mundo["usuarios"] if u["rol"] == "Cajero"]
    assert len(cajeros) == 2 and {c["sucursal_id"] for c in cajeros} == {1}


def test_02_es_idempotente_la_segunda_vez_no_crea_ni_mueve_nada():
    ApiFalsa.nuevo_mundo()
    admin = ApiFalsa("u", "admin@estiloandino.com", "x")
    demo.preparar_sucursales(admin, "u", "EMP-B", 12, [], crear_api=ApiFalsa)
    usuarios, movimientos = len(ApiFalsa.mundo["usuarios"]), len(ApiFalsa.mundo["movimientos"])
    r = demo.preparar_sucursales(admin, "u", "EMP-B", 12, [], crear_api=ApiFalsa)
    assert r["variantes_completadas"] == 0
    assert (len(ApiFalsa.mundo["usuarios"]), len(ApiFalsa.mundo["movimientos"])) == (usuarios, movimientos)


def test_03_la_tarjeta_de_prueba_se_guarda_solo_con_la_pasarela_simulada_y_una_sola_vez():
    ApiFalsa.nuevo_mundo()
    avisos: list[str] = []
    assert demo.tarjeta_de_prueba("u", "EMP-B", "cliente@emp-b.com", avisos, crear_api=ApiFalsa) == "tarjeta de prueba guardada"
    assert demo.tarjeta_de_prueba("u", "EMP-B", "cliente@emp-b.com", avisos, crear_api=ApiFalsa) == "ya tenía una tarjeta guardada"
    assert len(ApiFalsa.mundo["tarjetas"]) == 1 and avisos == []
    ApiFalsa.nuevo_mundo(modo="stripe")
    assert demo.tarjeta_de_prueba("u", "EMP-B", "cliente@emp-b.com", avisos, crear_api=ApiFalsa) == "pendiente (Stripe)"
    assert "Stripe" in avisos[0] and ApiFalsa.mundo["tarjetas"] == []


def test_04_el_script_no_lleva_claves_en_el_codigo():
    texto = open(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "preparar_demo.py"), encoding="utf-8").read()
    assert "sk_" not in texto and "Super2026" not in texto and 'os.environ.get("CLAVE_SUPERADMIN")' in texto
