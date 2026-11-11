import { AprendizajeService } from '../../core/ia/aprendizaje.service';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MEDIA_URL } from '../../core/api.config';
import { CatalogoAdminApi } from '../../core/api/catalogo-admin.api';
import { CatalogoApi } from '../../core/api/catalogo.api';
import { Categoria, ColorCatalogo, FiltrosCatalogo, GENEROS, Marca, Pagina, Prenda, SucursalCatalogo } from '../../core/catalogo.models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';
import { CatalogoLocalService } from '../../core/offline/catalogo-local.service';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { BsPipe } from '../../core/formato-bs';

/** CU-03 · Consultar catálogo de prendas y CU-04 · Buscar y filtrar. Todos los filtros viajan al backend. */
@Component({
  selector: 'app-catalogo',
  imports: [BsPipe, FormsModule, RouterLink, DatePipe],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Catálogo</h1><p>Encuentre su próxima prenda y revise la disponibilidad por sucursal.</p></div></div>
      @if (!red.online() && local.meta(); as m) { <div class="alert warn small" role="status">Sin conexión · Datos al {{ m.generado_en | date: 'dd/MM HH:mm' }}; pueden estar desactualizados. Precios, promociones y stock pueden haber cambiado.</div> }
      @if (red.online() && local.vencido() && local.meta(); as m) { <div class="alert warn small" role="status">Datos descargados al {{ m.generado_en | date: 'dd/MM HH:mm' }}; pueden estar desactualizados. <button type="button" class="btn sm" (click)="local.descargar()" [disabled]="local.descargando()">{{ local.descargando() ? 'Actualizando…' : 'Actualizar ahora' }}</button></div> }

      <form class="card pad stack" style="margin-bottom:1.1rem" (ngSubmit)="buscar()">
        <div class="row">
          <input name="q" [(ngModel)]="f.q" placeholder="Buscar por nombre, descripción o material…" style="flex:1;min-width:200px" />
          <button class="btn primary">Buscar</button>
          <button type="button" class="btn ghost" (click)="limpiar()">Limpiar</button>
        </div>
        <div class="form-grid">
          <label>Categoría<select name="c" [(ngModel)]="f.categoria_id" (ngModelChange)="buscar()"><option [ngValue]="null">Todas</option>@for (c of categorias(); track c.id) { <option [ngValue]="c.id">{{ c.nombre }}</option> }</select></label>
          <label>Marca<select name="m" [(ngModel)]="f.marca_id" (ngModelChange)="buscar()"><option [ngValue]="null">Todas</option>@for (m of marcas(); track m.id) { <option [ngValue]="m.id">{{ m.nombre }}</option> }</select></label>
          <label>Género<select name="g" [(ngModel)]="f.genero" (ngModelChange)="buscar()"><option value="">Todos</option>@for (g of generos; track g.valor) { <option [value]="g.valor">{{ g.texto }}</option> }</select></label>
          <label>Talla<select name="t" [(ngModel)]="f.talla" (ngModelChange)="buscar()"><option value="">Todas</option>@for (t of tallas(); track t) { <option [value]="t">{{ t }}</option> }</select></label>
          <label>Color<select name="co" [(ngModel)]="f.color_id" (ngModelChange)="buscar()"><option [ngValue]="null">Todos</option>@for (c of colores(); track c.id) { <option [ngValue]="c.id">{{ c.nombre }}</option> }</select></label>
          <label>Precio mínimo (Bs)<input name="pmin" type="number" min="0" [(ngModel)]="f.precio_min" (change)="buscar()" /></label>
          <label>Precio máximo (Bs)<input name="pmax" type="number" min="0" [(ngModel)]="f.precio_max" (change)="buscar()" /></label>
          <label>Sucursal<select name="s" [(ngModel)]="f.sucursal" (ngModelChange)="buscar()"><option [ngValue]="null">Todas</option>@for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }} · {{ s.ciudad }}</option> }</select></label>
          <label>Ordenar por<select name="o" [(ngModel)]="f.orden" (ngModelChange)="buscar()"><option value="recientes">Más recientes</option><option value="precio_asc">Precio: menor a mayor</option><option value="precio_desc">Precio: mayor a menor</option><option value="nombre">Nombre</option></select></label>
          <label class="check" style="align-self:end"><input name="sd" type="checkbox" [(ngModel)]="f.solo_disponibles" (ngModelChange)="buscar()" /> Solo con existencias</label>
        </div>
      </form>

      @if (cargando()) { <div class="empty">Cargando…</div> }
      @else if (!datos()?.items?.length) { <div class="card empty">No encontramos prendas con esos filtros.</div> }
      @else {
        <div class="prendas">
          @for (p of datos()!.items; track p.id) {
            <a class="prenda card" [routerLink]="['/tienda/catalogo', p.id]" [queryParams]="f.sucursal ? { sucursal: f.sucursal } : {}">
              <div class="foto">
                @if (p.imagen) { <img [src]="media + p.imagen" [alt]="p.nombre" loading="lazy" /> } @else { <span>👕</span> }
                @if (p.promocion) { <span class="badge danger oferta">Oferta</span> }
                @if (!p.disponible) { <span class="badge agotada">{{ f.sucursal ? 'Sin stock aquí' : 'Agotada' }}</span> }
              </div>
              <div class="info">
                <strong>{{ p.nombre }}</strong>
                <span class="muted small">{{ p.categoria }}{{ p.marca ? ' · ' + p.marca : '' }}</span>
                <span class="precio">@if (p.precio_final !== p.precio) { <s class="muted small">{{ p.precio | bs }}</s> } <b>{{ p.precio_final | bs }}</b></span>
                <span class="row" style="gap:.3rem">@for (c of p.colores; track c.id) { <span class="swatch" [style.background]="c.codigo_hex" [title]="c.nombre"></span> }</span>
                <span class="muted small">Tallas: {{ p.tallas.join(' · ') }}</span>
              </div>
            </a>
          }
        </div>
        <div class="row between" style="margin-top:1.1rem">
          <span class="muted small">{{ datos()!.total }} prendas · página {{ datos()!.pagina }} de {{ paginas() }}</span>
          <div class="row"><button class="btn sm" [disabled]="datos()!.pagina <= 1" (click)="irA(datos()!.pagina - 1)">Anterior</button><button class="btn sm" [disabled]="datos()!.pagina >= paginas()" (click)="irA(datos()!.pagina + 1)">Siguiente</button></div>
        </div>
      }
    </div>`,
  styles: `
    .prendas { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 1rem; }
    .prenda { display: grid; text-decoration: none; color: inherit; overflow: hidden; transition: transform .15s, box-shadow .15s; }
    .prenda:hover { transform: translateY(-2px); text-decoration: none; }
    .foto { position: relative; aspect-ratio: 3/4; background: #ece8e1; display: grid; place-items: center; font-size: 2.5rem; }
    .foto img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .oferta { position: absolute; top: .6rem; left: .6rem; } .agotada { position: absolute; bottom: .6rem; left: .6rem; background: #1d1a22; color: #fff; }
    .info { display: grid; gap: .25rem; padding: .8rem .9rem 1rem; } .precio b { font-size: 1.05rem; }`,
})
export class CatalogoPage implements OnInit {
  private catalogo = inject(CatalogoApi);
  private lecturas = inject(CatalogoAdminApi); // las listas de categorías, marcas, colores y tallas son de lectura para todos los roles
  private toast = inject(ToastService);
  private aprendizaje = inject(AprendizajeService);
  readonly local = inject(CatalogoLocalService);
  readonly red = inject(ConnectivityService);

  readonly media = MEDIA_URL;
  readonly generos = GENEROS;
  readonly categorias = signal<Categoria[]>([]);
  readonly marcas = signal<Marca[]>([]);
  readonly colores = signal<ColorCatalogo[]>([]);
  readonly tallas = signal<string[]>([]);
  readonly sucursales = signal<SucursalCatalogo[]>([]);
  readonly datos = signal<Pagina<Prenda> | null>(null);
  readonly paginas = computed(() => Math.max(1, Math.ceil((this.datos()?.total ?? 0) / (this.datos()?.tamano ?? 20))));
  readonly cargando = signal(true);
  f: FiltrosCatalogo = this.vacio();

  private readonly recargaAlVolverLaRed = inject(ColaOperacionesService).alRefrescar(() => this.irA(this.datos()?.pagina ?? 1));  // al volver la red la pantalla abierta se recarga sola
  ngOnInit() {
    this.lecturas.categorias().subscribe({ next: (r) => this.categorias.set(r), error: () => undefined });
    this.lecturas.marcas().subscribe({ next: (r) => this.marcas.set(r), error: () => undefined });
    this.lecturas.colores().subscribe({ next: (r) => this.colores.set(r), error: () => undefined });
    this.lecturas.grupos().subscribe((grupos) => this.tallas.set([...new Set(grupos.flatMap((g) => g.tallas.map((t) => t.codigo)))]));
    this.catalogo.sucursales().subscribe({ next: (r) => this.sucursales.set(r), error: () => undefined });
    this.local.cargar().then(() => this.sucursales.set(this.local.meta()?.sucursales ?? this.sucursales()));
    this.buscar();
  }

  buscar() { this.aprendizaje.busqueda(this.f); this.irA(1); }
  irA(pagina: number) {
    this.cargando.set(true);
    this.catalogo.buscar({ ...this.f, q: this.f.q?.trim(), pagina }).subscribe({
      next: (r) => { this.datos.set(r); this.cargando.set(false); },
      error: async (e) => {
        await this.local.listo();
        const m = this.local.meta();
        if (m && this.local.hayCatalogo()) {
          const q = (this.f.q ?? '').trim().toLowerCase();
          const items = this.local.productos().filter((p) => {
            const variantes = p.variantes.filter((v) => (!this.f.talla || v.talla === this.f.talla) && (!this.f.color_id || v.color_id === this.f.color_id) && (!this.f.sucursal || (v.stock[String(this.f.sucursal)] ?? 0) > 0) && (!this.f.solo_disponibles || Object.values(v.stock).some((n) => n > 0)) && (!this.f.precio_min || Number(v.precio_final) >= this.f.precio_min) && (!this.f.precio_max || Number(v.precio_final) <= this.f.precio_max));
            return variantes.length > 0 && (!q || `${p.nombre} ${p.categoria} ${p.marca ?? ''} ${p.descripcion ?? ''}`.toLowerCase().includes(q)) && (!this.f.genero || p.genero === this.f.genero) && (!this.f.categoria_id || this.categorias().find((c) => c.id === this.f.categoria_id)?.nombre === p.categoria) && (!this.f.marca_id || this.marcas().find((x) => x.id === this.f.marca_id)?.nombre === p.marca);
          }).map((p) => {
            const vs = p.variantes;
            const stock = vs.some((v) => Object.values(v.stock).some((n) => n > 0));
            return { id: p.id, publico_id: p.publico_id ?? String(p.id), nombre: p.nombre, slug: p.slug ?? String(p.id), categoria: p.categoria, marca: p.marca ?? null, genero: p.genero as Prenda['genero'], coleccion: p.coleccion ?? '', temporada: p.temporada ?? '', precio: vs[0]?.precio ?? '0', precio_final: vs[0]?.precio_final ?? '0', promocion: vs.find((v) => v.promocion)?.promocion ?? null, imagen: p.imagen, colores: [...new Map(vs.map((v) => [v.color_id ?? v.color, { id: v.color_id ?? 0, nombre: v.color, codigo_hex: v.color_hex ?? '#999999' }])).values()], tallas: [...new Set(vs.map((v) => v.talla))], disponible: stock } as Prenda;
          });
          this.datos.set({ total: items.length, pagina: 1, tamano: items.length || 20, items });
        } else this.toast.error(mensajeError(e));
        this.cargando.set(false);
      },
    });
  }
  limpiar() { this.f = this.vacio(); this.buscar(); }

  private vacio(): FiltrosCatalogo {
    return { q: '', categoria_id: null, marca_id: null, genero: '', talla: '', color_id: null, precio_min: null, precio_max: null, sucursal: null, solo_disponibles: false, orden: 'recientes' };
  }
}
