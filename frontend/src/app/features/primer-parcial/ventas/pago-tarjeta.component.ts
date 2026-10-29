import { Component, OnInit, computed, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ComprasApi } from '../../../core/api/compras.api';
import { ConfigPago, ResultadoPago, TarjetaGuardada, TarjetaPrueba, TarjetaSimulada } from '../../../core/compras.models';
import { StripeJsService } from '../../../core/pagos/stripe-js.service';
import { mensajeError } from '../../../core/ui/toast.service';

type Fase = 'pago' | 'procesando' | 'aprobado' | 'rechazado' | 'pendiente' | 'error';

/** CU-32 · Formulario de pago con tarjeta y resultado en pantalla (aprobada, rechazada o pendiente de confirmación).
 *  Lo usan el checkout del cliente y la caja: con Stripe en modo de prueba la tarjeta la captura Stripe.js; si no hay claves, es un formulario de pruebas. */
@Component({
  selector: 'app-pago-tarjeta',
  imports: [FormsModule],
  template: `
    <div class="stack">
      @if (config(); as cfg) {
        <p class="small muted">@if (cfg.modo === 'stripe') { Pago procesado por <strong>Stripe en modo de prueba</strong>: no se cobra dinero real. } @else { <strong>Pasarela de pruebas</strong>: no se cobra dinero real. Use una de las tarjetas de ejemplo. }</p>
      }

      @if (fase() === 'pago' || fase() === 'rechazado' || fase() === 'error') {
        @if (tarjetas().length) {
          <div class="stack">
            <strong>Tarjetas guardadas</strong>
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
          @if (permitirGuardar()) { <label class="check"><input type="checkbox" name="gt" [(ngModel)]="guardar" /> Guardar esta tarjeta para mis próximas compras</label> }
        }

        @if (fase() === 'rechazado') {
          <div class="alert danger resultado" role="alert"><strong>✖ Pago rechazado</strong><br />{{ mensaje() }}@if (motivo()) { <br /><span class="small">Motivo: {{ motivo() }}</span> }<br /><span class="small">No se cobró nada. Pruebe con otra tarjeta.</span></div>
        }
        @if (fase() === 'error') { <div class="alert danger resultado" role="alert">{{ mensaje() }}</div> }
        <div class="row between">
          <span class="muted small">Se cobrará el equivalente a <strong>US$ {{ dolares() }}</strong> (Bs {{ total() }} a {{ config()?.tasa_bob_por_usd }} Bs por dólar).</span>
          <button type="button" class="btn primary" (click)="pagar()">Pagar Bs {{ total() }}</button>
        </div>
      }

      @if (fase() === 'procesando') {
        <div class="resultado cargando" role="status"><span class="rueda"></span><div><strong>Verificando la tarjeta con el banco…</strong><br /><span class="small muted">No cierre esta ventana.</span></div></div>
      }
      @if (fase() === 'aprobado' && resultado(); as r) {
        <div class="alert ok resultado" role="status"><strong>✔ Pago aprobado</strong><br />{{ r.pago.tarjeta_marca }} terminada en {{ r.pago.tarjeta_ultimos4 }} · Comprobante N.° <strong>{{ r.pedido.comprobante_numero }}</strong></div>
      }
      @if (fase() === 'pendiente' && resultado(); as r) {
        <div class="alert warn resultado" role="status"><strong>⏳ Pendiente de confirmación</strong><br />{{ r.mensaje }}</div>
        <div><button type="button" class="btn primary" (click)="reconciliar(r.pago.id)" [disabled]="verificando()">{{ verificando() ? 'Verificando…' : 'Verificar estado del pago' }}</button></div>
      }
    </div>`,
  styles: `
    .campo-stripe { padding: .7rem; border: 1px solid #d6d1c9; border-radius: 9px; background: #fff; min-height: 2.6rem; }
    .opcion { border: 1px solid var(--line); border-radius: 10px; padding: .6rem .8rem; } .opcion:has(input:checked) { border-color: var(--accent); background: var(--accent-soft); }
    .prueba { border: 1px dashed var(--line); border-radius: 10px; padding: .6rem .8rem; } .prueba summary { cursor: pointer; font-weight: 600; }
    code { font-size: .82rem; } .resultado { font-size: 1rem; line-height: 1.5; }
    .cargando { display: flex; gap: 1rem; align-items: center; padding: 1.2rem; border: 1px solid var(--line); border-radius: 12px; }
    .rueda { width: 28px; height: 28px; border: 3px solid var(--line); border-top-color: var(--accent); border-radius: 50%; animation: gira .8s linear infinite; }
    @keyframes gira { to { transform: rotate(360deg); } }`,
})
export class PagoTarjetaComponent implements OnInit {
  private api = inject(ComprasApi);
  private stripeJs = inject(StripeJsService);

  readonly pedidoId = input.required<number>();
  readonly total = input.required<string>();
  readonly permitirGuardar = input(true);  // en caja no se guardan tarjetas
  readonly listo = output<ResultadoPago>();  // pago aprobado o pendiente de confirmación
  readonly sinStock = output<string>();  // el stock se agotó: el padre debe actualizar su pantalla

  readonly config = signal<ConfigPago | null>(null);
  readonly tarjetas = signal<TarjetaGuardada[]>([]);
  readonly resultado = signal<ResultadoPago | null>(null);
  readonly fase = signal<Fase>('pago');
  readonly verificando = signal(false);
  readonly mensaje = signal('');
  readonly motivo = signal('');
  readonly dolares = computed(() => {
    const c = this.config();
    return c ? (Number(this.total()) / c.tasa_bob_por_usd).toFixed(2) : '';
  });
  guardadaId: number | null = null;
  guardar = false;
  titular = '';
  sim = { numero: '', mes: 12, anio: new Date().getFullYear() + 3, cvc: '', titular: '' };
  private stripe: any = null;
  private campoTarjeta: any = null;
  private motivoStripe = '';

  ngOnInit() {
    this.api.configPago().subscribe((cfg) => {
      this.config.set(cfg);
      if (!this.permitirGuardar()) { if (cfg.modo === 'stripe') void this.montarStripe(cfg); return; }
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
    this.api.eliminarTarjeta(t.id).subscribe(() => { this.tarjetas.update((l) => l.filter((x) => x.id !== t.id)); if (this.guardadaId === t.id) this.elegirMedio(null); });
  }

  pagar() {
    this.fase.set('procesando'); this.mensaje.set(''); this.motivo.set('');
    this.api.iniciarPago(this.pedidoId(), this.guardadaId, this.guardar && this.guardadaId === null && this.permitirGuardar()).subscribe({
      next: (ini) => {
        if (ini.modo === 'stripe') void this.confirmarConStripe(ini.pago_id, ini.client_secret!, ini.publishable_key!);
        else this.confirmar(ini.pago_id, { ...this.sim });
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

  private confirmar(pagoId: number, tarjeta: TarjetaSimulada | null) {
    this.api.confirmarPago(pagoId, tarjeta).subscribe({ next: (r) => this.terminar(r), error: (e) => this.fallo(e) });
  }

  reconciliar(pagoId: number) {
    this.verificando.set(true);
    this.api.reconciliarPago(pagoId).subscribe({
      next: (r) => { this.verificando.set(false); this.terminar(r); },
      error: (e) => { this.verificando.set(false); this.fallo(e); },
    });
  }

  private terminar(r: ResultadoPago) {
    this.resultado.set(r); this.motivoStripe = '';
    this.fase.set(r.aprobado ? 'aprobado' : 'pendiente');
    this.listo.emit(r);
  }

  private fallo(e: unknown) {
    const err = e as { status?: number; error?: { motivo?: string } };
    this.mensaje.set(mensajeError(e));
    if (err.status === 402) { this.motivo.set(this.motivoStripe || err.error?.motivo || ''); this.fase.set('rechazado'); }
    else if (err.status === 409) { this.fase.set('error'); this.sinStock.emit(this.mensaje()); }
    else this.fase.set('error');
    this.motivoStripe = '';
    if ((this.fase() === 'rechazado' || this.fase() === 'error') && this.config()?.modo === 'stripe') void this.montarStripe(this.config()!);
  }
}
