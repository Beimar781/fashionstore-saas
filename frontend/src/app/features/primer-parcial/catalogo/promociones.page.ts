import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CatalogoAdminApi } from '../../../core/api/catalogo-admin.api';
import { Categoria, Coleccion, Promocion } from '../../../core/catalogo.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';
import { alternar } from './catalogo.util';

/** CU-19 · Gestionar promociones y descuentos. Se reflejan en el catálogo (CU-03) y, después, en el punto de venta. */
@Component({
  selector: 'app-promociones',
  imports: [FormsModule],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>Promociones y descuentos</h1><p>Las promociones sin código se aplican solas al precio del catálogo; las que tienen código son cupones.</p></div>
        <button class="btn primary" (click)="abrirNueva()">+ Nueva promoción</button>
      </div>

      <div class="card table-wrap">
        @if (cargando()) { <div class="empty">Cargando…</div> }
        @else if (!promociones().length) { <div class="empty">Aún no hay promociones.</div> }
        @else {
          <table>
            <thead><tr><th>Promoción</th><th>Descuento</th><th>Vigencia</th><th>Alcance</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              @for (p of promociones(); track p.id) {
                <tr>
                  <td><strong>{{ p.nombre }}</strong>@if (p.codigo) { <div class="small muted">Cupón <code>{{ p.codigo }}</code> · {{ p.usos }}{{ p.usos_maximos ? ' / ' + p.usos_maximos : '' }} usos</div> }</td>
                  <td class="nowrap">{{ p.tipo_descuento === 'PORCENTAJE' ? p.valor + ' %' : 'Bs ' + p.valor }}</td>
                  <td class="nowrap">{{ p.inicia }} → {{ p.termina }}</td>
                  <td class="small">{{ alcance(p) }}</td>
                  <td>@if (p.vigente) { <span class="badge ok">Vigente</span> } @else if (!p.activa) { <span class="badge warn">Inactiva</span> } @else { <span class="badge">Fuera de fechas</span> }</td>
                  <td class="actions"><button class="btn sm" (click)="abrirEditar(p)">Editar</button> <button class="btn sm danger" (click)="eliminar(p)">Eliminar</button></td>
                </tr>
              }
            </tbody>
          </table>
        }
      </div>
    </div>

    @if (modal()) {
      <div class="overlay" (click)="modal.set(false)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="guardar()" #f="ngForm" role="dialog" aria-modal="true">
          <header><h2>{{ editandoId ? 'Editar promoción' : 'Nueva promoción' }}</h2><button type="button" class="btn sm ghost" (click)="modal.set(false)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <div class="form-grid">
              <label class="full">Nombre<input name="n" [(ngModel)]="form.nombre" required minlength="2" /></label>
              <label>Tipo<select name="t" [(ngModel)]="form.tipo_descuento"><option value="PORCENTAJE">Porcentaje (%)</option><option value="MONTO">Monto fijo (Bs)</option></select></label>
              <label>Valor<input name="v" type="number" min="0.01" step="0.01" [max]="form.tipo_descuento === 'PORCENTAJE' ? 100 : 100000" [(ngModel)]="form.valor" required /></label>
              <label>Inicia<input name="i" type="date" [(ngModel)]="form.inicia" required /></label>
              <label>Termina<input name="te" type="date" [(ngModel)]="form.termina" required /></label>
              <label>Código de cupón <span class="hint">(opcional)</span><input name="c" [(ngModel)]="form.codigo" minlength="3" maxlength="50" placeholder="VERANO20" /></label>
              <label>Usos máximos <span class="hint">(opcional)</span><input name="u" type="number" min="1" [(ngModel)]="form.usos_maximos" /></label>
              <label class="check"><input name="a" type="checkbox" [(ngModel)]="form.activa" /> Activa</label>
            </div>
            <fieldset>
              <legend>Productos afectados</legend>
              <p class="muted small" style="margin-bottom:.5rem">Sin elegir nada, la promoción aplica a todo el catálogo.</p>
              <p class="small"><strong>Categorías</strong> (incluyen sus subcategorías)</p>
              <div class="chips">@for (c of categorias(); track c.id) { <button type="button" class="chip" [class.sel]="form.categorias_ids.includes(c.id)" (click)="alternar(form.categorias_ids, c.id)">{{ c.nombre }}</button> }</div>
              <p class="small" style="margin-top:.7rem"><strong>Colecciones</strong></p>
              <div class="chips">@for (c of colecciones(); track c.id) { <button type="button" class="chip" [class.sel]="form.colecciones_ids.includes(c.id)" (click)="alternar(form.colecciones_ids, c.id)">{{ c.nombre }}</button> }</div>
            </fieldset>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(false)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !f.valid">Guardar</button></footer>
        </form>
      </div>
    }`,
})
export class PromocionesPage implements OnInit {
  private api = inject(CatalogoAdminApi);
  private toast = inject(ToastService);

  readonly promociones = signal<Promocion[]>([]);
  readonly categorias = signal<Categoria[]>([]);
  readonly colecciones = signal<Coleccion[]>([]);
  readonly cargando = signal(true);
  readonly modal = signal(false);
  readonly guardando = signal(false);
  readonly error = signal('');
  alternar = alternar;
  editandoId = 0;
  form: any = this.vacio();

  ngOnInit() {
    this.api.categorias().subscribe((r) => this.categorias.set(r));
    this.api.colecciones().subscribe((r) => this.colecciones.set(r));
    this.cargar();
  }

  cargar() {
    this.api.promociones().subscribe({
      next: (r) => { this.promociones.set(r); this.cargando.set(false); },
      error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); },
    });
  }

  alcance(p: Promocion) {
    const partes = [
      ...p.categorias_ids.map((id) => this.categorias().find((c) => c.id === id)?.nombre),
      ...p.colecciones_ids.map((id) => this.colecciones().find((c) => c.id === id)?.nombre),
    ].filter(Boolean);
    if (p.productos_ids.length) partes.push(`${p.productos_ids.length} producto(s)`);
    return partes.length ? partes.join(', ') : 'Todo el catálogo';
  }

  abrirNueva() { this.editandoId = 0; this.form = this.vacio(); this.error.set(''); this.modal.set(true); }
  abrirEditar(p: Promocion) {
    this.editandoId = p.id; this.error.set('');
    this.form = { nombre: p.nombre, tipo_descuento: p.tipo_descuento, valor: Number(p.valor), inicia: p.inicia, termina: p.termina, codigo: p.codigo ?? '',
      usos_maximos: p.usos_maximos, activa: p.activa, categorias_ids: [...p.categorias_ids], colecciones_ids: [...p.colecciones_ids], productos_ids: [...p.productos_ids] };
    this.modal.set(true);
  }

  guardar() {
    const cuerpo = { ...this.form, codigo: this.form.codigo?.trim() || null, usos_maximos: this.form.usos_maximos || null };
    this.guardando.set(true); this.error.set('');
    (this.editandoId ? this.api.editarPromocion(this.editandoId, cuerpo) : this.api.crearPromocion(cuerpo)).subscribe({
      next: () => { this.guardando.set(false); this.modal.set(false); this.toast.ok('Promoción guardada.'); this.cargar(); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  eliminar(p: Promocion) {
    if (!confirm(`¿Eliminar la promoción ${p.nombre}?`)) return;
    this.api.eliminarPromocion(p.id).subscribe({ next: () => { this.toast.ok('Promoción eliminada.'); this.cargar(); }, error: (e) => this.toast.error(mensajeError(e)) });
  }

  private vacio() {
    return { nombre: '', tipo_descuento: 'PORCENTAJE', valor: null as number | null, inicia: '', termina: '', codigo: '', usos_maximos: null as number | null,
      activa: true, categorias_ids: [] as number[], colecciones_ids: [] as number[], productos_ids: [] as number[] };
  }
}
