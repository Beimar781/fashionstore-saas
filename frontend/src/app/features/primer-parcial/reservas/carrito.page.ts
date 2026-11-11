import { Component, OnInit, inject, signal } from '@angular/core';
import { ColaOperacionesService } from '../../../core/offline/cola-operaciones.service';
import { CargandoComponent, ErrorComponent } from '../../../core/ui/vacio.component';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MEDIA_URL } from '../../../core/api.config';
import { CatalogoApi } from '../../../core/api/catalogo.api';
import { ComprasApi } from '../../../core/api/compras.api';
import { SucursalCatalogo } from '../../../core/catalogo.models';
import { CarritoEstadoService } from '../../../core/carrito/carrito-estado.service';
import { Carrito, ItemCarrito } from '../../../core/compras.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';
import { ConnectivityService } from '../../../core/offline/connectivity.service';
import { BsPipe } from '../../../core/formato-bs';

/** CU-08 · Carrito de compras: cantidades, subtotal e IVA en tiempo real, con el stock de la sucursal elegida. */
@Component({
  selector: 'app-carrito',
  imports: [ErrorComponent, CargandoComponent, BsPipe, FormsModule, RouterLink],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Mi carrito</h1><p>Las prendas se descuentan del stock de la sucursal elegida recién cuando el pago se aprueba.</p></div></div>

      @if (!red.online() && (carrito() || estado.ediciones().length)) { <div class="alert warn" role="status">Sin conexión: los cambios de su carrito se guardan en este dispositivo y se aplicarán al volver Internet.</div> }
      @if (!carrito() && sinCarrito()) { <div class="card pad empty" role="status">Su carrito no está guardado en este dispositivo. Ábralo con conexión una vez.</div> }
      @else if (!carrito()) { <app-cargando /> }
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
            @if (error()) { <app-error [texto]="error()" /> }

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
                      <td class="right nowrap">@if (i.precio !== i.precio_final) { <s class="muted small">{{ i.precio | bs }}</s><br /> }{{ i.precio_final | bs }}</td>
                      <td><input type="number" min="1" max="10" [ngModel]="i.cantidad" (change)="cambiar(i, $any($event.target).value)" [name]="'q' + i.id" style="width:5.5rem;margin-left:auto;display:block" [disabled]="i.estado === 'RETIRADA'" /></td>
                      <td class="right nowrap"><strong>{{ i.subtotal | bs }}</strong></td>
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
            <div class="row between"><span class="muted">Subtotal</span><span>{{ c.subtotal | bs }}</span></div>
            @if (c.descuento !== '0.00') { <div class="row between"><span class="muted">Descuento</span><span class="ok-texto">− {{ c.descuento | bs }}</span></div> }
            <div class="row between total"><strong>Total</strong><strong>{{ c.total | bs }}</strong></div>
            <p class="muted small">Incluye IVA: {{ c.iva_incluido | bs }}</p>
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
  readonly estado = inject(CarritoEstadoService);
  readonly red = inject(ConnectivityService);
  private toast = inject(ToastService);

  readonly media = MEDIA_URL;
  readonly carrito = signal<Carrito | null>(null);
  readonly sucursales = signal<SucursalCatalogo[]>([]);
  readonly error = signal('');
  readonly sinCarrito = signal(false);

  private readonly recargaAlVolverLaRed = inject(ColaOperacionesService).alRefrescar(() => this.cargar());  // E1 · al volver la red la pantalla abierta se recarga sola
  ngOnInit() {
    this.catalogo.sucursales().subscribe({ next: (r) => this.sucursales.set(r), error: () => undefined });
    void this.cargar();
  }

  /** Con red, el carrito del servidor; sin red, la copia más los cambios hechos en este dispositivo (nunca «Cargando…» eterno). */
  private async cargar() {
    if (!this.red.online()) { await this.mostrarLocal(); return; }
    this.api.carrito().subscribe({ next: (c) => { this.sinCarrito.set(false); this.mostrar(c); }, error: (e) => { if (e.status === 0) void this.mostrarLocal(); else this.toast.error(mensajeError(e)); } });
  }

  private async mostrarLocal() {
    const c = await this.estado.vistaSinConexion();
    this.carrito.set(c); this.sinCarrito.set(!c); this.estado.fijar(c); this.error.set('');
  }

  /** Aplica un cambio en el dispositivo cuando no hay red; devuelve true si ya quedó resuelto aquí. */
  private async sinRed(cambio: () => Promise<void>): Promise<boolean> {
    if (this.red.online()) return false;
    try { await cambio(); await this.mostrarLocal(); this.toast.ok('Cambio guardado en este dispositivo; se aplicará al volver la conexión.'); } catch (e) { this.error.set((e as Error).message); }
    return true;
  }

  private mostrar(c: Carrito) { this.carrito.set(c); this.estado.fijar(c); this.error.set(''); }
  /** Un error (por ejemplo, stock insuficiente) se muestra y el carrito se recarga con lo que realmente hay. */
  private fallo(e: unknown) {
    this.api.carrito().subscribe((c) => { this.carrito.set(c); this.estado.fijar(c); this.error.set(mensajeError(e)); });
  }

  async cambiar(i: ItemCarrito, valor: string) {
    if (await this.sinRed(() => this.estado.cambiarCantidadSinConexion(i, Number(valor)))) return;
    this.api.cambiarCantidad(i.id, Number(valor)).subscribe({ next: (c) => this.mostrar(c), error: (e) => this.fallo(e) });
  }
  async quitar(i: ItemCarrito) {
    if (await this.sinRed(() => this.estado.quitarSinConexion(i))) return;
    this.api.quitar(i.id).subscribe({ next: (c) => this.mostrar(c), error: (e) => this.toast.error(mensajeError(e)) });
  }
  cambiarSucursal(id: number) {
    if (!this.red.online()) { this.error.set('Cambiar de sucursal necesita Internet.'); void this.mostrarLocal(); return; }
    this.api.elegirSucursal(id).subscribe({ next: (c) => this.mostrar(c), error: (e) => this.fallo(e) });
  }
  async vaciar() {
    if (!confirm('¿Vaciar el carrito?')) return;
    if (await this.sinRed(() => this.estado.vaciarSinConexion())) return;
    this.api.vaciar().subscribe({ next: (c) => this.mostrar(c), error: (e) => this.toast.error(mensajeError(e)) });
  }
}
