import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MEDIA_URL } from '../../../core/api.config';
import { CajaApi } from '../../../core/api/caja.api';
import { CobroCaja, LineaVenta, MetodoCaja, ProductoCaja } from '../../../core/caja.models';
import { Pedido, ResultadoPago } from '../../../core/compras.models';
import { Reserva } from '../../../core/reservas.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';
import { PagoTarjetaComponent } from './pago-tarjeta.component';

/** Punto de venta: CU-28 (escanear o buscar prendas), CU-29 (armar la venta, también desde una reserva) y CU-30 (cobrar y emitir el comprobante). */
@Component({
  selector: 'app-caja',
  imports: [FormsModule, PagoTarjetaComponent],
  template: `
    <div class="page" style="max-width:1180px">
      <div class="page-head"><div><h1>Caja</h1><p>Escanee las prendas, registre la venta y cóbrela. El stock se descuenta al cobrar.</p></div>
        @if (venta() || cobro() || resultadoTarjeta()) { <button class="btn" (click)="nueva()">+ Nueva venta</button> }</div>

      @if (pendientes().length && !venta()) {
        <section class="card pad stack" style="margin-bottom:1rem">
          <strong>Ventas pendientes de cobro</strong>
          @for (p of pendientes(); track p.id) {
            <div class="row between small"><span><strong>{{ p.codigo }}</strong> · {{ p.total_unidades }} prenda(s) · Bs {{ p.total }}{{ p.cliente ? ' · ' + p.cliente : '' }}</span>
              <span class="row"><button class="btn sm" (click)="retomar(p)">Retomar cobro</button><button class="btn sm danger" (click)="anular(p)">Anular</button></span></div>
          }
        </section>
      }

      @if (!venta()) {
        <div class="layout">
          <!-- CU-28: prendas -->
          <div class="stack">
            <section class="card pad stack">
              <h2>Prendas</h2>
              <form class="row" (ngSubmit)="escanear()">
                <label style="flex:1;min-width:220px">Escanear código de barras o SKU<input name="e" [(ngModel)]="codigo" placeholder="Escanee o escriba el código y presione Enter" autocomplete="off" autofocus /></label>
              </form>
              <form class="row" (ngSubmit)="buscar()">
                <label style="flex:1;min-width:220px">Buscar por nombre<input name="b" [(ngModel)]="consulta" placeholder="Camisa, polo, jean…" autocomplete="off" /></label>
                <button class="btn" style="align-self:end">Buscar</button>
              </form>
              @if (errorBusqueda()) { <div class="alert danger" role="alert">{{ errorBusqueda() }}</div> }
              @if (resultados().length) {
                <div class="resultados">
                  @for (p of resultados(); track p.variante_id) {
                    <button type="button" class="card producto" [disabled]="p.disponible === 0" (click)="agregar(p)">
                      @if (p.imagen) { <img [src]="media + p.imagen" [alt]="p.producto" /> } @else { <span class="foto">👕</span> }
                      <span><strong>{{ p.producto }}</strong><br /><span class="small muted">Talla {{ p.talla }} · {{ p.color }}</span><br />
                        @if (p.promocion) { <s class="muted small">Bs {{ p.precio }}</s> } <strong>Bs {{ p.precio_final }}</strong>
                        @if (p.promocion) { <span class="badge danger">{{ p.promocion }}</span> }<br />
                        <span class="badge" [class.ok]="p.disponible > 3" [class.warn]="p.disponible > 0 && p.disponible <= 3" [class.danger]="p.disponible === 0">{{ p.disponible === 0 ? 'Sin stock' : p.disponible + ' en tienda' }}</span></span>
                    </button>
                  }
                </div>
              }
            </section>

            <section class="card pad stack">
              <h2>Cobrar una reserva</h2>
              <form class="row" (ngSubmit)="cargarReserva()">
                <label style="flex:1;min-width:220px">Código de reserva<input name="r" [(ngModel)]="codigoReserva" placeholder="RSV-XXXXXXXX" autocomplete="off" style="text-transform:uppercase" /></label>
                <button class="btn" style="align-self:end">Buscar reserva</button>
              </form>
              @if (errorReserva()) { <div class="alert danger" role="alert">{{ errorReserva() }}</div> }
            </section>
          </div>

          <!-- CU-29: pre-factura -->
          <aside class="card pad stack resumen">
            <h2>Pre-factura</h2>
            @if (reserva(); as r) {
              <div class="alert ok small"><strong>Reserva {{ r.codigo }}</strong> de {{ r.cliente }}. Elija lo que se lleva; el resto vuelve a disponible.
                <button class="btn sm ghost" (click)="soltarReserva()">Quitar</button></div>
              @for (i of itemsReserva(); track i.variante_id) {
                <div class="row between small"><span>{{ i.producto }} · {{ i.talla }} · {{ i.color }}</span>
                  <input type="number" min="0" [max]="i.max" [(ngModel)]="i.cantidad" [name]="'rs' + i.variante_id" style="width:4.5rem" /></div>
              }
            } @else {
              @for (l of lineas(); track l.variante_id) {
                <div class="linea">
                  <div><strong>{{ l.producto }}</strong><div class="small muted">Talla {{ l.talla }} · {{ l.color }} · Bs {{ l.precio_final }}</div></div>
                  <input type="number" min="1" [max]="l.max" [ngModel]="l.cantidad" (change)="cantidad(l, $any($event.target).value)" [name]="'q' + l.variante_id" style="width:4.5rem" />
                  <button type="button" class="btn sm danger" (click)="quitar(l)" aria-label="Quitar">✕</button>
                </div>
              } @empty { <p class="muted small">Escanee o busque una prenda para agregarla.</p> }
              <div class="row between total"><strong>Total</strong><strong>Bs {{ total() }}</strong></div>
            }
            <label>Correo del cliente <span class="hint">(opcional: la compra aparece en su historial)</span><input name="c" [(ngModel)]="clienteEmail" type="email" [disabled]="!!reserva()" /></label>
            <div class="form-grid"><label>NIT o CI<input name="n" [(ngModel)]="nit" maxlength="20" /></label><label>Razón social<input name="rz" [(ngModel)]="razon" maxlength="120" /></label></div>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
            <button class="btn primary" (click)="registrar()" [disabled]="registrando() || (!reserva() && !lineas().length)">{{ registrando() ? 'Registrando…' : 'Registrar venta' }}</button>
          </aside>
        </div>
      }

      <!-- CU-30: cobro -->
      @if (venta(); as v) {
        <div class="layout">
          <section class="card pad stack">
            <h2>Cobrar la venta {{ v.codigo }}</h2>
            @if (!cobro() && !resultadoTarjeta()?.aprobado) {
              <div class="tabs" role="tablist">
                @for (m of metodos; track m.id) { <button role="tab" [class.activa]="metodo() === m.id" (click)="metodo.set(m.id)">{{ m.texto }}</button> }
              </div>
              @if (metodo() === 'EFECTIVO') {
                <div class="form-grid">
                  <label>Monto recibido (Bs)<input name="mr" type="number" min="0" step="0.01" [(ngModel)]="recibido" autofocus /></label>
                  <div class="cambio" [class.mal]="cambioNum() < 0"><span class="small muted">Cambio a entregar</span><strong>Bs {{ cambioNum() < 0 ? '—' : cambioNum().toFixed(2) }}</strong></div>
                </div>
                <div><button class="btn primary" (click)="cobrarCaja('EFECTIVO')" [disabled]="cobrando() || cambioNum() < 0">{{ cobrando() ? 'Cobrando…' : 'Cobrar Bs ' + v.total }}</button></div>
              }
              @if (metodo() === 'TARJETA') {
                <app-pago-tarjeta [pedidoId]="v.id" [total]="v.total" [permitirGuardar]="false" (listo)="alTarjeta($event)" (sinStock)="avisoSinStock()" />
              }
              @if (errorCobro()) { <div class="alert danger" role="alert">{{ errorCobro() }}</div> }
              <div><button class="btn danger sm" (click)="anular(v)">Anular esta venta</button></div>
            }

            @if (cobro(); as c) {
              <div class="alert ok resultado" role="status"><strong>✔ Venta cobrada</strong><br />Comprobante N.° <strong>{{ c.pedido.comprobante_numero }}</strong> ({{ c.pedido.comprobante_tipo === 'FACTURA' ? 'factura' : 'comprobante interno temporal' }})
                @if (c.pago.metodo === 'EFECTIVO') { <br />Recibido Bs {{ c.pago.monto_recibido }} · <strong>Cambio Bs {{ c.cambio }}</strong> }</div>
              @if (c.aviso) { <div class="alert warn" role="alert">{{ c.aviso }}</div> }
              <div class="row"><button class="btn primary" (click)="imprimir(c.pedido)">🖨 Imprimir comprobante</button><button class="btn" (click)="nueva()">Nueva venta</button></div>
            }
            @if (resultadoTarjeta(); as r) {
              @if (r.aprobado) {
                @if (r.pedido.comprobante_aviso) { <div class="alert warn" role="alert">{{ r.pedido.comprobante_aviso }}</div> }
                <div class="row"><button class="btn primary" (click)="imprimir(r.pedido)">🖨 Imprimir comprobante</button><button class="btn" (click)="nueva()">Nueva venta</button></div>
              }
            }
          </section>

          <aside class="card pad stack resumen">
            <h2>Venta {{ v.codigo }}</h2>
            @for (i of v.items; track i.id) { <div class="row between small"><span>{{ i.cantidad }} × {{ i.producto }} · {{ i.talla }} · {{ i.color }}</span><span class="nowrap">Bs {{ i.subtotal }}</span></div> }
            <div class="row between"><span class="muted">Subtotal</span><span>Bs {{ v.subtotal }}</span></div>
            @if (v.descuento !== '0.00') { <div class="row between"><span class="muted">Descuento</span><span>− Bs {{ v.descuento }}</span></div> }
            <div class="row between total"><strong>Total</strong><strong>Bs {{ v.total }}</strong></div>
            <p class="muted small">IVA incluido: Bs {{ v.iva_incluido }}{{ v.cliente ? ' · Cliente: ' + v.cliente : '' }}</p>
          </aside>
        </div>
      }
    </div>`,
  styles: `
    .layout { display: grid; grid-template-columns: 1fr 380px; gap: 1.2rem; align-items: start; }
    .resumen { position: sticky; top: 1rem; } .total { font-size: 1.15rem; border-top: 1px solid var(--line); padding-top: .6rem; }
    .resultados { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: .6rem; }
    .producto { display: flex; gap: .7rem; text-align: left; padding: .6rem; cursor: pointer; font: inherit; color: inherit; align-items: center; }
    .producto:hover:not(:disabled) { border-color: var(--accent); } .producto:disabled { opacity: .55; cursor: not-allowed; }
    .producto img, .foto { width: 54px; height: 70px; object-fit: cover; border-radius: 8px; background: #ece8e1; display: grid; place-items: center; flex: none; }
    .linea { display: grid; grid-template-columns: 1fr auto auto; gap: .5rem; align-items: center; }
    .cambio { display: grid; align-content: center; padding: .6rem 1rem; border-radius: 10px; background: var(--ok-soft); font-size: 1.3rem; } .cambio.mal { background: var(--danger-soft); }
    .resultado { font-size: 1.05rem; line-height: 1.6; }
    @media (max-width: 960px) { .layout { grid-template-columns: 1fr; } .resumen { position: static; } }`,
})
export class CajaPage implements OnInit {
  private api = inject(CajaApi);
  private toast = inject(ToastService);

  readonly media = MEDIA_URL;
  readonly metodos: { id: MetodoCaja; texto: string }[] = [{ id: 'EFECTIVO', texto: '💵 Efectivo' }, { id: 'TARJETA', texto: '💳 Tarjeta' }];
  readonly resultados = signal<ProductoCaja[]>([]);
  readonly lineas = signal<LineaVenta[]>([]);
  readonly reserva = signal<Reserva | null>(null);
  readonly itemsReserva = signal<LineaVenta[]>([]);
  readonly pendientes = signal<Pedido[]>([]);
  readonly venta = signal<Pedido | null>(null);
  readonly cobro = signal<CobroCaja | null>(null);
  readonly resultadoTarjeta = signal<ResultadoPago | null>(null);
  readonly metodo = signal<MetodoCaja>('EFECTIVO');
  readonly errorBusqueda = signal('');
  readonly errorReserva = signal('');
  readonly error = signal('');
  readonly errorCobro = signal('');
  readonly registrando = signal(false);
  readonly cobrando = signal(false);
  readonly total = computed(() => this.lineas().reduce((s, l) => s + l.precio_final * l.cantidad, 0).toFixed(2));
  codigo = ''; consulta = ''; codigoReserva = ''; clienteEmail = ''; nit = '0'; razon = 'Sin nombre';
  recibido: number | null = null;

  ngOnInit() { this.cargarPendientes(); }

  cambioNum() { return Number(this.recibido ?? 0) - Number(this.venta()?.total ?? 0); }

  private cargarPendientes() { this.api.pendientes().subscribe({ next: (p) => this.pendientes.set(p), error: () => {} }); }

  // ---- CU-28 ----
  escanear() {
    const c = this.codigo.trim();
    if (!c) return;
    this.errorBusqueda.set('');
    this.api.escanear(c).subscribe({
      next: (p) => { this.agregar(p); this.codigo = ''; },
      error: (e) => this.errorBusqueda.set(mensajeError(e)),  // «El código de barras escaneado no coincide con ningún producto…»
    });
  }

  buscar() {
    if (this.consulta.trim().length < 2) return;
    this.errorBusqueda.set('');
    this.api.buscar(this.consulta.trim()).subscribe({
      next: (r) => { this.resultados.set(r); if (!r.length) this.errorBusqueda.set('No hay prendas que coincidan con la búsqueda.'); },
      error: (e) => this.errorBusqueda.set(mensajeError(e)),
    });
  }

  agregar(p: ProductoCaja) {
    if (p.disponible === 0) { this.errorBusqueda.set(`${p.producto} (${p.talla}, ${p.color}) no tiene stock en esta sucursal.`); return; }
    this.soltarReserva();
    this.lineas.update((ls) => {
      const existente = ls.find((l) => l.variante_id === p.variante_id);
      if (existente) return ls.map((l) => (l === existente ? { ...l, cantidad: Math.min(l.cantidad + 1, l.max) } : l));
      return [...ls, { variante_id: p.variante_id, sku: p.sku, producto: p.producto, talla: p.talla, color: p.color, precio_final: Number(p.precio_final), cantidad: 1, max: p.disponible }];
    });
  }

  cantidad(l: LineaVenta, valor: string) { this.lineas.update((ls) => ls.map((x) => (x === l ? { ...x, cantidad: Math.max(1, Math.min(Number(valor) || 1, x.max)) } : x))); }
  quitar(l: LineaVenta) { this.lineas.update((ls) => ls.filter((x) => x !== l)); }

  // ---- CU-29 ----
  cargarReserva() {
    if (!this.codigoReserva.trim()) return;
    this.errorReserva.set('');
    this.api.reserva(this.codigoReserva.trim()).subscribe({
      next: (r) => {
        this.reserva.set(r); this.lineas.set([]);
        this.itemsReserva.set(r.items.filter((i) => i.estado === 'RESERVADO').map((i) => ({ variante_id: i.variante_id, sku: i.sku, producto: i.producto, talla: i.talla, color: i.color, precio_final: 0, cantidad: i.cantidad, max: i.cantidad })));
        this.codigoReserva = '';
      },
      error: (e) => this.errorReserva.set(mensajeError(e)),
    });
  }
  soltarReserva() { this.reserva.set(null); this.itemsReserva.set([]); }

  registrar() {
    this.registrando.set(true); this.error.set('');
    const r = this.reserva();
    const items = (r ? this.itemsReserva() : this.lineas()).filter((l) => l.cantidad > 0).map((l) => ({ variante_id: l.variante_id, cantidad: l.cantidad }));
    this.api.registrarVenta({ items, reserva_codigo: r?.codigo ?? null, cliente_email: this.clienteEmail.trim() || null, nit_ci: this.nit || '0', razon_social: this.razon || 'Sin nombre' }).subscribe({
      next: (p) => { this.registrando.set(false); this.abrirCobro(p); },
      error: (e) => { this.registrando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  private abrirCobro(p: Pedido) { this.venta.set(p); this.recibido = Number(p.total); this.metodo.set('EFECTIVO'); this.errorCobro.set(''); this.cobro.set(null); this.resultadoTarjeta.set(null); }

  retomar(p: Pedido) { this.abrirCobro(p); }

  anular(p: Pedido) {
    if (!confirm(`¿Anular la venta ${p.codigo}?`)) return;
    this.api.anular(p.id).subscribe({ next: () => { this.toast.ok('Venta anulada.'); this.nueva(); }, error: (e) => this.toast.error(mensajeError(e)) });
  }

  // ---- CU-30 ----
  cobrarCaja(metodo: 'EFECTIVO') {
    this.cobrando.set(true); this.errorCobro.set('');
    this.api.cobrar(this.venta()!.id, metodo, metodo === 'EFECTIVO' ? this.recibido : null).subscribe({
      next: (c) => { this.cobrando.set(false); this.cobro.set(c); this.venta.set(c.pedido); },
      error: (e) => { this.cobrando.set(false); this.errorCobro.set(mensajeError(e)); },
    });
  }

  alTarjeta(r: ResultadoPago) { this.resultadoTarjeta.set(r); if (r.aprobado) this.venta.set(r.pedido); }
  /** Con tarjeta, si el stock se agota a mitad del cobro el sistema cancela la autorización y la venta: no se cobró nada. */
  avisoSinStock() { this.toast.aviso('El stock se agotó mientras se cobraba: no se cobró nada y la venta quedó cancelada. Registre una nueva con lo disponible.'); this.nueva(); }

  imprimir(p: Pedido) {
    this.api.comprobante(p.id).subscribe({
      next: (blob) => window.open(URL.createObjectURL(blob), '_blank'),
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }

  nueva() {
    this.venta.set(null); this.cobro.set(null); this.resultadoTarjeta.set(null); this.lineas.set([]); this.soltarReserva(); this.resultados.set([]);
    this.clienteEmail = ''; this.nit = '0'; this.razon = 'Sin nombre'; this.error.set(''); this.errorCobro.set('');
    this.cargarPendientes();
  }
}
