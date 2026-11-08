import { describe, expect, it } from 'vitest';
import { colocarPrenda } from './anclaje';
import { evaluarPose, PoseCuerpo } from './cuerpo';
import { FiltroOneEuro } from './filtro-one-euro';

const pose = (
  ancho = 0.3,
  yHombros = 0.3,
  yCaderas = 0.62,
  confianza = 0.9,
  confianzaCaderas = 0.9,
): PoseCuerpo => {
  const izq = 0.5 - ancho / 2,
    der = 0.5 + ancho / 2;
  return {
    hombroIzq: { x: izq, y: yHombros, confianza },
    hombroDer: { x: der, y: yHombros, confianza },
    caderaIzq: { x: izq + 0.03, y: yCaderas, confianza: confianzaCaderas },
    caderaDer: { x: der - 0.03, y: yCaderas, confianza: confianzaCaderas },
  };
};

describe('lógica del vestidor compartida con móvil', () => {
  it('Filtro One Euro: una señal constante conserva el valor (caso móvil)', () => {
    const f = new FiltroOneEuro();
    for (let i = 0; i < 20; i++) expect(f.filtrar(0.5, i / 30)).toBeCloseTo(0.5, 9);
  });
  it('Anclaje: pose frontal produce el mismo tamaño que móvil', () => {
    const c = colocarPrenda(
      pose(),
      { y_hombros: 0.1, ancho_hombros: 0.85, y_cadera: 0.92, ajuste: 1 },
      1,
      { width: 300, height: 400 },
      400 / 480,
    );
    expect(c.ancho).toBeCloseTo(114.35, 1);
  });
  it('Guía: la pose frontal es apta (caso móvil)', () => {
    expect(evaluarPose(pose())).toBe('bien');
  });
  it('Guía conserva límite 0.30 del móvil', () => {
    expect(evaluarPose(pose(0.3, 0.3, 0.62, 0.29))).toBe('subeLaCamara');
  });
});
