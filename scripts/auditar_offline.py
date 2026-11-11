"""Auditoría estática de las pantallas sin conexión (segunda ronda · E5). Recorre las rutas de la web por rol y el código del móvil y busca los patrones que ya
causaron fallos: «Cargando…» sin salida, listas vacías que engañan, cargas que solo corren con red, escrituras sin protección. Escribe docs/AUDITORIA_OFFLINE.md.

Uso:  python scripts/auditar_offline.py          (escribe el informe)
      python scripts/auditar_offline.py --verificar   (sale con error si queda algún «FALLA»; sirve en la integración continua)
Es una revisión del código, no un navegador: la prueba con el service worker real se hace a mano (docs/PRUEBAS_SISTEMA.md §17 a §20)."""
import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "frontend" / "src" / "app"
MOVIL = RAIZ / "movil" / "lib"
INFORME = RAIZ / "docs" / "AUDITORIA_OFFLINE.md"

ROL_POR_RAIZ = {"plataforma": "SuperAdministrador", "empresa": "Administrador", "tienda": "Cliente", "sucursal": "Encargado", "proveedor": "Proveedor", "pos": "Cajero"}
ARCHIVO_DE_RUTAS = {
    "plataforma": "features/plataforma/plataforma.routes.ts", "empresa": "features/administracion/administracion.routes.ts", "tienda": "features/catalogo/catalogo.routes.ts",
    "sucursal": "features/inventario/inventario.routes.ts", "proveedor": "features/primer-parcial/proveedores/proveedores.routes.ts", "pos": "features/primer-parcial/ventas/ventas.routes.ts",
}
# pantallas que por definición solo existen con Internet (se comprueba que lo expliquen) o que no leen del servidor
SOLO_CON_INTERNET = {"login.page", "registro.page", "olvide-password.page", "restablecer-password.page"}

# avisos revisados a mano: la pantalla no necesita recargarse o ya protege sus escrituras de otra forma
ACEPTADOS_WEB = {
    "asistente.page": "responde con el catálogo descargado sin leer del servidor al abrir",
    "reservar.page": "formulario: la reserva sin conexión se guarda en la cola (RN11)",
    "vestidor.page": "trabaja con la cámara y las imágenes guardadas, no con listas del servidor",
    "checkout.page": "sin conexión guarda la compra en la cola; con red escribe en el servidor",
}
# puntos del móvil revisados a mano
ACEPTADOS_MOVIL = {
    ("features/auth/presentation/registro_screen.dart", "CircularProgressIndicator"): "indicador dentro del botón «Crear cuenta»; termina al responder",
    ("primer_parcial/catalogo/presentation/catalogo_screen.dart", "CircularProgressIndicator"): "paginación: `_mas` vuelve a false en `finally`",
    ("primer_parcial/ia/vestidor/presentation/vestidor_screen.dart", "CircularProgressIndicator"): "`cargando` pasa a false también en error (muestra el mensaje)",
    ("primer_parcial/ventas/presentation/boton_comprobante.dart", "CircularProgressIndicator"): "indicador dentro del botón; termina al responder o fallar",
    ("primer_parcial/reservas/data/pago_movil.dart", "catch ApiException"): "devuelve un resultado de pago con el mensaje (nunca queda en espera)",
    ("primer_parcial/reservas/presentation/reservas_screen.dart", "catch ApiException"): "usa la copia guardada y, si no hay, el mensaje «Sin conexión: todavía no se descargaron sus reservas.»",
    ("primer_parcial/ventas/presentation/pedidos_screen.dart", "catch ApiException"): "usa la copia guardada y, si no hay, el mensaje de sin conexión",
}


def importaciones(texto: str, base: Path) -> list[tuple[str, Path]]:
    """Rutas (path, archivo) de un archivo de rutas, con las rutas relativas resueltas."""
    salida = []
    for m in re.finditer(r"path:\s*'([^']*)'[^\n]*?import\('([^']+)'\)", texto):
        destino = (base.parent / (m.group(2) + ".ts")).resolve()
        salida.append((m.group(1) or "(inicio)", destino))
    for m in re.finditer(r"const (\w+) = \(\) => import\('([^']+)'\)", texto):
        destino = (base.parent / (m.group(2) + ".ts")).resolve()
        for n in re.finditer(r"path:\s*'([^']*)'[^\n]*?loadComponent:\s*" + m.group(1), texto):
            salida.append((n.group(1) or "(inicio)", destino))
    return salida


def revisar_web(archivo: Path) -> list[tuple[str, str]]:
    """Devuelve [(nivel, motivo)] con nivel FALLA o AVISO; vacío = sin hallazgos."""
    if not archivo.exists():
        return [("AVISO", "archivo no encontrado")]
    t = archivo.read_text(encoding="utf-8")
    hallazgos = []
    # un «Cargando…» atado a la señal `cargando()` termina siempre (también en error); uno atado a «dato todavía null» puede girar para siempre
    if any('<div class="empty">Cargando…</div>' in linea and "cargando()" not in linea for linea in t.splitlines()):
        hallazgos.append(("FALLA", "«Cargando…» sin salida (usar <app-cargando />)"))
    if re.search(r"ngOnInit\(\)\s*\{\s*if \((?:this\.)?(?:enLinea|red\.online)\(\)\)", t):
        hallazgos.append(("FALLA", "ngOnInit carga solo con red"))
    if "cargando.set(true)" in t or "cargando = signal(true)" in t:
        if t.count("cargando.set(false)") < 2 and "finalize" not in t:
            hallazgos.append(("FALLA", "«cargando» sin ruta de error"))
    if re.search(r"@else if \(![^\n]*length\)[^\n]*<div class=\"(?:card )?empty\">(?:No hay|Aún no)", t):
        hallazgos.append(("FALLA", "lista vacía que afirma «No hay…» sin distinguir la falta de conexión (usar <app-vacio>)"))
    # error rojo + «No hay…»: una lista vacía que no pasa por <app-vacio> afirma que no hay nada aunque no se haya podido consultar
    if re.search(r'<div class="(?:card )?empty">(?:No hay|Aún no|No tiene)', t) and ("error()" in t or ".subscribe(" in t):
        hallazgos.append(("FALLA", "error + «No hay…» engañoso: usar <app-vacio>"))
    llama = re.search(r"\.(?:post|put|patch|delete)\(|(?:api|this\.api)\.\w+\(.*\)\.subscribe", t) is not None
    escribe = re.search(r"\b(crear|guardar|eliminar|desactivar|activar|suspender|asignar|anular|cobrar|registrar|reintentar|descartar)\w*\(", t) is not None
    if llama and escribe and "necesitaInternet" not in t and "cola" not in t.lower() and "registrar(" not in t and "Local(" not in t:
        hallazgos.append(("AVISO", "escribe en el servidor sin «necesitaInternet» ni cola sin conexión"))
    if re.search(r"ngOnInit", t) and "alRefrescar" not in t and ".subscribe(" in t and "effect(" not in t:
        hallazgos.append(("AVISO", "no se recarga sola al volver la red"))
    return hallazgos


# mismo criterio que BOTON_DE_ESCRITURA de frontend/src/app/core/ui/solo-lectura-sin-red.directive.ts (las pantallas del Administrador apagan estos botones sin Internet)
ESCRITURA = re.compile(r"^\s*(\+\s*)?(nuev[oa]s?|crear|editar|guardar|desactivar|activar|eliminar|quitar|suspender|reactivar|asignar|anular|subir|generar|hacer principal|inactivar|retirar|volver a|cancelar (el )?(lote|aviso)|aplicar|restablecer|enviar|confirmar|cambiar (de )?(plan|estado))", re.I)
VERBOS_DE_ESCRITURA = re.compile(r"\((?:click|ngSubmit)\)=\"(?:crear|guardar|eliminar|desactivar|activar|suspender|reactivar|asignar|anular|subir|generar|hacerPrincipal|quitar|inactivar|abrirNuev|cambiarEstado|enviar)\w*\(", re.I)


def revisar_empresa(archivo: Path, hallazgos: list[tuple[str, str]]) -> None:
    """Pantallas del Administrador (/empresa/**): sus botones de escritura deben apagarse sin Internet (directiva global del shell o `necesitaInternet`)."""
    shell = (WEB / "layout" / "shell.component.ts").read_text(encoding="utf-8")
    if "[soloLecturaSinRed]" not in shell or "'Administrador'" not in shell:
        hallazgos.append(("FALLA", "el shell ya no apaga los botones de escritura del Administrador sin Internet"))
        return
    t = archivo.read_text(encoding="utf-8")
    for m in re.finditer(r"<button([^>]*)>([^<]*(?:<[^/][^>]*>[^<]*)*?)</button>", t):
        atributos, texto = m.group(1), re.sub(r"<[^>]+>|\{\{[^}]*\}\}|@\w+[^{]*\{|[{}]", " ", m.group(2)).strip()
        if VERBOS_DE_ESCRITURA.search(atributos) and not ESCRITURA.search(texto) and "necesitaInternet" not in atributos and "permiteSinRed" not in atributos and texto:
            hallazgos.append(("AVISO", f"botón de escritura «{texto[:30]}» no queda cubierto por la regla del shell"))


def auditar_web() -> list[tuple[str, str, str, str]]:
    filas = []
    for raiz, ruta_rutas in ARCHIVO_DE_RUTAS.items():
        archivo = WEB / ruta_rutas
        for path, destino in importaciones(archivo.read_text(encoding="utf-8"), archivo):
            if destino.stem in SOLO_CON_INTERNET:
                continue
            h = revisar_web(destino)
            if raiz in ("empresa", "plataforma"):
                revisar_empresa(destino, h)
            if destino.stem in ACEPTADOS_WEB:
                h = [(n, m) for n, m in h if n == "FALLA"]
            nivel = "FALLA" if any(n == "FALLA" for n, _ in h) else "AVISO" if h else "OK"
            filas.append((ROL_POR_RAIZ[raiz], f"/{raiz}/{path}", nivel, "; ".join(m for _, m in h) or ACEPTADOS_WEB.get(destino.stem) or "carga con lecturas guardadas o copia local; sin «Cargando…» eterno"))
    return filas


def auditar_movil() -> list[tuple[str, str, str]]:
    filas = []
    for archivo in sorted(MOVIL.rglob("*.dart")):
        t = archivo.read_text(encoding="utf-8")
        nombre = archivo.relative_to(MOVIL).as_posix()
        for m in re.finditer(r"CircularProgressIndicator\(", t):
            antes = t[max(0, m.start() - 260):m.start()]
            guardado = re.search(r"_error\s*==\s*null|_cargando|_cargandoOpciones|_mas\b|_camara\s*==\s*null|\.cargando|_filas\s*==\s*null|_conflictos\s*==\s*null|iniciando|child:\s*CircularProgress|CircularProgressIndicator\(\s*strokeWidth|ImagenPrenda|cargando: true|_reservas == null|_compras == null", antes)
            filas.append((nombre, "CircularProgressIndicator", "OK" if guardado or (nombre, "CircularProgressIndicator") in ACEPTADOS_MOVIL else "REVISAR"))
        for m in re.finditer(r"on ApiException(?: catch \((\w+)\))?", t):
            cuerpo = t[m.end():m.end() + 420]
            trata = "sinConexion" in cuerpo or "e.mensaje" in cuerpo or "mensaje" in cuerpo or "// " in cuerpo[:140] or "rethrow" in cuerpo
            filas.append((nombre, "catch ApiException", "OK" if trata or (nombre, "catch ApiException") in ACEPTADOS_MOVIL else "REVISAR"))
    return filas


def escribir(web, movil) -> int:
    fallas = sum(1 for f in web if f[2] == "FALLA") + sum(1 for f in movil if f[2] == "REVISAR")
    avisos = sum(1 for f in web if f[2] == "AVISO")
    L = ["# Auditoría de las funciones sin conexión", "",
         "Generada por `python scripts/auditar_offline.py` (revisión del código; la prueba con el service worker real se hace a mano, ver `PRUEBAS_SISTEMA.md` §17 a §20).", "",
         f"**Resumen:** {len(web)} pantallas web revisadas ({sum(1 for f in web if f[2] == 'OK')} OK, {avisos} con aviso, {sum(1 for f in web if f[2] == 'FALLA')} con falla) · "
         f"{len(movil)} puntos del móvil revisados ({sum(1 for f in movil if f[2] == 'OK')} OK, {sum(1 for f in movil if f[2] == 'REVISAR')} por revisar).", "",
         "## Web: actor × pantalla × resultado", "", "| Actor | Pantalla | Resultado | Detalle |", "|---|---|---|---|"]
    L += [f"| {a} | `{p}` | {n} | {d} |" for a, p, n, d in sorted(web)]
    L += ["", "## Móvil: indicadores de carga y manejo de `ApiException`", "", "| Archivo | Patrón | Resultado |", "|---|---|---|"]
    L += [f"| `{a}` | {p} | {n} |" for a, p, n in movil if n != "OK"] or ["| (todos con salida sin conexión) | | OK |"]
    L += ["", f"Total de puntos del móvil con salida sin conexión: {sum(1 for f in movil if f[2] == 'OK')} de {len(movil)}.", ""]
    INFORME.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Informe escrito en {INFORME.relative_to(RAIZ)}: {fallas} falla(s), {avisos} aviso(s).")
    return fallas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verificar", action="store_true", help="sale con error si queda alguna falla")
    a = ap.parse_args()
    fallas = escribir(auditar_web(), auditar_movil())
    return 1 if a.verificar and fallas else 0


if __name__ == "__main__":
    sys.exit(main())
