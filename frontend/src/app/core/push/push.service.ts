import { Injectable, inject, signal } from '@angular/core';
import { SwPush } from '@angular/service-worker';
import { firstValueFrom } from 'rxjs';
import { ReservasApi } from '../api/reservas.api';

const K_TOKEN = 'fs.push.token', K_PREFERENCIA = 'fs.push.activo';
export type ResultadoPush = 'activo' | 'simulado' | 'denegado' | 'error';

/** RF11 · Avisos push en el navegador (regla 17). Con claves VAPID en el servidor y el service worker activo se usa Web Push de verdad;
 *  si no, se registra una suscripción simulada para que el servidor deje el aviso anotado (modo simulado) y la campana siga funcionando. */
@Injectable({ providedIn: 'root' })
export class PushService {
  private api = inject(ReservasApi);
  private sw = inject(SwPush);

  readonly activo = signal(this.preferencia());
  readonly simulado = signal(false);

  async activar(): Promise<ResultadoPush> {
    try {
      const cfg = await firstValueFrom(this.api.configPush());
      const real = !!cfg.vapid_public_key && this.sw.isEnabled;
      const token = real ? JSON.stringify((await this.sw.requestSubscription({ serverPublicKey: cfg.vapid_public_key })).toJSON()) : this.suscripcionSimulada();
      await firstValueFrom(this.api.registrarDispositivo('WEB', token));
      this.guardar(token, true);
      this.simulado.set(!real);
      return real ? 'activo' : 'simulado';
    } catch {
      return typeof Notification !== 'undefined' && Notification.permission === 'denied' ? 'denegado' : 'error';
    }
  }

  /** El usuario apaga los avisos de este navegador: no se vuelven a activar solos al iniciar sesión. */
  async desactivar(): Promise<void> {
    await this.baja();
    try { localStorage.setItem(K_PREFERENCIA, '0'); } catch { /* sin almacenamiento */ }
    this.activo.set(false);
  }

  /** Al iniciar sesión: si el usuario ya había activado los avisos en este navegador, se registra de nuevo para su cuenta;
   *  al Cliente que nunca eligió se le pide el permiso la primera vez. */
  async reanudar(pedirPermiso = false): Promise<void> {
    if (this.preferencia() || (pedirPermiso && this.nuncaElegido())) await this.activar();
  }

  /** Al cerrar sesión: este navegador deja de recibir los avisos de esa cuenta (la preferencia se conserva). */
  async baja(): Promise<void> {
    const token = this.tokenGuardado();
    if (!token) return;
    try { await firstValueFrom(this.api.quitarDispositivo('WEB', token)); } catch { /* sin conexión: el servidor dejará de usarlo cuando el navegador lo rechace */ }
  }

  private suscripcionSimulada(): string {
    const previo = this.tokenGuardado();
    if (previo?.includes('simulado.local')) return previo;
    return JSON.stringify({ endpoint: `https://simulado.local/${crypto.randomUUID()}`, keys: { p256dh: 'simulado', auth: 'simulado' } });
  }

  private guardar(token: string, activo: boolean) {
    try { localStorage.setItem(K_TOKEN, token); localStorage.setItem(K_PREFERENCIA, activo ? '1' : '0'); } catch { /* sin almacenamiento */ }
    this.activo.set(activo);
  }
  private tokenGuardado(): string | null { try { return localStorage.getItem(K_TOKEN); } catch { return null; } }
  private nuncaElegido(): boolean { try { return localStorage.getItem(K_PREFERENCIA) === null; } catch { return false; } }
  private preferencia(): boolean { try { return localStorage.getItem(K_PREFERENCIA) === '1'; } catch { return false; } }
}
