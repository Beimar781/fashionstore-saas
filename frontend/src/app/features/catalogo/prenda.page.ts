import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MEDIA_URL } from '../../core/api.config';
import { CatalogoApi } from '../../core/api/catalogo.api';
import { InventarioApi } from '../../core/api/inventario.api';
import { Opciones, PrendaDetalle, SucursalCatalogo } from '../../core/catalogo.models';
import { Disponibilidad } from '../../core/inventario.models';
import { ReservaBorradorService } from '../../core/reservas/reserva-borrador.service';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** CU-03 · Detalle de la prenda. La matriz color × talla la calcula el backend (`/opciones`); aquí solo se dibuja. */
@Component({
  selector: 'app-prenda',
  imports: [FormsModule, RouterLink],
  template: `
    <div class="page">
      <a routerLink="/tienda/catalogo" class="small">← Catálogo</a>
      @if (prenda(); as p) {
        <div class="detalle">
          <div class="fotos">
            <div class="principal">@if (fotoActual(); as f) { <img [src]="media + f.url" [alt]="f.texto_alt || p.nombre" /> } @else { <span>👕</span> }</div>
            @if (p.imagenes.length > 1) {
              <div class="miniaturas">@for (i of p.imagenes; track i.id) { <button type="button" (click)="fotoElegida.set(i.id)" [class.sel]="fotoActual() === i"><img [src]="media + i.url" [alt]="i.texto_alt || p.nombre" /></button> }</div>
            }
          </div>

          <div class="stack">
            <div><span class="muted small">{{ p.categoria }}{{ p.marca ? ' · ' + p.marca : '' }} · {{ p.coleccion }}</span><h1>{{ p.nombre }}</h1></div>
            <div class="precio">
              @if (precioFinal() !== precioNormal()) { <s class="muted">Bs {{ precioNormal() }}</s> }
              <b>Bs {{ precioFinal() }}</b>
              @if (p.promocion) { <span class="badge danger">{{ p.promocion }}</span> }
            </div>
            <p>{{ p.descripcion }}</p>

            <label style="max-width:300px">Ver disponibilidad en
              <select [ngModel]="sucursalId()" (ngModelChange)="cambiarSucursal($event)" name="suc">
                <option [ngValue]="null">Todas las sucursales</option>
                @for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }} · {{ s.ciudad }}</option> }
              </select></label>

            @if (opciones(); as o) {
              <div class="stack">
                <strong>Color: <span class="muted">{{ colorElegido()?.nombre ?? 'elija uno' }}</span></strong>
                <div class="chips">
                  @for (c of o.colores; track c.id) {
                    <button type="button" class="chip" [class.sel]="colorId() === c.id" [class.agotado]="!c.disponible" [disabled]="!c.disponible" (click)="elegirColor(c.id)" [title]="c.disponible ? c.nombre : c.nombre + ' (agotado)'">
                      <span class="swatch" [style.background]="c.codigo_hex"></span>{{ c.nombre }}</button>
                  }
                </div>
                <strong>Talla: <span class="muted">{{ tallaCodigo() ?? 'elija una' }}</span></strong>
                <div class="chips">
                  @for (t of o.tallas; track t.id) {
                    <button type="button" class="chip" [class.sel]="tallaCodigo() === t.codigo" [class.agotado]="!hayStock(t.codigo)" [disabled]="!hayStock(t.codigo)" (click)="tallaCodigo.set(t.codigo)">{{ t.codigo }}</button>
                  }
                </div>
                @if (variante(); as v) {
                  <div class="card pad" style="max-width:420px">
                    <div class="row between"><span class="small muted">SKU {{ v.sku }}</span>
                      @if (v.cantidad > 5) { <span class="badge ok">Disponible</span> } @else { <span class="badge warn">Quedan {{ v.cantidad }}</span> }</div>
                    <p class="small muted" style="margin-top:.3rem">{{ sucursalId() ? 'En la sucursal elegida' : 'Sumando todas las sucursales' }}: {{ v.cantidad }} unidades.</p>
                  </div>
                  <div class="row">
                    <button type="button" class="btn primary" (click)="agregarAReserva(p)">+ Agregar a mi reserva</button>
                    @if (borrador.total() > 0) { <a class="btn" routerLink="/tienda/reservar">Ver mi reserva ({{ borrador.total() }})</a> }
                  </div>
                } @else if (!o.variantes.some(hayDisponible)) {
                  <div class="alert warn">Por ahora esta prenda está agotada{{ sucursalId() ? ' en la sucursal elegida' : '' }}. Pruebe con otra sucursal.</div>
                }
              </div>
            }

            @if (disponibilidad(); as d) {
              <div class="stack">
                <strong>Disponibilidad por sucursal</strong>
                <div class="sucursales">
                  @for (s of d.sucursales; track s.sucursal_id) {
                    <button type="button" class="card pad suc" [class.sel]="sucursalId() === s.sucursal_id" (click)="cambiarSucursal(sucursalId() === s.sucursal_id ? null : s.sucursal_id)">
                      <span class="row between"><strong>{{ s.sucursal }}</strong>@if (s.disponible) { <span class="badge ok">{{ s.total }} unid.</span> } @else { <span class="badge danger">Sin stock</span> }</span>
                      <span class="muted small">{{ s.ciudad }}{{ s.horario ? ' · ' + s.horario : '' }}</span>
                      @if (s.disponible) { <span class="small">Tallas: {{ s.tallas.join(' · ') }}<br />Colores: {{ s.colores.join(', ') }}</span> }
                    </button>
                  }
                </div>
              </div>
            }

            <dl class="datos small">
              @if (p.material) { <dt>Material</dt><dd>{{ p.material }}</dd> }
              @if (p.cuidado) { <dt>Cuidado</dt><dd>{{ p.cuidado }}</dd> }
              <dt>Temporada</dt><dd>{{ p.temporada }}</dd>
            </dl>
          </div>
        </div>
      } @else { <div class="empty">Cargando…</div> }
    </div>`,
  styles: `
    .detalle { display: grid; grid-template-columns: minmax(260px, 420px) 1fr; gap: 2rem; margin-top: 1rem; align-items: start; }
    .principal { aspect-ratio: 3/4; background: #ece8e1; border-radius: 12px; overflow: hidden; display: grid; place-items: center; font-size: 4rem; }
    .principal img { width: 100%; height: 100%; object-fit: cover; }
    .miniaturas { display: flex; gap: .5rem; margin-top: .6rem; flex-wrap: wrap; }
    .miniaturas button { border: 2px solid transparent; padding: 0; border-radius: 8px; overflow: hidden; width: 60px; height: 76px; cursor: pointer; background: none; }
    .miniaturas button.sel { border-color: var(--accent); } .miniaturas img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .precio b { font-size: 1.5rem; margin-left: .3rem; }
    .sucursales { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: .6rem; }
    .suc { text-align: left; display: grid; gap: .25rem; cursor: pointer; font: inherit; color: inherit; } .suc.sel { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-soft); }
    .datos { display: grid; grid-template-columns: max-content 1fr; gap: .3rem 1rem; margin: 0; } dt { color: var(--muted); } dd { margin: 0; }
    @media (max-width: 760px) { .detalle { grid-template-columns: 1fr; } }`,
})
export class PrendaPage implements OnInit {
  private api = inject(CatalogoApi);
  private inventario = inject(InventarioApi);
  private ruta = inject(ActivatedRoute);
  private toast = inject(ToastService);
  readonly borrador = inject(ReservaBorradorService);

  readonly media = MEDIA_URL;
  readonly prenda = signal<PrendaDetalle | null>(null);
  readonly opciones = signal<Opciones | null>(null);
  readonly sucursales = signal<SucursalCatalogo[]>([]);
  readonly disponibilidad = signal<Disponibilidad | null>(null);
  readonly sucursalId = signal<number | null>(null);
  readonly colorId = signal<number | null>(null);
  readonly tallaCodigo = signal<string | null>(null); // la talla se recuerda por código, no por id: cambia entre grupos de tallas
  readonly fotoElegida = signal<number | null>(null);
  private id = 0;

  readonly colorElegido = computed(() => this.opciones()?.colores.find((c) => c.id === this.colorId()) ?? null);
  readonly variante = computed(() => this.opciones()?.variantes.find((v) => v.color_id === this.colorId() && v.talla === this.tallaCodigo()) ?? null);
  readonly precioNormal = computed(() => this.variante()?.precio ?? this.prenda()?.precio ?? '');
  readonly precioFinal = computed(() => this.variante()?.precio_final ?? this.prenda()?.precio_final ?? '');
  readonly fotoActual = computed(() => {
    const imagenes = this.prenda()?.imagenes ?? [];
    return imagenes.find((i) => i.id === this.fotoElegida())
      ?? imagenes.find((i) => i.color_id === this.colorId()) ?? imagenes.find((i) => i.principal) ?? imagenes[0] ?? null;
  });
  readonly hayDisponible = (v: { disponible: boolean }) => v.disponible;

  ngOnInit() {
    this.api.sucursales().subscribe((r) => this.sucursales.set(r));
    this.ruta.paramMap.subscribe((pm) => {
      // Solo al cambiar de producto se reinicia la selección; actualizar los datos la conserva.
      this.id = Number(pm.get('id'));
      const s = this.ruta.snapshot.queryParamMap.get('sucursal');
      this.sucursalId.set(s ? Number(s) : null);
      this.colorId.set(null); this.tallaCodigo.set(null); this.fotoElegida.set(null);
      this.cargar();
    });
  }

  cargar() {
    this.api.prenda(this.id, this.sucursalId()).subscribe({ next: (p) => this.prenda.set(p), error: (e) => this.toast.error(mensajeError(e)) });
    this.inventario.disponibilidad(this.id).subscribe({ next: (d) => this.disponibilidad.set(d), error: (e) => this.toast.error(mensajeError(e)) });
    this.api.opciones(this.id, this.sucursalId()).subscribe({
      next: (o) => { this.opciones.set(o); this.ajustarSeleccion(o); },
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }

  agregarAReserva(p: PrendaDetalle) {
    const v = this.variante();
    if (!v) return;
    this.borrador.agregar({ variante_id: v.variante_id, sku: v.sku, producto: p.nombre, talla: v.talla, color: v.color, max: Math.max(v.cantidad, 1) });
    this.toast.ok(`${p.nombre} (${v.talla}, ${v.color}) agregada a su reserva.`);
  }

  cambiarSucursal(id: number | null) { this.sucursalId.set(id); this.cargar(); }

  /** ¿Hay stock de esa talla en el color elegido (o en cualquier color, si aún no se eligió)? */
  hayStock(codigo: string) {
    return !!this.opciones()?.variantes.some((v) => v.talla === codigo && v.disponible && (this.colorId() === null || v.color_id === this.colorId()));
  }

  elegirColor(id: number) {
    this.colorId.set(id);
    this.fotoElegida.set(null);
    this.ajustarSeleccion(this.opciones()!);
  }

  /** Conserva la talla si existe y tiene stock en el color elegido; si no, pasa a la primera con stock. */
  private ajustarSeleccion(o: Opciones) {
    let color = this.colorId();
    if (color === null || !o.colores.find((c) => c.id === color)?.disponible) color = o.colores.find((c) => c.disponible)?.id ?? null;
    this.colorId.set(color);
    const conStock = o.variantes.filter((v) => v.color_id === color && v.disponible).sort((a, b) => a.orden - b.orden);
    if (!conStock.some((v) => v.talla === this.tallaCodigo())) this.tallaCodigo.set(conStock[0]?.talla ?? null);
  }
}
