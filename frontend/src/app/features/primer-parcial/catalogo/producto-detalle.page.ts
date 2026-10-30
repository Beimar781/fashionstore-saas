import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MEDIA_URL } from '../../../core/api.config';
import { CatalogoAdminApi } from '../../../core/api/catalogo-admin.api';
import { Categoria, Coleccion, ColorCatalogo, GENEROS, GrupoTalla, Marca, ProductoDetalle } from '../../../core/catalogo.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';
import { alternar, tallasDeCategoria } from './catalogo.util';
import { VestidorProductoComponent } from './vestidor-producto.component';

interface FilaVariante { id: number; sku: string; talla: string; color: string; precio: string; barras: string; activa: boolean; }

/** CU-18 · Detalle del producto: datos, variantes (SKU), fotografías y retiro del catálogo. */
@Component({
  selector: 'app-producto-detalle',
  imports: [FormsModule, RouterLink, VestidorProductoComponent],
  template: `
    <div class="page">
      <a routerLink="/empresa/catalogo/productos" class="small">← Productos</a>
      @if (p(); as prod) {
        <div class="page-head" style="margin-top:.4rem">
          <div><h1>{{ prod.nombre }}</h1><p>{{ prod.categoria }} · {{ prod.coleccion }} ({{ prod.temporada }}) · <span class="badge" [class.ok]="prod.activo" [class.warn]="!prod.activo">{{ prod.activo ? 'Visible en la tienda' : 'Retirado' }}</span></p></div>
          @if (prod.activo) { <button class="btn danger" (click)="cambiarEstado(false)">Retirar del catálogo</button> } @else { <button class="btn primary" (click)="cambiarEstado(true)">Publicar</button> }
        </div>

        <form class="card pad stack" (ngSubmit)="guardarDatos()" #f="ngForm">
          <h2>Datos del producto</h2>
          <div class="form-grid">
            <label class="full">Nombre<input name="n" [(ngModel)]="datos.nombre" required minlength="2" /></label>
            <label class="full">Descripción<textarea name="d" rows="2" [(ngModel)]="datos.descripcion"></textarea></label>
            <label>Categoría<select name="c" [(ngModel)]="datos.categoria_id">@for (c of categorias(); track c.id) { <option [ngValue]="c.id">{{ c.nombre }}</option> }</select></label>
            <label>Colección<select name="co" [(ngModel)]="datos.coleccion_id">@for (c of colecciones(); track c.id) { <option [ngValue]="c.id">{{ c.nombre }} · {{ c.temporada }}</option> }</select></label>
            <label>Marca<select name="m" [(ngModel)]="datos.marca_id"><option [ngValue]="null">Sin marca</option>@for (m of marcas(); track m.id) { <option [ngValue]="m.id">{{ m.nombre }}</option> }</select></label>
            <label>Género<select name="g" [(ngModel)]="datos.genero">@for (g of generos; track g.valor) { <option [ngValue]="g.valor">{{ g.texto }}</option> }</select></label>
            <label>Precio base (Bs)<input name="p" type="number" min="0" step="0.01" [(ngModel)]="datos.precio_base" required /></label>
            <label>Material<input name="ma" [(ngModel)]="datos.material" /></label>
            <label class="full">Cuidado<input name="cu" [(ngModel)]="datos.cuidado" /></label>
          </div>
          @if (errorDatos()) { <div class="alert danger" role="alert">{{ errorDatos() }}</div> }
          <div><button class="btn primary" [disabled]="!f.valid || guardando()">Guardar datos</button></div>
        </form>

        <section class="card stack" style="margin-top:1rem">
          <div style="padding:1.25rem 1.25rem 0"><h2>Variantes (SKU)</h2><p class="muted small">Precio específico vacío = usa el precio base. El SKU se genera solo y no cambia.</p></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>SKU</th><th>Talla</th><th>Color</th><th>Precio específico</th><th>Código de barras</th><th>Activa</th><th></th></tr></thead>
              <tbody>
                @for (v of filas(); track v.id) {
                  <tr>
                    <td><code>{{ v.sku }}</code></td><td>{{ v.talla }}</td><td>{{ v.color }}</td>
                    <td><input type="number" min="0" step="0.01" [(ngModel)]="v.precio" [name]="'pr' + v.id" style="width:7.5rem" placeholder="{{ prod.precio_base }}" /></td>
                    <td><input [(ngModel)]="v.barras" [name]="'ba' + v.id" maxlength="32" style="width:9rem" /></td>
                    <td><input type="checkbox" [(ngModel)]="v.activa" [name]="'ac' + v.id" /></td>
                    <td class="actions"><button class="btn sm" (click)="guardarVariante(v)">Guardar</button></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
          <fieldset style="margin:0 1.25rem 1.25rem">
            <legend>Agregar variantes</legend>
            <div class="chips">@for (t of tallasDisponibles(); track t.id) { <button type="button" class="chip" [class.sel]="nuevasTallas.includes(t.id)" (click)="alternar(nuevasTallas, t.id)">{{ t.codigo }}</button> }</div>
            <div class="chips" style="margin-top:.6rem">@for (c of colores(); track c.id) { <button type="button" class="chip" [class.sel]="nuevosColores.includes(c.id)" (click)="alternar(nuevosColores, c.id)"><span class="swatch" [style.background]="c.codigo_hex"></span>{{ c.nombre }}</button> }</div>
            @if (errorVariantes()) { <div class="alert danger" role="alert" style="margin-top:.7rem">{{ errorVariantes() }}</div> }
            <div style="margin-top:.8rem"><button class="btn" (click)="generar()" [disabled]="!nuevasTallas.length || !nuevosColores.length">Generar variantes</button></div>
          </fieldset>
        </section>

        <section class="card pad stack" style="margin-top:1rem">
          <h2>Fotografías</h2>
          <div class="row">
            <input type="file" accept="image/png,image/jpeg,image/webp" (change)="elegirArchivo($event)" style="max-width:260px" />
            <select [(ngModel)]="colorImagen" name="ci" style="width:auto"><option [ngValue]="null">Todos los colores</option>@for (c of colores(); track c.id) { <option [ngValue]="c.id">{{ c.nombre }}</option> }</select>
            <input [(ngModel)]="textoAlt" name="alt" placeholder="Texto alternativo" style="max-width:220px" />
            <button class="btn primary" (click)="subir()" [disabled]="!archivo || subiendo()">{{ subiendo() ? 'Subiendo…' : 'Subir' }}</button>
          </div>
          @if (errorImagen()) { <div class="alert danger" role="alert">{{ errorImagen() }}</div> }
          <div class="galeria">
            @for (i of prod.imagenes; track i.id) {
              <figure>
                <img [src]="media + i.url" [alt]="i.texto_alt || prod.nombre" />
                <figcaption>
                  <span class="small">{{ nombreColor(i.color_id) }}</span>
                  @if (i.principal) { <span class="badge ok">Principal</span> } @else { <button class="btn sm" (click)="hacerPrincipal(i.id)">Hacer principal</button> }
                  <button class="btn sm danger" (click)="quitarImagen(i.id)">Quitar</button>
                </figcaption>
              </figure>
            } @empty { <p class="muted small">Todavía no hay fotografías: el producto se verá sin imagen en la tienda.</p> }
          </div>
        </section>
        <app-vestidor-producto [productoId]="prod.id" />
      } @else { <div class="empty">Cargando…</div> }
    </div>`,
  styles: `
    .galeria { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: .9rem; }
    figure { margin: 0; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
    figure img { width: 100%; aspect-ratio: 3/4; object-fit: cover; display: block; background: #ece8e1; }
    figcaption { display: grid; gap: .4rem; padding: .5rem; justify-items: start; }
    code { font-size: .82rem; background: #f1eee9; padding: .1rem .4rem; border-radius: 5px; }`,
})
export class ProductoDetallePage implements OnInit {
  private api = inject(CatalogoAdminApi);
  private toast = inject(ToastService);
  private ruta = inject(ActivatedRoute);

  readonly media = MEDIA_URL;
  readonly generos = GENEROS;
  readonly p = signal<ProductoDetalle | null>(null);
  readonly filas = signal<FilaVariante[]>([]);
  readonly categorias = signal<Categoria[]>([]);
  readonly grupos = signal<GrupoTalla[]>([]);
  readonly colores = signal<ColorCatalogo[]>([]);
  readonly marcas = signal<Marca[]>([]);
  readonly colecciones = signal<Coleccion[]>([]);
  readonly guardando = signal(false);
  readonly subiendo = signal(false);
  readonly errorDatos = signal('');
  readonly errorVariantes = signal('');
  readonly errorImagen = signal('');
  readonly tallasDisponibles = computed(() => tallasDeCategoria(this.categorias(), this.grupos(), this.p()?.categoria_id ?? null));
  alternar = alternar;
  datos: any = {};
  nuevasTallas: number[] = []; nuevosColores: number[] = [];
  archivo: File | null = null; colorImagen: number | null = null; textoAlt = '';
  private id = 0;

  ngOnInit() {
    this.id = Number(this.ruta.snapshot.paramMap.get('id'));
    this.api.categorias().subscribe((r) => this.categorias.set(r));
    this.api.grupos().subscribe((r) => this.grupos.set(r));
    this.api.colores().subscribe((r) => this.colores.set(r));
    this.api.marcas().subscribe((r) => this.marcas.set(r));
    this.api.colecciones().subscribe((r) => this.colecciones.set(r));
    this.cargar();
  }

  cargar() { this.api.producto(this.id).subscribe({ next: (p) => this.mostrar(p), error: (e) => this.toast.error(mensajeError(e)) }); }

  private mostrar(p: ProductoDetalle) {
    this.p.set(p);
    this.datos = { nombre: p.nombre, descripcion: p.descripcion, categoria_id: p.categoria_id, coleccion_id: p.coleccion_id, marca_id: p.marca_id,
      genero: p.genero, precio_base: Number(p.precio_base), material: p.material, cuidado: p.cuidado };
    this.filas.set(p.variantes.map((v) => ({ id: v.id, sku: v.sku, talla: v.talla, color: v.color, precio: v.precio_especifico ?? '', barras: v.codigo_barras ?? '', activa: v.activa })));
  }

  nombreColor(id: number | null) { return id === null ? 'Todos los colores' : (this.colores().find((c) => c.id === id)?.nombre ?? ''); }

  guardarDatos() {
    this.guardando.set(true); this.errorDatos.set('');
    this.api.editarProducto(this.id, this.datos).subscribe({
      next: (p) => { this.guardando.set(false); this.mostrar(p); this.toast.ok('Datos guardados.'); },
      error: (e) => { this.guardando.set(false); this.errorDatos.set(mensajeError(e)); },
    });
  }

  cambiarEstado(publicar: boolean) {
    (publicar ? this.api.activarProducto(this.id) : this.api.desactivarProducto(this.id)).subscribe({
      next: (p) => { this.p.set(p); this.toast.ok(publicar ? 'Producto publicado.' : 'Producto retirado del catálogo.'); },
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }

  guardarVariante(v: FilaVariante) {
    this.api.editarVariante(this.id, v.id, { precio_especifico: v.precio === '' || v.precio === null ? null : v.precio, codigo_barras: v.barras || null, activa: v.activa }).subscribe({
      next: () => { this.toast.ok(`Variante ${v.sku} guardada.`); this.cargar(); },
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }

  generar() {
    this.errorVariantes.set('');
    this.api.generarVariantes(this.id, { tallas_ids: this.nuevasTallas, colores_ids: this.nuevosColores }).subscribe({
      next: (r) => { this.toast.ok(`${r.creadas} variantes creadas, ${r.omitidas} ya existían.`); this.nuevasTallas = []; this.nuevosColores = []; this.cargar(); },
      error: (e) => this.errorVariantes.set(mensajeError(e)),
    });
  }

  elegirArchivo(ev: Event) { this.archivo = (ev.target as HTMLInputElement).files?.[0] ?? null; }

  subir() {
    if (!this.archivo) return;
    this.subiendo.set(true); this.errorImagen.set('');
    this.api.subirImagen(this.id, this.archivo, this.colorImagen, this.textoAlt).subscribe({
      next: () => { this.subiendo.set(false); this.archivo = null; this.textoAlt = ''; this.toast.ok('Fotografía subida.'); this.cargar(); },
      error: (e) => { this.subiendo.set(false); this.errorImagen.set(mensajeError(e)); },
    });
  }

  hacerPrincipal(imagenId: number) { this.api.imagenPrincipal(this.id, imagenId).subscribe({ next: (p) => this.p.set(p), error: (e) => this.toast.error(mensajeError(e)) }); }
  quitarImagen(imagenId: number) {
    if (!confirm('¿Quitar esta fotografía?')) return;
    this.api.eliminarImagen(this.id, imagenId).subscribe({ next: () => this.cargar(), error: (e) => this.toast.error(mensajeError(e)) });
  }
}
