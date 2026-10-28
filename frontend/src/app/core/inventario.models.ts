/** Modelos de proveedores, abastecimiento e inventario (Fase B). */

// ---- CU-15 · proveedores ----
export interface Proveedor {
  id: number; razon_social: string; nombre_comercial: string; nit: string | null; email: string | null; telefono: string | null;
  direccion: string; activo: boolean; tiene_acceso: boolean;
}

// ---- CU-31 · abastecimiento ----
export interface VarianteHabilitada { sku: string; producto: string; talla: string; color: string; }
export interface SucursalDestino { id: number; nombre: string; ciudad: string; }
export type EstadoLote = 'EN_TRANSITO' | 'RECIBIDO' | 'CANCELADO';
export interface LoteItem {
  id: number; variante_id: number; sku: string; producto: string; talla: string; color: string; cantidad: number;
  cantidad_recibida: number | null; costo_unitario: string | null;
}
export interface Lote {
  id: number; codigo: string; estado: EstadoLote; proveedor_id: number; proveedor: string; sucursal_id: number; sucursal: string;
  referencia: string; notas: string; creado_en: string; cerrado_en: string | null; total_unidades: number; items: LoteItem[];
}
export type EstadoPropuesta = 'PENDIENTE' | 'APROBADA' | 'RECHAZADA';
export interface Propuesta {
  id: number; proveedor_id: number; proveedor: string; nombre: string; descripcion: string; coleccion_id: number; coleccion: string;
  genero: string; precio_base: string; material: string; estado: EstadoPropuesta; notas_revision: string; creado_en: string;
}
export interface ResumenAbastecimiento { lotes_en_transito: number; propuestas_pendientes: number; }

// ---- CU-20 / CU-26 · inventario ----
export type EstadoExistencia = 'DISPONIBLE' | 'AGOTADA' | 'RESERVADA' | 'VENDIDA' | 'PROXIMA';
export const ESTADOS_EXISTENCIA: { valor: EstadoExistencia; texto: string }[] = [
  { valor: 'DISPONIBLE', texto: 'Disponibles' }, { valor: 'AGOTADA', texto: 'Agotadas' }, { valor: 'RESERVADA', texto: 'Reservadas' },
  { valor: 'VENDIDA', texto: 'Vendidas' }, { valor: 'PROXIMA', texto: 'Próximas a ingresar' },
];
export interface FilaInventario {
  variante_id: number; sku: string; producto_id: number; producto: string; categoria: string; talla: string; color: string;
  disponible: number; reservada: number; vendida: number; proxima: number; umbral_minimo: number | null; bajo_minimo: boolean; agotada: boolean;
}
export interface ResumenInventario { disponibles: number; reservadas: number; vendidas: number; agotadas: number; proximas_a_ingresar: number; }
export interface ResumenSucursal { sucursal_id: number; sucursal: string; disponibles: number; reservadas: number; vendidas: number; }
export interface InventarioPagina {
  resumen: ResumenInventario; por_sucursal: ResumenSucursal[]; total: number; pagina: number; tamano: number; items: FilaInventario[];
}
export interface FiltrosInventario {
  q?: string; categoria_id?: number | null; temporada_id?: number | null; estado?: EstadoExistencia | ''; sucursal?: number | null;
  solo_bajo_minimo?: boolean; pagina?: number; tamano?: number;
}
export interface Existencia { variante_id: number; disponible: number; reservada: number; vendida: number; umbral_minimo: number; }

export const TIPOS_MOVIMIENTO: Record<string, string> = {
  ENTRADA_RECEPCION: 'Recepción de lote', AJUSTE_ENTRADA: 'Ajuste de entrada', AJUSTE_SALIDA: 'Ajuste de salida', RESERVA: 'Reserva',
  LIBERA_RESERVA: 'Reserva liberada', VENTA: 'Venta', VENTA_RESERVA: 'Venta de reserva', DEVOLUCION: 'Devolución',
};
export interface Movimiento {
  id: number; creado_en: string; sucursal_id: number; sucursal: string; variante_id: number; sku: string; producto: string; talla: string;
  color: string; tipo: string; cantidad: number; referencia_tipo: string; referencia_id: number | null; usuario: string | null; nota: string;
}
export interface MovimientosPagina { total: number; pagina: number; tamano: number; items: Movimiento[]; }

// ---- CU-05 · disponibilidad por sucursal ----
export interface VarianteDisponible { variante_id: number; talla: string; color: string; cantidad: number; }
export interface SucursalDisponibilidad {
  sucursal_id: number; sucursal: string; ciudad: string; direccion: string | null; horario: string | null; total: number; disponible: boolean;
  tallas: string[]; colores: string[]; variantes: VarianteDisponible[];
}
export interface Disponibilidad { producto_id: number; producto: string; sucursales: SucursalDisponibilidad[]; }
