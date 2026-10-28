import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { CatalogoAdminApi } from '../../core/api/catalogo-admin.api';
import { CatalogoApi } from '../../core/api/catalogo.api';
import { InventarioApi } from '../../core/api/inventario.api';
import { Categoria, Temporada } from '../../core/catalogo.models';
import { ESTADOS_EXISTENCIA, EstadoExistencia, FilaInventario, InventarioPagina } from '../../core/inventario.models';
import { ROL } from '../../core/models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** CU-20 · Inventario global (Administrador) y CU-26 · Inventario de la sucursal (Encargado): la misma consulta, con ajustes solo en la sucursal. */
@Component({
  selector: 'app-inventario',
  imports: [FormsModule, RouterLink],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>{{ esEncargado ? 'Inventario de la sucursal' : 'Inventario global' }}</h1>
          <p>{{ esEncargado ? 'Disponibilidad de su sucursal: registre ajustes y defina el mínimo de reposición.' : 'Existencias de todas las sucursales: disponibles, reservadas, vendidas, agotadas y próximas a ingresar.' }}</p></div>
        <a class="btn" [routerLink]="rutaMovimientos">Ver movimientos</a>
      </div>

      @if (datos(); as d) {
        <div class="resumen">
          <div class="card pad"><span class="muted small">Disponibles</span><strong>{{ d.resumen.disponibles }}</strong></div>
          <div class="card pad"><span class="muted small">Reservadas</span><strong>{{ d.resumen.reservadas }}</strong></div>
          <div class="card pad"><span class="muted small">Vendidas</span><strong>{{ d.resumen.vendidas }}</strong></div>
          <div class="card pad"><span class="muted small">Agotadas (variantes)</span><strong [class.rojo]="d.resumen.agotadas > 0">{{ d.resumen.agotadas }}</strong></div>
          <div class="card pad"><span class="muted small">Próximas a ingresar</span><strong>{{ d.resumen.proximas_a_ingresar }}</strong></div>
        </div>
        @if (d.por_sucursal.length) {
          <div class="card table-wrap" style="margin-bottom:1rem"><table>
            <thead><tr><th>Sucursal</th><th class="right">Disponibles</th><th class="right">Reservadas</th><th class="right">Vendidas</th></tr></thead>
            <tbody>@for (s of d.por_sucursal; track s.sucursal_id) { <tr><td><strong>{{ s.sucursal }}</strong></td><td class="right">{{ s.disponibles }}</td><td class="right">{{ s.reservadas }}</td><td class="right">{{ s.vendidas }}</td></tr> }</tbody>
          </table></div>
        }
      }

      <form class="card pad stack" style="margin-bottom:1rem" (ngSubmit)="buscar()">
        <div class="row">
          <input name="q" [(ngModel)]="f.q" placeholder="Buscar por producto o SKU…" style="flex:1;min-width:200px" />
          <select name="c" [(ngModel)]="f.categoria_id" (ngModelChange)="buscar()" style="width:auto"><option [ngValue]="null">Todas las categorías</option>@for (c of categorias(); track c.id) { <option [ngValue]="c.id">{{ c.nombre }}</option> }</select>
          <select name="t" [(ngModel)]="f.temporada_id" (ngModelChange)="buscar()" style="width:auto"><option [ngValue]="null">Todas las temporadas</option>@for (t of temporadas(); track t.id) { <option [ngValue]="t.id">{{ t.nombre }}</option> }</select>
          @if (!esEncargado) { <select name="s" [(ngModel)]="f.sucursal" (ngModelChange)="buscar()" style="width:auto"><option [ngValue]="null">Todas las sucursales</option>@for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }}</option> }</select> }
          <button class="btn">Buscar</button>
        </div>
        <div class="chips">
          <button type="button" class="chip" [class.sel]="!f.estado" (click)="elegirEstado('')">Todas</button>
          @for (e of estados; track e.valor) { <button type="button" class="chip" [class.sel]="f.estado === e.valor" (click)="elegirEstado(e.valor)">{{ e.texto }}</button> }
          @if (esEncargado) { <label class="check"><input type="checkbox" name="bm" [(ngModel)]="f.solo_bajo_minimo" (ngModelChange)="buscar()" /> Solo bajo el mínimo</label> }
        </div>
      </form>

      <div class="card table-wrap">
        @if (cargando()) { <div class="empty">Cargando…</div> }
        @else if (!datos()?.items?.length) { <div class="empty">No hay variantes con esos filtros.</div> }
        @else {
          <table>
            <thead><tr><th>Producto</th><th>Talla</th><th>Color</th><th class="right">Disp.</th><th class="right">Reserv.</th><th class="right">Vend.</th><th class="right">Próx.</th>@if (esEncargado) { <th class="right">Mínimo</th> }<th>Estado</th>@if (esEncargado) { <th></th> }</tr></thead>
            <tbody>
              @for (r of datos()!.items; track r.variante_id) {
                <tr>
                  <td><strong>{{ r.producto }}</strong><div class="muted small">{{ r.sku }} · {{ r.categoria }}</div></td>
                  <td>{{ r.talla }}</td><td>{{ r.color }}</td>
                  <td class="right"><strong>{{ r.disponible }}</strong></td><td class="right">{{ r.reservada }}</td><td class="right">{{ r.vendida }}</td><td class="right">{{ r.proxima }}</td>
                  @if (esEncargado) { <td class="right">{{ r.umbral_minimo }}</td> }
                  <td>@if (r.agotada) { <span class="badge danger">Agotada</span> } @else if (r.bajo_minimo) { <span class="badge warn">Bajo mínimo</span> } @else { <span class="badge ok">Disponible</span> }
                    @if (r.proxima > 0) { <span class="badge accent">Viene en camino</span> }</td>
                  @if (esEncargado) { <td class="actions"><button class="btn sm" (click)="abrirAjuste(r)">Ajustar</button> <button class="btn sm" (click)="abrirUmbral(r)">Mínimo</button></td> }
                </tr>
              }
            </tbody>
          </table>
          <div class="row between" style="padding:.7rem 1rem">
            <span class="muted small">{{ datos()!.total }} variantes · página {{ datos()!.pagina }} de {{ paginas() }}</span>
            <div class="row"><button class="btn sm" [disabled]="datos()!.pagina <= 1" (click)="irA(datos()!.pagina - 1)">Anterior</button><button class="btn sm" [disabled]="datos()!.pagina >= paginas()" (click)="irA(datos()!.pagina + 1)">Siguiente</button></div>
          </div>
        }
      </div>
    </div>

    @if (modal(); as m) {
      <div class="overlay" (click)="modal.set(null)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="guardar()" #g="ngForm" role="dialog" aria-modal="true">
          <header><h2>{{ m === 'ajuste' ? 'Ajustar existencias' : 'Mínimo de reposición' }}</h2><button type="button" class="btn sm ghost" (click)="modal.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <p><strong>{{ fila?.producto }}</strong> · {{ fila?.talla }} · {{ fila?.color }} <span class="muted small">({{ fila?.disponible }} disponibles)</span></p>
            @if (m === 'ajuste') {
              <div class="form-grid">
                <label>Tipo<select name="tp" [(ngModel)]="ajuste.tipo"><option value="AJUSTE_ENTRADA">Entrada (suma)</option><option value="AJUSTE_SALIDA">Salida (resta)</option></select></label>
                <label>Cantidad<input name="ct" type="number" min="1" [(ngModel)]="ajuste.cantidad" required /></label>
                <label class="full">Motivo<input name="nt" [(ngModel)]="ajuste.nota" required minlength="3" placeholder="Conteo físico, prenda dañada…" /></label>
              </div>
            } @else {
              <label>Avisar cuando queden este número de unidades o menos<input name="um" type="number" min="0" [(ngModel)]="umbral" required /></label>
            }
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(null)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !g.valid">Guardar</button></footer>
        </form>
      </div>
    }`,
  styles: `
    .resumen { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .8rem; margin-bottom: 1rem; }
    .resumen .card { display: grid; gap: .1rem; } .resumen strong { font-size: 1.6rem; font-family: var(--serif); } .rojo { color: var(--danger); }`,
})
export class InventarioPage implements OnInit {
  private api = inject(InventarioApi);
  private catalogo = inject(CatalogoAdminApi);
  private publico = inject(CatalogoApi);
  private toast = inject(ToastService);
  readonly esEncargado = inject(AuthService).rol() === ROL.ENCARGADO;

  readonly estados = ESTADOS_EXISTENCIA;
  readonly rutaMovimientos = this.esEncargado ? '/sucursal/movimientos' : '/empresa/inventario/movimientos';
  readonly datos = signal<InventarioPagina | null>(null);
  readonly paginas = computed(() => Math.max(1, Math.ceil((this.datos()?.total ?? 0) / (this.datos()?.tamano ?? 25))));
  readonly categorias = signal<Categoria[]>([]);
  readonly temporadas = signal<Temporada[]>([]);
  readonly sucursales = signal<{ id: number; nombre: string }[]>([]);
  readonly cargando = signal(true);
  readonly modal = signal<'ajuste' | 'umbral' | null>(null);
  readonly guardando = signal(false);
  readonly error = signal('');
  f: { q: string; categoria_id: number | null; temporada_id: number | null; estado: EstadoExistencia | ''; sucursal: number | null; solo_bajo_minimo: boolean } =
    { q: '', categoria_id: null, temporada_id: null, estado: '', sucursal: null, solo_bajo_minimo: false };
  fila: FilaInventario | null = null;
  ajuste = { tipo: 'AJUSTE_ENTRADA', cantidad: 1, nota: '' };
  umbral = 0;

  ngOnInit() {
    this.catalogo.categorias().subscribe((r) => this.categorias.set(r));
    this.catalogo.temporadas().subscribe((r) => this.temporadas.set(r));
    if (!this.esEncargado) this.publico.sucursales().subscribe((r) => this.sucursales.set(r));
    this.irA(1);
  }

  buscar() { this.irA(1); }
  elegirEstado(e: EstadoExistencia | '') { this.f.estado = e; this.buscar(); }
  irA(pagina: number) {
    this.cargando.set(true);
    const consulta = this.esEncargado ? this.api.deMiSucursal({ ...this.f, q: this.f.q.trim(), pagina }) : this.api.global({ ...this.f, q: this.f.q.trim(), pagina });
    consulta.subscribe({
      next: (r) => { this.datos.set(r); this.cargando.set(false); },
      error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); },
    });
  }

  abrirAjuste(r: FilaInventario) { this.fila = r; this.ajuste = { tipo: 'AJUSTE_ENTRADA', cantidad: 1, nota: '' }; this.error.set(''); this.modal.set('ajuste'); }
  abrirUmbral(r: FilaInventario) { this.fila = r; this.umbral = r.umbral_minimo ?? 0; this.error.set(''); this.modal.set('umbral'); }

  guardar() {
    const r = this.fila!;
    this.guardando.set(true); this.error.set('');
    const op = this.modal() === 'ajuste' ? this.api.ajustar({ variante_id: r.variante_id, ...this.ajuste }) : this.api.fijarUmbral(r.variante_id, this.umbral);
    op.subscribe({
      next: () => { this.guardando.set(false); this.modal.set(null); this.toast.ok('Inventario actualizado.'); this.irA(this.datos()?.pagina ?? 1); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }
}
