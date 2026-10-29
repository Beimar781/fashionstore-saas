import { Pedido, PagoResumen } from './compras.models';
import { Reserva } from './reservas.models';

/** CU-28 · una prenda (variante) tal como la ve el cajero. */
export interface ProductoCaja {
  variante_id: number; producto_id: number; sku: string; codigo_barras: string | null; producto: string; talla: string; color: string;
  precio: string; precio_final: string; promocion: string | null; disponible: number; imagen: string | null;
}

/** Línea de la pre-factura que arma el cajero antes de registrar la venta. */
export interface LineaVenta { variante_id: number; sku: string; producto: string; talla: string; color: string; precio_final: number; cantidad: number; max: number; }

export interface CobroCaja { pedido: Pedido; pago: PagoResumen; cambio: string; aviso: string | null; }

export type MetodoCaja = 'EFECTIVO' | 'TARJETA';

/** CU-27 · ventas de la sucursal. */
export interface TotalCanal { ventas: number; unidades: number; total: string; }
export interface CierreMetodo { metodo: string; cobros: number; total: string; recibido: string | null; cambio: string | null; }
export interface DevolucionesDia {
  notas: number; devuelto: string; entregado_en_cambios: string; reembolsado_efectivo: string; reembolsado_tarjeta: string;
  cobrado_efectivo: string; cobrado_tarjeta: string;
}
export interface ResumenDia {
  fecha: string; sucursal_id: number; sucursal: string; total_vendido: string; ventas_netas: string; devoluciones: DevolucionesDia; ventas: number; unidades: number; ticket_promedio: string;
  presencial: TotalCanal; digital: TotalCanal; cierre_de_caja: CierreMetodo[]; efectivo_en_caja: string; reservas_completadas: number;
}
export interface Ticket {
  id: number; codigo: string; comprobante_numero: string | null; comprobante_tipo: string | null; fecha: string; canal: string;
  cliente: string | null; vendedor: string | null; metodo: string | null; unidades: number; total: string;
}
export interface VentasSucursal { desde: string; hasta: string; total: string; tickets: Ticket[]; }

export type ReservaCaja = Reserva;
