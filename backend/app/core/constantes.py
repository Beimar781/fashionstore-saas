"""Constantes de dominio compartidas por todos los paquetes (roles y estados)."""

# Roles (RN10)
SUPERADMIN = "SuperAdministrador"
ADMIN = "Administrador"
ENCARGADO = "Encargado"
CAJERO = "Cajero"
CLIENTE = "Cliente"
PROVEEDOR = "Proveedor"  # portal de proveedores (CU-31): envía avisos de remisión y propuestas de producto
ROLES_INTERNOS = (ADMIN, ENCARGADO, CAJERO)
ROLES_CON_SUCURSAL = (ENCARGADO, CAJERO)

# Estados de empresa y suscripción (RN05)
EMPRESA_ACTIVA = "ACTIVA"
EMPRESA_SUSPENDIDA = "SUSPENDIDA"
EMPRESA_CANCELADA = "CANCELADA"

SUS_ACTIVA = "ACTIVA"
SUS_VENCIDA = "VENCIDA"
SUS_SUSPENDIDA = "SUSPENDIDA"
SUS_CANCELADA = "CANCELADA"

# Formas de pago simuladas (CU-35)
FORMAS_PAGO = ("EFECTIVO", "TRANSFERENCIA", "QR")

# Panel al que se redirige cada rol tras iniciar sesión (CU-02, paso 7)
PANEL_POR_ROL = {
    SUPERADMIN: "plataforma",
    ADMIN: "empresa",
    ENCARGADO: "reservas_sucursal",
    CAJERO: "punto_venta",
    CLIENTE: "catalogo",
    PROVEEDOR: "proveedor",
}

MSG_SUSCRIPCION_NO_VIGENTE = "La suscripción de su empresa no está vigente."
MSG_EMPRESA_INACTIVA = "Empresa inactiva. Contacte al administrador de la plataforma."
MSG_RECURSO_AJENO = "El recurso no pertenece a su empresa."
