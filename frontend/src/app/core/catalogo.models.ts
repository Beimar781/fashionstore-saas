/** Modelos del catálogo (Fase A). Los importes llegan como texto con dos decimales («100.00»). */

// ---- CU-16 · categorías, tallas, colores y marcas ----
export interface Categoria { id: number; nombre: string; slug: string; padre_id: number | null; grupo_talla_id: number | null; orden: number; activa: boolean; }
export interface Talla { id: number; grupo_id: number; codigo: string; orden: number; }
export interface GrupoTalla { id: number; nombre: string; descripcion: string | null; tallas: Talla[]; }
export interface ColorCatalogo { id: number; nombre: string; slug: string; codigo: string; codigo_hex: string; }
export interface Marca { id: number; nombre: string; slug: string; }

// ---- CU-17 · temporadas y colecciones ----
export type TipoTemporada = 'PRIMAVERA_VERANO' | 'OTONO_INVIERNO' | 'ESCOLAR' | 'PROMOCIONAL' | 'NUEVA_COLECCION';
export const TIPOS_TEMPORADA: { valor: TipoTemporada; texto: string }[] = [
  { valor: 'PRIMAVERA_VERANO', texto: 'Primavera-Verano' }, { valor: 'OTONO_INVIERNO', texto: 'Otoño-Invierno' },
  { valor: 'ESCOLAR', texto: 'Escolar' }, { valor: 'PROMOCIONAL', texto: 'Promocional' }, { valor: 'NUEVA_COLECCION', texto: 'Nueva colección' },
];
export interface Temporada { id: number; nombre: string; codigo: string; tipo: TipoTemporada; inicio: string; fin: string; activa: boolean; }
export interface Coleccion { id: number; nombre: string; slug: string; temporada_id: number; temporada: string; fecha_lanzamiento: string | null; activa: boolean; }

// ---- CU-18 · productos ----
export type Genero = 'MASCULINO' | 'FEMENINO' | 'UNISEX' | 'NINOS';
export const GENEROS: { valor: Genero; texto: string }[] = [
  { valor: 'MASCULINO', texto: 'Masculino' }, { valor: 'FEMENINO', texto: 'Femenino' }, { valor: 'UNISEX', texto: 'Unisex' }, { valor: 'NINOS', texto: 'Niños' },
];
export interface Variante {
  id: number; sku: string; talla_id: number; talla: string; color_id: number; color: string;
  codigo_barras: string | null; precio_especifico: string | null; precio: string; activa: boolean;
}
export interface ImagenProducto { id: number; color_id: number | null; url: string; texto_alt: string; principal: boolean; orden: number; }
export interface ProductoDetalle {
  id: number; publico_id: string; nombre: string; slug: string; descripcion: string; categoria_id: number; categoria: string;
  marca_id: number | null; marca: string | null; coleccion_id: number; coleccion: string; temporada: string; genero: Genero;
  precio_base: string; material: string; cuidado: string; activo: boolean; variantes: Variante[]; imagenes: ImagenProducto[];
}
export interface ProductoResumen {
  id: number; nombre: string; categoria: string; marca: string | null; coleccion: string; precio_base: string; activo: boolean;
  variantes: number; imagen_principal: string | null;
}
export interface Pagina<T> { total: number; pagina: number; tamano: number; items: T[]; }
export interface VariantesGeneradas { creadas: number; omitidas: number; variantes: Variante[]; }

// ---- CU-19 · promociones ----
export interface Promocion {
  id: number; nombre: string; codigo: string | null; tipo_descuento: 'PORCENTAJE' | 'MONTO'; valor: string; inicia: string; termina: string;
  monto_minimo: string; usos_maximos: number | null; usos: number; activa: boolean; vigente: boolean;
  categorias_ids: number[]; colecciones_ids: number[]; productos_ids: number[];
}

// ---- CU-03 / CU-04 · catálogo del cliente ----
export interface ColorPrenda { id: number; nombre: string; codigo_hex: string; }
export interface Prenda {
  id: number; publico_id: string; nombre: string; slug: string; categoria: string; marca: string | null; genero: Genero; coleccion: string; temporada: string;
  precio: string; precio_final: string; promocion: string | null; imagen: string | null; colores: ColorPrenda[]; tallas: string[]; disponible: boolean;
}
export interface PrendaDetalle extends Prenda {
  descripcion: string; material: string; cuidado: string;
  imagenes: { id: number; color_id: number | null; url: string; texto_alt: string; principal: boolean }[];
}
export interface OpcionTalla { id: number; codigo: string; orden: number; disponible: boolean; }
export interface OpcionColor extends ColorPrenda { disponible: boolean; }
export interface OpcionVariante {
  variante_id: number; sku: string; talla_id: number; talla: string; color_id: number; color: string;
  precio: string; precio_final: string; disponible: boolean; cantidad: number; orden: number;
}
export interface Opciones { producto_id: number; sucursal_id: number | null; tallas: OpcionTalla[]; colores: OpcionColor[]; variantes: OpcionVariante[]; }
export interface SucursalCatalogo { id: number; nombre: string; ciudad: string; direccion: string | null; horario: string | null; }

export interface FiltrosCatalogo {
  q?: string; categoria_id?: number | null; marca_id?: number | null; genero?: Genero | ''; talla?: string; color_id?: number | null;
  precio_min?: number | null; precio_max?: number | null; sucursal?: number | null; solo_disponibles?: boolean;
  orden?: 'recientes' | 'precio_asc' | 'precio_desc' | 'nombre'; pagina?: number; tamano?: number;
}
