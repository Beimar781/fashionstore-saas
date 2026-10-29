import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdministracionApi } from '../../core/api/administracion.api';
import { ReportesApi } from '../../core/api/reportes.api';
import { Sucursal } from '../../core/models';
import { Indicador, Indicadores } from '../../core/reportes.models';
import { mensajeError } from '../../core/ui/toast.service';

/** CU-22 · Indicadores empresariales: el panel del Administrador, con cada cifra comparada con el periodo anterior. */
@Component({
  selector: 'app-indicadores',
  imports: [FormsModule, DatePipe, DecimalPipe],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Indicadores</h1><p>Panel de la empresa. Las ventas son netas de devoluciones y cambios.</p></div></div>
      <form class="card pad row" style="margin-bottom:1rem" (ngSubmit)="cargar()">
        <label style="max-width:190px">Periodo<select name="p" [(ngModel)]="dias" (ngModelChange)="cargar()">@for (d of periodos; track d) { <option [ngValue]="d">Últimos {{ d }} días</option> }</select></label>
        <label style="max-width:220px">Sucursal<select name="s" [(ngModel)]="sucursal" (ngModelChange)="cargar()"><option [ngValue]="null">Todas</option>@for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }}</option> }</select></label>
      </form>
      @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }

      @if (i(); as x) {
        <div class="grid cols-3" style="margin-bottom:1rem">
          @for (k of kpis(x); track k.titulo) {
            <div class="card pad"><div class="small muted">{{ k.titulo }}</div><div class="cifra">{{ k.prefijo }}{{ k.ind.valor | number: k.formato }}{{ k.sufijo }}</div>
              <div class="small"><span class="badge" [class.ok]="(k.ind.variacion ?? 0) > 0" [class.danger]="(k.ind.variacion ?? 0) < 0">{{ variacion(k.ind) }}</span> <span class="muted">vs. periodo anterior ({{ k.prefijo }}{{ k.ind.anterior | number: k.formato }}{{ k.sufijo }})</span></div></div>
          }
          <div class="card pad"><div class="small muted">Inventario</div><div class="cifra">{{ x.stock.disponibles | number }}</div>
            <div class="small muted">disponibles · {{ x.stock.reservadas }} reservadas · {{ x.stock.agotadas }} variantes agotadas · {{ x.productos_activos }} productos activos</div></div>
        </div>

        <div class="grid cols-2" style="margin-bottom:1rem">
          <section class="card pad stack"><h3>Ventas por día</h3>
            <div class="columnas" role="img" [attr.aria-label]="'Ventas por día, máximo Bs ' + maximo(x)">
              @for (d of x.ventas_por_dia; track d.fecha) { <div class="col" [title]="(d.fecha | date: 'dd/MM') + ': Bs ' + d.total + ' (' + d.ventas + ' venta(s))'"><span [style.height.%]="altura(d.total, x)"></span></div> }
            </div>
            <div class="row between small muted"><span>{{ x.desde | date: 'dd/MM' }}</span><span>{{ x.hasta | date: 'dd/MM' }}</span></div>
          </section>
          <section class="card pad stack">
            <h3>Por canal</h3>
            @for (c of x.por_canal; track c.canal) { <div class="row between small"><span>{{ c.canal === 'PRESENCIAL' ? 'Caja (POS)' : 'Online' }} · {{ c.ventas }} venta(s)</span><strong>Bs {{ c.total }}</strong></div> } @empty { <p class="muted small">Sin ventas.</p> }
            <h3>Por sucursal</h3>
            @for (s of x.por_sucursal; track s.sucursal_id) { <div class="row between small"><span>{{ s.sucursal }} · {{ s.ventas }} venta(s)</span><strong>Bs {{ s.total }}</strong></div> } @empty { <p class="muted small">Sin ventas.</p> }
            <h3>Reservas por estado</h3>
            @for (e of x.reservas_por_estado; track e.estado) { <div class="row between small"><span>{{ e.estado }}</span><strong>{{ e.cantidad }}</strong></div> } @empty { <p class="muted small">Sin reservas.</p> }
          </section>
        </div>

        <div class="grid cols-2">
          <section class="card pad stack"><h3>Más vendidos</h3>
            @for (p of x.mas_vendidos; track p.producto) { <div class="row between small"><span>{{ p.producto }} · {{ p.unidades }} u.</span><strong>Bs {{ p.ingresos }}</strong></div> } @empty { <p class="muted small">Sin ventas.</p> }
            <h3>Alertas de stock bajo</h3>
            @for (s of x.stock_bajo_items; track s.sku + s.sucursal) { <div class="row between small"><span>{{ s.sucursal }} · {{ s.producto }} ({{ s.sku }})</span><span class="badge danger">{{ s.disponible }} / mín. {{ s.umbral }}</span></div> } @empty { <p class="muted small">Ninguna alerta.</p> }
          </section>
          <section class="card pad stack"><h3>Últimas ventas</h3>
            @for (v of x.ultimas_ventas; track v.id) { <div class="row between small"><span>{{ v.comprobante ?? v.codigo }} · {{ v.sucursal }} · {{ v.canal === 'PRESENCIAL' ? 'Caja' : 'Online' }} · {{ v.fecha | date: 'dd/MM HH:mm' }}</span><strong>Bs {{ v.total }}</strong></div> } @empty { <p class="muted small">Sin ventas.</p> }
          </section>
        </div>
      } @else if (!error()) { <div class="empty">Cargando…</div> }
    </div>`,
  styles: `.cifra { font: 600 1.7rem var(--serif); margin: .2rem 0; }
    .columnas { display: flex; align-items: flex-end; gap: 2px; height: 140px; border-bottom: 1px solid var(--line); }
    .col { flex: 1; height: 100%; display: flex; align-items: flex-end; } .col span { display: block; width: 100%; background: var(--accent); border-radius: 3px 3px 0 0; min-height: 1px; }`,
})
export class IndicadoresPage implements OnInit {
  private api = inject(ReportesApi);
  private admin = inject(AdministracionApi);

  readonly periodos = [7, 14, 30, 90];
  readonly i = signal<Indicadores | null>(null);
  readonly sucursales = signal<Sucursal[]>([]);
  readonly error = signal('');
  dias = 30; sucursal: number | null = null;

  ngOnInit() { this.admin.sucursales().subscribe((r) => this.sucursales.set(r.sucursales)); this.cargar(); }

  cargar() {
    this.error.set('');
    this.api.indicadores(this.dias, this.sucursal).subscribe({ next: (r) => this.i.set(r), error: (e) => this.error.set(mensajeError(e)) });
  }

  kpis(x: Indicadores) {
    return [
      { titulo: 'Ventas netas', ind: x.ventas_netas, prefijo: 'Bs ', sufijo: '', formato: '1.2-2' },
      { titulo: 'Ventas', ind: x.ventas, prefijo: '', sufijo: '', formato: '1.0-0' },
      { titulo: 'Ticket promedio', ind: x.ticket_promedio, prefijo: 'Bs ', sufijo: '', formato: '1.2-2' },
      { titulo: 'Reservas', ind: x.reservas, prefijo: '', sufijo: '', formato: '1.0-0' },
      { titulo: 'Conversión de reservas', ind: x.conversion_reservas, prefijo: '', sufijo: '%', formato: '1.0-1' },
    ];
  }
  variacion(k: Indicador) { return k.variacion === null ? 'sin comparación' : `${k.variacion > 0 ? '▲ +' : k.variacion < 0 ? '▼ ' : ''}${k.variacion}%`; }
  maximo(x: Indicadores) { return Math.max(...x.ventas_por_dia.map((d) => Number(d.total)), 0); }
  altura(total: string, x: Indicadores) { const m = this.maximo(x); return m ? (Number(total) / m) * 100 : 0; }
}
