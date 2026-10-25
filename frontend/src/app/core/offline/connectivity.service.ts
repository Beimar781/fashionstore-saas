import { Injectable, signal } from '@angular/core';

/** Estado de conectividad del navegador (PWA). Alimenta el aviso "sin conexión". */
@Injectable({ providedIn: 'root' })
export class ConnectivityService {
  readonly online = signal(navigator.onLine);
  constructor() {
    window.addEventListener('online', () => this.online.set(true));
    window.addEventListener('offline', () => this.online.set(false));
  }
}
