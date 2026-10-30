/** CU-06 · vestidor virtual: el recurso AR (PNG con fondo transparente) de cada prenda superior por color. */
export interface Anclaje { y_hombros: number; ancho_hombros: number; y_cadera: number; ajuste: number; }
export interface ColorVestidor {
  color_id: number; color: string; codigo_hex: string; listo: boolean; imagen_url: string | null; ancho: number | null; alto: number | null; anclaje: Anclaje | null;
}
export interface VestidorProducto {
  producto_id: number; producto: string; admite: boolean; mensaje: string | null; colores: ColorVestidor[]; escala_tallas: Record<string, number>;
}
export const ANCLAJE_POR_DEFECTO: Anclaje = { y_hombros: 0.10, ancho_hombros: 0.85, y_cadera: 0.92, ajuste: 1.0 };
