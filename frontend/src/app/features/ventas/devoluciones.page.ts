import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { PagoTarjetaComponent } from '../primer-parcial/ventas/pago-tarjeta.component';
import { CajaApi } from '../../core/api/caja.api';
import { DevolucionesApi } from '../../core/api/devoluciones.api';
import { ProductoCaja } from '../../core/caja.models';
import { IniciarPago, ResultadoPago, TarjetaSimulada } from '../../core/compras.models';
import { Devolucion, LineaNueva, VentaDevolvible } from '../../core/devoluciones.models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** CU-41 · Devoluciones y cambios: se busca la venta por su comprobante (RN15), se eligen las prendas y se emite la nota. Cajero y Encargado, solo su sucursal. */
@Component({
  selector: 'app-devoluciones',
  imports: [FormsModule, DatePipe, PagoTarjetaComponent],
  template: `
    <div class="page" style="max-width:1100px">
      <div class="page-head"><div><h1>Devoluciones y cambios</h1><p>Ingrese el comprobante de la venta. La prenda devuelta vuelve al inventario de la sucursal.</p></div>
        @if (venta() || resultado()) { <button class="btn" (click)="nueva()">+ Otra devolución</button> }</div>

      @if (!venta() && !resultado()) {
        <form class="card pad row" (ngSubmit)="buscar()">
          <label style="flex:1;min-width:240px">N.° de comprobante<input name="c" [(ngModel)]="comprobante" placeholder="CMP-001-000001" autocomplete="off" style="text-transform:uppercase" autofocus /></label>
          <button class="btn primary" style="align-self:end">Buscar venta</button>
        </form>
        @if (errorBusqueda()) { <div class="alert danger" role="alert" style="margin-top:1rem">{{ errorBusqueda() }}</div> }
        <h3 style="margin:1.5rem 0 .5rem">Devoluciones recientes</h3>
        <div class="card table-wrap">
          @if (!recientes().length) { <div class="empty">Todavía no hay devoluciones.</div> } @else {
            <table>
              <thead><tr><th>Nota</th><th>Fecha</th><th>Tipo</th><th>Comprobante</th><th class="right">Devuelto</th><th class="right">Reembolso</th><th></th></tr></thead>
              <tbody>
                @for (d of recientes(); track d.id) {
                  <tr><td><strong>{{ d.numero }}</strong></td><td class="nowrap">{{ d.fecha | date: 'dd/MM HH:mm' }}</td><td>{{ d.tipo === 'CAMBIO' ? 'Cambio' : 'Devolución' }}</td><td>{{ d.comprobante }}</td>
                    <td class="right nowrap">Bs {{ d.monto_devuelto }}</td><td class="right nowrap">Bs {{ d.reembolso }}</td><td class="actions"><button class="btn sm" (click)="imprimir(d)">Nota</button></td></tr>
                }
              </tbody>
            </table>
          }
        </div>
      }

      @if (venta(); as v) {
        <div class="stack">
          <section class="card pad stack">
            <div class="row between"><h2>Venta {{ v.pedido.comprobante_numero }}</h2><span class="small muted">{{ v.pedido.codigo }} · {{ v.pedido.pagado_en | date: 'dd/MM/yyyy HH:mm' }} · Bs {{ v.pedido.total }}</span></div>
            <p class="small muted">Pagada con {{ nombreMedio(v.medio_pago) }}. @if (v.dentro_del_plazo) { Se acepta hasta el {{ v.vence_el | date: 'dd/MM/yyyy' }} ({{ v.plazo_dias }} días). }</p>
            @if (!v.dentro_del_plazo) { <div class="alert danger" role="alert">El plazo de {{ v.plazo_dias }} días venció el {{ v.vence_el | date: 'dd/MM/yyyy' }}: no se puede devolver ni cambiar.</div> }
            @if (v.devoluciones.length) { <p class="small">Ya registradas: @for (d of v.devoluciones; track d.id) { <span class="badge">{{ d.numero }}</span> }</p> }

            <div class="table-wrap"><table>
              <thead><tr><th>Prenda</th><th class="right">Vendidas</th><th class="right">Devueltas</th><th class="right">Precio</th><th class="right">Devolver</th></tr></thead>
              <tbody>
                @for (i of v.items; track i.pedido_item_id) {
                  <tr><td>{{ i.producto }}<div class="small muted">Talla {{ i.talla }} · {{ i.color }} · {{ i.sku }}</div></td><td class="right">{{ i.vendida }}</td><td class="right">{{ i.devuelta }}</td><td class="right">{{ i.precio_final }}</td>
                    <td class="right"><input type="number" min="0" [max]="i.devolvible" [name]="'q' + i.pedido_item_id" [ngModel]="cantidades()[i.pedido_item_id] || 0" (ngModelChange)="fijarCantidad(i.pedido_item_id, i.devolvible, $event)" [disabled]="i.devolvible === 0 || !v.dentro_del_plazo" style="width:4.5rem" /></td></tr>
                }
              </tbody>
            </table></div>
          </section>

          <section class="card pad stack">
            <div class="row">
              <label style="max-width:220px">Operación<select name="t" [ngModel]="tipo()" (ngModelChange)="tipo.set($event)"><option value="DEVOLUCION">Devolución</option><option value="CAMBIO">Cambio por otra prenda</option></select></label>
              <label style="flex:1;min-width:240px">Motivo<input name="m" [(ngModel)]="motivo" placeholder="Le quedó pequeña, falla de fábrica…" maxlength="200" /></label>
            </div>
            <fieldset class="stack" style="border:1px solid var(--line);border-radius:8px;padding:.6rem .8rem">
              <legend class="small"><strong>Revisión de la prenda que vuelve</strong></legend>
              <label class="check"><input type="checkbox" name="cd" [(ngModel)]="condicion.sin_danos" /> Sin daños (rotos, manchas ni costuras abiertas)</label>
              <label class="check"><input type="checkbox" name="cg" [(ngModel)]="condicion.sin_desgaste" /> Sin desgaste ni señales de uso o lavado</label>
              <label class="check"><input type="checkbox" name="ce" [(ngModel)]="condicion.con_etiquetas" /> Conserva sus etiquetas</label>
            </fieldset>

            @if (tipo() === 'CAMBIO') {
              <form class="row" (ngSubmit)="buscarNueva()">
                <label style="flex:1;min-width:220px">Prenda nueva<input name="b" [(ngModel)]="consulta" placeholder="Buscar por nombre en esta sucursal" autocomplete="off" /></label>
                <button class="btn" style="align-self:end">Buscar</button>
              </form>
              @if (errorNueva()) { <div class="alert danger" role="alert">{{ errorNueva() }}</div> }
              @if (resultados().length) {
                <div class="row" style="flex-wrap:wrap">
                  @for (p of resultados(); track p.variante_id) {
                    <button type="button" class="btn sm" [disabled]="p.disponible === 0" (click)="agregarNueva(p)">{{ p.producto }} · {{ p.talla }} · {{ p.color }} · Bs {{ p.precio_final }} ({{ p.disponible }})</button>
                  }
                </div>
              }
              @for (n of nuevas(); track n.variante_id) {
                <div class="row between small"><span>{{ n.producto }} · {{ n.talla }} · {{ n.color }} · Bs {{ n.precio_final }}</span>
                  <span class="row"><input type="number" min="1" [max]="n.max" [name]="'n' + n.variante_id" [(ngModel)]="n.cantidad" style="width:4.5rem" (ngModelChange)="nuevas.set([...nuevas()])" /><button type="button" class="btn sm danger" (click)="quitarNueva(n)">✕</button></span></div>
              }
            }

            <div class="resumen stack">
              <div class="row between"><span>Valor de lo devuelto</span><strong>Bs {{ devuelto().toFixed(2) }}</strong></div>
              @if (tipo() === 'CAMBIO') { <div class="row between"><span>Valor de lo nuevo</span><strong>Bs {{ nuevo().toFixed(2) }}</strong></div> }
              @if (diferencia() > 0) {
                <div class="alert warn">El cliente debe pagar Bs {{ diferencia().toFixed(2) }}.</div>
                <div class="tabs" role="tablist">
                  <button role="tab" [class.activa]="metodoCobro() === 'EFECTIVO'" (click)="metodoCobro.set('EFECTIVO')">💵 Efectivo</button>
                  <button role="tab" [class.activa]="metodoCobro() === 'TARJETA'" (click)="metodoCobro.set('TARJETA')">💳 Tarjeta</button>
                </div>
                @if (metodoCobro() === 'EFECTIVO') {
                  <div class="row"><label style="max-width:170px">Monto recibido en efectivo (Bs)<input name="mr" type="number" min="0" step="0.01" [(ngModel)]="montoRecibido" /></label></div>
                }
              } @else if (diferencia() < 0 || (tipo() === 'DEVOLUCION' && devuelto() > 0)) {
                <div class="alert ok">Se reembolsan Bs {{ reembolso().toFixed(2) }} con {{ nombreMedio(v.medio_pago) }}{{ v.medio_pago === 'TARJETA' ? ' (a la misma tarjeta)' : '' }}.</div>
              }
            </div>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
            @if (diferencia() > 0 && metodoCobro() === 'TARJETA') {
              @if (v.dentro_del_plazo && hayPrendas()) {
                <app-pago-tarjeta [total]="diferencia().toFixed(2)" [permitirGuardar]="false" [iniciarFn]="iniciarDiferencia" [confirmarFn]="confirmarDiferencia" (sinStock)="error.set($event)" />
              }
              <div class="row"><button class="btn ghost" (click)="nueva()">Cancelar</button></div>
            } @else {
            <div class="row"><button class="btn primary" [disabled]="enviando() || !v.dentro_del_plazo || !hayPrendas() || !condicionCompleta()" (click)="registrar()">{{ enviando() ? 'Registrando…' : tipo() === 'CAMBIO' ? 'Registrar cambio' : 'Registrar devolución' }}</button><button class="btn ghost" (click)="nueva()">Cancelar</button></div>
            }
          </section>
        </div>
      }

      @if (resultado(); as r) {
        <section class="card pad stack">
          <div class="alert ok" role="status"><strong>✔ {{ r.tipo === 'CAMBIO' ? 'Cambio registrado' : 'Devolución registrada' }}</strong><br />Nota N.° <strong>{{ r.numero }}</strong> sobre el comprobante {{ r.comprobante }}.
            @if (+r.reembolso > 0) { <br />Reembolso: Bs {{ r.reembolso }} en {{ nombreMedio(r.medio_reembolso) }}@if (r.referencia_reembolso) { (ref. {{ r.referencia_reembolso }}) }. }
            @if (+r.cobro_adicional > 0) { <br />Diferencia cobrada: Bs {{ r.cobro_adicional }} en {{ r.tarjeta_cobro ? 'tarjeta ' + r.tarjeta_cobro : nombreMedio(r.medio_cobro) }}@if (r.cambio_entregado && +r.cambio_entregado > 0) { · cambio Bs {{ r.cambio_entregado }} }. }
          </div>
          <div class="row"><button class="btn primary" (click)="imprimir(r)">🖨 Imprimir nota</button><button class="btn" (click)="nueva()">Otra devolución</button></div>
        </section>
      }
    </div>`,
  styles: `.resumen { border-top: 1px solid var(--line); padding-top: .8rem; }`,
})
export class DevolucionesPage implements OnInit {
  private api = inject(DevolucionesApi);
  private caja = inject(CajaApi);
  private toast = inject(ToastService);

  readonly venta = signal<VentaDevolvible | null>(null);
  readonly resultado = signal<Devolucion | null>(null);
  readonly recientes = signal<Devolucion[]>([]);
  readonly cantidades = signal<Record<number, number>>({});
  readonly nuevas = signal<LineaNueva[]>([]);
  readonly resultados = signal<ProductoCaja[]>([]);
  readonly tipo = signal<'DEVOLUCION' | 'CAMBIO'>('DEVOLUCION');
  readonly metodoCobro = signal<'EFECTIVO' | 'TARJETA'>('EFECTIVO');
  readonly errorBusqueda = signal('');
  readonly errorNueva = signal('');
  readonly error = signal('');
  readonly enviando = signal(false);
  comprobante = ''; motivo = ''; consulta = ''; montoRecibido: number | null = null;
  condicion = { sin_danos: false, sin_desgaste: false, con_etiquetas: false };  // RN15: quien recibe la prenda la revisa
  condicionCompleta() { const c = this.condicion; return c.sin_danos && c.sin_desgaste && c.con_etiquetas; }

  readonly devuelto = computed(() => (this.venta()?.items ?? []).reduce((t, i) => t + (this.cantidades()[i.pedido_item_id] ?? 0) * Number(i.precio_final), 0));
  readonly nuevo = computed(() => this.tipo() === 'CAMBIO' ? this.nuevas().reduce((t, n) => t + n.cantidad * n.precio_final, 0) : 0);
  readonly diferencia = computed(() => this.nuevo() - this.devuelto());
  readonly reembolso = computed(() => Math.max(0, -this.diferencia()));
  readonly hayPrendas = computed(() => this.devuelto() > 0 && (this.tipo() === 'DEVOLUCION' || this.nuevas().length > 0));

  ngOnInit() { this.cargarRecientes(); }

  nombreMedio(m: string | null) { return m === 'EFECTIVO' ? 'efectivo' : m === 'TARJETA' ? 'tarjeta' : '—'; }

  private cargarRecientes() { this.api.listar().subscribe({ next: (l) => this.recientes.set(l.slice(0, 15)), error: () => this.recientes.set([]) }); }

  buscar() {
    this.errorBusqueda.set('');
    this.api.venta(this.comprobante.trim()).subscribe({
      next: (v) => { this.venta.set(v); this.cantidades.set({}); this.nuevas.set([]); this.resultados.set([]); this.tipo.set('DEVOLUCION'); this.metodoCobro.set('EFECTIVO'); this.motivo = ''; this.condicion = { sin_danos: false, sin_desgaste: false, con_etiquetas: false }; this.error.set(''); },
      error: (e) => this.errorBusqueda.set(mensajeError(e)),
    });
  }

  fijarCantidad(id: number, max: number, valor: number) { this.cantidades.update((c) => ({ ...c, [id]: Math.max(0, Math.min(max, Math.floor(Number(valor) || 0))) })); }

  buscarNueva() {
    this.errorNueva.set('');
    this.caja.buscar(this.consulta.trim()).subscribe({
      next: (r) => { this.resultados.set(r); if (!r.length) this.errorNueva.set('No se encontraron prendas con ese nombre.'); },
      error: (e) => this.errorNueva.set(mensajeError(e)),
    });
  }

  agregarNueva(p: ProductoCaja) {
    const actual = this.nuevas().find((n) => n.variante_id === p.variante_id);
    if (actual) { if (actual.cantidad < actual.max) actual.cantidad++; this.nuevas.set([...this.nuevas()]); return; }
    this.nuevas.update((l) => [...l, { variante_id: p.variante_id, producto: p.producto, talla: p.talla, color: p.color, precio_final: Number(p.precio_final), cantidad: 1, max: p.disponible }]);
  }
  quitarNueva(n: LineaNueva) { this.nuevas.update((l) => l.filter((x) => x !== n)); }

  private cuerpo(): Record<string, unknown> {
    const v = this.venta()!;
    return {
      comprobante: v.pedido.comprobante_numero, tipo: this.tipo(), motivo: this.motivo, condicion: { ...this.condicion },
      items: v.items.filter((i) => (this.cantidades()[i.pedido_item_id] ?? 0) > 0).map((i) => ({ pedido_item_id: i.pedido_item_id, cantidad: this.cantidades()[i.pedido_item_id] })),
      nuevos: this.tipo() === 'CAMBIO' ? this.nuevas().map((n) => ({ variante_id: n.variante_id, cantidad: n.cantidad })) : [],
    };
  }

  /** Cobro con tarjeta de la diferencia: el servidor calcula el monto y lo pide a la pasarela (mismo formato que el pago del CU-32). */
  readonly iniciarDiferencia = (): Observable<IniciarPago> => this.api.iniciarDiferencia(this.cuerpo()) as Observable<IniciarPago>;

  /** Confirmar la tarjeta registra el cambio: si el banco rechaza o falta stock, no queda nada a medias. */
  readonly confirmarDiferencia = (pagoId: number, tarjeta: TarjetaSimulada | null): Observable<ResultadoPago> =>
    this.api.registrar({ ...this.cuerpo(), cobro: { metodo: 'TARJETA', intento_id: pagoId, tarjeta } }).pipe(
      map((d) => {
        this.resultado.set(d); this.venta.set(null); this.toast.ok(`Nota ${d.numero} registrada.`);
        return { aprobado: true, pendiente: false, mensaje: '', pago: {} as ResultadoPago['pago'], pedido: {} as ResultadoPago['pedido'] };
      }),
    );

  registrar() {
    if (!this.venta()) return;
    this.error.set('');
    const cuerpo = this.cuerpo();
    if (this.diferencia() > 0) cuerpo['cobro'] = { metodo: 'EFECTIVO', monto_recibido: this.montoRecibido };
    this.enviando.set(true);
    this.api.registrar(cuerpo).subscribe({
      next: (d) => { this.enviando.set(false); this.resultado.set(d); this.venta.set(null); this.toast.ok(`Nota ${d.numero} registrada.`); },
      error: (e) => { this.enviando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  imprimir(d: Devolucion) { this.api.nota(d.id).subscribe({ next: (blob) => window.open(URL.createObjectURL(blob), '_blank'), error: (e) => this.toast.error(mensajeError(e)) }); }

  nueva() { this.venta.set(null); this.resultado.set(null); this.comprobante = ''; this.errorBusqueda.set(''); this.montoRecibido = null; this.cargarRecientes(); }
}
