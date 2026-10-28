export type EstadoReserva = 'PENDIENTE' | 'PREPARADA' | 'EN_PROBADOR' | 'COMPLETADA' | 'CANCELADA' | 'EXPIRADA';

export interface ItemReserva { id: number; variante_id: number; sku: string; producto: string; talla: string; color: string; cantidad: number; estado: 'RESERVADO' | 'NO_ENCONTRADO' | 'VENDIDO' | 'LIBERADO'; }
export interface Reserva {
  id: number; codigo: string; estado: EstadoReserva; sucursal_id: number; sucursal: string; cliente_id: number; cliente: string;
  programada_para: string; vence_en: string; notas: string; creada_en: string; total_unidades: number; puede_cancelar: boolean; items: ItemReserva[];
}
export interface AtencionRespuesta { reserva: Reserva; habilita_venta: boolean; }

export interface Notificacion {
  id: number; tipo: string; titulo: string; mensaje: string; sucursal_id: number | null; referencia_tipo: string; referencia_id: number | null; leida: boolean; creada_en: string;
}

export const TEXTO_ESTADO_RESERVA: Record<EstadoReserva, string> = {
  PENDIENTE: 'Pendiente', PREPARADA: 'Preparada', EN_PROBADOR: 'En probador', COMPLETADA: 'Completada', CANCELADA: 'Cancelada', EXPIRADA: 'Expirada',
};
/** Clase de la etiqueta (badge) de cada estado. */
export const CLASE_ESTADO_RESERVA: Record<EstadoReserva, string> = {
  PENDIENTE: 'warn', PREPARADA: 'accent', EN_PROBADOR: 'accent', COMPLETADA: 'ok', CANCELADA: 'danger', EXPIRADA: '',
};
export const TEXTO_ESTADO_ITEM: Record<string, string> = { RESERVADO: 'Apartada', NO_ENCONTRADO: 'No encontrada', VENDIDO: 'Vendida', LIBERADO: 'Liberada' };

/** Prenda elegida por el cliente antes de confirmar la reserva (se guarda en el navegador). */
export interface PrendaElegida { variante_id: number; sku: string; producto: string; talla: string; color: string; cantidad: number; max: number; }
