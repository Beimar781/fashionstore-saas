import { PoseCuerpo } from './cuerpo';

export class FiltroOneEuro {
  private previo: number | null = null;
  private derivadaPrevia = 0;
  private instantePrevio: number | null = null;
  constructor(
    readonly frecuenciaMinima = 1.35,
    readonly beta = 0.02,
    readonly frecuenciaDerivada = 1.0,
  ) {}
  private alfa(corte: number, dt: number) {
    const tau = 1 / (2 * Math.PI * corte);
    return 1 / (1 + tau / dt);
  }
  filtrar(valor: number, instante: number): number {
    if (this.previo === null || this.instantePrevio === null || instante <= this.instantePrevio) {
      this.previo = valor;
      this.instantePrevio = instante;
      return valor;
    }
    const dt = instante - this.instantePrevio,
      derivada = (valor - this.previo) / dt;
    const derivadaSuave =
      this.derivadaPrevia +
      this.alfa(this.frecuenciaDerivada, dt) * (derivada - this.derivadaPrevia);
    const corte = this.frecuenciaMinima + this.beta * Math.abs(derivadaSuave);
    const suave = this.previo + this.alfa(corte, dt) * (valor - this.previo);
    this.previo = suave;
    this.derivadaPrevia = derivadaSuave;
    this.instantePrevio = instante;
    return suave;
  }
  reiniciar() {
    this.previo = null;
    this.instantePrevio = null;
    this.derivadaPrevia = 0;
  }
}

export class FiltroPose {
  private x = Array.from({ length: 4 }, () => new FiltroOneEuro());
  private y = Array.from({ length: 4 }, () => new FiltroOneEuro());
  filtrar(p: PoseCuerpo, t: number): PoseCuerpo {
    const puntos = [p.hombroIzq, p.hombroDer, p.caderaIzq, p.caderaDer].map((v, i) => ({
      x: this.x[i].filtrar(v.x, t),
      y: this.y[i].filtrar(v.y, t),
      confianza: v.confianza,
    }));
    return {
      hombroIzq: puntos[0],
      hombroDer: puntos[1],
      caderaIzq: puntos[2],
      caderaDer: puntos[3],
    };
  }
  reiniciar() {
    [...this.x, ...this.y].forEach((f) => f.reiniciar());
  }
}
