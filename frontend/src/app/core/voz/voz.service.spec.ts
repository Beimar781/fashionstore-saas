import { describe, expect, it } from 'vitest';
import { textoParaLeer } from './voz.service';

describe('Lectura en voz alta del reporte', () => {
  it('quita los símbolos de formato y separa en frases', () => {
    const frases = textoParaLeer('## Ventas del mes\n| Total | Bs 1200 |\nSe vendieron 40 prendas. La mejor fue la camisa.');
    expect(frases.join(' ')).not.toMatch(/[#|*]/);
    expect(frases).toContain('Se vendieron 40 prendas.');
    expect(frases.join(' ')).toContain('bolivianos 1200');
  });
  it('parte las frases muy largas para que Chrome no corte la lectura', () => {
    const frases = textoParaLeer('palabra '.repeat(80));
    expect(frases.every((f) => f.length <= 181)).toBe(true);
    expect(frases.length).toBeGreaterThan(2);
  });
  it('un texto vacío no genera nada', () => {
    expect(textoParaLeer('  \n ')).toEqual([]);
  });
});
