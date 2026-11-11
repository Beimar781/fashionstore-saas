import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { EstadoLocal, OperacionLocal } from '../../core/offline.models';
import { AuthService } from '../../core/auth/auth.service';
import { CatalogoLocalService } from '../../core/offline/catalogo-local.service';
import { comprobanteProvisional, numeroLocal } from '../../core/offline/comprobante-provisional';
import { PasoTiempo, lineaDeTiempo } from '../../core/offline/linea-de-tiempo';
import { LocalDbService } from '../../core/offline/local-db.service';

const TEXTO: Record<EstadoLocal, string> = {
  REGISTRADA_LOCAL: 'Registrada en el dispositivo', ENVIADA: 'Enviada, esperando respuesta', CONFIRMADA: 'Confirmada por el servidor', RECHAZADA: 'Rechazada', EN_CONFLICTO: 'En conflicto',
};

/** CU-39 y CU-38 · Operaciones del dispositivo con su estado (registrada, enviada, confirmada, rechazada o en conflicto) y sincronización con reintentos. */
@Component({
  selector: 'app-operaciones-locales',
  imports: [DatePipe],
  template: `
    <section class="card pad stack">
      <div class="row between">
        <div><h2>Mis operaciones</h2>
          <p class="small muted">@if (cola.ultimaSync(); as u) { Última sincronización: {{ u | date: 'dd/MM/yyyy HH:mm' }}. } @else { Aún no se sincronizó nada. } {{ cola.pendientes().length }} pendiente(s) de enviar.</p></div>
        <span class="row">
          <button class="btn primary" (click)="cola.sincronizar()" [disabled]="cola.sincronizando() || !red.online() || !cola.pendientes().length">{{ cola.sincronizando() ? 'Sincronizando…' : 'Sincronizar ahora' }}</button>
          <button class="btn ghost" (click)="cola.limpiarTerminadas()">Quitar confirmadas y rechazadas</button>
        </span>
      </div>
      @if (!red.online()) { <div class="alert warn small" role="status">Sin conexión: las operaciones se guardan aquí y se enviarán solas al volver Internet.</div> }
      @if (cola.errorSync()) { <div class="alert danger small" role="alert">{{ cola.errorSync() }}</div> }
      <div class="table-wrap"><table>
        <thead><tr><th>Registrada</th><th>Operación</th><th>Estado</th><th>Detalle</th></tr></thead>
        <tbody>
          @for (o of cola.operaciones(); track o.id) {
            <tr>
              <td class="nowrap">{{ o.creada_en | date: 'dd/MM HH:mm' }}</td>
              <td>{{ o.resumen }}<div class="small muted" title="Identificador único de la operación">{{ o.id }}</div></td>
              <td><span class="badge" [class.ok]="o.estado === 'CONFIRMADA'" [class.danger]="o.estado === 'RECHAZADA'" [class.warn]="o.estado === 'EN_CONFLICTO' || o.estado === 'ENVIADA'">{{ texto(o.estado) }}</span>@if (o.intentos > 1 && o.estado === 'REGISTRADA_LOCAL') { <div class="small muted">{{ o.intentos }} intento(s)</div> }</td>
              <td class="small">
                @if (o.referencia) { <strong>{{ o.referencia }}</strong>@if (o.comprobante) { · comprobante {{ o.comprobante }} } <br /> }
                {{ o.mensaje }}
                @if (o.tipo === 'VENTA_CONTADO') { <div><button type="button" class="btn sm" (click)="descargarProvisional(o)">Comprobante {{ o.comprobante ?? numeroLocal(o) }}</button></div> }
                @if (o.detalle?.faltantes?.length) { <ul class="faltantes">@for (f of o.detalle!.faltantes; track f.variante_id) { <li>{{ f.producto }} ({{ f.talla }}, {{ f.color }}): pidió {{ f.solicitadas }}, hay {{ f.disponibles }}</li> }</ul> }
                <div class="row" style="margin-top:.3rem">
                  <button type="button" class="btn sm ghost" (click)="alternar(o)" [attr.aria-expanded]="!!pasos()[o.id]">{{ pasos()[o.id] ? 'Ocultar la línea de tiempo' : 'Línea de tiempo' }}</button>
                  @if (cola.puedeDeshacer(o)) { <button type="button" class="btn sm danger" (click)="cola.deshacer(o)">Deshacer</button> }
                </div>
                @if (pasos()[o.id]; as ps) {
                  <ol class="tiempo">@for (p of ps; track $index) { <li [class]="p.tipo"><span>{{ p.texto }}</span>@if (p.fecha) { <span class="muted"> · {{ p.fecha | date: 'dd/MM HH:mm:ss' }}</span> }</li> }</ol>
                }
              </td>
            </tr>
          } @empty { <tr><td colspan="4" class="empty">No hay operaciones registradas en este dispositivo.</td></tr> }
        </tbody></table></div>
    </section>`,
  styles: `.faltantes { margin: .3rem 0 0; padding-left: 1.1rem; } .tiempo { margin: .4rem 0 0; padding-left: 1.2rem; } .tiempo .ok { color: #1e7a4f; } .tiempo .warn { color: #9a5b00; } .tiempo .danger { color: #b3261e; }`,
})
export class OperacionesLocalesComponent {
  readonly cola = inject(ColaOperacionesService);
  readonly red = inject(ConnectivityService);
  private readonly auth = inject(AuthService);
  private readonly local = inject(CatalogoLocalService);
  private readonly db = inject(LocalDbService);
  readonly numeroLocal = numeroLocal;
  readonly pasos = signal<Record<string, PasoTiempo[]>>({});

  /** Muestra u oculta la historia de la operación (sale de lo guardado en el dispositivo: sirve sin conexión). */
  async alternar(o: OperacionLocal) {
    if (this.pasos()[o.id]) { this.pasos.update((p) => { const { [o.id]: _quitar, ...resto } = p; return resto; }); return; }
    this.pasos.update((p) => ({ ...p, [o.id]: lineaDeTiempo(o, [], undefined) }));
    const registro = await this.db.registroSincronizacion(500);
    this.pasos.update((p) => ({ ...p, [o.id]: lineaDeTiempo(o, registro) }));
  }

  /** B1: descarga el comprobante provisional LOC-… de una venta de contado registrada sin conexión. */
  async descargarProvisional(o: OperacionLocal) {
    const nombre = (id: number) => { for (const p of this.local.productos()) { const v = p.variantes.find((x) => x.id === id); if (v) return `${p.nombre} (${v.talla}, ${v.color})`; } return `Prenda ${id}`; };
    (await comprobanteProvisional(o, this.auth.sesion()?.empresa?.razon_social ?? '', nombre)).save(`${numeroLocal(o)}.pdf`);
  }
  texto(e: EstadoLocal) { return TEXTO[e]; }
}
