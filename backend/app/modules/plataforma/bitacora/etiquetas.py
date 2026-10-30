"""Tabla de etiquetas de la bitácora: cada ruta de escritura (método + ruta) → acción, entidad y un detalle legible en español.

REGLA 16: al crear un endpoint de escritura (POST, PUT, PATCH o DELETE) se agrega aquí su ruta; hay una prueba que falla si falta alguna.
En el detalle, `{campo}` toma el valor de la respuesta, del cuerpo de la petición o de la ruta (en ese orden; `{a.b}` entra en un objeto) y `[ ... ]` es un
trozo opcional que se omite si le falta algún dato. Nunca se usan contraseñas, tokens ni datos de tarjeta.
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Etiqueta:
    metodo: str
    ruta: str  # sin el prefijo /api
    accion: str | None  # None: no se registra (consultas disfrazadas de POST y operaciones sin valor de auditoría)
    entidad: str
    detalle: str
    empresa: str = "usuario"  # de qué empresa es el registro: «usuario» (la del token), «ruta:<param>», «respuesta:<campo>» o «ninguna»
    sesion: str = "token"  # quién la hizo: «token» o «respuesta» (login y registro: el usuario viene en la respuesta) o «visitante»


def E(metodo, ruta, accion, entidad, detalle, **extra) -> Etiqueta:
    return Etiqueta(metodo, ruta, accion, entidad, detalle, **extra)


ETIQUETAS: list[Etiqueta] = [
    # ---- acceso ----
    E("POST", "/auth/login", "LOGIN", "sesión", "Inició sesión", sesion="respuesta", empresa="respuesta:empresa.id"),
    E("POST", "/auth/logout", "LOGOUT", "sesión", "Cerró sesión"),
    E("POST", "/auth/refresh", None, "sesión", ""),
    E("POST", "/auth/registro", "CREAR", "usuario", "Se registró como cliente[: {usuario.nombre} {usuario.apellidos}]", sesion="respuesta", empresa="respuesta:empresa.id"),
    E("POST", "/auth/olvide-password", "RECUPERAR", "usuario", "Pidió restablecer la contraseña[ de {email}]", sesion="visitante", empresa="ninguna"),
    E("POST", "/auth/restablecer-password", "RECUPERAR", "usuario", "Restableció su contraseña con el enlace de recuperación", sesion="visitante", empresa="ninguna"),
    E("POST", "/usuarios", "CREAR", "usuario", "Registró al usuario[ {nombre} {apellidos}][ ({rol})]"),
    E("PUT", "/usuarios/{usuario_id}", "MODIFICAR", "usuario", "Modificó al usuario[ {nombre} {apellidos}]"),
    E("POST", "/usuarios/{usuario_id}/desactivar", "DESACTIVAR", "usuario", "Desactivó al usuario[ {nombre} {apellidos}]"),
    # ---- plataforma (SuperAdministrador) ----
    E("POST", "/plataforma/empresas", "CREAR", "empresa", "Registró la empresa[ {razon_social}][ ({codigo})]", empresa="respuesta:id"),
    E("PUT", "/plataforma/empresas/{empresa_id}", "MODIFICAR", "empresa", "Modificó los datos de la empresa[ {razon_social}]", empresa="ruta:empresa_id"),
    E("DELETE", "/plataforma/empresas/{empresa_id}", "ELIMINAR", "empresa", "Intentó eliminar una empresa", empresa="ruta:empresa_id"),
    E("POST", "/plataforma/empresas/{empresa_id}/suspender", "SUSPENDER", "empresa", "Suspendió la empresa[ {razon_social}]", empresa="ruta:empresa_id"),
    E("POST", "/plataforma/empresas/{empresa_id}/reactivar", "ACTIVAR", "empresa", "Reactivó la empresa[ {razon_social}]", empresa="ruta:empresa_id"),
    E("POST", "/plataforma/empresas/{empresa_id}/suscripciones", "ASIGNAR", "suscripción", "Asignó el plan[ {plan.nombre}] a la empresa", empresa="ruta:empresa_id"),
    E("POST", "/plataforma/empresas/{empresa_id}/suscripcion/suspender", "SUSPENDER", "suscripción", "Suspendió o canceló la suscripción de la empresa", empresa="ruta:empresa_id"),
    E("POST", "/plataforma/planes", "CREAR", "plan", "Creó el plan[ {plan.nombre}]", empresa="ninguna"),
    E("PUT", "/plataforma/planes/{plan_id}", "MODIFICAR", "plan", "Modificó el plan[ {plan.nombre}]", empresa="ninguna"),
    E("POST", "/plataforma/planes/{plan_id}/inactivar", "DESACTIVAR", "plan", "Inactivó el plan[ {nombre}]", empresa="ninguna"),
    # ---- sucursales ----
    E("POST", "/ciudades", "CREAR", "ciudad", "Registró la ciudad[ {nombre}]"),
    E("POST", "/sucursales", "CREAR", "sucursal", "Registró la sucursal[ {nombre}]"),
    E("PUT", "/sucursales/{sucursal_id}", "MODIFICAR", "sucursal", "Modificó la sucursal[ {nombre}]"),
    E("POST", "/sucursales/{sucursal_id}/activar", "ACTIVAR", "sucursal", "Activó la sucursal[ {nombre}]"),
    E("POST", "/sucursales/{sucursal_id}/desactivar", "DESACTIVAR", "sucursal", "Desactivó la sucursal[ {nombre}]"),
    # ---- catálogo ----
    E("POST", "/categorias", "CREAR", "categoría", "Registró la categoría[ {nombre}]"),
    E("PUT", "/categorias/{categoria_id}", "MODIFICAR", "categoría", "Modificó la categoría[ {nombre}]"),
    E("DELETE", "/categorias/{categoria_id}", "ELIMINAR", "categoría", "Eliminó la categoría #{categoria_id}"),
    E("POST", "/grupos-talla", "CREAR", "talla", "Registró el grupo de tallas[ {nombre}]"),
    E("DELETE", "/grupos-talla/{grupo_id}", "ELIMINAR", "talla", "Eliminó el grupo de tallas #{grupo_id}"),
    E("POST", "/tallas", "CREAR", "talla", "Registró la talla[ {codigo}]"),
    E("PUT", "/tallas/{talla_id}", "MODIFICAR", "talla", "Modificó la talla[ {codigo}]"),
    E("DELETE", "/tallas/{talla_id}", "ELIMINAR", "talla", "Eliminó la talla #{talla_id}"),
    E("POST", "/colores", "CREAR", "color", "Registró el color[ {nombre}]"),
    E("PUT", "/colores/{color_id}", "MODIFICAR", "color", "Modificó el color[ {nombre}]"),
    E("DELETE", "/colores/{color_id}", "ELIMINAR", "color", "Eliminó el color #{color_id}"),
    E("POST", "/marcas", "CREAR", "marca", "Registró la marca[ {nombre}]"),
    E("DELETE", "/marcas/{marca_id}", "ELIMINAR", "marca", "Eliminó la marca #{marca_id}"),
    E("POST", "/temporadas", "CREAR", "temporada", "Registró la temporada[ {nombre}]"),
    E("PUT", "/temporadas/{temporada_id}", "MODIFICAR", "temporada", "Modificó la temporada[ {nombre}]"),
    E("DELETE", "/temporadas/{temporada_id}", "ELIMINAR", "temporada", "Eliminó la temporada #{temporada_id}"),
    E("POST", "/colecciones", "CREAR", "colección", "Registró la colección[ {nombre}]"),
    E("PUT", "/colecciones/{coleccion_id}", "MODIFICAR", "colección", "Modificó la colección[ {nombre}]"),
    E("DELETE", "/colecciones/{coleccion_id}", "ELIMINAR", "colección", "Eliminó la colección #{coleccion_id}"),
    E("PUT", "/colecciones/{coleccion_id}/proveedor", "MODIFICAR", "colección", "Cambió el proveedor de la colección #{coleccion_id}"),
    E("POST", "/productos", "CREAR", "producto", "Registró el producto[ {nombre}]"),
    E("PUT", "/productos/{producto_id}", "MODIFICAR", "producto", "Modificó el producto[ {nombre}]"),
    E("POST", "/productos/{producto_id}/activar", "ACTIVAR", "producto", "Activó el producto[ {nombre}]"),
    E("POST", "/productos/{producto_id}/desactivar", "DESACTIVAR", "producto", "Desactivó el producto[ {nombre}]"),
    E("POST", "/productos/{producto_id}/variantes", "CREAR", "producto", "Generó variantes del producto #{producto_id}"),
    E("PUT", "/productos/{producto_id}/variantes/{variante_id}", "MODIFICAR", "producto", "Modificó una variante del producto #{producto_id}"),
    E("POST", "/productos/{producto_id}/imagenes", "CREAR", "producto", "Agregó una imagen al producto #{producto_id}"),
    E("POST", "/productos/{producto_id}/imagenes/{imagen_id}/principal", "MODIFICAR", "producto", "Cambió la imagen principal del producto #{producto_id}"),
    E("DELETE", "/productos/{producto_id}/imagenes/{imagen_id}", "ELIMINAR", "producto", "Quitó una imagen del producto #{producto_id}"),
    E("POST", "/promociones", "CREAR", "promoción", "Registró la promoción[ {nombre}]"),
    E("PUT", "/promociones/{promocion_id}", "MODIFICAR", "promoción", "Modificó la promoción[ {nombre}]"),
    E("DELETE", "/promociones/{promocion_id}", "ELIMINAR", "promoción", "Eliminó la promoción #{promocion_id}"),
    # ---- proveedores y abastecimiento ----
    E("POST", "/proveedores", "CREAR", "proveedor", "Registró al proveedor[ {razon_social}]"),
    E("PUT", "/proveedores/{proveedor_id}", "MODIFICAR", "proveedor", "Modificó al proveedor[ {razon_social}]"),
    E("POST", "/proveedores/{proveedor_id}/activar", "ACTIVAR", "proveedor", "Activó al proveedor[ {razon_social}]"),
    E("POST", "/proveedores/{proveedor_id}/desactivar", "DESACTIVAR", "proveedor", "Desactivó al proveedor[ {razon_social}]"),
    E("POST", "/proveedores/{proveedor_id}/acceso", "CREAR", "proveedor", "Creó el acceso al portal del proveedor #{proveedor_id}"),
    E("POST", "/abastecimiento/lotes", "CREAR", "lote", "Registró el lote de abastecimiento[ {codigo}]"),
    E("POST", "/abastecimiento/lotes/{lote_id}/cancelar", "CANCELAR", "lote", "Canceló el lote[ {codigo}]"),
    E("POST", "/abastecimiento/propuestas", "CREAR", "propuesta", "Envió la propuesta de producto[ {nombre}]"),
    E("POST", "/abastecimiento/propuestas/{propuesta_id}/aprobar", "APROBAR", "propuesta", "Aprobó la propuesta[ {nombre}]"),
    E("POST", "/abastecimiento/propuestas/{propuesta_id}/rechazar", "RECHAZAR", "propuesta", "Rechazó la propuesta[ {nombre}]"),
    # ---- inventario ----
    E("POST", "/inventario/recepciones/{lote_id}/recibir", "RECIBIR", "lote", "Recibió el lote[ {codigo}] en la sucursal"),
    E("POST", "/inventario/sucursal/movimientos", "AJUSTAR", "inventario", "Ajustó el inventario[: {tipo} de {cantidad} unidad(es)]"),
    E("PUT", "/inventario/sucursal/variantes/{variante_id}/umbral", "MODIFICAR", "inventario", "Cambió el umbral mínimo de existencias de la variante #{variante_id}"),
    # ---- vestidor virtual ----
    E("PUT", "/vestidor/productos/{producto_id}/colores/{color_id}", "MODIFICAR", "vestidor", "Subió la imagen del vestidor virtual del producto #{producto_id} (color #{color_id})"),
    E("DELETE", "/vestidor/productos/{producto_id}/colores/{color_id}", "ELIMINAR", "vestidor", "Quitó la imagen del vestidor virtual del producto #{producto_id} (color #{color_id})"),
    # ---- reservas ----
    E("POST", "/reservas", "CREAR", "reserva", "Registró la reserva[ {codigo}]"),
    E("POST", "/reservas/{reserva_id}/cancelar", "CANCELAR", "reserva", "Canceló la reserva[ {codigo}]"),
    E("POST", "/reservas-sucursal/{reserva_id}/preparar", "ATENDER", "reserva", "Preparó la reserva[ {codigo}]"),
    E("POST", "/reservas-sucursal/{reserva_id}/items/{item_id}/no-encontrado", "MODIFICAR", "reserva", "Marcó una prenda como no encontrada en la reserva[ {codigo}]"),
    E("POST", "/atencion-reservas/validar", None, "reserva", ""),
    E("POST", "/atencion-reservas/{reserva_id}/atender", "ATENDER", "reserva", "Atendió al cliente de la reserva[ {codigo}]"),
    E("POST", "/atencion-reservas/{reserva_id}/completar", "ATENDER", "reserva", "Completó la reserva[ {codigo}]"),
    E("POST", "/notificaciones/leer-todas", None, "notificación", ""),
    E("POST", "/notificaciones/{notificacion_id}/leer", None, "notificación", ""),
    E("POST", "/notificaciones/dispositivos", "CREAR", "notificación", "Activó los avisos push en un dispositivo[ ({canal})]"),
    E("POST", "/notificaciones/dispositivos/baja", "DESACTIVAR", "notificación", "Desactivó los avisos push en un dispositivo[ ({canal})]"),
    # ---- carrito, compra y pagos ----
    E("POST", "/carrito/items", "CREAR", "carrito", "Agregó una prenda al carrito"),
    E("PUT", "/carrito/items/{item_id}", "MODIFICAR", "carrito", "Cambió la cantidad de una prenda del carrito"),
    E("DELETE", "/carrito/items/{item_id}", "ELIMINAR", "carrito", "Quitó una prenda del carrito"),
    E("PUT", "/carrito/sucursal", "MODIFICAR", "carrito", "Cambió la sucursal del carrito"),
    E("DELETE", "/carrito", "ELIMINAR", "carrito", "Vació el carrito"),
    E("POST", "/compras/checkout", "CREAR", "pedido", "Confirmó el pedido[ {codigo}][ por Bs {total}]"),
    E("POST", "/pagos/pedidos/{pedido_id}/iniciar", "PAGAR", "pago", "Inició el pago con tarjeta del pedido #{pedido_id}"),
    E("POST", "/pagos/{pago_id}/confirmar", "PAGAR", "pago", "Pagó el pedido[ {pedido.codigo}][ por Bs {pedido.total}] con tarjeta"),
    E("POST", "/pagos/{pago_id}/reconciliar", "PAGAR", "pago", "Verificó el estado del pago[ del pedido {pedido.codigo}]"),
    E("DELETE", "/pagos/tarjetas/{tarjeta_id}", "ELIMINAR", "pago", "Eliminó una tarjeta guardada"),
    # ---- punto de venta y devoluciones ----
    E("POST", "/caja/ventas", "CREAR", "venta", "Registró la venta de caja[ {codigo}][ por Bs {total}]"),
    E("DELETE", "/caja/ventas/{pedido_id}", "CANCELAR", "venta", "Anuló la venta de caja[ {codigo}]"),
    E("POST", "/caja/ventas/{pedido_id}/cobrar", "COBRAR", "venta", "Cobró la venta[ {pedido.codigo}][ por Bs {pedido.total}][ ({pago.metodo})]"),
    E("POST", "/devoluciones", "DEVOLVER", "devolución", "Registró la nota de devolución o cambio[ {numero}][ por Bs {monto_devuelto}]"),
    E("POST", "/devoluciones/diferencia", "PAGAR", "devolución", "Inició el cobro con tarjeta de la diferencia de un cambio"),
    E("PUT", "/devoluciones/configuracion", "MODIFICAR", "devolución", "Cambió el plazo de devolución[ a {plazo_dias} días]"),
    # ---- IA y offline ----
    E("POST", "/ia/reportes", "GENERAR", "reporte", "Generó un reporte con IA[: «{prompt}»]"),
    E("POST", "/asistente/chat", None, "asistente", ""),
    E("POST", "/asistente/interacciones", None, "asistente", ""),
    E("PUT", "/asistente/privacidad", "MODIFICAR", "asistente", "Cambió su preferencia de personalización"),
    E("DELETE", "/asistente/historial", "ELIMINAR", "asistente", "Borró lo que el asistente había aprendido de sus gustos"),
    E("POST", "/offline/sincronizar", "SINCRONIZAR", "operación offline", "Sincronizó[ {n_operaciones}] operación(es) hecha(s) sin conexión"),
    E("POST", "/offline/conflictos/{operacion_id}/resolver", "RESOLVER", "operación offline", "Resolvió un conflicto de sincronización[ ({accion})]"),
]

GENERICA = ("Realizó una operación de escritura en el sistema", "sistema")
_COMPILADAS: list[tuple[Etiqueta, re.Pattern]] = [(e, re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", e.ruta) + "$")) for e in ETIQUETAS]


def buscar(metodo: str, ruta: str) -> tuple[Etiqueta, dict[str, str]] | None:
    """La etiqueta de una ruta de escritura y los valores de sus parámetros de ruta; None si la ruta no tiene etiqueta."""
    ruta = ruta.removeprefix("/api") or "/"
    for etiqueta, patron in _COMPILADAS:
        if etiqueta.metodo == metodo:
            m = patron.match(ruta)
            if m:
                return etiqueta, m.groupdict()
    return None


def _valor(clave: str, *contextos: dict):
    for ctx in contextos:
        actual = ctx
        for parte in clave.split("."):
            actual = actual.get(parte) if isinstance(actual, dict) else None
            if actual is None:
                break
        if actual is not None and not isinstance(actual, (dict, list)) and str(actual).strip():
            return str(actual).strip()
    return None


def construir_detalle(plantilla: str, ruta: dict, cuerpo: dict, respuesta: dict) -> str:
    """Arma el detalle en español con los datos de la respuesta, del cuerpo o de la ruta. Nunca recibe contraseñas ni datos de tarjeta."""
    contextos = (respuesta, cuerpo, ruta)

    def opcional(m: re.Match) -> str:
        faltan = False

        def sustituir(p: re.Match) -> str:
            nonlocal faltan
            v = _valor(p.group(1), *contextos)
            if v is None:
                faltan = True
                return ""
            return v

        texto = re.sub(r"\{([\w.]+)\}", sustituir, m.group(1))
        return "" if faltan else texto

    texto = re.sub(r"\[([^\[\]]*)\]", opcional, plantilla)
    texto = re.sub(r"\{([\w.]+)\}", lambda p: _valor(p.group(1), *contextos) or "", texto)
    return re.sub(r"\s+", " ", texto).strip()[:400]


def resolver_empresa(regla: str, actor_empresa: int | None, ruta: dict, respuesta: dict) -> int | None:
    if regla == "usuario":
        return actor_empresa
    if regla.startswith("ruta:"):
        v = ruta.get(regla[5:])
        return int(v) if v and v.isdigit() else None
    if regla.startswith("respuesta:"):
        v = _valor(regla[10:], respuesta)
        return int(v) if v and v.isdigit() else None
    return None
