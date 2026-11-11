/** IVA que ya viene incluido en el precio. Misma fórmula que el servidor (`iva_incluido` de backend/app/core/tipos.py): total × porcentaje ÷ (100 + porcentaje), con redondeo medio hacia arriba al céntimo. */
export const IVA_PORCENTAJE_POR_DEFECTO = 13;

export function ivaIncluido(total: number | string, porcentaje: number = IVA_PORCENTAJE_POR_DEFECTO): string {
  const centimos = Math.round(Number(total) * 100);  // el total llega con dos decimales: se trabaja en enteros
  const divisor = 100 + porcentaje;
  const iva = Math.floor((centimos * porcentaje * 2 + divisor) / (divisor * 2));  // medio hacia arriba, sin errores de coma flotante
  return (iva / 100).toFixed(2);
}
