"""Catálogo de las acciones de la bitácora: texto legible en español y color de la etiqueta.
Verde: inicios de sesión, altas aprobadas y activaciones; gris: cierres de sesión y desactivaciones; rojo: intentos fallidos, rechazos, cancelaciones y eliminaciones;
azul: altas y operaciones normales; ámbar: modificaciones y ajustes; morado: dinero (pagos, cobros y devoluciones)."""

# código → (texto que se muestra, color)
ACCIONES: dict[str, tuple[str, str]] = {
    "LOGIN": ("Inicio de sesión", "verde"),
    "LOGIN_FALLIDO": ("Inicio de sesión fallido", "rojo"),
    "LOGOUT": ("Cierre de sesión", "gris"),
    "RECUPERAR": ("Recuperación de contraseña", "gris"),
    "CREAR": ("Crear", "azul"),
    "MODIFICAR": ("Modificar", "ambar"),
    "ELIMINAR": ("Eliminar", "rojo"),
    "ACTIVAR": ("Activar", "verde"),
    "DESACTIVAR": ("Desactivar", "gris"),
    "SUSPENDER": ("Suspender", "rojo"),
    "ASIGNAR": ("Asignar plan", "verde"),
    "APROBAR": ("Aprobar", "verde"),
    "RECHAZAR": ("Rechazar", "rojo"),
    "CANCELAR": ("Cancelar", "rojo"),
    "ATENDER": ("Atender", "azul"),
    "RECIBIR": ("Recibir", "azul"),
    "AJUSTAR": ("Ajustar inventario", "ambar"),
    "PAGAR": ("Pagar", "morado"),
    "COBRAR": ("Cobrar", "morado"),
    "DEVOLVER": ("Devolver o cambiar", "morado"),
    "SINCRONIZAR": ("Sincronizar", "azul"),
    "RESOLVER": ("Resolver conflicto", "ambar"),
    "GENERAR": ("Generar", "azul"),
}


def texto_de(accion: str) -> str:
    return ACCIONES.get(accion, (accion.replace("_", " ").capitalize(), "azul"))[0]


def tono_de(accion: str) -> str:
    return ACCIONES.get(accion, ("", "azul"))[1]
