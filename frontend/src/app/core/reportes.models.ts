import { Prenda } from './catalogo.models';

/** CU-21 · reportes de ventas, reservas y pagos. */
export interface TotalesVentas {
  ventas: number; unidades: number; total_bruto: string; devoluciones: number; devuelto: string; entregado_en_cambios: string; ventas_netas: string; ticket_promedio: string;
}
export interface PuntoDia { fecha: string; ventas: number; total: string; }
export interface ProductoVendido { producto: string; unidades: number; ingresos: string; }
export interface VentasReporte {
  desde: string; hasta: string; sucursal_id: number | null; canal: string | null; totales: TotalesVentas;
  por_canal: { canal: string; ventas: number; unidades: number; total: string }[];
  por_sucursal: { sucursal_id: number; sucursal: string; ventas: number; total: string }[];
  por_dia: PuntoDia[]; por_metodo: { metodo: string; cobros: number; total: string }[];
  mas_vendidos: ProductoVendido[]; menos_vendidos: ProductoVendido[];
}
export interface ReservasReporte {
  desde: string; hasta: string; total: number; completadas: number; conversion: number;
  por_estado: { estado: string; cantidad: number }[]; por_sucursal: { sucursal_id: number; sucursal: string; reservas: number; completadas: number }[];
  por_dia: { fecha: string; reservas: number; completadas: number }[];
}
export interface ResumenPago { cantidad: number; monto: string; }
export interface PagosReporte {
  desde: string; hasta: string; aprobados: ResumenPago; rechazados: ResumenPago; pendientes_confirmacion: ResumenPago;
  por_metodo: { metodo: string; estado: string; cantidad: number; monto: string }[];
  con_problemas: { id: number; pedido: string; sucursal: string; metodo: string; estado: string; monto: string; motivo: string; tarjeta: string; fecha: string }[];
}
export interface FiltroReporte { desde?: string; hasta?: string; sucursal?: number | null; canal?: string; }

/** CU-22 · indicadores empresariales. */
export interface Indicador { valor: number; anterior: number; variacion: number | null; }
export interface Indicadores {
  dias: number; desde: string; hasta: string; ventas_netas: Indicador; ventas: Indicador; ticket_promedio: Indicador; reservas: Indicador; conversion_reservas: Indicador;
  stock: { disponibles: number; reservadas: number; vendidas: number; stock_bajo: number; agotadas: number }; productos_activos: number;
  ventas_por_dia: PuntoDia[]; por_canal: { canal: string; ventas: number; unidades: number; total: string }[];
  por_sucursal: { sucursal_id: number; sucursal: string; ventas: number; total: string }[]; reservas_por_estado: { estado: string; cantidad: number }[];
  mas_vendidos: ProductoVendido[]; stock_bajo_items: { sucursal: string; producto: string; sku: string; disponible: number; umbral: number }[];
  ultimas_ventas: { id: number; codigo: string; comprobante: string | null; sucursal: string; canal: string; total: string; fecha: string }[];
}

/** CU-23 · reportes generativos. */
export interface ReporteGenerativo { id: number; prompt: string; origen: 'IA' | 'REGLAS'; especificacion: Record<string, unknown>; texto: string; datos: Record<string, unknown>; creado_en: string; }

/** CU-42 · analítica con ML. */
export interface Analitica {
  sucursal_id: number | null; desde: string; hasta: string; semanas_historia: number; semanas_proyeccion: number;
  rotacion: { producto: string; unidades_30d: number; stock: number; tasa_diaria: number; clase: 'ALTA' | 'MEDIA' | 'BAJA' }[];
  pronostico: { producto: string; semanas_con_ventas: number; historial: number[]; proyeccion: number[]; tendencia: 'SUBE' | 'ESTABLE' | 'BAJA'; r2: number; stock: number; recomendacion: string }[];
  serie_total: { semana_inicio: string; unidades: number; proyectada: boolean }[]; sin_historial_suficiente: number; mensaje: string | null; modelos: Record<string, string>;
}

/** CU-36 · plan, límites y uso. */
export interface MiPlan {
  plan: { id: number; nombre: string; descripcion: string | null; precio: string; periodicidad: string } | null;
  vigencia: { estado: string; fecha_inicio: string; fecha_vencimiento: string; dias_restantes: number | null; vigente: boolean } | null;
  limites: { clave: string; etiqueta: string; usado: number; limite: number | null; porcentaje: number | null; alcanzado: boolean }[];
  consumo: { clave: string; etiqueta: string; valor: number }[];
  funcionalidades: { clave: string; etiqueta: string; incluida: boolean }[];
  alertas: string[];
}

/** CU-07 · asistente y recomendador. */
export interface MensajeChat { rol: 'usuario' | 'asistente'; texto: string; productos?: Prenda[]; sugerencias?: string[]; }
export interface RespuestaChat { respuesta: string; productos: Prenda[]; sugerencias: string[]; filtros: Record<string, unknown>; origen: 'IA' | 'REGLAS'; }
export interface Recomendaciones { motivo: string; personalizada: boolean; productos: Prenda[]; motivos: Record<number, string>; ofertas: Prenda[]; origen: 'IA' | 'REGLAS'; }
export interface Outfit { base: Prenda | null; prendas: Prenda[]; motivo: string; motivos: Record<number, string>; origen: 'IA' | 'REGLAS'; }
export interface Privacidad { personalizar: boolean; interacciones: number; }
export interface InteraccionCliente { tipo: 'BUSQUEDA' | 'VISTA'; texto?: string | null; producto_id?: number | null; categoria_id?: number | null; color_id?: number | null; talla?: string | null; precio_max?: number | null; }
