import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CajaApi } from '../../../core/api/caja.api';
import { ResumenDia, Ticket } from '../../../core/caja.models';
import { Pedido } from '../../../core/compras.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';

const hoy = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };

/** CU-27 · Ventas de la sucursal: resumen monetario y cierre de caja del día, y los tickets con su detalle. Solo la sucursal del Encargado. */
@Component({
  selector: 'app-ventas-sucursal',
  imports: [FormsModule, DatePipe],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Ventas de la sucursal</h1><p>Resumen del día, cierre de caja y detalle de cada ticket de {{ resumen()?.sucursal ?? 'su sucursal' }}.</p></div></div>

      <form class="card pad row" style="margin-bottom:1rem" (ngSubmit)="cargar()">
        <label style="max-width:170px">Día<input name="f" type="date" [(ngModel)]="fecha" [max]="maximo" /></label>
        <label style="max-width:170px">Canal<select name="c" [(ngModel)]="canal"><option value="">Todos</option><option value="PRESENCIAL">Caja (POS)</option><option value="DIGITAL">Pedidos online</option></select></label>
        <label style="max-width:170px">Cobrado con<select name="m" [(ngModel)]="metodo"><option value="">Todos</option><option value="EFECTIVO">Efectivo</option><option value="TARJETA">Tarjeta</option><option value="QR">QR</option></select></label>
        <div class="row" style="align-self:end"><button class="btn primary">Consultar</button><button type="button" class="btn ghost" (click)="hoyDia()">Hoy</button></div>
      </form>
      @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }

      @if (resumen(); as r) {
        <div class="grid cols-3" style="margin-bottom:1rem">
          <div class="card pad"><div class="small muted">Total vendido</div><div class="cifra">Bs {{ r.total_vendido }}</div><div class="small muted">{{ r.ventas }} venta(s) · {{ r.unidades }} prenda(s) · ticket promedio Bs {{ r.ticket_promedio }}</div></div>
          <div class="card pad"><div class="small muted">Ventas en caja (POS)</div><div class="cifra">Bs {{ r.presencial.total }}</div><div class="small muted">{{ r.presencial.ventas }} venta(s) · {{ r.presencial.unidades }} prenda(s)</div></div>
          <div class="card pad"><div class="small muted">Pedidos online (retiro o despacho)</div><div class="cifra">Bs {{ r.digital.total }}</div><div class="small muted">{{ r.digital.ventas }} pedido(s) · {{ r.digital.unidades }} prenda(s)</div></div>
        </div>
        <div class="grid cols-2" style="margin-bottom:1rem">
          <section class="card pad stack">
            <h3>Cierre de caja</h3>
            @for (c of r.cierre_de_caja; track c.metodo) {
              <div class="row between small"><span><strong>{{ nombreMetodo(c.metodo) }}</strong> · {{ c.cobros }} cobro(s)@if (c.recibido) { · recibido Bs {{ c.recibido }}, cambio Bs {{ c.cambio }} }</span><strong>Bs {{ c.total }}</strong></div>
            } @empty { <p class="muted small">Sin cobros en el día.</p> }
            <div class="row between total"><strong>Efectivo que debe haber en caja</strong><strong>Bs {{ r.efectivo_en_caja }}</strong></div>
          </section>
          <section class="card pad stack"><h3>Reservas</h3><div class="cifra">{{ r.reservas_completadas }}</div><p class="small muted">reserva(s) completada(s) en el día</p></section>
        </div>
      }

      <div class="card table-wrap">
        @if (!tickets().length) { <div class="empty">No hay ventas con esos filtros.</div> } @else {
          <table>
            <thead><tr><th>Hora</th><th>Comprobante</th><th>Canal</th><th>Cliente</th><th>Atendió</th><th>Cobro</th><th class="right">Prendas</th><th class="right">Total</th><th></th></tr></thead>
            <tbody>
              @for (t of tickets(); track t.id) {
                <tr><td class="nowrap">{{ t.fecha | date: 'dd/MM HH:mm' }}</td><td><strong>{{ t.comprobante_numero }}</strong>@if (t.comprobante_tipo === 'INTERNO_TEMPORAL') { <span class="badge warn">interno</span> }</td>
                  <td>{{ t.canal === 'PRESENCIAL' ? 'Caja' : 'Online' }}</td><td>{{ t.cliente ?? '—' }}</td><td>{{ t.vendedor ?? '—' }}</td><td>{{ nombreMetodo(t.metodo) }}</td>
                  <td class="right">{{ t.unidades }}</td><td class="right nowrap">Bs {{ t.total }}</td><td class="actions"><button class="btn sm" (click)="ver(t)">Ver ticket</button></td></tr>
              }
            </tbody>
            <tfoot><tr><td colspan="7" class="right muted">Total del listado</td><td class="right nowrap"><strong>Bs {{ total() }}</strong></td><td></td></tr></tfoot>
          </table>
        }
      </div>
    </div>

    @if (detalle(); as p) {
      <div class="overlay" (click)="detalle.set(null)">
        <div class="modal" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <header><h2>Ticket {{ p.comprobante_numero }}</h2><button type="button" class="btn sm ghost" (click)="detalle.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <p class="small muted">{{ p.codigo }} · {{ p.canal === 'PRESENCIAL' ? 'Venta en caja' : 'Pedido online' }} · {{ p.pagado_en | date: 'dd/MM/yyyy HH:mm' }}{{ p.cliente ? ' · ' + p.cliente : '' }}{{ p.vendedor ? ' · atendió ' + p.vendedor : '' }}</p>
            <div class="table-wrap"><table>
              <thead><tr><th>Prenda</th><th class="right">Cant.</th><th class="right">Precio</th><th class="right">Subtotal</th></tr></thead>
              <tbody>@for (i of p.items; track i.id) { <tr><td>{{ i.producto }}<div class="small muted">Talla {{ i.talla }} · {{ i.color }} · {{ i.sku }}</div></td><td class="right">{{ i.cantidad }}</td><td class="right">{{ i.precio_final }}</td><td class="right">{{ i.subtotal }}</td></tr> }</tbody>
            </table></div>
            <div class="row between"><span class="muted small">IVA incluido Bs {{ p.iva_incluido }}@if (p.descuento !== '0.00') { · descuento Bs {{ p.descuento }} }</span><strong>Total Bs {{ p.total }}</strong></div>
            @for (g of p.pagos; track g.id) { <p class="small">Cobro: {{ nombreMetodo(g.metodo) }}@if (g.tarjeta_ultimos4) { {{ g.tarjeta_marca }} ****{{ g.tarjeta_ultimos4 }} }@if (g.monto_recibido) { · recibido Bs {{ g.monto_recibido }} · cambio Bs {{ g.cambio }} } · {{ g.estado }}</p> }
          </div>
          <footer><button class="btn" (click)="detalle.set(null)">Cerrar</button></footer>
        </div>
      </div>
    }`,
  styles: `.cifra { font: 600 1.7rem var(--serif); margin: .2rem 0; } .total { border-top: 1px solid var(--line); padding-top: .6rem; }`,
})
export class VentasSucursalPage implements OnInit {
  private api = inject(CajaApi);
  private toast = inject(ToastService);

  readonly maximo = hoy();
  readonly resumen = signal<ResumenDia | null>(null);
  readonly tickets = signal<Ticket[]>([]);
  readonly total = signal('0.00');
  readonly detalle = signal<Pedido | null>(null);
  readonly error = signal('');
  fecha = hoy(); canal = ''; metodo = '';

  ngOnInit() { this.cargar(); }

  nombreMetodo(m: string | null) { return m === 'EFECTIVO' ? 'Efectivo' : m === 'TARJETA' ? 'Tarjeta' : m === 'QR' ? 'QR' : '—'; }
  hoyDia() { this.fecha = hoy(); this.cargar(); }

  cargar() {
    this.error.set('');
    this.api.resumen(this.fecha).subscribe({ next: (r) => this.resumen.set(r), error: (e) => this.error.set(mensajeError(e)) });
    this.api.tickets({ desde: this.fecha, hasta: this.fecha, canal: this.canal, metodo: this.metodo }).subscribe({
      next: (r) => { this.tickets.set(r.tickets); this.total.set(r.total); },
      error: (e) => this.error.set(mensajeError(e)),
    });
  }

  ver(t: Ticket) { this.api.ticket(t.id).subscribe({ next: (p) => this.detalle.set(p), error: (e) => this.toast.error(mensajeError(e)) }); }
}
