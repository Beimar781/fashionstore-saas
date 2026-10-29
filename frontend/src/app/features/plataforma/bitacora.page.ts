import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { BitacoraApi, FiltrosBitacora, OpcionesBitacora, PaginaBitacora } from '../../core/api/bitacora.api';
import { mensajeError } from '../../core/ui/toast.service';

/** Bitácora del sistema. El Administrador ve las operaciones de su empresa; el SuperAdministrador, las de todas las empresas (con filtro y columna Empresa) y las de la plataforma. Solo lectura. */
@Component({
  selector: 'app-bitacora',
  imports: [FormsModule, DatePipe],
  template: `
    <div class="page">
      <div class="page-head">
        <div style="display:flex;align-items:center;gap:.8rem"><h1>Bitácora</h1>@if (datos(); as d) { <span class="badge">{{ d.total }} {{ d.total === 1 ? 'registro' : 'registros' }}</span> }</div>
      </div>

      <section class="card pad stack">
        <h2>Operaciones registradas en el sistema</h2>
        <form class="filtros" (ngSubmit)="filtrar()" role="search">
          <label>Usuario<select name="u" [(ngModel)]="f.usuario"><option value="">Todos</option>@for (u of opciones()?.usuarios ?? []; track u) { <option [value]="u">{{ u }}</option> }</select></label>
          @if (general) { <label>Empresa<select name="e" [(ngModel)]="f.empresa"><option value="">Todas</option><option value="plataforma">Plataforma</option>@for (e of opciones()?.empresas ?? []; track e.id) { <option [value]="'' + e.id">{{ e.nombre }}</option> }</select></label> }
          <label>Entidad<select name="n" [(ngModel)]="f.entidad"><option value="">Todas</option>@for (n of opciones()?.entidades ?? []; track n) { <option [value]="n">{{ n }}</option> }</select></label>
          <label>Acción<select name="a" [(ngModel)]="f.accion"><option value="">Todas</option>@for (a of opciones()?.acciones ?? []; track a.codigo) { <option [value]="a.codigo">{{ a.texto }}</option> }</select></label>
          <label>Desde<input name="d" type="date" [(ngModel)]="f.desde" /></label>
          <label>Hasta (incluye todo el día)<input name="h" type="date" [(ngModel)]="f.hasta" /></label>
          <label>Buscar en el detalle o la IP<input name="q" type="search" [(ngModel)]="f.q" maxlength="100" placeholder="Ej.: reserva o 203.0.113" /></label>
          <div class="botones"><button class="btn primary">Filtrar</button><button type="button" class="btn ghost" (click)="limpiar()">Limpiar</button></div>
        </form>
        @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }

        <div class="table-wrap">
          <table class="bitacora">
            <thead><tr><th>Fecha y hora</th>@if (general) { <th>Empresa</th> }<th>Usuario</th><th>Acción</th><th>Entidad</th><th>Detalle</th><th>IP</th></tr></thead>
            <tbody>
              @for (r of datos()?.items ?? []; track r.id) {
                <tr>
                  <td class="nowrap">{{ r.fecha | date: 'dd/MM/yyyy HH:mm:ss' }}</td>
                  @if (general) { <td>{{ r.empresa }}</td> }
                  <td>{{ r.usuario }}@if (r.rol) { <div class="small muted">{{ r.rol }}</div> }</td>
                  <td><span class="etiqueta" [class]="'etiqueta accion-' + r.tono" [title]="r.accion">{{ r.accion_texto }}</span></td>
                  <td>{{ r.entidad }}</td>
                  <td class="detalle">{{ r.detalle }}</td>
                  <td class="nowrap">{{ r.ip ?? '—' }}</td>
                </tr>
              } @empty { <tr><td [attr.colspan]="general ? 7 : 6" class="empty">No hay registros con esos filtros.</td></tr> }
            </tbody>
          </table>
        </div>

        @if (paginas() > 1) {
          <div class="row between">
            <button class="btn" (click)="ir(f.pagina! - 1)" [disabled]="f.pagina! <= 1">← Anterior</button>
            <span class="small muted">Página {{ f.pagina }} de {{ paginas() }}</span>
            <button class="btn" (click)="ir(f.pagina! + 1)" [disabled]="f.pagina! >= paginas()">Siguiente →</button>
          </div>
        }
      </section>
    </div>`,
  styles: `
    .filtros { display: grid; gap: .8rem 1rem; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); align-items: end; }
    .botones { display: flex; gap: .6rem; flex-wrap: wrap; }
    .bitacora { font-size: .88rem; } .bitacora .detalle { min-width: 16rem; max-width: 34rem; overflow-wrap: anywhere; }
    .etiqueta { display: inline-block; white-space: nowrap; border: 1px solid; border-radius: 999px; padding: .1rem .6rem; font-size: .78rem; font-weight: 600; }
    .accion-verde { background: #ddf3e8; color: #11643f; border-color: #a9dec6; } .accion-gris { background: #eceff2; color: #4c5b69; border-color: #d3d9df; }
    .accion-azul { background: #e3eefb; color: #1f4f8f; border-color: #b9d2f0; } .accion-ambar { background: #fdf0d5; color: #8a5a00; border-color: #efd5a5; }
    .accion-rojo { background: #fbe3e3; color: #9c2b2b; border-color: #efb4b4; } .accion-morado { background: #efe6fb; color: #5b2f9a; border-color: #d3bff0; }`,
})
export class BitacoraPage implements OnInit {
  private api = inject(BitacoraApi);
  readonly general = !!inject(ActivatedRoute).snapshot.data['general'];  // SuperAdministrador: todas las empresas

  readonly datos = signal<PaginaBitacora | null>(null);
  readonly opciones = signal<OpcionesBitacora | null>(null);
  readonly error = signal('');
  readonly paginas = computed(() => Math.max(1, Math.ceil((this.datos()?.total ?? 0) / (this.f.tamano ?? 25))));
  f: FiltrosBitacora = { usuario: '', entidad: '', accion: '', desde: '', hasta: '', q: '', empresa: '', pagina: 1, tamano: 25 };

  ngOnInit() {
    this.api.opciones(this.general).subscribe({ next: (o) => this.opciones.set(o), error: (e) => this.error.set(mensajeError(e)) });
    this.cargar();
  }

  cargar() {
    this.error.set('');
    this.api.consultar(this.general, this.f).subscribe({ next: (d) => this.datos.set(d), error: (e) => this.error.set(mensajeError(e)) });
  }

  filtrar() { this.f.pagina = 1; this.cargar(); }
  limpiar() { this.f = { usuario: '', entidad: '', accion: '', desde: '', hasta: '', q: '', empresa: '', pagina: 1, tamano: 25 }; this.cargar(); }
  ir(pagina: number) { this.f.pagina = pagina; this.cargar(); }
}
