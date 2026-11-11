import { DatePipe } from '@angular/common';
import { ErrorComponent } from '../../../core/ui/vacio.component';
import { ivaIncluido } from '../../../core/iva';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MEDIA_URL } from '../../../core/api.config';
import { CajaApi } from '../../../core/api/caja.api';
import { CobroCaja, LineaVenta, MetodoCaja, ProductoCaja } from '../../../core/caja.models';
import { Pedido, ResultadoPago } from '../../../core/compras.models';
import { Reserva } from '../../../core/reservas.models';
import { AuthService } from '../../../core/auth/auth.service';
import { CatalogoLocalService, PrendaLocal } from '../../../core/offline/catalogo-local.service';
import { comprobanteProvisional, numeroLocal } from '../../../core/offline/comprobante-provisional';
import { ConnectivityService } from '../../../core/offline/connectivity.service';
import { OperacionLocal, ReservaSucursalLocal } from '../../../core/offline.models';
import { ResumenTurnoComponent } from '../../offline/resumen-turno.component';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';
import { PagoTarjetaComponent } from './pago-tarjeta.component';
import { BsPipe, formatoBs } from '../../../core/formato-bs';
import { ColaOperacionesService } from '../../../core/offline/cola-operaciones.service';
import { OperacionesConProblemaComponent } from '../../offline/operaciones-con-problema.component';

/** Punto de venta: CU-28 (escanear o buscar prendas), CU-29 (armar la venta, también desde una reserva) y CU-30 (cobrar y emitir el comprobante). */
@Component({
  selector: 'app-caja',
  imports: [ErrorComponent, BsPipe, DatePipe, FormsModule, PagoTarjetaComponent, OperacionesConProblemaComponent, ResumenTurnoComponent],
  template: `
    <div class="page" style="max-width:1180px">
      <div class="page-head"><div><h1>Caja</h1><p>Escanee las prendas, registre la venta y cóbrela. El stock se descuenta al cobrar.</p></div>
        <span class="row">
          @if (pendientesDeSync().length) { <span class="badge warn" title="Ventas guardadas en este dispositivo que todavía no se enviaron">{{ pendientesDeSync().length }} venta(s) por sincronizar</span> }
          @if (venta() || cobro() || resultadoTarjeta()) { <button class="btn" (click)="nueva()">+ Nueva venta</button> }
        </span></div>

      @if (!enLinea()) {
        <div class="alert warn" role="status">Sin conexión: la venta se guarda en este dispositivo con un comprobante provisional y se envía sola al volver la red.
          @if (!local.hayCatalogo()) { <strong> Todavía no hay una copia del catálogo en este dispositivo: se descarga sola cuando hay conexión.</strong> }</div>
      }

      <app-operaciones-con-problema [tipos]="['VENTA_CONTADO']" titulo="Ventas con problema" />

      @if (pendientes().length && !venta()) {
        <section class="card pad stack" style="margin-bottom:1rem">
          <strong>Ventas pendientes de cobro</strong>
          @for (p of pendientes(); track p.id) {
            <div class="row between small"><span><strong>{{ p.codigo }}</strong> · {{ p.total_unidades }} prenda(s) · {{ p.total | bs }}{{ p.cliente ? ' · ' + p.cliente : '' }}</span>
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
                        @if (p.promocion) { <s class="muted small">{{ p.precio | bs }}</s> } <strong>{{ p.precio_final | bs }}</strong>
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
                  <div><strong>{{ l.producto }}</strong><div class="small muted">Talla {{ l.talla }} · {{ l.color }} · {{ l.precio_final | bs }}</div></div>
                  <input type="number" min="1" [max]="l.max" [ngModel]="l.cantidad" (change)="cantidad(l, $any($event.target).value)" [name]="'q' + l.variante_id" style="width:4.5rem" />
                  <button type="button" class="btn sm danger" (click)="quitar(l)" aria-label="Quitar">✕</button>
                </div>
              } @empty { <p class="muted small">Escanee o busque una prenda para agregarla.</p> }
              <div class="row between total"><strong>Total</strong><strong>{{ total() | bs }}</strong></div>
              @if (lineas().length) { <p class="muted small">IVA incluido: {{ ivaPrefactura() | bs }}</p> }
            }
            <label>Correo del cliente <span class="hint">(opcional: la compra aparece en su historial)</span><input name="c" [(ngModel)]="clienteEmail" type="email" [disabled]="!!reserva()" /></label>
            <div class="form-grid"><label>NIT o CI<input name="n" [(ngModel)]="nit" maxlength="20" /></label><label>Razón social<input name="rz" [(ngModel)]="razon" maxlength="120" /></label></div>
            @if (error()) { <app-error [texto]="error()" /> }
            <button class="btn primary" (click)="registrar()" [disabled]="registrando() || (!reserva() && !lineas().length)">{{ registrando() ? 'Registrando…' : 'Registrar venta' }}</button>
          </aside>
        </div>
      }

      <!-- CU-30: cobro -->
      @if (venta(); as v) {
        <div class="layout">
          <section class="card pad stack">
            <h2>Cobrar la venta@if (v.id) { {{ v.codigo }} }</h2>
            @if (!cobro() && !resultadoTarjeta()?.aprobado) {
              @if (!esLocal(v)) {
                <div class="tabs" role="tablist">
                  @for (m of metodos; track m.id) { <button role="tab" [class.activa]="metodo() === m.id" (click)="metodo.set(m.id)">{{ m.texto }}</button> }
                </div>
              } @else { <p class="small muted">Sin conexión solo se cobra en efectivo{{ reserva() ? ' (reserva ' + reserva()!.codigo + ')' : '' }}; la venta se enviará sola al volver la red.</p> }
              @if (metodo() === 'EFECTIVO') {
                <div class="form-grid">
                  <label>Monto recibido (Bs)<input name="mr" type="number" min="0" step="0.01" [(ngModel)]="recibido" autofocus /></label>
                  <div class="cambio" [class.mal]="cambioNum() < 0"><span class="small muted">Cambio a entregar</span><strong>{{ (cambioNum() < 0 ? '—' : cambioNum().toFixed(2)) | bs }}</strong></div>
                </div>
                <div><button class="btn primary" (click)="cobrarCaja('EFECTIVO')" [disabled]="cobrando() || cambioNum() < 0">{{ cobrando() ? 'Cobrando…' : 'Cobrar ' + (v.total | bs) }}</button></div>
              }
              @if (metodo() === 'TARJETA') {
                <app-pago-tarjeta [pedidoId]="v.id" [total]="v.total" [permitirGuardar]="false" (listo)="alTarjeta($event)" (sinStock)="avisoSinStock()" />
              }
              @if (errorCobro()) { <div class="alert danger" role="alert">{{ errorCobro() }}</div> }
              <div>@if (esLocal(v)) { <button class="btn sm" (click)="nueva()">Cancelar esta venta</button> } @else { <button class="btn danger sm" (click)="anular(v)">Anular esta venta</button> }</div>
            }

            @if (cobro(); as c) {
              <div class="alert ok resultado" role="status"><strong>✔ Venta cobrada</strong><br />Comprobante N.° <strong>{{ c.pedido.comprobante_numero }}</strong> ({{ c.pedido.comprobante_tipo === 'FACTURA' ? 'factura' : c.pedido.comprobante_tipo === 'PROVISIONAL' ? 'comprobante provisional: se confirma al sincronizar' : 'comprobante interno temporal' }})
                @if (c.pago.metodo === 'EFECTIVO') { <br />Recibido {{ c.pago.monto_recibido | bs }} · <strong>Cambio {{ c.cambio | bs }}</strong> }</div>
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
            <h2>{{ v.id ? 'Venta ' + v.codigo : 'Venta local' }}</h2>
            @for (i of v.items; track i.id) { <div class="row between small"><span>{{ i.cantidad }} × {{ i.producto }} · {{ i.talla }} · {{ i.color }}</span><span class="nowrap">{{ i.subtotal | bs }}</span></div> }
            <div class="row between"><span class="muted">Subtotal</span><span>{{ v.subtotal | bs }}</span></div>
            @if (v.descuento !== '0.00') { <div class="row between"><span class="muted">Descuento</span><span>− {{ v.descuento | bs }}</span></div> }
            <div class="row between total"><strong>Total</strong><strong>{{ v.total | bs }}</strong></div>
            <p class="muted small">IVA incluido: {{ v.iva_incluido | bs }}{{ v.cliente ? ' · Cliente: ' + v.cliente : '' }}</p>
          </aside>
        </div>
      }

      @if (ventasTurno().length) {
        <section class="card pad stack" style="margin-top:1rem">
          <div class="row between"><h2>Mi turno</h2><span class="row"><span class="badge" [class.warn]="pendientesDeSync().length">{{ pendientesDeSync().length }} por sincronizar</span>
            <button class="btn sm" (click)="verResumen.set(!verResumen())">{{ verResumen() ? 'Ocultar el resumen' : 'Resumen de mi turno' }}</button></span></div>
          @for (o of ventasTurno(); track o.id) {
            <div class="row between small"><span>{{ o.creada_en | date: 'HH:mm' }} · {{ o.resumen }}</span>
              <span class="row"><strong>{{ o.comprobante ?? comprobanteLocal(o) }}</strong><span class="badge" [class.ok]="o.estado === 'CONFIRMADA'" [class.warn]="o.estado === 'REGISTRADA_LOCAL' || o.estado === 'ENVIADA' || o.estado === 'EN_CONFLICTO'" [class.danger]="o.estado === 'RECHAZADA'">{{ estadoTexto(o.estado) }}</span>@if (cola.puedeDeshacer(o)) { <button type="button" class="btn sm danger" (click)="deshacerVenta(o)">Deshacer</button> }</span></div>
          }
          @if (verResumen()) { <app-resumen-turno /> }
        </section>
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
  private auth = inject(AuthService);
  private red = inject(ConnectivityService);
  readonly cola = inject(ColaOperacionesService);
  readonly local = inject(CatalogoLocalService);
  readonly enLinea = this.red.online;
  readonly verResumen = signal(false);
  /** Operación de la venta que se cobró sin conexión (para imprimir su comprobante provisional). */
  private operacionLocal: OperacionLocal | null = null;
  readonly ventasTurno = computed(() => this.cola.operaciones().filter((o) => o.tipo === 'VENTA_CONTADO').slice(0, 10));
  readonly pendientesDeSync = computed(() => this.cola.pendientes().filter((o) => o.tipo === 'VENTA_CONTADO'));

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
  readonly ivaPrefactura = computed(() => ivaIncluido(this.total(), this.local.meta()?.iva_porcentaje));
  codigo = ''; consulta = ''; codigoReserva = ''; clienteEmail = ''; nit = '0'; razon = 'Sin nombre';
  recibido: number | null = null;

  constructor() { this.cola.alRefrescar(() => this.cargarPendientes()); }  // tras sincronizar o al volver la red

  ngOnInit() { this.cargarPendientes(); }

  cambioNum() { return Number(this.recibido ?? 0) - Number(this.venta()?.total ?? 0); }

  private cargarPendientes() { if (this.enLinea()) this.api.pendientes().subscribe({ next: (p) => this.pendientes.set(p), error: () => {} }); }

  private get sucursalId() { return this.auth.sesion()?.usuario.sucursal_id ?? null; }
  esLocal(p: Pedido) { return p.id === 0; }
  comprobanteLocal(o: OperacionLocal) { return numeroLocal(o); }

  /** Al deshacer la venta que se acaba de cobrar, el panel «Venta cobrada» desaparece y la pantalla vuelve al estado inicial. */
  async deshacerVenta(o: OperacionLocal) {
    if (await this.cola.deshacer(o) && this.operacionLocal?.id === o.id) this.nueva();
  }
  estadoTexto(e: string) { return ({ REGISTRADA_LOCAL: 'Pendiente', ENVIADA: 'Enviando', CONFIRMADA: 'Confirmada', EN_CONFLICTO: 'En conflicto', RECHAZADA: 'Rechazada' } as Record<string, string>)[e] ?? e; }

  /** Una prenda de la copia local con la misma forma que la que devuelve el servidor (CU-28), con el stock de esta sucursal. */
  private comoProductoCaja(r: PrendaLocal): ProductoCaja {
    const v = r.variante;
    return { variante_id: v.id, producto_id: r.producto.id, sku: v.sku, codigo_barras: v.codigo_barras, producto: r.producto.nombre, talla: v.talla, color: v.color, precio: v.precio, precio_final: v.precio_final, promocion: v.promocion, disponible: this.local.stock(v, this.sucursalId), imagen: r.producto.imagen ?? null };
  }

  // ---- CU-28 ----
  escanear() {
    const c = this.codigo.trim();
    if (!c) return;
    this.errorBusqueda.set('');
    if (!this.enLinea()) { this.escanearLocal(c); return; }
    this.api.escanear(c).subscribe({
      next: (p) => { this.agregar(p); this.codigo = ''; },
      error: (e) => { if (e.status === 0) this.escanearLocal(c); else this.errorBusqueda.set(mensajeError(e)); },  // «El código de barras escaneado no coincide con ningún producto…»
    });
  }

  /** Sin conexión el código se busca en la copia descargada (SKU o código de barras exactos). */
  private escanearLocal(c: string) {
    const q = c.toLowerCase();
    const hallada = this.local.buscar(c).find((r) => r.variante.sku.toLowerCase() === q || (r.variante.codigo_barras ?? '').toLowerCase() === q);
    if (hallada) { this.agregar(this.comoProductoCaja(hallada)); this.codigo = ''; }
    else this.errorBusqueda.set('El código escaneado no coincide con ninguna prenda de la copia de este dispositivo.');
  }

  buscar() {
    if (this.consulta.trim().length < 2) return;
    this.errorBusqueda.set('');
    if (!this.enLinea()) { this.buscarLocal(); return; }
    this.api.buscar(this.consulta.trim()).subscribe({
      next: (r) => { this.resultados.set(r); if (!r.length) this.errorBusqueda.set('No hay prendas que coincidan con la búsqueda.'); },
      error: (e) => { if (e.status === 0) this.buscarLocal(); else this.errorBusqueda.set(mensajeError(e)); },
    });
  }

  private buscarLocal() {
    const r = this.local.buscar(this.consulta.trim()).map((x) => this.comoProductoCaja(x));
    this.resultados.set(r);
    if (!r.length) this.errorBusqueda.set(this.local.hayCatalogo() ? 'No hay prendas que coincidan con la búsqueda.' : 'Sin conexión y sin copia del catálogo en este dispositivo.');
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
    if (!this.enLinea()) { this.cargarReservaLocal(); return; }
    this.api.reserva(this.codigoReserva.trim()).subscribe({
      next: (r) => {
        this.reserva.set(r); this.lineas.set([]);
        this.itemsReserva.set(r.items.filter((i) => i.estado === 'RESERVADO').map((i) => ({ variante_id: i.variante_id, sku: i.sku, producto: i.producto, talla: i.talla, color: i.color, precio_final: 0, cantidad: i.cantidad, max: i.cantidad })));
        this.codigoReserva = '';
      },
      error: (e) => this.errorReserva.set(mensajeError(e)),
    });
  }
  /** Sin conexión la reserva sale de la copia descargada: solo las que ya están preparadas o atendidas se pueden cobrar (CU-29). */
  private cargarReservaLocal() {
    const codigo = this.codigoReserva.trim().toUpperCase();
    const local = (this.local.meta()?.reservas_sucursal ?? []).find((r) => r.codigo.toUpperCase() === codigo);
    if (!local || !['PREPARADA', 'EN_PROBADOR'].includes(local.estado)) { this.errorReserva.set('El código de reserva no existe, no está lista para cobrar o no está en la copia de este dispositivo.'); return; }
    this.reserva.set({ id: local.id, codigo: local.codigo, estado: local.estado, cliente: local.cliente ?? '', items: local.items } as unknown as Reserva);
    this.lineas.set([]);
    this.itemsReserva.set(local.items.filter((i) => i.estado === 'RESERVADO').map((i) => ({ variante_id: i.variante_id, sku: '', producto: i.producto, talla: i.talla, color: i.color, precio_final: this.precioLocal(i.variante_id), cantidad: i.cantidad, max: i.cantidad })));
    this.codigoReserva = '';
  }

  private precioLocal(varianteId: number): number {
    for (const p of this.local.productos()) { const v = p.variantes.find((x) => x.id === varianteId); if (v) return Number(v.precio_final); }
    return 0;
  }

  soltarReserva() { this.reserva.set(null); this.itemsReserva.set([]); }

  registrar() {
    this.registrando.set(true); this.error.set('');
    const r = this.reserva();
    const items = (r ? this.itemsReserva() : this.lineas()).filter((l) => l.cantidad > 0).map((l) => ({ variante_id: l.variante_id, cantidad: l.cantidad }));
    if (!this.enLinea()) { this.registrarLocal(); return; }
    this.api.registrarVenta({ items, reserva_codigo: r?.codigo ?? null, cliente_email: this.clienteEmail.trim() || null, nit_ci: this.nit || '0', razon_social: this.razon || 'Sin nombre' }).subscribe({
      next: (p) => { this.registrando.set(false); this.abrirCobro(p); },
      error: (e) => { this.registrando.set(false); if (e.status === 0) this.registrarLocal(); else this.error.set(mensajeError(e)); },
    });
  }

  /** Sin conexión: se arma la misma pre-factura y se pasa al cobro; la venta se guarda en la cola al cobrar. */
  private registrarLocal() {
    this.registrando.set(false);
    const r = this.reserva();
    const lineas = r ? this.itemsReserva().filter((l) => l.cantidad > 0) : this.lineas();
    if (this.sucursalId === null || !lineas.length) { this.error.set('Agregue al menos una prenda.'); return; }
    const total = lineas.reduce((s, l) => s + l.precio_final * l.cantidad, 0).toFixed(2);
    const items = lineas.map((l, i) => ({ id: i, variante_id: l.variante_id, sku: l.sku, producto: l.producto, talla: l.talla, color: l.color, cantidad: l.cantidad, precio_unitario: l.precio_final.toFixed(2), precio_final: l.precio_final.toFixed(2), subtotal: (l.precio_final * l.cantidad).toFixed(2) }));
    this.abrirCobro({
      id: 0, codigo: 'Venta local', estado: 'PENDIENTE_PAGO', canal: 'PRESENCIAL', tipo_entrega: 'EN_TIENDA', direccion_entrega: '', nit_ci: this.nit || '0', razon_social: this.razon || 'Sin nombre',
      sucursal_id: this.sucursalId, sucursal: '', subtotal: total, descuento: '0.00', iva_incluido: ivaIncluido(total, this.local.meta()?.iva_porcentaje), total, moneda: 'BOB', total_unidades: items.reduce((s, i) => s + i.cantidad, 0),
      comprobante_numero: null, comprobante_tipo: 'PROVISIONAL', cliente: r ? r.cliente : this.clienteEmail.trim() || null, reserva_id: r?.id ?? null, creado_en: new Date().toISOString(), pagado_en: null, items, pagos: [],
    });
  }

  private abrirCobro(p: Pedido) { this.venta.set(p); this.recibido = Number(p.total); this.metodo.set('EFECTIVO'); this.errorCobro.set(''); this.cobro.set(null); this.resultadoTarjeta.set(null); }

  retomar(p: Pedido) { this.abrirCobro(p); }

  anular(p: Pedido) {
    if (!confirm(`¿Anular la venta ${p.codigo}?`)) return;
    this.api.anular(p.id).subscribe({ next: () => { this.toast.ok('Venta anulada.'); this.nueva(); }, error: (e) => this.toast.error(mensajeError(e)) });
  }

  // ---- CU-30 ----
  cobrarCaja(metodo: 'EFECTIVO'): void | Promise<void> {
    if (this.esLocal(this.venta()!)) return this.cobrarLocal();
    this.cobrando.set(true); this.errorCobro.set('');
    this.api.cobrar(this.venta()!.id, metodo, metodo === 'EFECTIVO' ? this.recibido : null).subscribe({
      next: (c) => { this.cobrando.set(false); this.cobro.set(c); this.venta.set(c.pedido); },
      error: (e) => { this.cobrando.set(false); this.errorCobro.set(mensajeError(e)); },
    });
  }

  /** Sin conexión: la venta de contado queda en la cola con su UUID (RN11), baja el stock local y se entrega el comprobante provisional LOC-… (RN13). */
  async cobrarLocal() {
    const v = this.venta()!;
    if (Number(this.recibido ?? 0) < Number(v.total)) { this.errorCobro.set('El efectivo recibido es menor al total de la venta.'); return; }
    this.cobrando.set(true); this.errorCobro.set('');
    const items = v.items.map((i) => ({ variante_id: i.variante_id, cantidad: i.cantidad, precio_unitario: i.precio_unitario }));
    const resumen = v.items.map((i) => `${i.cantidad}× ${i.producto} (${i.talla}, ${i.color})`).join(', ');
    const reserva = this.reserva();
    const cuerpo = { items, forma_pago: 'EFECTIVO', monto_recibido: Number(this.recibido).toFixed(2), ...(reserva ? { reserva_codigo: reserva.codigo } : { cliente_email: v.cliente ?? null }) };
    const op = await this.cola.registrar('VENTA_CONTADO', cuerpo, v.sucursal_id, `${reserva ? `Cobro de la reserva ${reserva.codigo}` : 'Venta de contado'} ${formatoBs(Number(v.total))}: ${resumen}`, reserva ? undefined : { stock: items.map((i) => ({ variante_id: i.variante_id, delta: -i.cantidad })) });
    if (reserva) await this.local.actualizarExtras((m) => { m.reservas_sucursal = (m.reservas_sucursal ?? []).filter((x) => x.id !== reserva.id); });  // ya se cobró: sale de la copia
    else await this.local.comprometer(items, v.sucursal_id);  // la reserva ya tenía su stock apartado
    this.operacionLocal = op;
    const pedido: Pedido = { ...v, estado: 'PAGADO', comprobante_numero: numeroLocal(op), comprobante_tipo: 'PROVISIONAL' };
    const pago = { id: 0, estado: 'APROBADO', metodo: 'EFECTIVO', proveedor: 'LOCAL', monto: v.total, monto_recibido: Number(this.recibido).toFixed(2), cambio: this.cambioNum().toFixed(2), tarjeta_marca: '', tarjeta_ultimos4: '', mensaje: '', motivo: '', creado_en: op.creada_en };
    this.cobrando.set(false);
    this.cobro.set({ pedido, pago, cambio: this.cambioNum().toFixed(2), aviso: null });
    this.venta.set(pedido);
    this.toast.ok('Venta guardada en este dispositivo. Se enviará sola al volver la red.');
  }

  alTarjeta(r: ResultadoPago) { this.resultadoTarjeta.set(r); if (r.aprobado) this.venta.set(r.pedido); }
  /** Con tarjeta, si el stock se agota a mitad del cobro el sistema cancela la autorización y la venta: no se cobró nada. */
  avisoSinStock() { this.toast.aviso('El stock se agotó mientras se cobraba: no se cobró nada y la venta quedó cancelada. Registre una nueva con lo disponible.'); this.nueva(); }

  imprimir(p: Pedido) {
    if (p.comprobante_tipo === 'PROVISIONAL' && this.operacionLocal) { void this.imprimirProvisional(this.operacionLocal); return; }
    this.api.comprobante(p.id).subscribe({
      next: (blob) => window.open(URL.createObjectURL(blob), '_blank'),
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }

  /** Comprobante provisional LOC-… armado en el dispositivo; vale una vez sincronizada la venta, cuando recibe su número CMP-… oficial. */
  private async imprimirProvisional(op: OperacionLocal) {
    const nombreDe = (id: number) => { for (const x of this.local.productos()) { const v = x.variantes.find((y) => y.id === id); if (v) return `${x.nombre} (${v.talla}, ${v.color})`; } return `Prenda ${id}`; };
    (await comprobanteProvisional(op, this.auth.sesion()?.empresa?.razon_social ?? '', nombreDe)).save(`${numeroLocal(op)}.pdf`);
  }

  nueva() {
    this.venta.set(null); this.cobro.set(null); this.resultadoTarjeta.set(null); this.lineas.set([]); this.soltarReserva(); this.resultados.set([]);
    this.clienteEmail = ''; this.nit = '0'; this.razon = 'Sin nombre'; this.error.set(''); this.errorCobro.set('');
    this.cargarPendientes();
  }
}
