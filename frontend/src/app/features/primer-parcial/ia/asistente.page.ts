import { NgTemplateOutlet } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MEDIA_URL } from '../../../core/api.config';
import { CatalogoApi } from '../../../core/api/catalogo.api';
import { ReportesApi } from '../../../core/api/reportes.api';
import { Prenda, SucursalCatalogo } from '../../../core/catalogo.models';
import { MensajeChat, Outfit, Privacidad, Recomendaciones } from '../../../core/reportes.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';

/** CU-07 · Asistente y recomendador: el cliente pide prendas en lenguaje natural; el sistema aprende de lo que compra, busca y mira para recomendarle, armarle outfits y mostrarle ofertas que le convienen. */
@Component({
  selector: 'app-asistente',
  imports: [FormsModule, RouterLink, NgTemplateOutlet],
  template: `
    <div class="page" style="max-width:1000px">
      <div class="page-head"><div><h1>Asistente de compras</h1><p>Cuénteme qué busca y le muestro prendas disponibles. Aprendo de lo que compra, busca y mira para recomendarle lo que le va a gustar.</p></div></div>
      <label style="max-width:260px;margin-bottom:1rem">Ver prendas con stock en
        <select name="s" [ngModel]="sucursal" (ngModelChange)="cambiarSucursal($event)"><option [ngValue]="null">Cualquier sucursal</option>@for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }}</option> }</select></label>

      <section class="card pad stack">
        <div class="conversacion" aria-live="polite">
          @if (!mensajes().length) { <p class="muted">Empiece escribiendo abajo, por ejemplo «recomiéndame algo» o «arma un outfit casual».</p> }
          @for (m of mensajes(); track $index) {
            <div class="msg" [class.yo]="m.rol === 'usuario'">
              <div class="burbuja">{{ m.texto }}</div>
              @if (m.productos?.length) { <div class="prendas">@for (p of m.productos; track p.id) { <ng-container *ngTemplateOutlet="tarjeta; context: { p: p }" /> }</div> }
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

      @if (outfit(); as o) {
        <section class="card pad stack" style="margin-top:1.5rem">
          <div class="row between"><h2>Outfit para usted</h2><span class="badge" [class.ok]="o.origen === 'IA'">{{ o.origen === 'IA' ? 'Armado por IA' : 'Reglas de combinación' }}</span></div>
          <p class="muted small">{{ o.motivo }}</p>
          @if (o.base) { <div class="prendas"><ng-container *ngTemplateOutlet="tarjeta; context: { p: o.base, etiqueta: 'Prenda base' }" />@for (p of o.prendas; track p.id) { <ng-container *ngTemplateOutlet="tarjeta; context: { p: p, motivo: o.motivos[p.id] }" /> }</div> }
        </section>
      }

      @if (rec(); as r) {
        <h2 style="margin:1.5rem 0 .3rem">Recomendadas para usted</h2>
        <p class="muted small">{{ r.motivo }} @if (r.origen === 'IA') { <span class="badge ok">Elegidas por IA</span> }</p>
        <div class="prendas">@for (p of r.productos; track p.id) { <ng-container *ngTemplateOutlet="tarjeta; context: { p: p, motivo: r.motivos[p.id] }" /> } @empty { <p class="muted">Por ahora no hay recomendaciones disponibles.</p> }</div>
        @if (r.ofertas.length) {
          <h2 style="margin:1.5rem 0 .3rem">Ofertas que le convienen</h2>
          <div class="prendas">@for (p of r.ofertas; track p.id) { <ng-container *ngTemplateOutlet="tarjeta; context: { p: p, motivo: r.motivos[p.id] }" /> }</div>
        }
        <div style="margin-top:1rem"><button class="btn" (click)="armarOutfit(null)">👗 Armar un outfit para mí</button></div>
      }

      @if (priv(); as v) {
        <section class="card pad stack" style="margin-top:1.5rem">
          <h3>Mi privacidad</h3>
          <label class="check"><input type="checkbox" [ngModel]="v.personalizar" (ngModelChange)="personalizar($event)" name="pers" /> Permitir que la tienda aprenda de lo que compro, busco y miro para recomendarme prendas</label>
          <div class="row between small"><span class="muted">{{ v.interacciones }} búsqueda(s) y prenda(s) vista(s) recordadas.</span><button class="btn sm danger" (click)="borrar()" [disabled]="!v.interacciones">Borrar lo que aprendió</button></div>
        </section>
      }
    </div>

    <ng-template #tarjeta let-p="p" let-motivo="motivo" let-etiqueta="etiqueta">
      <div class="card prenda">
        <a [routerLink]="['/tienda/catalogo', p.id]" class="enlace">
          @if (p.imagen) { <img [src]="media + p.imagen" [alt]="p.nombre" /> } @else { <span class="foto">👕</span> }
          @if (etiqueta) { <span class="badge">{{ etiqueta }}</span> }
          <strong>{{ p.nombre }}</strong><span class="small muted">{{ p.categoria }}</span>
          <span>@if (p.promocion) { <s class="muted small">Bs {{ p.precio }}</s> } <strong>Bs {{ p.precio_final }}</strong> @if (p.promocion) { <span class="badge danger">{{ p.promocion }}</span> }</span>
        </a>
        @if (motivo) { <span class="small motivo">{{ motivo }}</span> }
        <button type="button" class="btn sm ghost" (click)="armarOutfit(p.id)">Armar outfit con esta</button>
      </div>
    </ng-template>`,
  styles: `.conversacion { display: grid; gap: .8rem; max-height: 55vh; overflow-y: auto; padding: .3rem; }
    .msg { display: grid; gap: .5rem; justify-items: start; } .msg.yo { justify-items: end; }
    .burbuja { background: var(--surface-2, #f1ece6); border-radius: 14px; padding: .55rem .9rem; max-width: 85%; } .yo .burbuja { background: var(--accent); color: #fff; }
    .prendas { display: grid; grid-template-columns: repeat(auto-fill, minmax(165px, 1fr)); gap: .7rem; width: 100%; }
    .prenda { display: grid; gap: .35rem; padding: .6rem; align-content: start; } .enlace { display: grid; gap: .25rem; text-decoration: none; color: inherit; }
    .prenda img { width: 100%; aspect-ratio: 3/4; object-fit: cover; border-radius: 8px; } .motivo { color: var(--muted); font-style: italic; }
    .foto { font-size: 2.5rem; display: grid; place-items: center; aspect-ratio: 3/4; background: #f1ece6; border-radius: 8px; }
    .chip { border: 1px solid var(--line); background: var(--surface); border-radius: 999px; padding: .25rem .7rem; font-size: .82rem; cursor: pointer; }`,
})
export class AsistentePage implements OnInit {
  private api = inject(ReportesApi);
  private catalogo = inject(CatalogoApi);
  private toast = inject(ToastService);

  readonly media = MEDIA_URL;
  readonly mensajes = signal<MensajeChat[]>([]);
  readonly sucursales = signal<SucursalCatalogo[]>([]);
  readonly rec = signal<Recomendaciones | null>(null);
  readonly outfit = signal<Outfit | null>(null);
  readonly priv = signal<Privacidad | null>(null);
  readonly pensando = signal(false);
  readonly error = signal('');
  texto = '';
  sucursal: number | null = null;

  ngOnInit() {
    this.catalogo.sucursales().subscribe((s) => this.sucursales.set(s));
    this.cargarRecomendaciones();
    this.api.privacidad().subscribe({ next: (p) => this.priv.set(p), error: () => undefined });
  }

  private cargarRecomendaciones() {
    this.api.recomendaciones(this.sucursal).subscribe({ next: (r) => this.rec.set(r), error: (e) => this.error.set(mensajeError(e)) });
  }

  cambiarSucursal(id: number | null) { this.sucursal = id; this.outfit.set(null); this.cargarRecomendaciones(); }

  enviar(texto: string) {
    texto = texto.trim();
    if (!texto || this.pensando()) return;
    this.error.set(''); this.texto = '';
    this.mensajes.update((m) => [...m, { rol: 'usuario', texto }]);
    this.pensando.set(true);
    this.api.chat(this.mensajes(), this.sucursal).subscribe({
      next: (r) => {
        this.pensando.set(false);
        this.mensajes.update((m) => [...m, { rol: 'asistente', texto: r.respuesta, productos: r.productos as Prenda[], sugerencias: r.sugerencias }]);
        this.api.privacidad().subscribe({ next: (p) => this.priv.set(p), error: () => undefined });
      },
      error: (e) => { this.pensando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  armarOutfit(productoId: number | null) {
    this.api.outfit(productoId, this.sucursal).subscribe({ next: (o) => this.outfit.set(o), error: (e) => this.toast.error(mensajeError(e)) });
  }

  personalizar(valor: boolean) {
    this.api.fijarPrivacidad(valor).subscribe({
      next: (p) => { this.priv.set(p); this.cargarRecomendaciones(); this.toast.ok(valor ? 'La tienda volverá a aprender de sus gustos.' : 'Listo: ya no se recuerda lo que busca y se borró lo aprendido.'); },
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }

  borrar() {
    this.api.borrarHistorial().subscribe({ next: (p) => { this.priv.set(p); this.cargarRecomendaciones(); this.toast.ok('Se borró lo que el sistema había aprendido.'); }, error: (e) => this.toast.error(mensajeError(e)) });
  }
}
