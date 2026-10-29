import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MEDIA_URL } from '../../../core/api.config';
import { CatalogoApi } from '../../../core/api/catalogo.api';
import { ReportesApi } from '../../../core/api/reportes.api';
import { Prenda, SucursalCatalogo } from '../../../core/catalogo.models';
import { MensajeChat, Recomendaciones } from '../../../core/reportes.models';
import { mensajeError } from '../../../core/ui/toast.service';

/** CU-07 · Asistente y recomendador de prendas: el cliente pide lo que busca en lenguaje natural y recibe prendas reales con stock, además de recomendaciones según sus compras. */
@Component({
  selector: 'app-asistente',
  imports: [FormsModule, RouterLink],
  template: `
    <div class="page" style="max-width:1000px">
      <div class="page-head"><div><h1>Asistente de compras</h1><p>Cuénteme qué busca y le muestro prendas disponibles. Por ejemplo: «una camisa azul de menos de 200 Bs».</p></div></div>
      <label style="max-width:260px;margin-bottom:1rem">Ver prendas con stock en
        <select name="s" [ngModel]="sucursal" (ngModelChange)="sucursal = $event"><option [ngValue]="null">Cualquier sucursal</option>@for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }}</option> }</select></label>

      <section class="card pad stack">
        <div class="conversacion" aria-live="polite">
          @if (!mensajes().length) { <p class="muted">Empiece escribiendo abajo o elija una sugerencia.</p> }
          @for (m of mensajes(); track $index) {
            <div class="msg" [class.yo]="m.rol === 'usuario'">
              <div class="burbuja">{{ m.texto }}</div>
              @if (m.productos?.length) {
                <div class="prendas">
                  @for (p of m.productos; track p.id) {
                    <a class="card prenda" [routerLink]="['/tienda/catalogo', p.id]">
                      @if (p.imagen) { <img [src]="media + p.imagen" [alt]="p.nombre" /> } @else { <span class="foto">👕</span> }
                      <strong>{{ p.nombre }}</strong><span class="small muted">{{ p.categoria }}</span>
                      <span>@if (p.promocion) { <s class="muted small">Bs {{ p.precio }}</s> } <strong>Bs {{ p.precio_final }}</strong> @if (p.promocion) { <span class="badge danger">{{ p.promocion }}</span> }</span>
                    </a>
                  }
                </div>
              }
              @if (m.sugerencias?.length && $last) { <div class="row" style="flex-wrap:wrap">@for (s of m.sugerencias; track s) { <button type="button" class="chip" (click)="enviar(s)">{{ s }}</button> }</div> }
            </div>
          }
          @if (pensando()) { <div class="msg"><div class="burbuja">Buscando…</div></div> }
        </div>
        @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
        <form class="row" (ngSubmit)="enviar(texto)">
          <input name="t" [(ngModel)]="texto" placeholder="Escriba su consulta…" maxlength="500" autocomplete="off" style="flex:1" [disabled]="pensando()" />
          <button class="btn primary" [disabled]="pensando() || !texto.trim()">Enviar</button>
        </form>
      </section>

      @if (rec(); as r) {
        <h2 style="margin:1.5rem 0 .3rem">Recomendadas para usted</h2>
        <p class="muted small">{{ r.motivo }}</p>
        <div class="prendas">
          @for (p of r.productos; track p.id) {
            <a class="card prenda" [routerLink]="['/tienda/catalogo', p.id]">
              @if (p.imagen) { <img [src]="media + p.imagen" [alt]="p.nombre" /> } @else { <span class="foto">👕</span> }
              <strong>{{ p.nombre }}</strong><span class="small muted">{{ p.categoria }}</span><strong>Bs {{ p.precio_final }}</strong>
            </a>
          } @empty { <p class="muted">Por ahora no hay recomendaciones disponibles.</p> }
        </div>
      }
    </div>`,
  styles: `.conversacion { display: grid; gap: .8rem; max-height: 55vh; overflow-y: auto; padding: .3rem; }
    .msg { display: grid; gap: .5rem; justify-items: start; } .msg.yo { justify-items: end; }
    .burbuja { background: var(--surface-2, #f1ece6); border-radius: 14px; padding: .55rem .9rem; max-width: 85%; } .yo .burbuja { background: var(--accent); color: #fff; }
    .prendas { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: .7rem; width: 100%; }
    .prenda { display: grid; gap: .25rem; padding: .6rem; text-decoration: none; color: inherit; } .prenda img { width: 100%; aspect-ratio: 3/4; object-fit: cover; border-radius: 8px; }
    .foto { font-size: 2.5rem; display: grid; place-items: center; aspect-ratio: 3/4; background: #f1ece6; border-radius: 8px; }
    .chip { border: 1px solid var(--line); background: var(--surface); border-radius: 999px; padding: .25rem .7rem; font-size: .82rem; cursor: pointer; }`,
})
export class AsistentePage implements OnInit {
  private api = inject(ReportesApi);
  private catalogo = inject(CatalogoApi);

  readonly media = MEDIA_URL;
  readonly mensajes = signal<MensajeChat[]>([]);
  readonly sucursales = signal<SucursalCatalogo[]>([]);
  readonly rec = signal<Recomendaciones | null>(null);
  readonly pensando = signal(false);
  readonly error = signal('');
  texto = '';
  sucursal: number | null = null;

  ngOnInit() {
    this.catalogo.sucursales().subscribe((s) => this.sucursales.set(s));
    this.api.recomendaciones(null).subscribe({ next: (r) => this.rec.set(r), error: (e) => this.error.set(mensajeError(e)) });
  }

  enviar(texto: string) {
    texto = texto.trim();
    if (!texto || this.pensando()) return;
    this.error.set(''); this.texto = '';
    this.mensajes.update((m) => [...m, { rol: 'usuario', texto }]);
    this.pensando.set(true);
    this.api.chat(this.mensajes(), this.sucursal).subscribe({
      next: (r) => { this.pensando.set(false); this.mensajes.update((m) => [...m, { rol: 'asistente', texto: r.respuesta, productos: r.productos as Prenda[], sugerencias: r.sugerencias }]); },
      error: (e) => { this.pensando.set(false); this.error.set(mensajeError(e)); },
    });
  }
}
