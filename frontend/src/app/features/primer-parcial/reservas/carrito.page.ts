import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MEDIA_URL } from '../../../core/api.config';
import { CatalogoApi } from '../../../core/api/catalogo.api';
import { ComprasApi } from '../../../core/api/compras.api';
import { SucursalCatalogo } from '../../../core/catalogo.models';
import { CarritoEstadoService } from '../../../core/carrito/carrito-estado.service';
import { Carrito, ItemCarrito } from '../../../core/compras.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';

/** CU-08 · Carrito de compras: cantidades, subtotal e IVA en tiempo real, con el stock de la sucursal elegida. */
@Component({
  selector: 'app-carrito',
  imports: [FormsModule, RouterLink],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Mi carrito</h1><p>Las prendas se descuentan del stock de la sucursal elegida recién cuando el pago se aprueba.</p></div></div>

      @if (!carrito()) { <div class="empty">Cargando…</div> }
      @else if (!carrito()!.items.length) {
        <div class="card empty">Su carrito está vacío. <a routerLink="/tienda/catalogo">Ver el catálogo</a></div>
      } @else {
        @let c = carrito()!;
        <div class="layout">
          <div class="stack">
            <section class="card pad row between">
              <label style="min-width:240px">Comprar en la sucursal
                <select [ngModel]="c.sucursal_id" (ngModelChange)="cambiarSucursal($event)" name="suc">
                  @for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }} · {{ s.ciudad }}</option> }
                </select></label>
              <button type="button" class="btn ghost danger" (click)="vaciar()">Vaciar carrito</button>
            </section>

            @for (a of c.avisos; track a) { <div class="alert warn" role="alert">{{ a }}</div> }
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }

            <section class="card table-wrap">
              <table>
                <thead><tr><th></th><th>Prenda</th><th class="right">Precio</th><th class="right">Cantidad</th><th class="right">Subtotal</th><th></th></tr></thead>
                <tbody>
                  @for (i of c.items; track i.id) {
                    <tr [class.mala]="i.estado !== 'OK'">
                      <td>@if (i.imagen) { <img class="mini" [src]="media + i.imagen" [alt]="i.producto" /> } @else { <span class="mini vacia">👕</span> }</td>
                      <td><a [routerLink]="['/tienda/catalogo', i.producto_id]"><strong>{{ i.producto }}</strong></a>
                        <div class="muted small">Talla {{ i.talla }} · {{ i.color }} · {{ i.sku }}</div>
                        @if (i.estado === 'SIN_STOCK') { <span class="badge danger">Hay {{ i.disponible }} disponible(s)</span> }
                        @if (i.estado === 'RETIRADA') { <span class="badge danger">Ya no está en el catálogo</span> }</td>
                      <td class="right nowrap">@if (i.precio !== i.precio_final) { <s class="muted small">Bs {{ i.precio }}</s><br /> }Bs {{ i.precio_final }}</td>
                      <td><input type="number" min="1" max="10" [ngModel]="i.cantidad" (change)="cambiar(i, $any($event.target).value)" [name]="'q' + i.id" style="width:5.5rem;margin-left:auto;display:block" [disabled]="i.estado === 'RETIRADA'" /></td>
                      <td class="right nowrap"><strong>Bs {{ i.subtotal }}</strong></td>
                      <td class="actions"><button type="button" class="btn sm danger" (click)="quitar(i)">Quitar</button></td>
                    </tr>
                  }
                </tbody>
              </table>
            </section>
          </div>

          <aside class="card pad stack resumen">
            <h2>Resumen</h2>
            <div class="row between"><span class="muted">Prendas</span><span>{{ c.total_unidades }}</span></div>
            <div class="row between"><span class="muted">Subtotal</span><span>Bs {{ c.subtotal }}</span></div>
            @if (c.descuento !== '0.00') { <div class="row between"><span class="muted">Descuento</span><span class="ok-texto">− Bs {{ c.descuento }}</span></div> }
            <div class="row between total"><strong>Total</strong><strong>Bs {{ c.total }}</strong></div>
            <p class="muted small">Incluye IVA: Bs {{ c.iva_incluido }}</p>
            <a class="btn primary" routerLink="/tienda/checkout" [class.disabled]="!c.puede_pagar" [attr.aria-disabled]="!c.puede_pagar" (click)="!c.puede_pagar && $event.preventDefault()">Proceder al pago</a>
            @if (!c.puede_pagar) { <p class="small muted">Corrija los avisos de arriba para poder pagar.</p> }
            <a routerLink="/tienda/catalogo" class="small">← Seguir comprando</a>
          </aside>
        </div>
      }
    </div>`,
  styles: `
    .layout { display: grid; grid-template-columns: 1fr 320px; gap: 1.2rem; align-items: start; }
    .mini { width: 52px; height: 66px; object-fit: cover; border-radius: 8px; display: grid; place-items: center; background: #ece8e1; }
    tr.mala { background: var(--danger-soft); } .total { font-size: 1.15rem; border-top: 1px solid var(--line); padding-top: .6rem; }
    .ok-texto { color: var(--ok); } .resumen { position: sticky; top: 1rem; }
    a.btn.disabled { opacity: .5; cursor: not-allowed; pointer-events: auto; }
    @media (max-width: 900px) { .layout { grid-template-columns: 1fr; } .resumen { position: static; } }`,
})
export class CarritoPage implements OnInit {
  private api = inject(ComprasApi);
  private catalogo = inject(CatalogoApi);
  private estado = inject(CarritoEstadoService);
  private toast = inject(ToastService);

  readonly media = MEDIA_URL;
  readonly carrito = signal<Carrito | null>(null);
  readonly sucursales = signal<SucursalCatalogo[]>([]);
  readonly error = signal('');

  ngOnInit() {
    this.catalogo.sucursales().subscribe((r) => this.sucursales.set(r));
    this.api.carrito().subscribe({ next: (c) => this.mostrar(c), error: (e) => this.toast.error(mensajeError(e)) });
  }

  private mostrar(c: Carrito) { this.carrito.set(c); this.estado.fijar(c); this.error.set(''); }
  /** Un error (por ejemplo, stock insuficiente) se muestra y el carrito se recarga con lo que realmente hay. */
  private fallo(e: unknown) {
    this.api.carrito().subscribe((c) => { this.carrito.set(c); this.estado.fijar(c); this.error.set(mensajeError(e)); });
  }

  cambiar(i: ItemCarrito, valor: string) {
    this.api.cambiarCantidad(i.id, Number(valor)).subscribe({ next: (c) => this.mostrar(c), error: (e) => this.fallo(e) });
  }
  quitar(i: ItemCarrito) { this.api.quitar(i.id).subscribe({ next: (c) => this.mostrar(c), error: (e) => this.toast.error(mensajeError(e)) }); }
  cambiarSucursal(id: number) { this.api.elegirSucursal(id).subscribe({ next: (c) => this.mostrar(c), error: (e) => this.fallo(e) }); }
  vaciar() {
    if (!confirm('¿Vaciar el carrito?')) return;
    this.api.vaciar().subscribe({ next: (c) => this.mostrar(c), error: (e) => this.toast.error(mensajeError(e)) });
  }
}
