import { DatePipe } from '@angular/common';
import { estadoLegible } from '../../../core/offline/estado-legible';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ComprasApi } from '../../../core/api/compras.api';
import { CLASE_ESTADO_PEDIDO, CompraResumen, EstadoPedido, TEXTO_ESTADO_PEDIDO } from '../../../core/compras.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';
import { AuthService } from '../../../core/auth/auth.service';
import { ColaOperacionesService } from '../../../core/offline/cola-operaciones.service';
import { LocalDbService } from '../../../core/offline/local-db.service';
import { ConnectivityService } from '../../../core/offline/connectivity.service';
import { CatalogoLocalService } from '../../../core/offline/catalogo-local.service';
import { BsPipe } from '../../../core/formato-bs';
import { OperacionesConProblemaComponent } from '../../offline/operaciones-con-problema.component';

interface CompraEnLista { id: string | number; codigo: string; fecha: string; sucursal: string; total: string; total_unidades: number; comprobante_numero: string | null; estado: string; pendiente: boolean; leyenda?: string; }

/** CU-12 · Historial de compras del cliente, ordenado por fecha, con monto, sucursal y estado. */
@Component({
  selector: 'app-mis-compras',
  imports: [BsPipe, RouterLink, DatePipe, OperacionesConProblemaComponent],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Mis compras</h1><p>Sus compras digitales, con su comprobante.</p></div><a class="btn primary" routerLink="/tienda/catalogo">Seguir comprando</a></div>

      <app-operaciones-con-problema [tipos]="['COMPRA']" titulo="Compras que no se pudieron realizar" [paraCliente]="true" />

      @if (cargando()) { <div class="empty">Cargando…</div> }
      @else if (mensaje()) { <div class="card empty">{{ mensaje() }} <a routerLink="/tienda/catalogo">Ver el catálogo</a></div> }
      @else {
        <div class="card table-wrap">
          <table>
            <thead><tr><th>Fecha</th><th>Pedido</th><th>Sucursal</th><th class="right">Prendas</th><th class="right">Monto</th><th>Estado</th><th>Comprobante</th><th></th></tr></thead>
            <tbody>
              @for (c of compras(); track c.id) {
                <tr [style.background]="c.estado === 'PENDIENTE_PAGO' ? '#fbefd9' : null">
                  <td class="nowrap">{{ c.fecha | date: 'dd/MM/yyyy HH:mm' }}</td><td><strong>{{ c.codigo }}</strong></td><td>{{ c.sucursal }}</td>
                  <td class="right">{{ c.total_unidades }}</td><td class="right nowrap">{{ c.total | bs }}</td>
                  <td>@if (c.pendiente) { <span class="badge warn">{{ c.leyenda }}</span> } @else { <span class="badge" [class]="clase(c.estado)">{{ texto(c.estado) }}</span> }</td><td>{{ c.comprobante_numero ?? '—' }}</td>
                  <td class="actions">@if (!c.pendiente) { <a class="btn sm" [routerLink]="['/tienda/compras', c.id]">Ver detalle</a> } @else { @if (puedeDeshacer(c.id)) { <button type="button" class="btn sm danger" (click)="deshacer(c.id)">Deshacer</button> } <a class="btn sm ghost" routerLink="/tienda/offline" [queryParams]="{ pestana: 'operaciones' }">Línea de tiempo</a> }</td>
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
  private auth = inject(AuthService);
  private cola = inject(ColaOperacionesService);
  private db = inject(LocalDbService);
  readonly red = inject(ConnectivityService);
  private catalogoLocal = inject(CatalogoLocalService);

  private servidor = signal<CompraResumen[]>([]);
  readonly compras = computed<CompraEnLista[]>(() => this.conPorPagarArriba([
    ...this.servidor().map((c) => ({ ...c, estado: c.estado, pendiente: false })),
    ...this.cola.operaciones().filter((o) => o.tipo === 'COMPRA' && ['REGISTRADA_LOCAL', 'ENVIADA'].includes(o.estado)).map((o) => {
      const items = (o.payload['items'] as { variante_id: number; cantidad: number }[] | undefined) ?? [];
      const total = items.reduce((s, i) => { const v = this.catalogoLocal.productos().flatMap((p) => p.variantes).find((x) => x.id === i.variante_id); return s + Number(v?.precio_final ?? 0) * i.cantidad; }, 0);
      const sucursal = this.catalogoLocal.meta()?.sucursales.find((s) => s.id === o.sucursal_id)?.nombre ?? 'Sucursal';
      return { id: o.id, codigo: o.referencia ?? 'En este dispositivo', leyenda: estadoLegible(o), fecha: o.creada_en, sucursal, total: total.toFixed(2), total_unidades: items.reduce((s, i) => s + i.cantidad, 0), comprobante_numero: null, estado: o.estado, pendiente: true };
    }),
  ]));
  /** Los pedidos «Por pagar» van primero y se resaltan, igual que en el móvil. */
  private conPorPagarArriba(lista: CompraEnLista[]) { return [...lista].sort((a, b) => Number(b.estado === 'PENDIENTE_PAGO') - Number(a.estado === 'PENDIENTE_PAGO')); }
  readonly mensaje = signal<string | null>(null);
  puedeDeshacer(id: string | number) { const o = this.cola.operaciones().find((x) => x.id === id); return !!o && this.cola.puedeDeshacer(o); }
  async deshacer(id: string | number) { const o = this.cola.operaciones().find((x) => x.id === id); if (o) await this.cola.deshacer(o); }
  readonly cargando = signal(true);
  readonly texto = (e: string) => TEXTO_ESTADO_PEDIDO[e as EstadoPedido] ?? e;
  readonly clase = (e: string) => CLASE_ESTADO_PEDIDO[e as EstadoPedido] ?? '';

  constructor() { this.cola.alRefrescar(() => void this.cargar()); }  // tras sincronizar o al volver la red, la lista se actualiza sola

  async ngOnInit() { await this.cola.cargar(); await this.cargar(); }

  private async cargar() {
    const s = this.auth.sesion();
    const cache = s ? await this.db.leerComprasClienteLocal<CompraResumen[]>(`${s.empresa?.id ?? 0}:${s.usuario.id}`) : undefined;
    if (!this.red.online()) { this.servidor.set(cache ?? []); const pendientes = this.cola.operaciones().some((o) => o.tipo === 'COMPRA' && ['REGISTRADA_LOCAL', 'ENVIADA'].includes(o.estado)); this.mensaje.set(cache?.length || pendientes ? null : 'Sin conexión: todavía no se descargó su historial de compras.'); this.cargando.set(false); return; }
    this.api.compras().subscribe({
      next: (r) => { this.servidor.set(r.compras); if (s) void this.db.guardarComprasClienteLocal(`${s.empresa?.id ?? 0}:${s.usuario.id}`, r.compras); const pendientes = this.cola.operaciones().some((o) => o.tipo === 'COMPRA' && ['REGISTRADA_LOCAL', 'ENVIADA'].includes(o.estado)); this.mensaje.set(pendientes ? null : r.mensaje); this.cargando.set(false); },
      error: (e) => { this.servidor.set(cache ?? []); this.mensaje.set(cache?.length ? null : mensajeError(e)); this.cargando.set(false); if (!cache?.length) this.toast.error(mensajeError(e)); },
    });
  }
}
