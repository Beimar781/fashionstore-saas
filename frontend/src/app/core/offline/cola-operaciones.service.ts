import { Injectable, computed, effect, inject, signal, untracked } from '@angular/core';
import { OfflineApi } from '../api/offline.api';
import { AuthService } from '../auth/auth.service';
import { EfectoLocal, OperacionLocal, OperacionServidor, TipoOperacion } from '../offline.models';
import { ToastService } from '../ui/toast.service';
import { CatalogoLocalService } from './catalogo-local.service';
import { ConnectivityService } from './connectivity.service';
import { LocalDbService } from './local-db.service';

const REINTENTO_MS = 30_000;

/** Operaciones que se pueden deshacer mientras no se hayan enviado (las de reservas del Encargado cambian el estado de la reserva y no se deshacen). */
const SE_PUEDEN_DESHACER: TipoOperacion[] = ['VENTA_CONTADO', 'COMPRA', 'RESERVA', 'CANCELAR_RESERVA', 'AJUSTE_INVENTARIO', 'RECEPCION', 'DEVOLUCION', 'PROPUESTA_PROVEEDOR'];

/** Resultado de una pasada de sincronización (lo anuncia AvisosConexionService). */
export interface ResumenSync { confirmadas: number; conflictos: number; rechazadas: number; }

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
  private toast = inject(ToastService);
  private local = inject(CatalogoLocalService);

  /** RNF06: tras cada fallo de red o respuesta 5xx la espera se duplica (30 s, 1 min, 2 min…, máximo 15 min); un 4xx de negocio no se reintenta (la operación queda RECHAZADA). */
  private fallosSeguidos = 0;
  private proximoIntento = 0;

  readonly operaciones = signal<OperacionLocal[]>([]);
  readonly sincronizando = signal(false);
  readonly errorSync = signal('');
  readonly ultimaSync = signal<string | null>(null);
  readonly ultimoResumen = signal<ResumenSync | null>(null);
  /** Cambia tras cada sincronización y al volver la red: las pantallas abiertas vuelven a pedir sus datos sin recargar la página. */
  readonly refresco = signal(0);
  readonly pendientes = computed(() => this.operaciones().filter((o) => o.estado === 'REGISTRADA_LOCAL' || o.estado === 'ENVIADA'));
  readonly enConflicto = computed(() => this.operaciones().filter((o) => o.estado === 'EN_CONFLICTO'));

  constructor() {
    navigator.serviceWorker?.addEventListener('message', (m) => { if (m.data?.tipo === 'SINCRONIZAR_COLA' && this.auth.autenticado()) void this.sincronizar(); });
    void this.cargar();
    // al volver la conexión se sincroniza solo, y mientras haya pendientes se reintenta cada 30 segundos
    let sinRed = !this.red.online();
    effect(() => {
      const enLinea = this.red.online();
      const volvio = enLinea && sinRed;
      sinRed = !enLinea;
      if (enLinea && this.auth.autenticado()) void this.sincronizar().then(() => { if (volvio) this.refresco.update((n) => n + 1); });
    });
    setInterval(() => { if (this.red.online() && this.auth.autenticado() && this.pendientes().length && Date.now() >= this.proximoIntento) void this.sincronizar(); }, REINTENTO_MS);
  }

  /** Para las pantallas: vuelve a ejecutar `recargar` cuando hubo una sincronización o volvió la red (se llama desde el constructor de la página). */
  alRefrescar(recargar: () => void) {
    let visto = this.refresco();
    effect(() => { const n = this.refresco(); if (n !== visto) { visto = n; untracked(recargar); } });
  }

  async cargar() {
    const s = this.auth.sesion();
    const todas = await this.db.operaciones();
    this.operaciones.set(todas.filter((o) => o.usuario_id === s?.usuario.id && o.empresa_id === s?.empresa?.id).sort((a, b) => b.creada_en.localeCompare(a.creada_en)));
    this.ultimaSync.set((await this.db.ultimaSincronizacion()) ?? null);
  }

  /** B10 · Pide al navegador que despierte la sincronización cuando vuelva la red, incluso con la pestaña en segundo plano. Sin soporte, basta el evento 'online' de la app. */
  private async pedirSincronizacionEnSegundoPlano() {
    try {
      const reg = await navigator.serviceWorker?.ready;
      await (reg as any)?.sync?.register('sincronizar-cola');
    } catch { /* el navegador no lo permite: queda el reintento normal */ }
  }

  /** Registra una operación en el dispositivo (estado REGISTRADA_LOCAL) y, si hay conexión, la sincroniza enseguida. */
  async registrar(tipo: TipoOperacion, payload: Record<string, unknown>, sucursalId: number | null, resumen: string, efecto?: EfectoLocal): Promise<OperacionLocal> {
    const s = this.auth.sesion()!;
    const op: OperacionLocal = {
      id: crypto.randomUUID(), empresa_id: s.empresa!.id, sucursal_id: sucursalId, usuario_id: s.usuario.id, tipo, payload, estado: 'REGISTRADA_LOCAL',
      intentos: 0, mensaje: '', referencia: null, comprobante: null, detalle: null, creada_en: new Date().toISOString(), resumen, ...(efecto ? { efecto_local: efecto } : {}),
    };
    await this.db.guardarOperacion(op);
    this.operaciones.update((l) => [op, ...l]);
    if (this.red.online()) void this.sincronizar();
    else void this.pedirSincronizacionEnSegundoPlano();
    return op;
  }

  /** Solo mientras la operación sigue en el dispositivo sin enviarse; una venta que cobró una reserva cambió datos del servidor y no se deshace. */
  puedeDeshacer(o: OperacionLocal): boolean { return o.estado === 'REGISTRADA_LOCAL' && SE_PUEDEN_DESHACER.includes(o.tipo) && !o.payload['reserva_codigo']; }

  /** Deshace una operación que aún no se sincronizó: sale de la cola y la copia local vuelve a como estaba (stock y devoluciones). */
  async deshacer(o: OperacionLocal): Promise<boolean> {
    const viva = this.operaciones().find((x) => x.id === o.id);
    if (!viva || !this.puedeDeshacer(viva)) { this.toast.aviso('Esa operación ya se envió y no se puede deshacer.'); return false; }
    await this.db.borrarOperacion(viva.id);
    const efecto = viva.efecto_local;
    if (viva.sucursal_id !== null) for (const m of efecto?.stock ?? []) await this.local.moverStock(m.variante_id, viva.sucursal_id, -m.delta);
    if (efecto?.devuelto) await this.local.restaurarDevolvible(efecto.devuelto.comprobante, efecto.devuelto.items);
    this.operaciones.update((l) => l.filter((x) => x.id !== viva.id));
    this.toast.ok(efecto?.stock?.length || efecto?.devuelto ? 'Operación deshecha: ya no se enviará y el inventario local volvió a como estaba.' : 'Operación deshecha: ya no se enviará.');
    return true;
  }

  private fallo() {
    this.fallosSeguidos++;
    this.proximoIntento = Date.now() + Math.min(REINTENTO_MS * 2 ** this.fallosSeguidos, 15 * 60 * 1000);
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
        void Promise.all(lote.map(async (o) => ({ id: o.id, tipo: o.tipo, creada_en: o.creada_en, sucursal_id: o.sucursal_id, payload: await this.db.payloadDesdeDetalle(o) }))).then((ops) => this.api.sincronizar(ops).subscribe({ next: ok, error: mal })));
      let confirmadas = 0, conflictos = 0, rechazadas = 0, conError = false;
      for (const res of r.resultados) {
        const o = lote.find((x) => x.id === res.id);
        if (!o) continue;
        if (res.estado === 'ERROR') { o.estado = 'REGISTRADA_LOCAL'; conError = true; }  // el servidor no pudo procesarla ahora: se conserva y se reintenta (RNF06)
        else { o.estado = res.estado; o.referencia = res.referencia; o.comprobante = res.comprobante; o.detalle = res.detalle; }
        o.mensaje = res.mensaje;
        await this.db.guardarOperacion(o);
        await this.db.anotarIntento({ operacion_id: o.id, tipo: o.tipo, intento: o.intentos, fecha: new Date().toISOString(), resultado: res.estado, codigo: res.estado === 'ERROR' ? '5xx' : '200', motivo: o.estado === 'RECHAZADA' || o.estado === 'EN_CONFLICTO' ? o.mensaje : '' });
        this.avisarAlCliente(o);
        if (o.estado === 'CONFIRMADA') confirmadas++;
        if (o.estado === 'EN_CONFLICTO') conflictos++;
        if (o.estado === 'RECHAZADA') rechazadas++;
      }
      if (conError) this.fallo(); else { this.fallosSeguidos = 0; this.proximoIntento = 0; }
      this.ultimoResumen.set({ confirmadas, conflictos, rechazadas });  // lo anuncia AvisosConexionService (aviso global y notificación del sistema)
      this.refresco.update((n) => n + 1);
      await this.db.marcarSincronizacion();
      this.ultimaSync.set(r.sincronizado_en);
      if (r.aviso_reloj) this.errorSync.set(r.aviso_reloj);  // §7.2: la hora del dispositivo parece incorrecta
    } catch (e) {
      const codigoHttp = String((e as { status?: number }).status || 'SIN_RED');
      for (const o of lote) { o.estado = 'REGISTRADA_LOCAL'; await this.db.guardarOperacion(o); await this.db.anotarIntento({ operacion_id: o.id, tipo: o.tipo, intento: o.intentos, fecha: new Date().toISOString(), resultado: 'SIN_RESPUESTA', codigo: codigoHttp, motivo: '' }); }  // sin respuesta: nada se pierde
      const estadoHttp = (e as { status?: number }).status;
      if (estadoHttp === undefined || estadoHttp === 0 || estadoHttp >= 500) this.fallo();  // un 4xx de negocio no se reintenta con espera: el servidor ya respondió
      const err = e as { status?: number; error?: { detail?: string } };
      this.errorSync.set(err.status === 0 || err.status === undefined ? 'Sin conexión con el servidor: las operaciones siguen guardadas y se reintentarán.' : (typeof err.error?.detail === 'string' ? err.error.detail : 'No se pudo sincronizar. Se reintentará.'));
    }
    this.operaciones.update((l) => [...l]);
    this.sincronizando.set(false);
    await this.refrescarEstados();
  }

  /** Mensaje emergente para el cliente cuando el servidor resuelve su compra o su reserva (además del aviso push y de la campana). */
  private avisarAlCliente(o: OperacionLocal) {
    if (o.tipo === 'VENTA_CONTADO') return;
    if (o.tipo === 'CANCELAR_RESERVA' && o.estado === 'CONFIRMADA') { this.toast.ok(`Reserva ${o.referencia ?? ''} cancelada.`); return; }
    const nombre = o.tipo === 'COMPRA' ? 'compra' : 'reserva';
    if (o.estado === 'EN_CONFLICTO') this.toast.aviso(`Su ${nombre} no se pudo realizar: la prenda se agotó mientras estaba sin conexión. No se le cobró nada.`);
    else if (o.estado === 'RECHAZADA') this.toast.error(`Su ${nombre} no se pudo realizar: ${o.mensaje}`);
    else if (o.estado === 'CONFIRMADA' && o.tipo === 'COMPRA') this.toast.ok(`Su compra ${o.referencia} está lista: págela con tarjeta en «Mis compras».`);
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
          this.refresco.update((n) => n + 1);
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
