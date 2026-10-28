import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ReservasApi } from '../../../core/api/reservas.api';
import { CLASE_ESTADO_RESERVA, Reserva, TEXTO_ESTADO_ITEM, TEXTO_ESTADO_RESERVA } from '../../../core/reservas.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';

/** CU-25 · Atención en el mostrador: validar el código del cliente, entregar las prendas y cerrar la atención. */
@Component({
  selector: 'app-atencion',
  imports: [FormsModule, DatePipe],
  template: `
    <div class="page" style="max-width:760px">
      <div class="page-head"><div><h1>Atención de reservas</h1><p>El cliente presenta su código; valídelo, entregue las prendas y cierre la atención.</p></div></div>

      <form class="card pad row" (ngSubmit)="validar()">
        <label style="flex:1;min-width:220px">Código de reserva
          <input name="c" [(ngModel)]="codigo" placeholder="RSV-XXXXXXXX" autocomplete="off" required style="text-transform:uppercase;font-family:ui-monospace,Consolas,monospace;letter-spacing:.06em" /></label>
        <button class="btn primary" style="align-self:end" [disabled]="buscando() || !codigo.trim()">{{ buscando() ? 'Validando…' : 'Validar código' }}</button>
      </form>
      @if (error()) { <div class="alert danger" role="alert" style="margin-top:1rem">{{ error() }}</div> }

      @if (reserva(); as r) {
        <section class="card pad stack" style="margin-top:1rem">
          <div class="row between">
            <div><h2>{{ r.codigo }} <span class="badge" [class]="clase(r.estado)">{{ texto(r.estado) }}</span></h2>
              <p class="muted small">{{ r.cliente }} · visita {{ r.programada_para | date: 'dd/MM/yyyy HH:mm' }} · {{ r.sucursal }}</p></div>
          </div>
          <ul class="items">
            @for (i of r.items; track i.id) { <li>{{ i.cantidad }} × {{ i.producto }} · {{ i.talla }} · {{ i.color }} <code>{{ i.sku }}</code>
              @if (i.estado !== 'RESERVADO') { <span class="badge danger">{{ itemTexto(i.estado) }}</span> }</li> }
          </ul>

          @if (r.estado === 'PENDIENTE' || r.estado === 'PREPARADA') {
            <div class="row"><button class="btn primary" (click)="atender(r)" [disabled]="enviando()">Entregar prendas y enviar al probador</button></div>
          } @else if (r.estado === 'EN_PROBADOR') {
            <div class="alert ok">El cliente está en el probador. Al terminar, indique si se lleva las prendas.</div>
            <div class="row">
              <button class="btn" (click)="completar(r, false)" [disabled]="enviando()">No se lleva nada · completar</button>
              <button class="btn primary" (click)="completar(r, true)" [disabled]="enviando()">Se lleva las prendas</button>
            </div>
          }
        </section>
      }

      @if (cobro()) {
        <div class="alert ok" style="margin-top:1rem"><strong>Pase a caja.</strong> La venta de estas prendas se registra desde la reserva en el punto de venta (próxima fase); su stock sigue apartado hasta el cobro.</div>
      }
    </div>`,
  styles: `.items { margin: 0; padding-left: 1.1rem; display: grid; gap: .3rem; } code { font-size: .8rem; background: #f1eee9; padding: .05rem .35rem; border-radius: 5px; margin-left: .3rem; }`,
})
export class AtencionPage {
  private api = inject(ReservasApi);
  private toast = inject(ToastService);

  readonly reserva = signal<Reserva | null>(null);
  readonly buscando = signal(false);
  readonly enviando = signal(false);
  readonly error = signal('');
  readonly cobro = signal(false);
  codigo = '';
  readonly texto = (e: Reserva['estado']) => TEXTO_ESTADO_RESERVA[e];
  readonly clase = (e: Reserva['estado']) => CLASE_ESTADO_RESERVA[e];
  readonly itemTexto = (e: string) => TEXTO_ESTADO_ITEM[e] ?? e;

  validar() {
    this.buscando.set(true); this.error.set(''); this.cobro.set(false); this.reserva.set(null);
    this.api.validarCodigo(this.codigo.trim()).subscribe({
      next: (r) => { this.buscando.set(false); this.reserva.set(r); },
      error: (e) => { this.buscando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  atender(r: Reserva) {
    this.enviando.set(true); this.error.set('');
    this.api.atender(r.id).subscribe({
      next: (n) => { this.enviando.set(false); this.reserva.set(n); this.toast.ok('Prendas entregadas: el cliente pasa a los vestidores.'); },
      error: (e) => { this.enviando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  completar(r: Reserva, llevara: boolean) {
    this.enviando.set(true); this.error.set('');
    this.api.completar(r.id, llevara).subscribe({
      next: (res) => {
        this.enviando.set(false); this.reserva.set(res.reserva); this.cobro.set(res.habilita_venta);
        if (!res.habilita_venta) { this.toast.ok('Atención completada.'); this.codigo = ''; }
      },
      error: (e) => { this.enviando.set(false); this.error.set(mensajeError(e)); },
    });
  }
}
