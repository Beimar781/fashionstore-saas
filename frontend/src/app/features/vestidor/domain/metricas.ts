export class MedidorRendimiento {
  static readonly metaFps = 15;
  static readonly metaPrendaMs = 1000;
  private cuadros: number[] = [];
  private latencias: number[] = [];
  private primerCuadro: number | null = null;
  prendaVisibleMs: number | null = null;
  constructor(private reloj: () => number = () => Date.now()) {}
  registrarCuadro(latenciaMs: number) {
    const ahora = this.reloj();
    this.primerCuadro ??= ahora - latenciaMs;
    this.cuadros.push(ahora);
    this.cuadros = this.cuadros.filter((t) => ahora - t <= 1000);
    this.latencias.push(latenciaMs);
    if (this.latencias.length > 30) this.latencias.shift();
  }
  registrarFrame() {
    const ahora = this.reloj();
    this.cuadros.push(ahora);
    this.cuadros = this.cuadros.filter((t) => ahora - t <= 1000);
  }
  marcarPrendaVisible() {
    if (this.primerCuadro !== null) this.prendaVisibleMs ??= this.reloj() - this.primerCuadro;
  }
  get fps() {
    return this.cuadros.length;
  }
  get latenciaMs() {
    return this.latencias.length
      ? this.latencias.reduce((a, b) => a + b, 0) / this.latencias.length
      : 0;
  }
  get cumpleFps() {
    return this.fps >= MedidorRendimiento.metaFps;
  }
  get cumplePrenda() {
    return this.prendaVisibleMs !== null && this.prendaVisibleMs < MedidorRendimiento.metaPrendaMs;
  }
  reiniciar() {
    this.cuadros = [];
    this.latencias = [];
    this.primerCuadro = null;
    this.prendaVisibleMs = null;
  }
}
