import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ComprasApi } from '../../../core/api/compras.api';
import { CLASE_ESTADO_PEDIDO, CompraResumen, EstadoPedido, TEXTO_ESTADO_PEDIDO } from '../../../core/compras.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';

/** CU-12 · Historial de compras del cliente, ordenado por fecha, con monto, sucursal y estado. */
@Component({
  selector: 'app-mis-compras',
  imports: [RouterLink, DatePipe],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Mis compras</h1><p>Sus compras digitales, con su comprobante.</p></div><a class="btn primary" routerLink="/tienda/catalogo">Seguir comprando</a></div>

      @if (cargando()) { <div class="empty">Cargando…</div> }
      @else if (mensaje()) { <div class="card empty">{{ mensaje() }} <a routerLink="/tienda/catalogo">Ver el catálogo</a></div> }
      @else {
        <div class="card table-wrap">
          <table>
            <thead><tr><th>Fecha</th><th>Pedido</th><th>Sucursal</th><th class="right">Prendas</th><th class="right">Monto</th><th>Estado</th><th>Comprobante</th><th></th></tr></thead>
            <tbody>
              @for (c of compras(); track c.id) {
                <tr>
                  <td class="nowrap">{{ c.fecha | date: 'dd/MM/yyyy HH:mm' }}</td><td><strong>{{ c.codigo }}</strong></td><td>{{ c.sucursal }}</td>
                  <td class="right">{{ c.total_unidades }}</td><td class="right nowrap">Bs {{ c.total }}</td>
                  <td><span class="badge" [class]="clase(c.estado)">{{ texto(c.estado) }}</span></td><td>{{ c.comprobante_numero ?? '—' }}</td>
                  <td class="actions"><a class="btn sm" [routerLink]="['/tienda/compras', c.id]">Ver detalle</a></td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>`,
})
export class MisComprasPage implements OnInit {
  private api = inject(ComprasApi);
  private toast = inject(ToastService);

  readonly compras = signal<CompraResumen[]>([]);
  readonly mensaje = signal<string | null>(null);
  readonly cargando = signal(true);
  readonly texto = (e: EstadoPedido) => TEXTO_ESTADO_PEDIDO[e];
  readonly clase = (e: EstadoPedido) => CLASE_ESTADO_PEDIDO[e];

  ngOnInit() {
    this.api.compras().subscribe({
      next: (r) => { this.compras.set(r.compras); this.mensaje.set(r.mensaje); this.cargando.set(false); },
      error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); },
    });
  }
}
