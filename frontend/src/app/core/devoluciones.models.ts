import { Pedido } from './compras.models';

/** CU-41 · devoluciones y cambios de prendas. */
export interface ItemDevolucion {
  sentido: 'DEVUELTA' | 'ENTREGADA'; sku: string; producto: string; talla: string; color: string; cantidad: number; precio_final: string; subtotal: string;
}
export interface Devolucion {
  id: number; numero: string; tipo: 'DEVOLUCION' | 'CAMBIO'; motivo: string; comprobante: string | null; pedido_codigo: string; sucursal_id: number; sucursal: string;
  fecha: string; monto_devuelto: string; monto_nuevo: string; reembolso: string; cobro_adicional: string; medio_reembolso: string | null;
  referencia_reembolso: string | null; medio_cobro: string | null; monto_recibido: string | null; cambio_entregado: string | null; tarjeta_cobro: string | null;
  registrada_por: string | null; items: ItemDevolucion[];
}
export interface ItemDevolvible {
  pedido_item_id: number; variante_id: number; sku: string; producto: string; talla: string; color: string; precio_final: string;
  vendida: number; devuelta: number; devolvible: number;
}
export interface VentaDevolvible {
  pedido: Pedido; items: ItemDevolvible[]; medio_pago: string | null; plazo_dias: number; vence_el: string; dentro_del_plazo: boolean; devoluciones: Devolucion[];
}
export interface ConfiguracionDevolucion { plazo_dias: number; }

/** Prenda nueva que el cliente se lleva en un cambio. */
export interface LineaNueva { variante_id: number; producto: string; talla: string; color: string; precio_final: number; cantidad: number; max: number; }
