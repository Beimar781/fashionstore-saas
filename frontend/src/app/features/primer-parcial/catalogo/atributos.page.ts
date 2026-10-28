import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { CatalogoAdminApi } from '../../../core/api/catalogo-admin.api';
import { Categoria, ColorCatalogo, GrupoTalla, Marca, Talla } from '../../../core/catalogo.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';

type Pestana = 'categorias' | 'tallas' | 'colores' | 'marcas';
type Modal = 'categoria' | 'grupo' | 'talla' | 'color' | 'marca' | null;

/** CU-16 · Gestionar categorías, tallas y colores (más marcas). Solo el Administrador escribe. */
@Component({
  selector: 'app-atributos',
  imports: [FormsModule],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Categorías, tallas y colores</h1><p>Atributos que se asignan a las prendas del catálogo.</p></div></div>

      <div class="tabs" role="tablist">
        @for (p of pestanas; track p.id) { <button role="tab" [class.activa]="pestana() === p.id" (click)="pestana.set(p.id)">{{ p.texto }}</button> }
      </div>

      @switch (pestana()) {
        @case ('categorias') {
          <div class="row between" style="margin-bottom:.8rem"><span class="muted small">{{ categorias().length }} categorías</span><button class="btn primary" (click)="nuevaCategoria()">+ Nueva categoría</button></div>
          <div class="card table-wrap">
            @if (!categorias().length) { <div class="empty">Aún no hay categorías.</div> } @else {
              <table>
                <thead><tr><th>Categoría</th><th>Grupo de tallas</th><th>Orden</th><th>Estado</th><th></th></tr></thead>
                <tbody>
                  @for (c of categoriasOrdenadas(); track c.c.id) {
                    <tr>
                      <td [style.padding-left.rem]="1 + c.nivel * 1.4"><strong>{{ c.nivel ? '↳ ' : '' }}{{ c.c.nombre }}</strong></td>
                      <td>{{ nombreGrupo(c.c.grupo_talla_id) }}</td><td>{{ c.c.orden }}</td>
                      <td><span class="badge" [class.ok]="c.c.activa" [class.warn]="!c.c.activa">{{ c.c.activa ? 'Activa' : 'Inactiva' }}</span></td>
                      <td class="actions"><button class="btn sm" (click)="editarCategoria(c.c)">Editar</button> <button class="btn sm danger" (click)="eliminar('categoría', api.eliminarCategoria(c.c.id))">Eliminar</button></td>
                    </tr>
                  }
                </tbody>
              </table>
            }
          </div>
        }
        @case ('tallas') {
          <div class="row between" style="margin-bottom:.8rem"><span class="muted small">Cada categoría usa un grupo de tallas (no se mezclan S/M con 28/30).</span><button class="btn primary" (click)="nuevoGrupo()">+ Nuevo grupo</button></div>
          <div class="grid cols-2">
            @for (g of grupos(); track g.id) {
              <section class="card pad stack">
                <div class="row between"><div><h3>{{ g.nombre }}</h3>@if (g.descripcion) { <p class="muted small">{{ g.descripcion }}</p> }</div>
                  <div class="row"><button class="btn sm" (click)="nuevaTalla(g)">+ Talla</button><button class="btn sm danger" (click)="eliminar('grupo de tallas', api.eliminarGrupo(g.id))">Eliminar</button></div></div>
                <div class="chips">
                  @for (t of g.tallas; track t.id) { <button class="chip" (click)="editarTalla(t)" title="Editar talla (orden {{ t.orden }})">{{ t.codigo }}</button> }
                  @empty { <span class="muted small">Sin tallas todavía.</span> }
                </div>
              </section>
            } @empty { <div class="card empty">Aún no hay grupos de tallas.</div> }
          </div>
        }
        @case ('colores') {
          <div class="row between" style="margin-bottom:.8rem"><span class="muted small">El código corto se usa en el SKU y no cambia al renombrar el color.</span><button class="btn primary" (click)="nuevoColor()">+ Nuevo color</button></div>
          <div class="card table-wrap">
            @if (!colores().length) { <div class="empty">Aún no hay colores.</div> } @else {
              <table>
                <thead><tr><th>Color</th><th>Código SKU</th><th>Hexadecimal</th><th></th></tr></thead>
                <tbody>
                  @for (c of colores(); track c.id) {
                    <tr><td><span class="swatch" [style.background]="c.codigo_hex"></span> <strong>{{ c.nombre }}</strong></td><td>{{ c.codigo }}</td><td>{{ c.codigo_hex }}</td>
                      <td class="actions"><button class="btn sm" (click)="editarColor(c)">Editar</button> <button class="btn sm danger" (click)="eliminar('color', api.eliminarColor(c.id))">Eliminar</button></td></tr>
                  }
                </tbody>
              </table>
            }
          </div>
        }
        @case ('marcas') {
          <div class="row between" style="margin-bottom:.8rem"><span class="muted small">{{ marcas().length }} marcas</span><button class="btn primary" (click)="nuevaMarca()">+ Nueva marca</button></div>
          <div class="card table-wrap">
            @if (!marcas().length) { <div class="empty">Aún no hay marcas.</div> } @else {
              <table><thead><tr><th>Marca</th><th></th></tr></thead><tbody>
                @for (m of marcas(); track m.id) { <tr><td><strong>{{ m.nombre }}</strong></td><td class="actions"><button class="btn sm danger" (click)="eliminar('marca', api.eliminarMarca(m.id))">Eliminar</button></td></tr> }
              </tbody></table>
            }
          </div>
        }
      }
    </div>

    @if (modal()) {
      <div class="overlay" (click)="modal.set(null)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="guardar()" #f="ngForm" role="dialog" aria-modal="true">
          <header><h2>{{ titulo() }}</h2><button type="button" class="btn sm ghost" (click)="modal.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <div class="form-grid">
              @switch (modal()) {
                @case ('categoria') {
                  <label class="full">Nombre<input name="n" [(ngModel)]="form.nombre" required minlength="2" /></label>
                  <label>Categoría padre
                    <select name="p" [(ngModel)]="form.padre_id"><option [ngValue]="null">Ninguna (principal)</option>
                      @for (c of categorias(); track c.id) { @if (c.id !== editandoId) { <option [ngValue]="c.id">{{ c.nombre }}</option> } }</select></label>
                  <label>Grupo de tallas
                    <select name="g" [(ngModel)]="form.grupo_talla_id"><option [ngValue]="null">Heredar de la categoría padre</option>
                      @for (g of grupos(); track g.id) { <option [ngValue]="g.id">{{ g.nombre }}</option> }</select></label>
                  <label>Orden<input name="o" type="number" min="0" [(ngModel)]="form.orden" /></label>
                  <label class="check"><input name="a" type="checkbox" [(ngModel)]="form.activa" /> Activa (visible para los clientes)</label>
                }
                @case ('grupo') {
                  <label class="full">Nombre del grupo<input name="n" [(ngModel)]="form.nombre" required minlength="2" placeholder="Ropa superior" /></label>
                  <label class="full">Descripción<input name="d" [(ngModel)]="form.descripcion" /></label>
                }
                @case ('talla') {
                  <label>Código<input name="c" [(ngModel)]="form.codigo" required maxlength="8" placeholder="M, 32, 38.5" /></label>
                  <label>Orden<input name="o" type="number" min="0" [(ngModel)]="form.orden" /><span class="hint">Define cómo se ordenan (S, M, L, XL).</span></label>
                }
                @case ('color') {
                  <label class="full">Nombre<input name="n" [(ngModel)]="form.nombre" required minlength="2" /></label>
                  <label>Color<input name="h" type="color" [(ngModel)]="form.codigo_hex" style="height:2.6rem;padding:.2rem" /></label>
                  <label>Hexadecimal<input name="hx" [(ngModel)]="form.codigo_hex" required pattern="#[0-9A-Fa-f]{6}" /></label>
                }
                @case ('marca') {
                  <label class="full">Nombre de la marca<input name="n" [(ngModel)]="form.nombre" required minlength="2" /></label>
                }
              }
            </div>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(null)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !f.valid">Guardar</button></footer>
        </form>
      </div>
    }`,
})
export class AtributosPage implements OnInit {
  readonly api = inject(CatalogoAdminApi);
  private toast = inject(ToastService);

  readonly pestanas: { id: Pestana; texto: string }[] = [
    { id: 'categorias', texto: 'Categorías' }, { id: 'tallas', texto: 'Tallas' }, { id: 'colores', texto: 'Colores' }, { id: 'marcas', texto: 'Marcas' },
  ];
  readonly pestana = signal<Pestana>('categorias');
  readonly categorias = signal<Categoria[]>([]);
  readonly grupos = signal<GrupoTalla[]>([]);
  readonly colores = signal<ColorCatalogo[]>([]);
  readonly marcas = signal<Marca[]>([]);
  readonly modal = signal<Modal>(null);
  readonly guardando = signal(false);
  readonly error = signal('');
  editandoId = 0;
  grupoId = 0;
  form: any = {};

  /** Categorías en orden de árbol (padre y luego sus hijas), con su nivel de sangría. */
  readonly categoriasOrdenadas = computed(() => {
    const todas = this.categorias(), salida: { c: Categoria; nivel: number }[] = [];
    const agregar = (padreId: number | null, nivel: number) => {
      for (const c of todas.filter((x) => x.padre_id === padreId)) { salida.push({ c, nivel }); agregar(c.id, nivel + 1); }
    };
    agregar(null, 0);
    return salida;
  });

  readonly titulo = computed(() => {
    const nuevo = !this.editandoId;
    switch (this.modal()) {
      case 'categoria': return nuevo ? 'Nueva categoría' : 'Editar categoría';
      case 'grupo': return 'Nuevo grupo de tallas';
      case 'talla': return nuevo ? 'Nueva talla' : 'Editar talla';
      case 'color': return nuevo ? 'Nuevo color' : 'Editar color';
      default: return 'Nueva marca';
    }
  });

  ngOnInit() { this.cargar(); }

  cargar() {
    this.api.categorias().subscribe((r) => this.categorias.set(r));
    this.api.grupos().subscribe((r) => this.grupos.set(r));
    this.api.colores().subscribe((r) => this.colores.set(r));
    this.api.marcas().subscribe((r) => this.marcas.set(r));
  }

  nombreGrupo(id: number | null) { return id === null ? 'Heredado / ninguno' : (this.grupos().find((g) => g.id === id)?.nombre ?? '—'); }

  private abrir(m: Modal, id: number, form: object) { this.editandoId = id; this.form = form; this.error.set(''); this.modal.set(m); }
  nuevaCategoria() { this.abrir('categoria', 0, { nombre: '', padre_id: null, grupo_talla_id: null, orden: 0, activa: true }); }
  editarCategoria(c: Categoria) { this.abrir('categoria', c.id, { nombre: c.nombre, padre_id: c.padre_id, grupo_talla_id: c.grupo_talla_id, orden: c.orden, activa: c.activa }); }
  nuevoGrupo() { this.abrir('grupo', 0, { nombre: '', descripcion: '' }); }
  nuevaTalla(g: GrupoTalla) { this.grupoId = g.id; this.abrir('talla', 0, { codigo: '', orden: null }); }
  editarTalla(t: Talla) { this.grupoId = t.grupo_id; this.abrir('talla', t.id, { codigo: t.codigo, orden: t.orden }); }
  nuevoColor() { this.abrir('color', 0, { nombre: '', codigo_hex: '#7A1F3D' }); }
  editarColor(c: ColorCatalogo) { this.abrir('color', c.id, { nombre: c.nombre, codigo_hex: c.codigo_hex }); }
  nuevaMarca() { this.abrir('marca', 0, { nombre: '' }); }

  guardar() {
    const f = this.form, id = this.editandoId;
    const peticion: Observable<unknown> = {
      categoria: () => id ? this.api.editarCategoria(id, f) : this.api.crearCategoria(f),
      grupo: () => this.api.crearGrupo({ nombre: f.nombre, descripcion: f.descripcion || null }),
      talla: () => id ? this.api.editarTalla(id, { codigo: f.codigo, orden: f.orden }) : this.api.crearTalla({ grupo_id: this.grupoId, codigo: f.codigo, orden: f.orden }),
      color: () => id ? this.api.editarColor(id, f) : this.api.crearColor(f),
      marca: () => this.api.crearMarca(f),
    }[this.modal()!]();
    this.guardando.set(true); this.error.set('');
    peticion.subscribe({
      next: () => { this.guardando.set(false); this.modal.set(null); this.toast.ok('Guardado.'); this.cargar(); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  eliminar(que: string, peticion: ReturnType<CatalogoAdminApi['eliminarMarca']>) {
    if (!confirm(`¿Eliminar este/a ${que}?`)) return;
    peticion.subscribe({ next: () => { this.toast.ok('Eliminado.'); this.cargar(); }, error: (e) => this.toast.error(mensajeError(e)) });
  }
}
