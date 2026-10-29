import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { OfflineApi } from '../api/offline.api';
import { AuthService } from '../auth/auth.service';
import { OperacionLocal, OperacionServidor, TipoOperacion } from '../offline.models';
import { ConnectivityService } from './connectivity.service';
import { LocalDbService } from './local-db.service';

const REINTENTO_MS = 30_000;

/**
 * Cola de operaciones sin conexión (CU-38 y CU-39).
 * - Cada operación nace con un UUID generado aquí (RN11) y se guarda en IndexedDB: sobrevive al cierre del navegador (RNF03).
 * - Al sincronizar pasa a ENVIADA y NO se borra hasta que el servidor la confirme o rechace (RN12). Si falla la comunicación, vuelve a REGISTRADA_LOCAL y se reintenta (RNF06).
 * - Reenviar una operación ya confirmada no la duplica: el servidor devuelve el resultado original (RNF05).
 */
@Injectable({ providedIn: 'root' })
export class ColaOperacionesService {
  private api = inject(OfflineApi);
  private db = inject(LocalDbService);
  private auth = inject(AuthService);
  private red = inject(ConnectivityService);

  readonly operaciones = signal<OperacionLocal[]>([]);
  readonly sincronizando = signal(false);
  readonly errorSync = signal('');
  readonly ultimaSync = signal<string | null>(null);
  readonly pendientes = computed(() => this.operaciones().filter((o) => o.estado === 'REGISTRADA_LOCAL' || o.estado === 'ENVIADA'));
  readonly enConflicto = computed(() => this.operaciones().filter((o) => o.estado === 'EN_CONFLICTO'));

  constructor() {
    void this.cargar();
    // al volver la conexión se sincroniza solo, y mientras haya pendientes se reintenta cada 30 segundos
    effect(() => { if (this.red.online() && this.auth.autenticado()) void this.sincronizar(); });
    setInterval(() => { if (this.red.online() && this.auth.autenticado() && this.pendientes().length) void this.sincronizar(); }, REINTENTO_MS);
  }

  async cargar() {
    const s = this.auth.sesion();
    const todas = await this.db.operaciones();
    this.operaciones.set(todas.filter((o) => o.usuario_id === s?.usuario.id && o.empresa_id === s?.empresa?.id).sort((a, b) => b.creada_en.localeCompare(a.creada_en)));
    this.ultimaSync.set((await this.db.ultimaSincronizacion()) ?? null);
  }

  /** Registra una operación en el dispositivo (estado REGISTRADA_LOCAL) y, si hay conexión, la sincroniza enseguida. */
  async registrar(tipo: TipoOperacion, payload: Record<string, unknown>, sucursalId: number | null, resumen: string): Promise<OperacionLocal> {
    const s = this.auth.sesion()!;
    const op: OperacionLocal = {
      id: crypto.randomUUID(), empresa_id: s.empresa!.id, sucursal_id: sucursalId, usuario_id: s.usuario.id, tipo, payload, estado: 'REGISTRADA_LOCAL',
      intentos: 0, mensaje: '', referencia: null, comprobante: null, detalle: null, creada_en: new Date().toISOString(), resumen,
    };
    await this.db.guardarOperacion(op);
    this.operaciones.update((l) => [op, ...l]);
    if (this.red.online()) void this.sincronizar();
    return op;
  }

  async sincronizar(): Promise<void> {
    if (this.sincronizando() || !this.red.online()) return;
    const lote = this.operaciones().filter((o) => o.estado === 'REGISTRADA_LOCAL' || o.estado === 'ENVIADA').sort((a, b) => a.creada_en.localeCompare(b.creada_en));
    if (!lote.length) { await this.refrescarEstados(); return; }
    this.sincronizando.set(true);
    this.errorSync.set('');
    for (const o of lote) { o.estado = 'ENVIADA'; o.intentos += 1; await this.db.guardarOperacion(o); }  // RN12: enviada, pero todavía guardada
    this.operaciones.update((l) => [...l]);
    try {
      const r = await new Promise<import('../offline.models').RespuestaSync>((ok, mal) =>
        this.api.sincronizar(lote.map((o) => ({ id: o.id, tipo: o.tipo, creada_en: o.creada_en, sucursal_id: o.sucursal_id, payload: o.payload }))).subscribe({ next: ok, error: mal }));
      for (const res of r.resultados) {
        const o = lote.find((x) => x.id === res.id);
        if (!o) continue;
        if (res.estado === 'ERROR') o.estado = 'REGISTRADA_LOCAL';  // el servidor no pudo procesarla ahora: se conserva y se reintenta (RNF06)
        else { o.estado = res.estado; o.referencia = res.referencia; o.comprobante = res.comprobante; o.detalle = res.detalle; }
        o.mensaje = res.mensaje;
        await this.db.guardarOperacion(o);
      }
      await this.db.marcarSincronizacion();
      this.ultimaSync.set(r.sincronizado_en);
    } catch (e) {
      for (const o of lote) { o.estado = 'REGISTRADA_LOCAL'; await this.db.guardarOperacion(o); }  // sin respuesta: nada se pierde
      const err = e as { status?: number; error?: { detail?: string } };
      this.errorSync.set(err.status === 0 || err.status === undefined ? 'Sin conexión con el servidor: las operaciones siguen guardadas y se reintentarán.' : (typeof err.error?.detail === 'string' ? err.error.detail : 'No se pudo sincronizar. Se reintentará.'));
    }
    this.operaciones.update((l) => [...l]);
    this.sincronizando.set(false);
    await this.refrescarEstados();
  }

  /** CU-39: una operación que quedó en conflicto y el Encargado resolvió cambia de estado también en este dispositivo. */
  async refrescarEstados(): Promise<void> {
    if (!this.red.online() || !this.operaciones().some((o) => o.estado === 'EN_CONFLICTO')) return;
    try {
      const servidor = await new Promise<OperacionServidor[]>((ok, mal) => this.api.mias().subscribe({ next: ok, error: mal }));
      for (const s of servidor) {
        const o = this.operaciones().find((x) => x.id === s.id);
        if (o && o.estado === 'EN_CONFLICTO' && s.estado !== 'EN_CONFLICTO') {
          o.estado = s.estado; o.mensaje = s.mensaje; o.referencia = s.referencia; o.comprobante = s.comprobante; o.detalle = s.detalle;
          await this.db.guardarOperacion(o);
        }
      }
      this.operaciones.update((l) => [...l]);
    } catch { /* sin conexión: se vuelve a intentar después */ }
  }

  /** Solo se pueden quitar del dispositivo las operaciones que el servidor ya confirmó o rechazó (RN12). */
  async limpiarTerminadas() {
    for (const o of this.operaciones().filter((x) => x.estado === 'CONFIRMADA' || x.estado === 'RECHAZADA')) await this.db.borrarOperacion(o.id);
    await this.cargar();
  }
}
