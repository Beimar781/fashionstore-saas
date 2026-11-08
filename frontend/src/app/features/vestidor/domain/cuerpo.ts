export interface PuntoCuerpo {
  x: number;
  y: number;
  confianza: number;
}
export interface PoseCuerpo {
  hombroIzq: PuntoCuerpo;
  hombroDer: PuntoCuerpo;
  caderaIzq: PuntoCuerpo;
  caderaDer: PuntoCuerpo;
}

export const umbralConfianza = 0.3;
export type Guia =
  'sinPersona' | 'subeLaCamara' | 'acercate' | 'alejate' | 'ponteDeFrente' | 'bien';
export const mensajesGuia: Record<Guia, string> = {
  sinPersona: 'Ponte frente a la cámara',
  subeLaCamara: 'Sube la cámara hasta que se vean tus hombros',
  acercate: 'Acércate un poco',
  alejate: 'Aléjate un poco',
  ponteDeFrente: 'Ponte de frente a la cámara',
  bien: 'Listo',
};

export function evaluarPose(pose: PoseCuerpo | null, proporcionCuadro = 0.75): Guia {
  if (!pose) return 'sinPersona';
  if (pose.hombroIzq.confianza < umbralConfianza || pose.hombroDer.confianza < umbralConfianza)
    return 'subeLaCamara';
  const ancho = Math.abs(pose.hombroDer.x - pose.hombroIzq.x);
  if (ancho < 0.14) return 'acercate';
  if (ancho > 0.85) return 'alejate';
  if (pose.caderaIzq.confianza >= umbralConfianza && pose.caderaDer.confianza >= umbralConfianza) {
    const torso =
      (pose.caderaIzq.y + pose.caderaDer.y) / 2 - (pose.hombroIzq.y + pose.hombroDer.y) / 2;
    if (torso > 0 && (ancho * proporcionCuadro) / torso < 0.3) return 'ponteDeFrente';
  }
  return 'bien';
}

export class BloqueoPose {
  buenos = 0;
  malos = 0;
  bloqueado = false;
  ultimaGuia: Guia = 'sinPersona';
  constructor(
    readonly cuadrosParaBloquear = 2,
    readonly cuadrosParaSoltar = 8,
    readonly proporcionCuadro = 0.75,
  ) {}
  registrar(pose: PoseCuerpo | null): boolean {
    this.ultimaGuia = evaluarPose(pose, this.proporcionCuadro);
    if (this.ultimaGuia === 'bien') {
      this.malos = 0;
      this.buenos++;
      if (!this.bloqueado && this.buenos >= this.cuadrosParaBloquear) {
        this.bloqueado = true;
        return true;
      }
    } else {
      this.buenos = 0;
      this.malos++;
      if (this.bloqueado && this.malos >= this.cuadrosParaSoltar) this.bloqueado = false;
    }
    return false;
  }
  reiniciar() {
    this.buenos = 0;
    this.malos = 0;
    this.bloqueado = false;
    this.ultimaGuia = 'sinPersona';
  }
}
