import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ComprasApi } from '../../../core/api/compras.api';
import { CarritoEstadoService } from '../../../core/carrito/carrito-estado.service';
import { Carrito, ConfigPago, Pedido, ResultadoPago, TarjetaGuardada, TarjetaPrueba, TarjetaSimulada } from '../../../core/compras.models';
import { StripeJsService } from '../../../core/pagos/stripe-js.service';
import { mensajeError } from '../../../core/ui/toast.service';

type Fase = 'datos' | 'pago' | 'procesando' | 'aprobado' | 'rechazado' | 'pendiente' | 'error';

/** CU-11 · Checkout (entrega y facturación) y CU-32 · pago con tarjeta: se ve en pantalla cómo la pasarela aprueba o rechaza. */
@Component({
  selector: 'app-checkout',
  imports: [FormsModule, RouterLink],
  template: `
    <div class="page" style="max-width:980px">
      <div class="page-head"><div><h1>Pagar mi compra</h1><p>Complete los datos de entrega y facturación, y pague con tarjeta.</p></div></div>

      @if (!carrito()) { <div class="empty">Cargando…</div> }
      @else if (!carrito()!.items.length && fase() === 'datos') { <div class="card empty">Su carrito está vacío. <a routerLink="/tienda/catalogo">Ver el catálogo</a></div> }
      @else {
        <div class="layout">
          <div class="stack">
            <!-- 1 · entrega y facturación -->
            <form class="card pad stack" (ngSubmit)="crearPedido()" #f="ngForm">
              <h2>1 · Entrega y facturación</h2>
              <fieldset [disabled]="fase() !== 'datos'" style="border:0;padding:0;display:grid;gap:.8rem">
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
              @if (fase() === 'datos') { <div><button class="btn primary" [disabled]="creando() || !carrito()!.puede_pagar">{{ creando() ? 'Preparando…' : 'Continuar al pago' }}</button>
                @if (!carrito()!.puede_pagar) { <span class="small muted" style="margin-left:.6rem">Revise su carrito: hay prendas sin stock.</span> }</div> }
            </form>

            <!-- 2 · pago -->
            @if (pedido()) {
              <section class="card pad stack">
                <h2>2 · Pago con tarjeta</h2>
                @if (config(); as cfg) {
                  <p class="small muted">@if (cfg.modo === 'stripe') { Pago procesado por <strong>Stripe en modo de prueba</strong>: no se cobra dinero real. } @else { <strong>Pasarela de pruebas</strong>: no se cobra dinero real. Use una de las tarjetas de ejemplo. }</p>
                }

                @if (fase() === 'pago' || fase() === 'rechazado' || fase() === 'error') {
                  @if (tarjetas().length) {
                    <div class="stack">
                      <strong>Sus tarjetas guardadas</strong>
                      @for (t of tarjetas(); track t.id) {
                        <label class="check opcion"><input type="radio" name="tg" [value]="t.id" [ngModel]="guardadaId" (ngModelChange)="elegirMedio($event)" /> {{ t.marca }} terminada en <strong>{{ t.ultimos4 }}</strong> · vence {{ t.exp_mes }}/{{ t.exp_anio }}
                          <button type="button" class="btn sm ghost danger" (click)="olvidar(t)" style="margin-left:auto">Eliminar</button></label>
                      }
                      <label class="check opcion"><input type="radio" name="tg" [value]="null" [ngModel]="guardadaId" (ngModelChange)="elegirMedio($event)" /> Usar otra tarjeta</label>
                    </div>
                  }

                  @if (guardadaId === null) {
                    @if (config()?.modo === 'stripe') {
                      <label>Datos de la tarjeta<div id="tarjeta-stripe" class="campo-stripe"></div></label>
                      <label>Nombre del titular<input name="th" [(ngModel)]="titular" /></label>
                    } @else {
                      <div class="form-grid">
                        <label class="full">Número de tarjeta<input name="nt" [(ngModel)]="sim.numero" inputmode="numeric" autocomplete="off" maxlength="23" placeholder="4242 4242 4242 4242" (ngModelChange)="formatear($event)" /></label>
                        <label>Vence (mes / año)<span class="row"><input name="mm" type="number" [(ngModel)]="sim.mes" min="1" max="12" style="width:5rem" /><input name="aa" type="number" [(ngModel)]="sim.anio" min="2024" style="width:6rem" /></span></label>
                        <label>CVC<input name="cv" [(ngModel)]="sim.cvc" maxlength="4" inputmode="numeric" autocomplete="off" style="width:6rem" /></label>
                        <label class="full">Nombre del titular<input name="th2" [(ngModel)]="sim.titular" /></label>
                      </div>
                      @if (config()?.tarjetas_prueba?.length) {
                        <details class="prueba"><summary>Tarjetas de prueba</summary>
                          <div class="stack" style="margin-top:.5rem">
                            @for (t of config()!.tarjetas_prueba; track t.numero) { <button type="button" class="chip" (click)="usarPrueba(t)"><code>{{ t.numero }}</code> {{ t.resultado }}</button> }
                          </div></details>
                      }
                    }
                    <label class="check"><input type="checkbox" name="gt" [(ngModel)]="guardar" /> Guardar esta tarjeta para mis próximas compras</label>
                  }

                  @if (fase() === 'rechazado') {
                    <div class="alert danger resultado" role="alert"><strong>✖ Pago rechazado</strong><br />{{ mensaje() }}@if (motivo()) { <br /><span class="small">Motivo: {{ motivo() }}</span> }<br /><span class="small">No se le cobró nada. Pruebe con otra tarjeta.</span></div>
                  }
                  @if (fase() === 'error') { <div class="alert danger resultado" role="alert">{{ mensaje() }} <a routerLink="/tienda/carrito">Revisar mi carrito</a></div> }
                  <div class="row between">
                    <span class="muted small">Se cobrará el equivalente a <strong>US$ {{ dolares() }}</strong> (Bs {{ pedido()!.total }} a {{ config()?.tasa_bob_por_usd }} Bs por dólar).</span>
                    <button type="button" class="btn primary" (click)="pagar()">Pagar Bs {{ pedido()!.total }}</button>
                  </div>
                }

                @if (fase() === 'procesando') {
                  <div class="resultado cargando" role="status"><span class="rueda"></span><div><strong>Verificando su tarjeta con el banco…</strong><br /><span class="small muted">No cierre esta ventana.</span></div></div>
                }
                @if (fase() === 'aprobado' && resultado(); as r) {
                  <div class="alert ok resultado" role="status"><strong>✔ Pago aprobado</strong><br />Su compra <strong>{{ r.pedido.codigo }}</strong> está pagada ({{ r.pago.tarjeta_marca }} terminada en {{ r.pago.tarjeta_ultimos4 }}).<br />Comprobante N.° <strong>{{ r.pedido.comprobante_numero }}</strong></div>
                  <div class="row"><button type="button" class="btn primary" (click)="descargar(r.pedido)">⬇ Descargar comprobante</button>
                    <a class="btn" [routerLink]="['/tienda/compras', r.pedido.id]">Ver mi compra</a><a class="btn ghost" routerLink="/tienda/catalogo">Seguir comprando</a></div>
                }
                @if (fase() === 'pendiente' && resultado(); as r) {
                  <div class="alert warn resultado" role="status"><strong>⏳ Pendiente de confirmación</strong><br />{{ r.mensaje }}</div>
                  <div class="row"><button type="button" class="btn primary" (click)="reconciliar(r.pago.id)" [disabled]="verificando()">{{ verificando() ? 'Verificando…' : 'Verificar estado del pago' }}</button>
                    <a class="btn" routerLink="/tienda/compras">Mis compras</a></div>
                }
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
    .campo-stripe { padding: .7rem; border: 1px solid #d6d1c9; border-radius: 9px; background: #fff; min-height: 2.6rem; }
    .opcion { border: 1px solid var(--line); border-radius: 10px; padding: .6rem .8rem; } .opcion:has(input:checked) { border-color: var(--accent); background: var(--accent-soft); }
    .prueba { border: 1px dashed var(--line); border-radius: 10px; padding: .6rem .8rem; } .prueba summary { cursor: pointer; font-weight: 600; }
    code { font-size: .82rem; } .resultado { font-size: 1rem; line-height: 1.5; }
    .cargando { display: flex; gap: 1rem; align-items: center; padding: 1.2rem; border: 1px solid var(--line); border-radius: 12px; }
    .rueda { width: 28px; height: 28px; border: 3px solid var(--line); border-top-color: var(--accent); border-radius: 50%; animation: gira .8s linear infinite; }
    @keyframes gira { to { transform: rotate(360deg); } }
    @media (max-width: 900px) { .layout { grid-template-columns: 1fr; } .resumen { position: static; } }`,
})
export class CheckoutPage implements OnInit {
  private api = inject(ComprasApi);
  private estado = inject(CarritoEstadoService);
  private stripeJs = inject(StripeJsService);
  private router = inject(Router);

  readonly carrito = signal<Carrito | null>(null);
  readonly pedido = signal<Pedido | null>(null);
  readonly config = signal<ConfigPago | null>(null);
  readonly tarjetas = signal<TarjetaGuardada[]>([]);
  readonly resultado = signal<ResultadoPago | null>(null);
  readonly fase = signal<Fase>('datos');
  readonly creando = signal(false);
  readonly verificando = signal(false);
  readonly errorDatos = signal('');
  readonly mensaje = signal('');
  readonly motivo = signal('');
  readonly dolares = computed(() => {
    const p = this.pedido(), c = this.config();
    return p && c ? (Number(p.total) / c.tasa_bob_por_usd).toFixed(2) : '';
  });
  form = { tipo_entrega: 'RETIRO', direccion_entrega: '', nit_ci: '', razon_social: '' };
  guardadaId: number | null = null;
  guardar = false;
  titular = '';
  sim = { numero: '', mes: 12, anio: new Date().getFullYear() + 3, cvc: '', titular: '' };
  private stripe: any = null;
  private campoTarjeta: any = null;

  ngOnInit() {
    this.api.carrito().subscribe((c) => { this.carrito.set(c); this.estado.fijar(c); });
  }

  // ---- CU-11: del carrito al pedido ----
  crearPedido() {
    this.creando.set(true); this.errorDatos.set('');
    this.api.checkout(this.form).subscribe({
      next: (p) => { this.creando.set(false); this.pedido.set(p); this.fase.set('pago'); this.prepararPago(); },
      error: (e) => { this.creando.set(false); this.errorDatos.set(mensajeError(e)); this.api.carrito().subscribe((c) => this.carrito.set(c)); },
    });
  }

  private prepararPago() {
    this.api.configPago().subscribe((cfg) => {
      this.config.set(cfg);
      this.api.tarjetas().subscribe((t) => { this.tarjetas.set(t); this.guardadaId = t[0]?.id ?? null; if (cfg.modo === 'stripe') void this.montarStripe(cfg); });
    });
  }

  /** Monta el campo de tarjeta de Stripe cuando ya está en pantalla (se reintenta mientras Angular lo dibuja). */
  private async montarStripe(cfg: ConfigPago, intentos = 40) {
    if (this.guardadaId !== null) return;  // con una tarjeta guardada no hace falta el campo
    try {
      const Stripe = await this.stripeJs.cargar();
      this.stripe ??= Stripe(cfg.publishable_key!, { locale: 'es' });
      const destino = document.getElementById('tarjeta-stripe');
      if (!destino) { if (intentos > 0) setTimeout(() => void this.montarStripe(cfg, intentos - 1), 50); return; }
      if (!destino.hasChildNodes()) {
        this.campoTarjeta?.destroy?.();
        this.campoTarjeta = this.stripe.elements().create('card', { hidePostalCode: true });
        this.campoTarjeta.mount('#tarjeta-stripe');
      }
    } catch (e) { this.mensaje.set(String((e as Error).message)); this.fase.set('error'); }
  }

  elegirMedio(id: number | null) {
    this.guardadaId = id;
    if (id === null && this.config()?.modo === 'stripe') void this.montarStripe(this.config()!);
  }

  formatear(v: string) { this.sim.numero = v.replace(/[^\d]/g, '').replace(/(.{4})/g, '$1 ').trim(); }
  usarPrueba(t: TarjetaPrueba) { this.sim.numero = t.numero; this.sim.cvc = '123'; this.sim.mes = 12; this.sim.anio = new Date().getFullYear() + 3; }

  olvidar(t: TarjetaGuardada) {
    this.api.eliminarTarjeta(t.id).subscribe(() => { this.tarjetas.update((l) => l.filter((x) => x.id !== t.id)); if (this.guardadaId === t.id) { this.guardadaId = null; this.elegirMedio(null); } });
  }

  // ---- CU-32: pago ----
  pagar() {
    this.fase.set('procesando'); this.mensaje.set(''); this.motivo.set('');
    this.api.iniciarPago(this.pedido()!.id, this.guardadaId, this.guardar && this.guardadaId === null).subscribe({
      next: (ini) => {
        if (ini.modo === 'stripe') void this.confirmarConStripe(ini.pago_id, ini.client_secret!, ini.publishable_key!);
        else this.confirmar(ini.pago_id, { ...this.sim, titular: this.sim.titular });
      },
      error: (e) => this.fallo(e),
    });
  }

  /** Con Stripe la tarjeta se confirma en el navegador; luego el servidor lee el resultado de Stripe y cobra solo si hay stock. */
  private async confirmarConStripe(pagoId: number, secreto: string, clave: string) {
    try {
      const Stripe = await this.stripeJs.cargar();
      this.stripe ??= Stripe(clave, { locale: 'es' });
      const datos = this.guardadaId !== null ? undefined : { payment_method: { card: this.campoTarjeta, billing_details: { name: this.titular } } };
      const r = await this.stripe.confirmCardPayment(secreto, datos);
      if (r.error) this.motivoStripe = r.error.message ?? '';
    } catch (e) { this.motivoStripe = String((e as Error).message); }
    this.confirmar(pagoId, null);
  }
  private motivoStripe = '';

  private confirmar(pagoId: number, tarjeta: TarjetaSimulada | null) {
    this.api.confirmarPago(pagoId, tarjeta).subscribe({
      next: (r) => { this.resultado.set(r); this.fase.set(r.aprobado ? 'aprobado' : 'pendiente'); if (r.aprobado) this.estado.fijar(null); this.motivoStripe = ''; },
      error: (e) => this.fallo(e),
    });
  }

  reconciliar(pagoId: number) {
    this.verificando.set(true);
    this.api.reconciliarPago(pagoId).subscribe({
      next: (r) => { this.verificando.set(false); this.resultado.set(r); this.fase.set(r.aprobado ? 'aprobado' : 'pendiente'); if (r.aprobado) this.estado.fijar(null); },
      error: (e) => { this.verificando.set(false); this.fallo(e); },
    });
  }

  private fallo(e: unknown) {
    const err = e as { status?: number; error?: { motivo?: string } };
    this.mensaje.set(mensajeError(e));
    if (err.status === 402) { this.motivo.set(this.motivoStripe || err.error?.motivo || ''); this.fase.set('rechazado'); }
    else if (err.status === 409) { this.fase.set('error'); this.api.carrito().subscribe((c) => { this.carrito.set(c); this.estado.fijar(c); }); }
    else this.fase.set(this.pedido() ? 'pago' : 'datos');
    if ((this.fase() === 'pago' || this.fase() === 'rechazado') && this.config()?.modo === 'stripe') void this.montarStripe(this.config()!);
    this.motivoStripe = '';
  }

  descargar(p: Pedido) {
    this.api.comprobante(p.id).subscribe((blob) => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = `${p.comprobante_numero}.pdf`; a.click(); URL.revokeObjectURL(a.href);
    });
  }
}
