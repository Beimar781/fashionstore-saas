import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ComprasApi } from '../../../core/api/compras.api';
import { CarritoEstadoService } from '../../../core/carrito/carrito-estado.service';
import { Carrito, Pedido, ResultadoPago } from '../../../core/compras.models';
import { mensajeError } from '../../../core/ui/toast.service';
import { PagoTarjetaComponent } from './pago-tarjeta.component';

/** CU-11 · Checkout (entrega y facturación). El pago con tarjeta (CU-32) lo resuelve el componente compartido `app-pago-tarjeta`. */
@Component({
  selector: 'app-checkout',
  imports: [FormsModule, RouterLink, PagoTarjetaComponent],
  template: `
    <div class="page" style="max-width:980px">
      <div class="page-head"><div><h1>Pagar mi compra</h1><p>Complete los datos de entrega y facturación, y pague con tarjeta.</p></div></div>

      @if (!carrito()) { <div class="empty">Cargando…</div> }
      @else if (!carrito()!.items.length && !pedido()) { <div class="card empty">Su carrito está vacío. <a routerLink="/tienda/catalogo">Ver el catálogo</a></div> }
      @else {
        <div class="layout">
          <div class="stack">
            <!-- 1 · entrega y facturación -->
            <form class="card pad stack" (ngSubmit)="crearPedido()" #f="ngForm">
              <h2>1 · Entrega y facturación</h2>
              <fieldset [disabled]="!!pedido()" style="border:0;padding:0;display:grid;gap:.8rem">
                <div class="chips">
                  <button type="button" class="chip" [class.sel]="form.tipo_entrega === 'RETIRO'" (click)="form.tipo_entrega = 'RETIRO'">🏬 Retiro en {{ carrito()!.sucursal ?? 'la sucursal' }}</button>
                  <button type="button" class="chip" [class.sel]="form.tipo_entrega === 'DELIVERY'" (click)="form.tipo_entrega = 'DELIVERY'">🚚 Entrega a domicilio</button>
                </div>
                @if (form.tipo_entrega === 'DELIVERY') { <label>Dirección de entrega<input name="d" [(ngModel)]="form.direccion_entrega" maxlength="300" placeholder="Calle, número, barrio y referencia" /></label> }
                <div class="form-grid">
                  <label>NIT o CI<input name="n" [(ngModel)]="form.nit_ci" maxlength="20" required /></label>
                  <label>Razón social <span class="hint">(opcional)</span><input name="r" [(ngModel)]="form.razon_social" maxlength="120" /></label>
                </div>
              </fieldset>
              @if (errorDatos()) { <div class="alert danger" role="alert">{{ errorDatos() }}</div> }
              @if (!pedido()) { <div><button class="btn primary" [disabled]="creando() || !carrito()!.puede_pagar">{{ creando() ? 'Preparando…' : 'Continuar al pago' }}</button>
                @if (!carrito()!.puede_pagar) { <span class="small muted" style="margin-left:.6rem">Revise su carrito: hay prendas sin stock.</span> }</div> }
            </form>

            <!-- 2 · pago -->
            @if (pedido(); as p) {
              <section class="card pad stack">
                <h2>2 · Pago con tarjeta</h2>
                <app-pago-tarjeta [pedidoId]="p.id" [total]="p.total" (listo)="alPagar($event)" (sinStock)="alAgotarse()" />
                @if (resultado(); as r) {
                  @if (r.aprobado) {
                    <p>Su compra <strong>{{ r.pedido.codigo }}</strong> está pagada.</p>
                    <div class="row"><button type="button" class="btn primary" (click)="descargar(r.pedido)">⬇ Descargar comprobante</button>
                      <a class="btn" [routerLink]="['/tienda/compras', r.pedido.id]">Ver mi compra</a><a class="btn ghost" routerLink="/tienda/catalogo">Seguir comprando</a></div>
                  } @else { <div class="row"><a class="btn" routerLink="/tienda/compras">Mis compras</a></div> }
                }
                @if (agotado()) { <a class="btn" routerLink="/tienda/carrito">Revisar mi carrito</a> }
              </section>
            }
          </div>

          <aside class="card pad stack resumen">
            <h2>Su pedido</h2>
            @for (i of (pedido()?.items ?? carrito()!.items); track i.id) { <div class="row between small"><span>{{ i.cantidad }} × {{ i.producto }} · {{ i.talla }} · {{ i.color }}</span><span class="nowrap">Bs {{ i.subtotal }}</span></div> }
            <div class="row between"><span class="muted">Subtotal</span><span>Bs {{ pedido()?.subtotal ?? carrito()!.subtotal }}</span></div>
            @if ((pedido()?.descuento ?? carrito()!.descuento) !== '0.00') { <div class="row between"><span class="muted">Descuento</span><span>− Bs {{ pedido()?.descuento ?? carrito()!.descuento }}</span></div> }
            <div class="row between total"><strong>Total</strong><strong>Bs {{ pedido()?.total ?? carrito()!.total }}</strong></div>
            <p class="muted small">Incluye IVA: Bs {{ pedido()?.iva_incluido ?? carrito()!.iva_incluido }}</p>
          </aside>
        </div>
      }
    </div>`,
  styles: `
    .layout { display: grid; grid-template-columns: 1fr 320px; gap: 1.2rem; align-items: start; }
    .resumen { position: sticky; top: 1rem; } .total { font-size: 1.15rem; border-top: 1px solid var(--line); padding-top: .6rem; }
    @media (max-width: 900px) { .layout { grid-template-columns: 1fr; } .resumen { position: static; } }`,
})
export class CheckoutPage implements OnInit {
  private api = inject(ComprasApi);
  private estado = inject(CarritoEstadoService);

  readonly carrito = signal<Carrito | null>(null);
  readonly pedido = signal<Pedido | null>(null);
  readonly resultado = signal<ResultadoPago | null>(null);
  readonly creando = signal(false);
  readonly agotado = signal(false);
  readonly errorDatos = signal('');
  form = { tipo_entrega: 'RETIRO', direccion_entrega: '', nit_ci: '', razon_social: '' };

  ngOnInit() { this.api.carrito().subscribe((c) => { this.carrito.set(c); this.estado.fijar(c); }); }

  // ---- CU-11: del carrito al pedido ----
  crearPedido() {
    this.creando.set(true); this.errorDatos.set('');
    this.api.checkout(this.form).subscribe({
      next: (p) => { this.creando.set(false); this.pedido.set(p); },
      error: (e) => { this.creando.set(false); this.errorDatos.set(mensajeError(e)); this.api.carrito().subscribe((c) => this.carrito.set(c)); },
    });
  }

  alPagar(r: ResultadoPago) { this.resultado.set(r); if (r.aprobado) this.estado.fijar(null); }

  /** El stock se agotó mientras pagaba: se actualiza el carrito, que conserva sus prendas. */
  alAgotarse() { this.agotado.set(true); this.api.carrito().subscribe((c) => { this.carrito.set(c); this.estado.fijar(c); }); }

  descargar(p: Pedido) {
    this.estado.fijar(null);
    this.api.comprobante(p.id).subscribe((blob) => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = `${p.comprobante_numero}.pdf`; a.click(); URL.revokeObjectURL(a.href);
    });
  }
}
