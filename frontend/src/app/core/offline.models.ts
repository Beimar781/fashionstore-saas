/** Fase H · operación offline: lo que se guarda en el dispositivo (IndexedDB) y lo que viaja a la API. */
export type EstadoLocal = 'REGISTRADA_LOCAL' | 'ENVIADA' | 'CONFIRMADA' | 'RECHAZADA' | 'EN_CONFLICTO';  // RN11
export type TipoOperacion = 'VENTA_CONTADO' | 'RESERVA';

export interface VarianteLocal {
  id: number; sku: string; codigo_barras: string | null; talla: string; color: string; precio: string; precio_final: string; promocion: string | null; stock: Record<string, number>;
}
export interface ProductoLocal { id: number; empresa_id: number; nombre: string; categoria: string; genero: string; imagen: string | null; variantes: VarianteLocal[]; }
export interface SucursalLocal { id: number; nombre: string; ciudad: string; direccion: string | null; horario: string | null; }
export interface ClienteLocal { id: number; nombre: string; email: string; }
export interface CatalogoDescargado { generado_en: string; empresa_id: number; sucursales: SucursalLocal[]; productos: Omit<ProductoLocal, 'empresa_id'>[]; clientes: ClienteLocal[]; }
export interface MetaCatalogo { generado_en: string; empresa_id: number; sucursales: SucursalLocal[]; clientes: ClienteLocal[]; }

export interface Faltante { variante_id: number; producto: string; talla: string; color: string; solicitadas: number; disponibles: number; }
export interface OperacionLocal {
  id: string;  // UUID generado en el dispositivo (RN11)
  empresa_id: number; sucursal_id: number | null; usuario_id: number;
  tipo: TipoOperacion; payload: Record<string, unknown>; estado: EstadoLocal;
  intentos: number; mensaje: string; referencia: string | null; comprobante: string | null; detalle: { faltantes: Faltante[] } | null;
  creada_en: string; resumen: string;
}

export interface ResultadoSync { id: string; estado: 'CONFIRMADA' | 'RECHAZADA' | 'EN_CONFLICTO' | 'ERROR'; mensaje: string; referencia: string | null; comprobante: string | null; detalle: { faltantes: Faltante[] } | null; ya_procesada: boolean; }
export interface RespuestaSync { resultados: ResultadoSync[]; sincronizado_en: string; }
export interface OperacionServidor {
  id: string; tipo: TipoOperacion; estado: EstadoLocal; mensaje: string; referencia: string | null; comprobante: string | null; detalle: { faltantes: Faltante[] } | null;
  sucursal_id: number; sucursal: string; usuario: string; creada_en: string; procesada_en: string; intentos: number; resolucion: string | null; motivo_resolucion: string | null;
}
