import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ReservasApi } from '../../../core/api/reservas.api';
import { CLASE_ESTADO_RESERVA, EstadoReserva, Reserva, TEXTO_ESTADO_ITEM, TEXTO_ESTADO_RESERVA } from '../../../core/reservas.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';

/** CU-24 · El Encargado revisa las reservas de su sucursal, prepara las prendas y reporta las que no encuentra. */
@Component({
  selector: 'app-reservas-sucursal',
  imports: [FormsModule, DatePipe],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Reservas de la sucursal</h1><p>Reúna las prendas reservadas y avise al cliente que puede pasar.</p></div></div>

      <form class="card pad row" style="margin-bottom:1rem" (ngSubmit)="cargar()">
        <label style="max-width:200px">Estado
          <select name="e" [(ngModel)]="estado"><option value="">Activas (pendientes, preparadas, en probador)</option>
            @for (e of estados; track e) { <option [value]="e">{{ texto(e) }}</option> }</select></label>
        <label style="max-width:180px">Día de la visita<input name="f" type="date" [(ngModel)]="fecha" /></label>
        <div class="row" style="align-self:end"><button class="btn">Filtrar</button><button type="button" class="btn ghost" (click)="hoy()">Hoy</button><button type="button" class="btn ghost" (click)="limpiar()">Limpiar</button></div>
      </form>

      @if (cargando()) { <div class="empty">Cargando…</div> }
      @else if (!reservas().length) { <div class="card empty">No hay reservas con esos filtros.</div> }
      @else {
        <div class="card table-wrap">
          <table>
            <thead><tr><th>Código</th><th>Cliente</th><th>Visita</th><th class="right">Prendas</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              @for (r of reservas(); track r.id) {
                <tr>
                  <td><strong class="codigo">{{ r.codigo }}</strong></td><td>{{ r.cliente }}</td><td class="nowrap">{{ r.programada_para | date: 'dd/MM HH:mm' }}</td>
                  <td class="right">{{ r.total_unidades }}</td>
                  <td><span class="badge" [class]="clase(r.estado)">{{ texto(r.estado) }}</span></td>
                  <td class="actions"><button class="btn sm" (click)="detalle.set(r); error.set('')">Ver detalle</button></td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>

    @if (detalle(); as r) {
      <div class="overlay" (click)="detalle.set(null)">
        <div class="modal" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <header><h2>{{ r.codigo }} · <span class="badge" [class]="clase(r.estado)">{{ texto(r.estado) }}</span></h2><button type="button" class="btn sm ghost" (click)="detalle.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <p class="small muted">{{ r.cliente }} · visita {{ r.programada_para | date: 'dd/MM/yyyy HH:mm' }} · vence {{ r.vence_en | date: 'dd/MM HH:mm' }}</p>
            @if (r.notas) { <p class="alert warn small">{{ r.notas }}</p> }
            <div class="table-wrap"><table>
              <thead><tr><th>SKU</th><th>Prenda</th><th>Talla</th><th>Color</th><th class="right">Cant.</th><th>Estado</th><th></th></tr></thead>
              <tbody>
                @for (i of r.items; track i.id) {
                  <tr><td><code>{{ i.sku }}</code></td><td>{{ i.producto }}</td><td>{{ i.talla }}</td><td>{{ i.color }}</td><td class="right">{{ i.cantidad }}</td>
                    <td><span class="badge" [class.danger]="i.estado === 'NO_ENCONTRADO'">{{ itemTexto(i.estado) }}</span></td>
                    <td class="actions">@if (i.estado === 'RESERVADO' && (r.estado === 'PENDIENTE' || r.estado === 'PREPARADA')) { <button class="btn sm danger" (click)="noEncontrado(r, i.id)">No encontrado</button> }</td></tr>
                }
              </tbody>
            </table></div>
            <p class="small muted">«No encontrado» descuenta la prenda del inventario y avisa al cliente con una disculpa.</p>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer>
            <button class="btn" (click)="detalle.set(null)">Cerrar</button>
            @if (r.estado === 'PENDIENTE') { <button class="btn primary" (click)="preparar(r)" [disabled]="enviando()">Prendas preparadas</button> }
          </footer>
        </div>
      </div>
    }`,
  styles: `.codigo { font-family: ui-monospace, Consolas, monospace; letter-spacing: .04em; } code { font-size: .8rem; background: #f1eee9; padding: .05rem .35rem; border-radius: 5px; }`,
})
export class ReservasSucursalPage implements OnInit {
  private api = inject(ReservasApi);
  private toast = inject(ToastService);

  readonly estados: EstadoReserva[] = ['PENDIENTE', 'PREPARADA', 'EN_PROBADOR', 'COMPLETADA', 'CANCELADA', 'EXPIRADA'];
  readonly reservas = signal<Reserva[]>([]);
  readonly detalle = signal<Reserva | null>(null);
  readonly cargando = signal(true);
  readonly enviando = signal(false);
  readonly error = signal('');
  estado = ''; fecha = '';
  readonly texto = (e: EstadoReserva) => TEXTO_ESTADO_RESERVA[e];
  readonly clase = (e: EstadoReserva) => CLASE_ESTADO_RESERVA[e];
  readonly itemTexto = (e: string) => TEXTO_ESTADO_ITEM[e] ?? e;

  ngOnInit() { this.cargar(); }

  hoy() { const d = new Date(); this.fecha = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; this.estado = 'PENDIENTE'; this.cargar(); }
  limpiar() { this.estado = ''; this.fecha = ''; this.cargar(); }

  cargar() {
    this.cargando.set(true);
    this.api.deMiSucursal({ estado: this.estado, fecha: this.fecha }).subscribe({
      next: (r) => { this.reservas.set(r); this.cargando.set(false); },
      error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); },
    });
  }

  preparar(r: Reserva) {
    this.enviando.set(true); this.error.set('');
    this.api.preparar(r.id).subscribe({
      next: (n) => { this.enviando.set(false); this.detalle.set(n); this.toast.ok('Reserva preparada: el cliente recibió el aviso.'); this.cargar(); },
      error: (e) => { this.enviando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  noEncontrado(r: Reserva, itemId: number) {
    if (!confirm('¿Marcar la prenda como no encontrada en físico? Se descontará del inventario.')) return;
    this.error.set('');
    this.api.noEncontrado(r.id, itemId).subscribe({
      next: (n) => { this.detalle.set(n); this.toast.aviso('Prenda marcada como no encontrada: se ajustó el stock y se avisó al cliente.'); this.cargar(); },
      error: (e) => this.error.set(mensajeError(e)),
    });
  }
}
