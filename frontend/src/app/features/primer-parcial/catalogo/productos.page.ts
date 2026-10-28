import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MEDIA_URL } from '../../../core/api.config';
import { CatalogoAdminApi } from '../../../core/api/catalogo-admin.api';
import { Categoria, Coleccion, ColorCatalogo, GENEROS, GrupoTalla, Marca, Pagina, ProductoResumen } from '../../../core/catalogo.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';
import { alternar, tallasDeCategoria } from './catalogo.util';

/** CU-18 · Gestionar productos: listado y alta con sus variantes (talla × color). Las fotos se suben en el detalle. */
@Component({
  selector: 'app-productos',
  imports: [FormsModule, RouterLink],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>Productos</h1><p>Prendas del catálogo con sus variantes de talla y color.</p></div>
        <button class="btn primary" (click)="abrirNuevo()">+ Nuevo producto</button>
      </div>

      <form class="card pad row" style="margin-bottom:1rem" (ngSubmit)="buscar()">
        <input name="q" [(ngModel)]="q" placeholder="Buscar por nombre…" style="flex:1;min-width:180px" />
        <select name="c" [(ngModel)]="categoriaId" style="width:auto"><option [ngValue]="null">Todas las categorías</option>@for (c of categorias(); track c.id) { <option [ngValue]="c.id">{{ c.nombre }}</option> }</select>
        <select name="e" [(ngModel)]="activo" style="width:auto"><option [ngValue]="null">Todos</option><option [ngValue]="true">Activos</option><option [ngValue]="false">Retirados</option></select>
        <button class="btn">Buscar</button>
      </form>

      <div class="card table-wrap">
        @if (cargando()) { <div class="empty">Cargando…</div> }
        @else if (!datos()?.items?.length) { <div class="empty">No hay productos con esos filtros.</div> }
        @else {
          <table>
            <thead><tr><th></th><th>Producto</th><th>Categoría</th><th>Colección</th><th class="right">Precio</th><th class="right">Variantes</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              @for (p of datos()!.items; track p.id) {
                <tr>
                  <td>@if (p.imagen_principal) { <img class="thumb" [src]="media + p.imagen_principal" [alt]="p.nombre" /> } @else { <span class="thumb vacia">👕</span> }</td>
                  <td><strong>{{ p.nombre }}</strong>@if (p.marca) { <div class="muted small">{{ p.marca }}</div> }</td>
                  <td>{{ p.categoria }}</td><td>{{ p.coleccion }}</td><td class="right nowrap">Bs {{ p.precio_base }}</td><td class="right">{{ p.variantes }}</td>
                  <td><span class="badge" [class.ok]="p.activo" [class.warn]="!p.activo">{{ p.activo ? 'Activo' : 'Retirado' }}</span></td>
                  <td class="actions"><a class="btn sm" [routerLink]="['/empresa/catalogo/productos', p.id]">Editar</a></td>
                </tr>
              }
            </tbody>
          </table>
          <div class="row between" style="padding:.7rem 1rem">
            <span class="muted small">{{ datos()!.total }} productos · página {{ datos()!.pagina }} de {{ paginas() }}</span>
            <div class="row"><button class="btn sm" [disabled]="datos()!.pagina <= 1" (click)="irA(datos()!.pagina - 1)">Anterior</button><button class="btn sm" [disabled]="datos()!.pagina >= paginas()" (click)="irA(datos()!.pagina + 1)">Siguiente</button></div>
          </div>
        }
      </div>
    </div>

    @if (modal()) {
      <div class="overlay" (click)="modal.set(false)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="crear()" #f="ngForm" role="dialog" aria-modal="true" style="width:min(760px,100%)">
          <header><h2>Nuevo producto</h2><button type="button" class="btn sm ghost" (click)="modal.set(false)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <div class="form-grid">
              <label class="full">Nombre<input name="n" [(ngModel)]="form.nombre" required minlength="2" /></label>
              <label class="full">Descripción<textarea name="d" rows="2" [(ngModel)]="form.descripcion"></textarea></label>
              <label>Categoría<select name="c" [(ngModel)]="form.categoria_id" (ngModelChange)="form.tallas_ids = []" required>@for (c of categorias(); track c.id) { <option [ngValue]="c.id">{{ c.nombre }}</option> }</select></label>
              <label>Colección (temporada)<select name="co" [(ngModel)]="form.coleccion_id" required>@for (c of colecciones(); track c.id) { <option [ngValue]="c.id">{{ c.nombre }} · {{ c.temporada }}</option> }</select></label>
              <label>Marca<select name="m" [(ngModel)]="form.marca_id"><option [ngValue]="null">Sin marca</option>@for (m of marcas(); track m.id) { <option [ngValue]="m.id">{{ m.nombre }}</option> }</select></label>
              <label>Género<select name="g" [(ngModel)]="form.genero">@for (g of generos; track g.valor) { <option [ngValue]="g.valor">{{ g.texto }}</option> }</select></label>
              <label>Precio base (Bs)<input name="p" type="number" min="0" step="0.01" [(ngModel)]="form.precio_base" required /></label>
              <label>Material<input name="ma" [(ngModel)]="form.material" /></label>
              <label class="full">Cuidado<input name="cu" [(ngModel)]="form.cuidado" /></label>
            </div>
            <fieldset>
              <legend>Variantes: tallas × colores</legend>
              @if (!form.categoria_id) { <p class="muted small">Elija una categoría para ver sus tallas.</p> }
              @else if (!tallasDisponibles().length) { <p class="alert warn">La categoría no tiene grupo de tallas. Asígnele uno en «Categorías, tallas y colores».</p> }
              @else {
                <p class="small" style="margin-bottom:.4rem"><strong>Tallas</strong></p>
                <div class="chips">@for (t of tallasDisponibles(); track t.id) { <button type="button" class="chip" [class.sel]="form.tallas_ids.includes(t.id)" (click)="alternar(form.tallas_ids, t.id)">{{ t.codigo }}</button> }</div>
              }
              <p class="small" style="margin:.8rem 0 .4rem"><strong>Colores</strong></p>
              <div class="chips">@for (c of colores(); track c.id) { <button type="button" class="chip" [class.sel]="form.colores_ids.includes(c.id)" (click)="alternar(form.colores_ids, c.id)"><span class="swatch" [style.background]="c.codigo_hex"></span>{{ c.nombre }}</button> }</div>
              <p class="muted small" style="margin-top:.7rem">Se crearán {{ form.tallas_ids.length * form.colores_ids.length }} variantes (un SKU por combinación).</p>
            </fieldset>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(false)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !f.valid">Crear producto</button></footer>
        </form>
      </div>
    }`,
})
export class ProductosPage implements OnInit {
  private api = inject(CatalogoAdminApi);
  private toast = inject(ToastService);
  private router = inject(Router);

  readonly media = MEDIA_URL;
  readonly generos = GENEROS;
  readonly datos = signal<Pagina<ProductoResumen> | null>(null);
  readonly paginas = computed(() => Math.max(1, Math.ceil((this.datos()?.total ?? 0) / (this.datos()?.tamano ?? 20))));
  readonly categorias = signal<Categoria[]>([]);
  readonly grupos = signal<GrupoTalla[]>([]);
  readonly colores = signal<ColorCatalogo[]>([]);
  readonly marcas = signal<Marca[]>([]);
  readonly colecciones = signal<Coleccion[]>([]);
  readonly cargando = signal(true);
  readonly modal = signal(false);
  readonly guardando = signal(false);
  readonly error = signal('');
  q = ''; categoriaId: number | null = null; activo: boolean | null = null;
  form: any = this.vacio();

  ngOnInit() {
    this.api.categorias().subscribe((r) => this.categorias.set(r));
    this.api.grupos().subscribe((r) => this.grupos.set(r));
    this.api.colores().subscribe((r) => this.colores.set(r));
    this.api.marcas().subscribe((r) => this.marcas.set(r));
    this.api.colecciones().subscribe((r) => this.colecciones.set(r));
    this.irA(1);
  }

  buscar() { this.irA(1); }
  irA(pagina: number) {
    this.cargando.set(true);
    this.api.productos({ q: this.q.trim(), categoria_id: this.categoriaId, activo: this.activo, pagina }).subscribe({
      next: (r) => { this.datos.set(r); this.cargando.set(false); },
      error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); },
    });
  }

  tallasDisponibles() { return tallasDeCategoria(this.categorias(), this.grupos(), this.form.categoria_id); }
  alternar = alternar;

  abrirNuevo() { this.form = this.vacio(); this.error.set(''); this.modal.set(true); }

  crear() {
    this.guardando.set(true); this.error.set('');
    this.api.crearProducto(this.form).subscribe({
      next: (p) => { this.guardando.set(false); this.modal.set(false); this.toast.ok('Producto creado. Suba sus fotografías.'); void this.router.navigate(['/empresa/catalogo/productos', p.id]); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  private vacio() {
    return { nombre: '', descripcion: '', categoria_id: null as number | null, coleccion_id: null as number | null, marca_id: null as number | null,
      genero: 'UNISEX', precio_base: null as number | null, material: '', cuidado: '', tallas_ids: [] as number[], colores_ids: [] as number[] };
  }
}
