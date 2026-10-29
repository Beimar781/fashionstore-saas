import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdministracionApi } from '../../core/api/administracion.api';
import { ReportesApi } from '../../core/api/reportes.api';
import { Sucursal } from '../../core/models';
import { PagosReporte, ReservasReporte, VentasReporte } from '../../core/reportes.models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

type Pestana = 'ventas' | 'reservas' | 'pagos';

/** CU-21 · Reportes de ventas y reservas del Administrador: ventas netas de devoluciones, reservas con su conversión y vista de pagos (aprobados, rechazados y pendientes). */
@Component({
  selector: 'app-reportes',
  imports: [FormsModule, DatePipe],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Reportes</h1><p>Ventas digitales y presenciales netas de devoluciones, reservas y pagos de su empresa.</p></div>
        <button class="btn" (click)="exportar()">⬇ Exportar CSV</button></div>

      <form class="card pad row" style="margin-bottom:1rem" (ngSubmit)="cargar()">
        <label style="max-width:160px">Desde<input name="d" type="date" [(ngModel)]="desde" /></label>
        <label style="max-width:160px">Hasta<input name="h" type="date" [(ngModel)]="hasta" /></label>
        <label style="max-width:200px">Sucursal<select name="s" [(ngModel)]="sucursal"><option [ngValue]="null">Todas</option>@for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }}</option> }</select></label>
        @if (pestana() === 'ventas') { <label style="max-width:170px">Canal<select name="c" [(ngModel)]="canal"><option value="">Todos</option><option value="PRESENCIAL">Caja (POS)</option><option value="DIGITAL">Online</option></select></label> }
        <button class="btn primary" style="align-self:end">Consultar</button>
      </form>
      <p class="muted small">Si no elige fechas se muestran los últimos 30 días.</p>
      @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }

      <div class="tabs" role="tablist">
        <button role="tab" [class.activa]="pestana() === 'ventas'" (click)="ir('ventas')">Ventas</button>
        <button role="tab" [class.activa]="pestana() === 'reservas'" (click)="ir('reservas')">Reservas</button>
        <button role="tab" [class.activa]="pestana() === 'pagos'" (click)="ir('pagos')">Pagos</button>
      </div>

      @if (pestana() === 'ventas' && ventas(); as v) {
        <div class="grid cols-3" style="margin-bottom:1rem">
          <div class="card pad"><div class="small muted">Ventas netas</div><div class="cifra">Bs {{ v.totales.ventas_netas }}</div><div class="small muted">Bruto Bs {{ v.totales.total_bruto }} − devuelto Bs {{ v.totales.devuelto }} + cambios Bs {{ v.totales.entregado_en_cambios }}</div></div>
          <div class="card pad"><div class="small muted">Ventas</div><div class="cifra">{{ v.totales.ventas }}</div><div class="small muted">{{ v.totales.unidades }} prenda(s) · ticket promedio Bs {{ v.totales.ticket_promedio }}</div></div>
          <div class="card pad"><div class="small muted">Devoluciones y cambios</div><div class="cifra">{{ v.totales.devoluciones }}</div><div class="small muted">notas en el periodo</div></div>
        </div>
        <div class="grid cols-2" style="margin-bottom:1rem">
          <section class="card pad stack"><h3>Ventas por día</h3>
            @for (d of v.por_dia; track d.fecha) { @if (d.ventas) { <div class="barra"><span class="small">{{ d.fecha | date: 'dd/MM' }}</span><div class="meter"><span [style.width.%]="pct(d.total, maxDia(v))"></span></div><strong class="small">Bs {{ d.total }}</strong></div> } }
            @if (!v.totales.ventas) { <p class="muted small">Sin ventas en el periodo.</p> }
          </section>
          <section class="card pad stack">
            <h3>Por canal</h3>
            @for (c of v.por_canal; track c.canal) { <div class="row between small"><span>{{ c.canal === 'PRESENCIAL' ? 'Caja (POS)' : 'Online' }} · {{ c.ventas }} venta(s) · {{ c.unidades }} prenda(s)</span><strong>Bs {{ c.total }}</strong></div> }
            <h3>Medio de pago</h3>
            @for (m of v.por_metodo; track m.metodo) { <div class="row between small"><span>{{ m.metodo === 'EFECTIVO' ? 'Efectivo' : 'Tarjeta' }} · {{ m.cobros }} cobro(s)</span><strong>Bs {{ m.total }}</strong></div> }
            <h3>Por sucursal</h3>
            @for (s of v.por_sucursal; track s.sucursal_id) { <div class="row between small"><span>{{ s.sucursal }} · {{ s.ventas }} venta(s)</span><strong>Bs {{ s.total }}</strong></div> }
          </section>
        </div>
        <div class="grid cols-2">
          <section class="card pad stack"><h3>Más vendidos</h3>
            @for (p of v.mas_vendidos; track p.producto) { <div class="row between small"><span>{{ p.producto }} · {{ p.unidades }} u.</span><strong>Bs {{ p.ingresos }}</strong></div> } @empty { <p class="muted small">Sin ventas.</p> }</section>
          <section class="card pad stack"><h3>Menos vendidos</h3>
            @for (p of v.menos_vendidos; track p.producto) { <div class="row between small"><span>{{ p.producto }} · {{ p.unidades }} u.</span><strong>Bs {{ p.ingresos }}</strong></div> } @empty { <p class="muted small">Sin ventas.</p> }</section>
        </div>
      }

      @if (pestana() === 'reservas' && reservas(); as r) {
        <div class="grid cols-3" style="margin-bottom:1rem">
          <div class="card pad"><div class="small muted">Reservas</div><div class="cifra">{{ r.total }}</div></div>
          <div class="card pad"><div class="small muted">Completadas</div><div class="cifra">{{ r.completadas }}</div></div>
          <div class="card pad"><div class="small muted">Conversión</div><div class="cifra">{{ r.conversion }}%</div><div class="small muted">reservas en que el cliente se llevó la prenda</div></div>
        </div>
        <div class="grid cols-2">
          <section class="card pad stack"><h3>Por estado</h3>
            @for (e of r.por_estado; track e.estado) { <div class="barra"><span class="small">{{ e.estado }}</span><div class="meter"><span [style.width.%]="(e.cantidad / (r.total || 1)) * 100"></span></div><strong class="small">{{ e.cantidad }}</strong></div> } @empty { <p class="muted small">Sin reservas.</p> }</section>
          <section class="card pad stack"><h3>Por sucursal</h3>
            @for (s of r.por_sucursal; track s.sucursal_id) { <div class="row between small"><span>{{ s.sucursal }}</span><strong>{{ s.reservas }} · {{ s.completadas }} completada(s)</strong></div> } @empty { <p class="muted small">Sin reservas.</p> }</section>
        </div>
      }

      @if (pestana() === 'pagos' && pagos(); as p) {
        <div class="grid cols-3" style="margin-bottom:1rem">
          <div class="card pad"><div class="small muted">Aprobados</div><div class="cifra ok">{{ p.aprobados.cantidad }}</div><div class="small muted">Bs {{ p.aprobados.monto }}</div></div>
          <div class="card pad"><div class="small muted">Rechazados</div><div class="cifra mal">{{ p.rechazados.cantidad }}</div><div class="small muted">Bs {{ p.rechazados.monto }}</div></div>
          <div class="card pad"><div class="small muted">Pendientes de confirmación</div><div class="cifra aviso">{{ p.pendientes_confirmacion.cantidad }}</div><div class="small muted">Bs {{ p.pendientes_confirmacion.monto }}</div></div>
        </div>
        <section class="card table-wrap">
          <h3 style="padding:1rem 1rem 0">Pagos con problemas</h3>
          @if (!p.con_problemas.length) { <div class="empty">No hay pagos rechazados ni pendientes en el periodo.</div> } @else {
            <table><thead><tr><th>Fecha</th><th>Pedido</th><th>Sucursal</th><th>Medio</th><th>Estado</th><th>Motivo</th><th class="right">Monto</th></tr></thead>
              <tbody>@for (x of p.con_problemas; track x.id) {
                <tr><td class="nowrap">{{ x.fecha | date: 'dd/MM HH:mm' }}</td><td>{{ x.pedido }}</td><td>{{ x.sucursal }}</td><td>{{ x.tarjeta || x.metodo }}</td>
                  <td><span class="badge" [class.danger]="x.estado === 'RECHAZADO'" [class.warn]="x.estado !== 'RECHAZADO'">{{ x.estado === 'RECHAZADO' ? 'Rechazado' : 'Pendiente' }}</span></td><td>{{ x.motivo }}</td><td class="right nowrap">Bs {{ x.monto }}</td></tr> }</tbody></table>
          }
        </section>
      }
    </div>`,
  styles: `.cifra { font: 600 1.7rem var(--serif); margin: .2rem 0; } .cifra.ok { color: var(--ok); } .cifra.mal { color: var(--danger); } .cifra.aviso { color: #a06a00; }
    .barra { display: grid; grid-template-columns: 3.2rem 1fr 6rem; gap: .6rem; align-items: center; } .barra strong { text-align: right; }`,
})
export class ReportesPage implements OnInit {
  private api = inject(ReportesApi);
  private admin = inject(AdministracionApi);
  private toast = inject(ToastService);

  readonly pestana = signal<Pestana>('ventas');
  readonly ventas = signal<VentasReporte | null>(null);
  readonly reservas = signal<ReservasReporte | null>(null);
  readonly pagos = signal<PagosReporte | null>(null);
  readonly sucursales = signal<Sucursal[]>([]);
  readonly error = signal('');
  desde = ''; hasta = ''; canal = ''; sucursal: number | null = null;

  ngOnInit() {
    this.admin.sucursales().subscribe((r) => this.sucursales.set(r.sucursales));
    this.cargar();
  }

  ir(p: Pestana) { this.pestana.set(p); this.cargar(); }
  pct(valor: string, maximo: number) { return maximo ? (Number(valor) / maximo) * 100 : 0; }
  maxDia(v: VentasReporte) { return Math.max(...v.por_dia.map((d) => Number(d.total)), 0); }

  cargar() {
    this.error.set('');
    const f = { desde: this.desde, hasta: this.hasta, sucursal: this.sucursal, canal: this.canal };
    const alFallar = (e: unknown) => this.error.set(mensajeError(e));
    if (this.pestana() === 'ventas') this.api.ventas(f).subscribe({ next: (r) => this.ventas.set(r), error: alFallar });
    else if (this.pestana() === 'reservas') this.api.reservas(f).subscribe({ next: (r) => this.reservas.set(r), error: alFallar });
    else this.api.pagos(f).subscribe({ next: (r) => this.pagos.set(r), error: alFallar });
  }

  exportar() {
    const tipo = this.pestana();
    this.api.exportar(tipo, { desde: this.desde, hasta: this.hasta, sucursal: this.sucursal }).subscribe({
      next: (blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = `${tipo}.csv`; a.click(); URL.revokeObjectURL(a.href);
      },
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }
}
