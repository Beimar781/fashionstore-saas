import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ComprasApi } from '../../../core/api/compras.api';
import { CLASE_ESTADO_PEDIDO, Pedido, TEXTO_ESTADO_PEDIDO } from '../../../core/compras.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';

/** CU-12 · Detalle de una compra: prendas, totales, entrega, facturación, pagos y descarga del comprobante. */
@Component({
  selector: 'app-compra-detalle',
  imports: [RouterLink, DatePipe],
  template: `
    <div class="page" style="max-width:900px">
      <a routerLink="/tienda/compras" class="small">← Mis compras</a>
      @if (pedido(); as p) {
        <div class="page-head" style="margin-top:.4rem">
          <div><h1>{{ p.codigo }}</h1><p><span class="badge" [class]="CLASE[p.estado]">{{ TEXTO[p.estado] }}</span> · {{ (p.pagado_en ?? p.creado_en) | date: 'dd/MM/yyyy HH:mm' }} · {{ p.sucursal }}</p></div>
          @if (p.estado === 'PAGADO') { <button class="btn primary" (click)="descargar(p)">⬇ Descargar comprobante</button> }
          @if (p.estado === 'PENDIENTE_CONFIRMACION') { <button class="btn primary" (click)="verificar(p)" [disabled]="verificando()">{{ verificando() ? 'Verificando…' : 'Verificar estado del pago' }}</button> }
        </div>
        @if (p.estado === 'PENDIENTE_CONFIRMACION') { <div class="alert warn" role="status" style="margin-bottom:1rem">Su pago está pendiente de confirmación: el banco aún no respondió. No se le cobrará dos veces.</div> }

        <section class="card table-wrap">
          <table>
            <thead><tr><th>Prenda</th><th class="right">Cantidad</th><th class="right">Precio</th><th class="right">Subtotal</th></tr></thead>
            <tbody>@for (i of p.items; track i.id) { <tr><td><strong>{{ i.producto }}</strong><div class="muted small">Talla {{ i.talla }} · {{ i.color }} · {{ i.sku }}</div></td>
              <td class="right">{{ i.cantidad }}</td><td class="right nowrap">Bs {{ i.precio_final }}</td><td class="right nowrap">Bs {{ i.subtotal }}</td></tr> }</tbody>
          </table>
        </section>

        <div class="grid cols-2" style="margin-top:1rem">
          <section class="card pad stack">
            <h3>Totales</h3>
            <div class="row between"><span class="muted">Subtotal</span><span>Bs {{ p.subtotal }}</span></div>
            @if (p.descuento !== '0.00') { <div class="row between"><span class="muted">Descuento</span><span>− Bs {{ p.descuento }}</span></div> }
            <div class="row between"><strong>Total</strong><strong>Bs {{ p.total }}</strong></div>
            <p class="muted small">Incluye IVA: Bs {{ p.iva_incluido }}</p>
          </section>
          <section class="card pad stack">
            <h3>Entrega y facturación</h3>
            <p>{{ p.tipo_entrega === 'DELIVERY' ? '🚚 Entrega a domicilio: ' + p.direccion_entrega : '🏬 Retiro en ' + p.sucursal }}</p>
            <p class="small">Factura a: {{ p.razon_social || '—' }} · NIT/CI {{ p.nit_ci }}</p>
            @if (p.comprobante_numero) { <p class="small">Comprobante N.° <strong>{{ p.comprobante_numero }}</strong></p> }
          </section>
        </div>

        <section class="card pad stack" style="margin-top:1rem">
          <h3>Pagos</h3>
          @for (g of p.pagos; track g.id) {
            <div class="row between small">
              <span>{{ g.creado_en | date: 'dd/MM HH:mm' }} · Tarjeta {{ g.tarjeta_marca }} {{ g.tarjeta_ultimos4 ? 'terminada en ' + g.tarjeta_ultimos4 : '' }}@if (g.motivo) { · {{ g.motivo }} }</span>
              <span><span class="badge" [class.ok]="g.estado === 'APROBADO'" [class.danger]="g.estado === 'RECHAZADO' || g.estado === 'CANCELADO'" [class.warn]="g.estado === 'PENDIENTE_CONFIRMACION'">{{ g.estado.replaceAll('_', ' ') }}</span> Bs {{ g.monto }}</span>
            </div>
          } @empty { <p class="muted small">Sin intentos de pago.</p> }
        </section>
      } @else { <div class="empty">Cargando…</div> }
    </div>`,
})
export class CompraDetallePage implements OnInit {
  private api = inject(ComprasApi);
  private ruta = inject(ActivatedRoute);
  private toast = inject(ToastService);

  readonly TEXTO = TEXTO_ESTADO_PEDIDO;
  readonly CLASE = CLASE_ESTADO_PEDIDO;
  readonly pedido = signal<Pedido | null>(null);
  readonly verificando = signal(false);

  ngOnInit() { this.cargar(); }

  private cargar() {
    this.api.compra(Number(this.ruta.snapshot.paramMap.get('id'))).subscribe({ next: (p) => this.pedido.set(p), error: (e) => this.toast.error(mensajeError(e)) });
  }

  descargar(p: Pedido) {
    this.api.comprobante(p.id).subscribe({
      next: (blob) => { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `${p.comprobante_numero}.pdf`; a.click(); URL.revokeObjectURL(a.href); },
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }

  verificar(p: Pedido) {
    const pago = [...p.pagos].reverse().find((g) => g.estado === 'PENDIENTE_CONFIRMACION');
    if (!pago) return;
    this.verificando.set(true);
    this.api.reconciliarPago(pago.id).subscribe({
      next: (r) => { this.verificando.set(false); this.pedido.set(r.pedido); this.toast.ok(r.aprobado ? 'Pago confirmado.' : 'Sigue pendiente de confirmación.'); },
      error: (e) => { this.verificando.set(false); this.toast.error(mensajeError(e)); this.cargar(); },
    });
  }
}
