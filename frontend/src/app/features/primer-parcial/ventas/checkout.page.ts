import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ComprasApi } from '../../../core/api/compras.api';
import { CarritoEstadoService } from '../../../core/carrito/carrito-estado.service';
import { Carrito, Pedido, ResultadoPago } from '../../../core/compras.models';
import { mensajeError } from '../../../core/ui/toast.service';
import { PagoTarjetaComponent } from './pago-tarjeta.component';
import { ConnectivityService } from '../../../core/offline/connectivity.service';
import { LocalDbService } from '../../../core/offline/local-db.service';
import { BsPipe } from '../../../core/formato-bs';

const MSG_COMPROBANTE_SIN_CACHE = 'Sin conexión: este comprobante todavía no se descargó. Ábralo una vez con Internet para tenerlo disponible sin conexión.';

/** CU-11 · Checkout (entrega y facturación). El pago con tarjeta (CU-32) lo resuelve el componente compartido `app-pago-tarjeta`. */
@Component({
  selector: 'app-checkout',
  imports: [BsPipe, FormsModule, RouterLink, PagoTarjetaComponent],
  template: `
    <div class="page" style="max-width:980px">
      <div class="page-head"><div><h1>Pagar mi compra</h1><p>Complete los datos de entrega y facturación, y pague con tarjeta.</p></div></div>
      @if (compraPendiente()) { <div class="alert warn" role="status">Compra guardada en este dispositivo. Se pagará con tarjeta al recuperar la conexión, desde Mis compras.<br /><a routerLink="/tienda/compras">Ir a Mis compras</a></div> }

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
                @if (!pedido()) { <div><button class="btn primary" [disabled]="creando() || !carrito()!.puede_pagar">{{ creando() ? 'Preparando…' : red.online() ? 'Continuar al pago' : 'Guardar compra para sincronizar' }}</button>
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
            @for (i of (pedido()?.items ?? carrito()!.items); track i.id) { <div class="row between small"><span>{{ i.cantidad }} × {{ i.producto }} · {{ i.talla }} · {{ i.color }}</span><span class="nowrap">{{ i.subtotal | bs }}</span></div> }
            <div class="row between"><span class="muted">Subtotal</span><span>{{ (pedido()?.subtotal ?? carrito()!.subtotal) | bs }}</span></div>
            @if ((pedido()?.descuento ?? carrito()!.descuento) !== '0.00') { <div class="row between"><span class="muted">Descuento</span><span>− {{ (pedido()?.descuento ?? carrito()!.descuento) | bs }}</span></div> }
            <div class="row between total"><strong>Total</strong><strong>{{ (pedido()?.total ?? carrito()!.total) | bs }}</strong></div>
            <p class="muted small">Incluye IVA: {{ (pedido()?.iva_incluido ?? carrito()!.iva_incluido) | bs }}</p>
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
  readonly red = inject(ConnectivityService);
  private db = inject(LocalDbService);

  readonly carrito = signal<Carrito | null>(null);
  readonly pedido = signal<Pedido | null>(null);
  readonly resultado = signal<ResultadoPago | null>(null);
  readonly creando = signal(false);
  readonly agotado = signal(false);
  readonly errorDatos = signal('');
  readonly compraPendiente = signal(false);
  form: { tipo_entrega: 'RETIRO' | 'DELIVERY'; direccion_entrega: string; nit_ci: string; razon_social: string } = { tipo_entrega: 'RETIRO', direccion_entrega: '', nit_ci: '', razon_social: '' };

  async ngOnInit() {
    if (!this.red.online()) { await this.estado.cargarLocal(); this.carrito.set(this.estado.carritoLocal()); return; }
    await this.estado.cargarLocal();
    await this.estado.refrescar();
    if (this.estado.carritoLocal()?.items.length) this.carrito.set(this.estado.carritoLocal());
    else this.api.carrito().subscribe({ next: (c) => { this.carrito.set(c); this.estado.fijar(c); }, error: (e) => { if (e.status === 0) void this.estado.cargarLocal().then(() => this.carrito.set(this.estado.carritoLocal())); else this.errorDatos.set(mensajeError(e)); } });
  }

  // ---- CU-11: del carrito al pedido ----
  crearPedido() {
    if (!this.red.online()) {
      if (this.carrito() && !this.estado.carritoLocal()) void this.estado.guardarLocal(this.carrito()!);
      this.errorDatos.set('');
      if (this.form.nit_ci.trim().length < 3) { this.errorDatos.set('Ingrese su NIT o CI para la facturación.'); return; }
      if (this.form.tipo_entrega === 'DELIVERY' && !this.form.direccion_entrega.trim()) { this.errorDatos.set('Ingrese la dirección de entrega.'); return; }
      this.creando.set(true);
      void (async () => { if (this.carrito() && !this.estado.carritoLocal()) await this.estado.guardarLocal(this.carrito()!); await this.estado.registrarCompraLocal(this.form); })().then(() => { this.creando.set(false); this.compraPendiente.set(true); this.carrito.set(null); }).catch((e) => { this.creando.set(false); this.errorDatos.set(mensajeError(e)); });
      return;
    }
    this.creando.set(true); this.errorDatos.set('');
    this.api.checkout(this.form).subscribe({
      next: (p) => { this.creando.set(false); this.pedido.set(p); },
      error: (e) => { this.creando.set(false); this.errorDatos.set(mensajeError(e)); this.api.carrito().subscribe((c) => this.carrito.set(c)); },
    });
  }

  alPagar(r: ResultadoPago) { this.resultado.set(r); if (r.aprobado) this.estado.fijar(null); }

  /** El stock se agotó mientras pagaba: se actualiza el carrito, que conserva sus prendas. */
  alAgotarse() { this.agotado.set(true); this.api.carrito().subscribe((c) => { this.carrito.set(c); this.estado.fijar(c); }); }

  async descargar(p: Pedido) {
    this.estado.fijar(null);
    if (!this.red.online()) {
      const guardado = await this.db.leerComprobanteLocal(p.id);
      if (!guardado) { this.errorDatos.set(MSG_COMPROBANTE_SIN_CACHE); return; }
      this.abrirPdf(guardado, p); return;
    }
    this.api.comprobante(p.id).subscribe((blob) => { void this.db.guardarComprobanteLocal(p.id, blob); this.abrirPdf(blob, p); });
  }

  private abrirPdf(blob: Blob, p: Pedido) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `${p.comprobante_numero}.pdf`; a.click(); URL.revokeObjectURL(a.href); }
}
