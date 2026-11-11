import { describe, expect, it } from 'vitest';
import { ivaIncluido } from './iva';

// misma tabla que backend/tests/test_f_iva_y_catalogo.py y movil/test/iva_test.dart (la calcula el servidor)
const TABLA: [string, string][] = [['0.00', '0.00'], ['0.50', '0.06'], ['1.00', '0.12'], ['9.99', '1.15'], ['100.00', '11.50'], ['235.00', '27.04'], ['300.00', '34.51'], ['1250.50', '143.86'], ['8.69', '1.00'], ['4.35', '0.50']];

describe('IVA incluido sin conexión (F)', () => {
  it('coincide con el servidor al céntimo', () => {
    for (const [total, esperado] of TABLA) expect(ivaIncluido(total), total).toBe(esperado);
  });
  it('usa la tasa de la empresa descargada y 13 % si no hay', () => {
    expect(ivaIncluido('113.00')).toBe('13.00');
    expect(ivaIncluido('120.00', 20)).toBe('20.00');
  });
});
