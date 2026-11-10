import { Injectable, effect, inject, untracked } from '@angular/core';
import { AuthService } from '../auth/auth.service';
import { ROL } from '../models';
import { ToastService } from '../ui/toast.service';
import { ColaOperacionesService, ResumenSync } from './cola-operaciones.service';
import { ConnectivityService } from './connectivity.service';

export const MSG_SIN_RED = 'Sin conexión: sus acciones se guardarán en este dispositivo y se enviarán solas al volver la red.';
export const textoReconexion = (pendientes: number) => (pendientes ? `Conexión restablecida. Sincronizando ${pendientes} operaciones…` : 'Conexión restablecida.');
export const textoResumen = (r: ResumenSync) => `Sincronización completa: ${r.confirmadas} confirmadas, ${r.conflictos} en conflicto, ${r.rechazadas} rechazadas`;

/** Dónde ve cada rol el detalle de su cola (el panel de diagnóstico). */
const DETALLE: Record<string, string> = { [ROL.CLIENTE]: '/tienda/offline', [ROL.CAJERO]: '/pos/offline', [ROL.ENCARGADO]: '/sucursal/offline', [ROL.ADMIN]: '/empresa/conflictos' };

/**
 * Avisos globales de conexión (visibles en cualquier pantalla, sin recargar la página):
 * al perder la red, al recuperarla (real o al apagar «Simular sin conexión») y al terminar la sincronización, con «Ver detalle».
 * Si la pestaña está en segundo plano y hay permiso, el mismo texto sale además como notificación del sistema.
 */
@Injectable({ providedIn: 'root' })
export class AvisosConexionService {
  private red = inject(ConnectivityService);
  private cola = inject(ColaOperacionesService);
  private auth = inject(AuthService);
  private toast = inject(ToastService);
  private esperaResumen = false;

  constructor() {
    let antes = this.red.online();
    effect(() => {
      const ahora = this.red.online();
      if (ahora === antes) return;
      antes = ahora;
      untracked(() => (ahora ? this.volvioLaRed() : this.sePerdioLaRed()));
    });
    effect(() => {
      const resumen = this.cola.ultimoResumen();
      if (resumen) untracked(() => this.alSincronizar(resumen));
    });
  }

  private sePerdioLaRed() {
    if (this.auth.autenticado()) this.avisar('warn', MSG_SIN_RED);
  }

  private volvioLaRed() {
    if (!this.auth.autenticado()) return;
    const pendientes = this.cola.pendientes().length;
    this.esperaResumen = pendientes > 0;
    this.avisar('ok', textoReconexion(pendientes));
  }

  /** El resumen solo se anuncia después de una reconexión: una operación hecha con red ya avisa en su propia pantalla. */
  private alSincronizar(r: ResumenSync) {
    if (!this.esperaResumen) return;
    this.esperaResumen = false;
    this.avisar(r.conflictos || r.rechazadas ? 'warn' : 'ok', textoResumen(r), true);
  }

  private avisar(tipo: 'ok' | 'warn', texto: string, conDetalle = false) {
    const ruta = DETALLE[this.auth.rol() ?? ''];
    this.toast.mostrarAviso(tipo, texto, conDetalle && ruta ? { texto: 'Ver detalle', ruta } : undefined);
    this.notificarSiEstaOculta(texto);
  }

  private notificarSiEstaOculta(texto: string) {
    if (!document.hidden || !('Notification' in window) || Notification.permission !== 'granted') return;
    const opciones = { body: texto, icon: 'icons/icon-192.png', tag: 'fs-conexion' };
    const conServiceWorker = navigator.serviceWorker?.ready.then((reg) => reg.showNotification('FashionStore', opciones));
    (conServiceWorker ?? Promise.reject()).catch(() => { try { new Notification('FashionStore', opciones); } catch { /* sin notificaciones: queda el aviso dentro de la app */ } });
  }
}
