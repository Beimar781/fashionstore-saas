import { Component, OnInit, effect, inject, signal, untracked } from '@angular/core';
import { TarjetasGuardadasService } from '../../../core/pagos/tarjetas-guardadas.service';
import { CargandoComponent } from '../../../core/ui/vacio.component';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ComprasApi } from '../../../core/api/compras.api';
import { CarritoEstadoService } from '../../../core/carrito/carrito-estado.service';
import { Carrito, Pedido, ResultadoPago, TarjetaGuardada } from '../../../core/compras.models';
import { AuthService } from '../../../core/auth/auth.service';
import { mensajeError } from '../../../core/ui/toast.service';
import { PagoTarjetaComponent } from './pago-tarjeta.component';
import { ConnectivityService } from '../../../core/offline/connectivity.service';
import { LocalDbService } from '../../../core/offline/local-db.service';
import { BsPipe } from '../../../core/formato-bs';

export const MSG_TARJETA_NUEVA = 'Para usar una tarjeta nueva necesita Internet. Puede pagar con una tarjeta guardada o dejar la compra por pagar.';
export const MSG_AUTORIZAR = 'Confirme la autorización del cobro para pagar con la tarjeta guardada.';

/** Las tarjetas guardadas que se pueden ofrecer sin conexión: no vencidas al día de hoy. */
export function tarjetasVigentes(tarjetas: TarjetaGuardada[], hoy = new Date()): TarjetaGuardada[] {
  const mes = hoy.getFullYear() * 12 + hoy.getMonth() + 1;
  return tarjetas.filter((t) => t.exp_anio * 12 + t.exp_mes >= mes);
}

const MSG_COMPROBANTE_SIN_CACHE = 'Sin conexión: este comprobante todavía no se descargó. Ábralo una vez con Internet para tenerlo disponible sin conexión.';

/** CU-11 · Checkout (entrega y facturación). El pago con tarjeta (CU-32) lo resuelve el componente compartido `app-pago-tarjeta`. */
@Component({
  selector: 'app-checkout',
  imports: [CargandoComponent, BsPipe, FormsModule, RouterLink, PagoTarjetaComponent],
  template: `
    <div class="page" style="max-width:980px">
      <div class="page-head"><div><h1>Pagar mi compra</h1><p>Complete los datos de entrega y facturación, y pague con tarjeta.</p></div></div>
      @if (compraPendiente()) { <div class="alert warn" role="status">@if (cobroAutorizado()) { Compra guardada en este dispositivo. Al recuperar la conexión se cobrará a su {{ cobroAutorizado() }}; si no se puede cobrar, quedará por pagar en Mis compras. } @else { Compra guardada en este dispositivo. Se pagará con tarjeta al recuperar la conexión, desde Mis compras. }<br /><a routerLink="/tienda/compras">Ir a Mis compras</a></div> }

      @if (!carrito() && compraPendiente()) { }  <!-- solo el aviso de compra guardada, nada más -->
      @else if (!carrito() && sinCarrito()) { <div class="card pad empty" role="status">Su carrito no está guardado en este dispositivo. Ábralo con conexión una vez.</div> }
      @else if (!carrito()) { <app-cargando /> }
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
                  <label>NIT o CI<input name="n" [(ngModel)]="form.nit_ci" (ngModelChange)="errorDatos.set('')" maxlength="20" required /></label>
                  <label>Razón social <span class="hint">(opcional)</span><input name="r" [(ngModel)]="form.razon_social" maxlength="120" /></label>
                </div>
              </fieldset>
              @if (errorDatos()) { <div class="alert danger" role="alert">{{ errorDatos() }}</div> }
                @if (!red.online() && !pedido()) {
                  <div class="stack">
                    <strong>Pago</strong>
                    @if (tarjetas().length) {
                      <label class="check"><input type="radio" name="pagoOffline" [value]="0" [(ngModel)]="tarjetaElegida" /> Dejar por pagar</label>
                      @for (t of tarjetas(); track t.id) { <label class="check"><input type="radio" name="pagoOffline" [value]="t.id" [(ngModel)]="tarjetaElegida" /> Pagar con {{ t.marca }} terminada en {{ t.ultimos4 }} al volver la conexión@if (venceEsteMes(t)) { <span class="small muted"> · vence antes del {{ ultimoDiaDelMes() }}: si se envía después, quedará por pagar (puede elegir «Dejar por pagar»)</span> }</label> }
                      @if (tarjetaElegida) { <label class="check"><input type="checkbox" name="autorizo" [(ngModel)]="autorizo" /> Autorizo el cobro de {{ carrito()!.total | bs }} a esta tarjeta cuando se confirme mi compra.</label> }
                    }
                    <p class="small muted">{{ msgTarjetaNueva }}</p>
                  </div>
                }
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
  private tarjetasGuardadas = inject(TarjetasGuardadasService);
  private auth = inject(AuthService);

  readonly carrito = signal<Carrito | null>(null);
  readonly pedido = signal<Pedido | null>(null);
  readonly resultado = signal<ResultadoPago | null>(null);
  readonly creando = signal(false);
  readonly agotado = signal(false);
  readonly errorDatos = signal('');
  readonly compraPendiente = signal(false);
  readonly sinCarrito = signal(false);  // sin conexión y sin copia del carrito: se explica en vez de quedar en «Cargando…»
  readonly cobroAutorizado = signal('');
  readonly tarjetas = signal<TarjetaGuardada[]>([]);  // sin conexión: las que se guardaron la última vez con red
  readonly msgTarjetaNueva = MSG_TARJETA_NUEVA;
  tarjetaElegida = 0;
  autorizo = false;
  form: { tipo_entrega: 'RETIRO' | 'DELIVERY'; direccion_entrega: string; nit_ci: string; razon_social: string } = { tipo_entrega: 'RETIRO', direccion_entrega: '', nit_ci: '', razon_social: '' };

  constructor() {
    // sin conexión (también si se pierde con la pantalla abierta) se ofrecen las tarjetas guardadas la última vez con red
    effect(() => { if (!this.red.online()) void this.cargarTarjetasLocales(); });
    // al volver la red (o al perderla) con la pantalla abierta, el carrito se vuelve a cargar solo
    effect(() => { const enLinea = this.red.online(); untracked(() => { if (this.iniciado && !this.pedido()) void this.cargar(enLinea); }); });
  }

  /** Una tarjeta que vence este mes puede estar vencida cuando la compra se sincronice: se avisa al registrar. */
  venceEsteMes(t: TarjetaGuardada, hoy = new Date()) { return t.exp_anio === hoy.getFullYear() && t.exp_mes === hoy.getMonth() + 1; }
  ultimoDiaDelMes(hoy = new Date()) { const f = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0); return `${String(f.getDate()).padStart(2, '0')}/${String(f.getMonth() + 1).padStart(2, '0')}`; }

  async cargarTarjetasLocales() { this.tarjetas.set(tarjetasVigentes(await this.tarjetasGuardadas.locales())); }

  private get claveTarjetas() { const s = this.auth.sesion(); return `${s?.empresa?.id ?? 0}:${s?.usuario.id ?? 0}`; }

  private iniciado = false;

  async ngOnInit() { this.iniciado = true; await this.cargar(this.red.online()); }

  private async cargar(enLinea: boolean) {
    if (!enLinea) {
      const c = await this.estado.vistaSinConexion();  // la copia del servidor + los cambios hechos sin conexión + lo agregado sin conexión
      this.carrito.set(c); this.sinCarrito.set(!c);
      return;
    }
    this.sinCarrito.set(false);
    // con red se guarda la lista de tarjetas (marca, últimos 4 y vencimiento) para ofrecerlas si después se queda sin conexión
    void this.tarjetasGuardadas.refrescar();
    await this.estado.cargarLocal();
    await this.estado.refrescar();
    if (this.estado.carritoLocal()?.items.length) this.carrito.set(this.estado.carritoLocal());
    else this.api.carrito().subscribe({ next: (c) => { this.carrito.set(c); this.estado.fijar(c); }, error: (e) => { if (e.status === 0) void this.estado.cargarLocal().then(() => this.carrito.set(this.estado.carritoLocal())); else this.errorDatos.set(mensajeError(e)); } });
  }

  // ---- CU-11: del carrito al pedido ----
  crearPedido() {
    if (!this.red.online()) {
      this.errorDatos.set('');
      if (this.form.nit_ci.trim().length < 3) { this.errorDatos.set('Ingrese su NIT o CI (al menos 3 caracteres; consumidor final: su CI).'); return; }
      if (this.form.tipo_entrega === 'DELIVERY' && !this.form.direccion_entrega.trim()) { this.errorDatos.set('Ingrese la dirección de entrega.'); return; }
      const tarjeta = this.tarjetas().find((t) => t.id === this.tarjetaElegida);
      if (tarjeta && !this.autorizo) { this.errorDatos.set(MSG_AUTORIZAR); return; }
      this.creando.set(true);
      void (async () => { await this.estado.registrarCompraLocal(this.form, tarjeta ? { tarjeta_guardada_id: tarjeta.id, marca: tarjeta.marca, ultimos4: tarjeta.ultimos4 } : undefined, this.carrito()); this.cobroAutorizado.set(tarjeta ? `${tarjeta.marca} terminada en ${tarjeta.ultimos4}` : ''); })().then(() => { this.creando.set(false); this.compraPendiente.set(true); this.carrito.set(null); }).catch((e) => { this.creando.set(false); this.errorDatos.set(mensajeError(e)); });
      return;
    }
    this.creando.set(true); this.errorDatos.set('');
    this.api.checkout(this.form).subscribe({
      next: (p) => { this.creando.set(false); this.pedido.set(p); },
      error: (e) => { this.creando.set(false); this.errorDatos.set(mensajeError(e)); this.api.carrito().subscribe({ next: (c) => this.carrito.set(c), error: () => undefined }); },
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
