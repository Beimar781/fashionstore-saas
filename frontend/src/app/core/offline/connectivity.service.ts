import { Injectable, computed, signal } from '@angular/core';

const CLAVE_SIMULACION = 'fs.simular_sin_conexion';

/** Estado de conectividad del navegador (PWA). Alimenta el aviso "sin conexión".
 *  «Simular sin conexión» (§B11) fuerza el modo sin conexión aunque haya Internet: sirve para demostrar el offline sin apagar el WiFi. */
@Injectable({ providedIn: 'root' })
export class ConnectivityService {
  private readonly real = signal(navigator.onLine);
  readonly simulado = signal(this.leerSimulacion());
  readonly online = computed(() => this.real() && !this.simulado());

  constructor() {
    window.addEventListener('online', () => this.real.set(true));
    window.addEventListener('offline', () => this.real.set(false));
  }

  /** Al apagar la simulación `online` vuelve a ser true y la cola se sincroniza sola. */
  simular(valor: boolean) {
    this.simulado.set(valor);
    try { valor ? localStorage.setItem(CLAVE_SIMULACION, '1') : localStorage.removeItem(CLAVE_SIMULACION); } catch { /* sin almacenamiento: queda solo en memoria */ }
  }

  private leerSimulacion(): boolean {
    try { return localStorage.getItem(CLAVE_SIMULACION) === '1'; } catch { return false; }
  }
}
