import { PoseCuerpo } from './cuerpo';
export interface Anclaje {
  y_hombros: number;
  ancho_hombros: number;
  y_cadera: number;
  ajuste: number;
}
export interface Colocacion {
  centroX: number;
  centroY: number;
  ancho: number;
  alto: number;
  angulo: number;
}
export const pesoDelTorso = 0.35;

export function colocarPrenda(
  pose: PoseCuerpo,
  anclaje: Anclaje,
  escalaTalla: number,
  area: { width: number; height: number },
  proporcionPng: number,
  umbralCadera = 0.3,
): Colocacion {
  const izq = pose.hombroIzq.x <= pose.hombroDer.x ? pose.hombroIzq : pose.hombroDer;
  const der = izq === pose.hombroIzq ? pose.hombroDer : pose.hombroIzq;
  const ax = izq.x * area.width,
    ay = izq.y * area.height,
    bx = der.x * area.width,
    by = der.y * area.height;
  const medioX = (ax + bx) / 2,
    medioY = (ay + by) / 2,
    anchoHombros = Math.hypot(bx - ax, by - ay);
  const angulo = Math.atan2(by - ay, bx - ax);
  let ancho = anchoHombros / anclaje.ancho_hombros;
  if (pose.caderaIzq.confianza >= umbralCadera && pose.caderaDer.confianza >= umbralCadera) {
    const cx = ((pose.caderaIzq.x + pose.caderaDer.x) / 2) * area.width,
      cy = ((pose.caderaIzq.y + pose.caderaDer.y) / 2) * area.height;
    const torso = Math.hypot(cx - medioX, cy - medioY),
      tramo = anclaje.y_cadera - anclaje.y_hombros;
    if (torso > 0 && tramo > 0) {
      const anchoPorTorso = (torso / tramo) * proporcionPng;
      ancho = ancho * (1 - pesoDelTorso) + anchoPorTorso * pesoDelTorso;
    }
  }
  ancho *= anclaje.ajuste * escalaTalla;
  const alto = ancho / proporcionPng,
    bajada = (0.5 - anclaje.y_hombros) * alto;
  return {
    centroX: medioX - Math.sin(angulo) * bajada,
    centroY: medioY + Math.cos(angulo) * bajada,
    ancho,
    alto,
    angulo,
  };
}
