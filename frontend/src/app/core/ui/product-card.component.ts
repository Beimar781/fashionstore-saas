import { Component, computed, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MEDIA_URL } from '../api.config';
import { Prenda } from '../catalogo.models';
import { BsPipe } from '../formato-bs';

const MAX_COLORES = 5;

/** Tarjeta de prenda con tamaño y distribución fijos: imagen 4:5, nombre a 2 líneas, y precio, colores y tallas siempre abajo. Lo que se pase dentro de la etiqueta (motivo, botones) va debajo. */
@Component({
  selector: 'app-product-card',
  imports: [RouterLink, BsPipe],
  template: `
    <article class="pc card">
      <a class="pc-link" [routerLink]="['/tienda/catalogo', prenda().id]" [queryParams]="sucursal() ? { sucursal: sucursal() } : {}" [attr.aria-label]="prenda().nombre">
        <div class="pc-foto">
          @if (prenda().imagen && !fallo()) { <img [src]="media + prenda().imagen" [alt]="prenda().nombre" loading="lazy" (error)="fallo.set(true)" /> } @else { <span class="pc-vacia" aria-hidden="true">👕</span> }
          @if (etiqueta()) { <span class="badge pc-etiqueta">{{ etiqueta() }}</span> }
          @if (prenda().promocion) { <span class="badge danger pc-oferta">Oferta</span> }
          @if (!prenda().disponible) { <span class="badge pc-agotada">{{ sucursal() ? 'Sin stock aquí' : 'Agotada' }}</span> }
        </div>
        <div class="pc-info">
          <strong class="pc-nombre" [title]="prenda().nombre">{{ prenda().nombre }}</strong>
          <span class="pc-cat muted small">{{ prenda().categoria }}{{ prenda().marca ? ' · ' + prenda().marca : '' }}</span>
          <div class="pc-pie">
            <span class="pc-precio">@if (prenda().precio_final !== prenda().precio) { <s class="muted small">{{ prenda().precio | bs }}</s> } <b>{{ prenda().precio_final | bs }}</b></span>
            <span class="pc-colores">
              @for (c of visibles(); track c.id) { <span class="swatch" [style.background]="c.codigo_hex" [title]="c.nombre"></span> }
              @if (extra() > 0) { <span class="pc-mas small muted">+{{ extra() }}</span> }
            </span>
            <span class="pc-tallas muted small" [title]="prenda().tallas.join(' · ')">Tallas: {{ prenda().tallas.join(' · ') }}</span>
          </div>
        </div>
      </a>
      <ng-content />
    </article>`,
  styles: `
    :host { display: block; min-width: 0; }
    .pc { display: flex; flex-direction: column; height: 100%; border-radius: 14px; overflow: hidden; transition: transform .15s, box-shadow .15s; }
    .pc:hover { transform: translateY(-3px); box-shadow: 0 2px 4px rgba(29,26,34,.08), 0 12px 28px rgba(29,26,34,.12); }
    .pc-link { display: flex; flex-direction: column; flex: 1; color: inherit; text-decoration: none; min-width: 0; }
    .pc-link:hover { text-decoration: none; }
    .pc-link:focus-visible { outline: 3px solid var(--accent); outline-offset: -3px; }
    .pc-foto { position: relative; aspect-ratio: 4 / 5; overflow: hidden; background: #ece8e1; display: grid; place-items: center; }
    .pc-foto img { width: 100%; height: 100%; object-fit: cover; object-position: center top; display: block; transition: transform .3s; }
    .pc:hover .pc-foto img { transform: scale(1.04); }
    .pc-vacia { font-size: 2.5rem; }
    .pc-oferta { position: absolute; top: .6rem; left: .6rem; }
    .pc-etiqueta { position: absolute; top: .6rem; right: .6rem; background: #fff; }
    .pc-agotada { position: absolute; top: .6rem; right: .6rem; background: #1d1a22; color: #fff; }
    .pc-info { display: flex; flex-direction: column; gap: .25rem; flex: 1; padding: .8rem .9rem 1rem; min-width: 0; }
    .pc-nombre { display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.3; min-height: 2.6em; }
    .pc-cat, .pc-tallas { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .pc-pie { margin-top: auto; display: flex; flex-direction: column; gap: .3rem; padding-top: .3rem; }
    .pc-precio b { font-size: 1.05rem; }
    .pc-colores { display: flex; align-items: center; gap: .3rem; min-height: 1.1rem; flex-wrap: nowrap; overflow: hidden; }
    .pc-colores .swatch { width: 1rem; height: 1rem; }
    @media (max-width: 600px) { .pc-info { padding: .6rem .6rem .75rem; } .pc-nombre { font-size: .9rem; } }
  `,
})
export class ProductCardComponent {
  readonly prenda = input.required<Prenda>();
  readonly sucursal = input<number | null>(null);
  readonly etiqueta = input<string | null>(null);

  readonly media = MEDIA_URL;
  readonly fallo = signal(false);  // si la foto no carga, queda el recuadro del mismo tamaño
  readonly visibles = computed(() => this.prenda().colores.slice(0, MAX_COLORES));
  readonly extra = computed(() => Math.max(0, this.prenda().colores.length - MAX_COLORES));
}
