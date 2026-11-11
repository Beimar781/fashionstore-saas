from datetime import datetime

from pydantic import BaseModel

from app.core.tipos import Dinero


class SucursalLocalOut(BaseModel):
    id: int
    nombre: str
    ciudad: str
    direccion: str | None
    horario: str | None


class VarianteLocalOut(BaseModel):
    id: int
    sku: str
    codigo_barras: str | None
    talla: str
    color: str
    precio: Dinero
    precio_final: Dinero  # con la promoción vigente al descargar
    promocion: str | None
    talla_id: int
    color_id: int
    color_hex: str
    stock: dict[int, int]  # sucursal → disponibles; el personal recibe solo la de su sucursal


class ProductoLocalOut(BaseModel):
    id: int
    nombre: str
    categoria: str
    genero: str
    imagen: str | None
    publico_id: str
    slug: str
    descripcion: str
    marca: str | None
    coleccion: str
    temporada: str
    material: str
    cuidado: str
    imagenes: list[dict]
    variantes: list[VarianteLocalOut]


class ClienteLocalOut(BaseModel):
    id: int
    nombre: str
    email: str


class ItemReservaLocalOut(BaseModel):
    id: int
    variante_id: int
    producto: str
    talla: str
    color: str
    cantidad: int
    estado: str


class ReservaSucursalLocalOut(BaseModel):
    """Reserva de la sucursal descargada para atenderla o cobrarla sin conexión: el Encargado recibe las activas (B4) y el Cajero solo las que ya se pueden cobrar."""

    id: int
    codigo: str
    cliente: str = ""
    estado: str
    programada_para: datetime
    items: list[ItemReservaLocalOut]


class ItemVentaLocalOut(BaseModel):
    pedido_item_id: int
    producto: str
    talla: str
    color: str
    vendida: int
    devolvible: int
    precio_final: Dinero


class VentaRecienteLocalOut(BaseModel):
    """Venta reciente de la sucursal, dentro del plazo de devolución, para registrar una devolución sin conexión (B3)."""

    comprobante: str
    pagado_en: datetime
    total: Dinero
    vence_el: datetime
    items: list[ItemVentaLocalOut]


class CatalogoLocalOut(BaseModel):
    generado_en: datetime  # RN16: el cliente muestra esta fecha para avisar que la información puede estar desactualizada
    empresa_id: int
    sucursales: list[SucursalLocalOut]
    productos: list[ProductoLocalOut]
    clientes: list[ClienteLocalOut]  # solo para el personal (datos mínimos)
    plazo_devolucion_dias: int | None = None
    reservas_sucursal: list[ReservaSucursalLocalOut] = []
    ventas_recientes: list[VentaRecienteLocalOut] = []
