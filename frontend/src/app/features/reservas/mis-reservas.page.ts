import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ReservasApi } from '../../core/api/reservas.api';
import { CLASE_ESTADO_RESERVA, EstadoReserva, Reserva, TEXTO_ESTADO_ITEM, TEXTO_ESTADO_RESERVA } from '../../core/reservas.models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** CU-10 · Consultar el estado de las reservas y cancelarlas (RF12). */
@Component({
  selector: 'app-mis-reservas',
  imports: [FormsModule, RouterLink, DatePipe],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Mis reservas</h1><p>Presente el código en el mostrador de la sucursal.</p></div><a class="btn primary" routerLink="/tienda/catalogo">+ Nueva reserva</a></div>

      <div class="tabs" role="tablist">
        @for (f of filtros; track f.valor) { <button role="tab" [class.activa]="estado() === f.valor" (click)="filtrar(f.valor)">{{ f.texto }}</button> }
      </div>

      @if (cargando()) { <div class="empty">Cargando…</div> }
      @else if (!reservas().length) { <div class="card empty">No tiene reservas {{ estado() ? 'con ese estado' : 'todavía' }}.</div> }
      @else {
        <div class="stack">
          @for (r of reservas(); track r.id) {
            <section class="card pad stack">
              <div class="row between">
                <div><span class="codigo">{{ r.codigo }}</span> <span class="badge" [class]="clase(r.estado)">{{ texto(r.estado) }}</span>
                  <p class="muted small">{{ r.sucursal }} · {{ r.programada_para | date: 'dd/MM/yyyy HH:mm' }} · {{ r.total_unidades }} prenda(s)</p></div>
                @if (r.puede_cancelar) { <button class="btn danger sm" (click)="pedirCancelar(r)">Cancelar reserva</button> }
              </div>
              <ul class="items">
                @for (i of r.items; track i.id) {
                  <li>{{ i.cantidad }} × {{ i.producto }} · {{ i.talla }} · {{ i.color }}
                    @if (i.estado !== 'RESERVADO') { <span class="badge" [class.danger]="i.estado === 'NO_ENCONTRADO'">{{ itemTexto(i.estado) }}</span> }</li>
                }
              </ul>
              @if (r.estado === 'PREPARADA') { <div class="alert ok">Sus prendas están preparadas: puede pasar a la tienda.</div> }
              @if (r.estado === 'PENDIENTE') { <p class="small muted">Vence el {{ r.vence_en | date: 'dd/MM/yyyy HH:mm' }} si no se presenta.</p> }
              @if (r.notas) { <p class="small muted">{{ r.notas }}</p> }
            </section>
          }
        </div>
      }
    </div>

    @if (cancelando(); as r) {
      <div class="overlay" (click)="cancelando.set(null)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="cancelar()" role="dialog" aria-modal="true">
          <header><h2>Cancelar {{ r.codigo }}</h2><button type="button" class="btn sm ghost" (click)="cancelando.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <p>Las prendas volverán a estar disponibles para otros clientes.</p>
            <label>Motivo <span class="hint">(opcional)</span><input name="m" [(ngModel)]="motivo" maxlength="200" /></label>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="cancelando.set(null)">Volver</button><button class="btn danger" [disabled]="enviando()">Sí, cancelar</button></footer>
        </form>
      </div>
    }`,
  styles: `.codigo { font: 700 1.2rem ui-monospace, Consolas, monospace; letter-spacing: .05em; margin-right: .5rem; } .items { margin: 0; padding-left: 1.1rem; display: grid; gap: .25rem; }`,
})
export class MisReservasPage implements OnInit {
  private api = inject(ReservasApi);
  private toast = inject(ToastService);

  readonly filtros: { valor: string; texto: string }[] = [
    { valor: '', texto: 'Todas' }, { valor: 'PENDIENTE', texto: 'Pendientes' }, { valor: 'PREPARADA', texto: 'Preparadas' },
    { valor: 'COMPLETADA', texto: 'Completadas' }, { valor: 'CANCELADA', texto: 'Canceladas' }, { valor: 'EXPIRADA', texto: 'Expiradas' },
  ];
  readonly reservas = signal<Reserva[]>([]);
  readonly estado = signal('');
  readonly cargando = signal(true);
  readonly cancelando = signal<Reserva | null>(null);
  readonly enviando = signal(false);
  readonly error = signal('');
  motivo = '';
  readonly texto = (e: EstadoReserva) => TEXTO_ESTADO_RESERVA[e];
  readonly clase = (e: EstadoReserva) => CLASE_ESTADO_RESERVA[e];
  readonly itemTexto = (e: string) => TEXTO_ESTADO_ITEM[e] ?? e;

  ngOnInit() { this.cargar(); }

  filtrar(valor: string) { this.estado.set(valor); this.cargar(); }

  cargar() {
    this.cargando.set(true);
    this.api.misReservas(this.estado()).subscribe({
      next: (r) => { this.reservas.set(r); this.cargando.set(false); },
      error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); },
    });
  }

  pedirCancelar(r: Reserva) { this.motivo = ''; this.error.set(''); this.cancelando.set(r); }

  cancelar() {
    const r = this.cancelando()!;
    this.enviando.set(true); this.error.set('');
    this.api.cancelar(r.id, this.motivo).subscribe({
      next: () => { this.enviando.set(false); this.cancelando.set(null); this.toast.ok(`Reserva ${r.codigo} cancelada.`); this.cargar(); },
      error: (e) => { this.enviando.set(false); this.error.set(mensajeError(e)); },
    });
  }
}
