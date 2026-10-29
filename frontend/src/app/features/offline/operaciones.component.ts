import { DatePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { EstadoLocal } from '../../core/offline.models';

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
                @if (o.detalle?.faltantes?.length) { <ul class="faltantes">@for (f of o.detalle!.faltantes; track f.variante_id) { <li>{{ f.producto }} ({{ f.talla }}, {{ f.color }}): pidió {{ f.solicitadas }}, hay {{ f.disponibles }}</li> }</ul> }
              </td>
            </tr>
          } @empty { <tr><td colspan="4" class="empty">No hay operaciones registradas en este dispositivo.</td></tr> }
        </tbody></table></div>
    </section>`,
  styles: `.faltantes { margin: .3rem 0 0; padding-left: 1.1rem; }`,
})
export class OperacionesLocalesComponent {
  readonly cola = inject(ColaOperacionesService);
  readonly red = inject(ConnectivityService);
  texto(e: EstadoLocal) { return TEXTO[e]; }
}
