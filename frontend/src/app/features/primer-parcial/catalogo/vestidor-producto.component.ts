import { Component, OnInit, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MEDIA_URL } from '../../../core/api.config';
import { VestidorApi } from '../../../core/api/vestidor.api';
import { ANCLAJE_POR_DEFECTO, Anclaje, ColorVestidor, VestidorProducto } from '../../../core/vestidor.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';

/** CU-06 · Vestidor virtual del producto: el Administrador sube, por color, el PNG ya recortado (fondo transparente) de la prenda y ajusta sus puntos de anclaje.
 *  Solo camisas, polos y chaquetas. El cliente se la prueba desde la app móvil. */
@Component({
  selector: 'app-vestidor-producto',
  imports: [FormsModule],
  template: `
    <section class="card pad stack">
      <h2>Vestidor virtual (móvil)</h2>
      @if (datos(); as d) {
        @if (!d.admite) { <p class="muted small" role="status">{{ d.mensaje }} Solo se prueban camisas, polos y chaquetas.</p> }
        @else {
          <p class="muted small">Suba el PNG de la prenda <strong>ya recortado, con fondo transparente</strong> (se reduce a 800 px de ancho). Los puntos de anclaje indican dónde están los hombros y la cadera dentro de la imagen.</p>
          @for (c of d.colores; track c.color_id) {
            <div class="fila">
              <div class="vista">@if (c.imagen_url) { <img [src]="media + c.imagen_url" [alt]="'Vestidor ' + c.color" /> } @else { <span class="small muted">Sin imagen</span> }</div>
              <div class="stack" style="flex:1;min-width:240px">
                <div class="row"><span class="swatch" [style.background]="c.codigo_hex"></span><strong>{{ c.color }}</strong>
                  <span class="badge" [class.ok]="c.listo" [class.warn]="!c.listo">{{ c.listo ? 'Listo para el vestidor' : 'Falta la imagen' }}</span></div>
                <div class="row" style="flex-wrap:wrap">
                  <label class="small">Línea de hombros (0–0.5)<input type="number" step="0.01" min="0" max="0.5" [(ngModel)]="anclaje(c).y_hombros" [name]="'yh' + c.color_id" style="width:6rem" /></label>
                  <label class="small">Ancho de hombros (0.3–1)<input type="number" step="0.01" min="0.3" max="1" [(ngModel)]="anclaje(c).ancho_hombros" [name]="'ah' + c.color_id" style="width:6rem" /></label>
                  <label class="small">Cadera (0.4–1)<input type="number" step="0.01" min="0.4" max="1" [(ngModel)]="anclaje(c).y_cadera" [name]="'yc' + c.color_id" style="width:6rem" /></label>
                  <label class="small">Ajuste de escala<input type="number" step="0.05" min="0.5" max="1.5" [(ngModel)]="anclaje(c).ajuste" [name]="'aj' + c.color_id" style="width:6rem" /></label>
                </div>
                <div class="row">
                  <input type="file" accept="image/png" (change)="elegir(c, $event)" [attr.aria-label]="'PNG del color ' + c.color" />
                  <button class="btn primary sm" (click)="subir(c)" [disabled]="!archivos[c.color_id] || trabajando()">Subir PNG</button>
                  @if (c.listo) { <button class="btn danger sm" (click)="quitar(c)" [disabled]="trabajando()">Quitar</button> }
                </div>
              </div>
            </div>
          }
          @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
        }
      } @else { <p class="muted small">Cargando…</p> }
    </section>`,
  styles: `
    .fila { display: flex; gap: 1rem; flex-wrap: wrap; border-top: 1px solid var(--line); padding-top: .8rem; }
    .vista { width: 120px; height: 144px; display: grid; place-items: center; border: 1px solid var(--line); border-radius: 8px; background: repeating-conic-gradient(#e8e4dd 0 25%, #f7f5f1 0 50%) 0 / 16px 16px; }
    .vista img { max-width: 100%; max-height: 100%; }
    .swatch { width: 1rem; height: 1rem; border-radius: 50%; border: 1px solid var(--line); display: inline-block; }`,
})
export class VestidorProductoComponent implements OnInit {
  readonly productoId = input.required<number>();
  private api = inject(VestidorApi);
  private toast = inject(ToastService);

  readonly media = MEDIA_URL;
  readonly datos = signal<VestidorProducto | null>(null);
  readonly error = signal('');
  readonly trabajando = signal(false);
  archivos: Record<number, File | null> = {};
  private anclajes: Record<number, Anclaje> = {};

  ngOnInit() { this.cargar(); }

  cargar() {
    this.api.producto(this.productoId()).subscribe({
      next: (d) => { this.datos.set(d); for (const c of d.colores) this.anclajes[c.color_id] = { ...(c.anclaje ?? ANCLAJE_POR_DEFECTO) }; },
      error: (e) => this.error.set(mensajeError(e)),
    });
  }

  anclaje(c: ColorVestidor): Anclaje { return (this.anclajes[c.color_id] ??= { ...ANCLAJE_POR_DEFECTO }); }
  elegir(c: ColorVestidor, ev: Event) { this.archivos[c.color_id] = (ev.target as HTMLInputElement).files?.[0] ?? null; }

  subir(c: ColorVestidor) {
    const archivo = this.archivos[c.color_id];
    if (!archivo) return;
    this.trabajando.set(true); this.error.set('');
    this.api.subir(this.productoId(), c.color_id, archivo, this.anclaje(c)).subscribe({
      next: () => { this.trabajando.set(false); this.archivos[c.color_id] = null; this.toast.ok(`Imagen del vestidor (${c.color}) guardada.`); this.cargar(); },
      error: (e) => { this.trabajando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  quitar(c: ColorVestidor) {
    if (!confirm(`¿Quitar la imagen del vestidor en ${c.color}?`)) return;
    this.api.quitar(this.productoId(), c.color_id).subscribe({ next: () => this.cargar(), error: (e) => this.toast.error(mensajeError(e)) });
  }
}
