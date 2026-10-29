import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdministracionApi } from '../../core/api/administracion.api';
import { ReportesApi } from '../../core/api/reportes.api';
import { Sucursal } from '../../core/models';
import { Analitica } from '../../core/reportes.models';
import { mensajeError } from '../../core/ui/toast.service';

/** CU-42 · Dashboard analítico con Machine Learning: rotación de productos (KMeans) y pronóstico de demanda a 4 semanas (regresión lineal) con recomendación de reposición. */
@Component({
  selector: 'app-analitica',
  imports: [FormsModule, DatePipe],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Analítica con ML</h1><p>Qué productos rotan más y cuánto se espera vender en las próximas semanas, con modelos de aprendizaje automático (scikit-learn).</p></div></div>
      <form class="card pad row" style="margin-bottom:1rem">
        <label style="max-width:240px">Sucursal<select name="s" [(ngModel)]="sucursal" (ngModelChange)="cargar()"><option [ngValue]="null">Todas</option>@for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }}</option> }</select></label>
      </form>
      @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }

      @if (a(); as x) {
        @if (x.mensaje) { <div class="alert warn" role="status">{{ x.mensaje }}</div> }
        <div class="grid cols-2" style="margin-bottom:1rem">
          <section class="card pad stack"><h3>Unidades por semana (historia y proyección)</h3>
            <div class="columnas" role="img" aria-label="Unidades vendidas por semana y su proyección">
              @for (p of x.serie_total; track p.semana_inicio) { <div class="col" [title]="(p.semana_inicio | date: 'dd/MM') + ': ' + p.unidades + ' u.' + (p.proyectada ? ' (proyectado)' : '')"><span [class.proy]="p.proyectada" [style.height.%]="alto(p.unidades, maxSerie(x))"></span></div> }
            </div>
            <div class="small muted row"><span><i class="cuadro"></i> historia</span><span><i class="cuadro proy"></i> proyección</span></div>
          </section>
          <section class="card pad stack"><h3>Modelos usados</h3>
            <p class="small"><strong>Rotación:</strong> {{ x.modelos['rotacion'] }}.</p>
            <p class="small"><strong>Pronóstico:</strong> {{ x.modelos['pronostico'] }}.</p>
            @if (x.sin_historial_suficiente) { <p class="small muted">{{ x.sin_historial_suficiente }} producto(s) tienen muy pocas semanas de ventas para pronosticar.</p> }
          </section>
        </div>

        <section class="card table-wrap" style="margin-bottom:1rem">
          <h3 style="padding:1rem 1rem 0">Rotación de productos (últimos 30 días)</h3>
          @if (!x.rotacion.length) { <div class="empty">No hay productos con ventas ni stock.</div> } @else {
            <table><thead><tr><th>Producto</th><th class="right">Vendidas</th><th class="right">Por día</th><th class="right">Stock</th><th>Rotación</th></tr></thead>
              <tbody>@for (r of x.rotacion; track r.producto) { <tr><td>{{ r.producto }}</td><td class="right">{{ r.unidades_30d }}</td><td class="right">{{ r.tasa_diaria }}</td><td class="right">{{ r.stock }}</td>
                <td><span class="badge" [class.ok]="r.clase === 'ALTA'" [class.warn]="r.clase === 'MEDIA'" [class.danger]="r.clase === 'BAJA'">{{ r.clase }}</span></td></tr> }</tbody></table>
          }
        </section>

        <h3 style="margin-bottom:.5rem">Pronóstico de demanda por producto</h3>
        <div class="grid cols-2">
          @for (p of x.pronostico; track p.producto) {
            <section class="card pad stack">
              <div class="row between"><strong>{{ p.producto }}</strong><span class="badge" [class.ok]="p.tendencia === 'SUBE'" [class.danger]="p.tendencia === 'BAJA'">Tendencia {{ p.tendencia.toLowerCase() }}</span></div>
              <div class="columnas corto">
                @for (v of p.historial; track $index) { <div class="col" [title]="v + ' u.'"><span [style.height.%]="alto(v, maxProducto(p))"></span></div> }
                @for (v of p.proyeccion; track $index) { <div class="col" [title]="v + ' u. (proyectado)'"><span class="proy" [style.height.%]="alto(v, maxProducto(p))"></span></div> }
              </div>
              <p class="small muted">Próximas {{ x.semanas_proyeccion }} semanas: {{ p.proyeccion.join(' · ') }} u. · stock {{ p.stock }} u. · ajuste del modelo R² {{ p.r2 }}</p>
              <p class="small">{{ p.recomendacion }}</p>
            </section>
          } @empty { <div class="card empty">Aún no hay productos con suficiente historia.</div> }
        </div>
      } @else if (!error()) { <div class="empty">Calculando…</div> }
    </div>`,
  styles: `.columnas { display: flex; align-items: flex-end; gap: 3px; height: 150px; border-bottom: 1px solid var(--line); } .columnas.corto { height: 70px; }
    .col { flex: 1; height: 100%; display: flex; align-items: flex-end; } .col span { display: block; width: 100%; background: var(--accent); border-radius: 3px 3px 0 0; min-height: 1px; }
    .col span.proy { background: repeating-linear-gradient(45deg, var(--accent-soft, #e9d9f2), var(--accent-soft, #e9d9f2) 3px, var(--accent) 3px, var(--accent) 5px); opacity: .75; }
    .cuadro { display: inline-block; width: .8rem; height: .8rem; background: var(--accent); border-radius: 2px; margin-right: .3rem; vertical-align: middle; } .cuadro.proy { opacity: .5; }`,
})
export class AnaliticaPage implements OnInit {
  private api = inject(ReportesApi);
  private admin = inject(AdministracionApi);

  readonly a = signal<Analitica | null>(null);
  readonly sucursales = signal<Sucursal[]>([]);
  readonly error = signal('');
  sucursal: number | null = null;

  ngOnInit() { this.admin.sucursales().subscribe((r) => this.sucursales.set(r.sucursales)); this.cargar(); }

  cargar() {
    this.error.set(''); this.a.set(null);
    this.api.analitica(this.sucursal).subscribe({ next: (r) => this.a.set(r), error: (e) => this.error.set(mensajeError(e)) });
  }

  alto(valor: number, maximo: number) { return maximo ? (valor / maximo) * 100 : 0; }
  maxSerie(x: Analitica) { return Math.max(...x.serie_total.map((p) => p.unidades), 0); }
  maxProducto(p: Analitica['pronostico'][number]) { return Math.max(...p.historial, ...p.proyeccion, 0); }
}
