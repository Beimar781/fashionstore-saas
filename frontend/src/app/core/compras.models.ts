export type EstadoItemCarrito = 'OK' | 'SIN_STOCK' | 'RETIRADA';
export interface ItemCarrito {
  id: number; variante_id: number; producto_id: number; sku: string; producto: string; talla: string; color: string; imagen: string | null;
  cantidad: number; precio: string; precio_final: string; subtotal: string; disponible: number; estado: EstadoItemCarrito;
}
export interface Carrito {
  sucursal_id: number | null; sucursal: string | null; items: ItemCarrito[]; total_unidades: number; subtotal: string; descuento: string;
  iva_incluido: string; total: string; puede_pagar: boolean; avisos: string[];
}

export type EstadoPedido = 'PENDIENTE_PAGO' | 'PENDIENTE_CONFIRMACION' | 'PAGADO' | 'CANCELADO';
export interface ItemPedido { id: number; variante_id: number; sku: string; producto: string; talla: string; color: string; cantidad: number; precio_unitario: string; precio_final: string; subtotal: string; }
export interface PagoResumen {
  id: number; estado: string; metodo: string; proveedor: string; monto: string; tarjeta_marca: string; tarjeta_ultimos4: string; mensaje: string; motivo: string; creado_en: string;
}
export interface Pedido {
  id: number; codigo: string; estado: EstadoPedido; canal: string; tipo_entrega: string; direccion_entrega: string; nit_ci: string; razon_social: string;
  sucursal_id: number; sucursal: string; subtotal: string; descuento: string; iva_incluido: string; total: string; moneda: string; total_unidades: number;
  comprobante_numero: string | null; creado_en: string; pagado_en: string | null; items: ItemPedido[]; pagos: PagoResumen[];
}
export interface CompraResumen { id: number; codigo: string; fecha: string; sucursal: string; canal: string; estado: EstadoPedido; total: string; total_unidades: number; comprobante_numero: string | null; }
export interface Historial { compras: CompraResumen[]; mensaje: string | null; }

export interface TarjetaPrueba { numero: string; marca: string; resultado: string; }
export interface ConfigPago { modo: 'stripe' | 'simulado'; publishable_key: string | null; tarjetas_prueba: TarjetaPrueba[]; moneda_pasarela: string; tasa_bob_por_usd: number; }
export interface TarjetaGuardada { id: number; marca: string; ultimos4: string; exp_mes: number; exp_anio: number; }
export interface IniciarPago {
  pago_id: number; modo: 'stripe' | 'simulado'; publishable_key: string | null; client_secret: string | null; monto: string; moneda: string;
  monto_pasarela: number; moneda_pasarela: string; tarjeta_guardada: TarjetaGuardada | null;
}
export interface TarjetaSimulada { numero: string; mes: number; anio: number; cvc: string; titular: string; }
export interface ResultadoPago { aprobado: boolean; pendiente: boolean; mensaje: string; pago: PagoResumen; pedido: Pedido; }

export const TEXTO_ESTADO_PEDIDO: Record<EstadoPedido, string> = {
  PENDIENTE_PAGO: 'Pendiente de pago', PENDIENTE_CONFIRMACION: 'Pendiente de confirmación', PAGADO: 'Pagado', CANCELADO: 'Cancelado',
};
export const CLASE_ESTADO_PEDIDO: Record<EstadoPedido, string> = { PENDIENTE_PAGO: 'warn', PENDIENTE_CONFIRMACION: 'warn', PAGADO: 'ok', CANCELADO: 'danger' };
