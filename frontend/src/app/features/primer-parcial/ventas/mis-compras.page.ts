import { DatePipe } from '@angular/common';
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

interface CompraEnLista { id: string | number; codigo: string; fecha: string; sucursal: string; total: string; total_unidades: number; comprobante_numero: string | null; estado: string; pendiente: boolean; }

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
                  <td>@if (c.pendiente) { <span class="badge warn">Pendiente de sincronizar · {{ c.estado }}</span> } @else { <span class="badge" [class]="clase(c.estado)">{{ texto(c.estado) }}</span> }</td><td>{{ c.comprobante_numero ?? '—' }}</td>
                  <td class="actions">@if (!c.pendiente) { <a class="btn sm" [routerLink]="['/tienda/compras', c.id]">Ver detalle</a> }</td>
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
  readonly compras = computed<CompraEnLista[]>(() => [
    ...this.servidor().map((c) => ({ ...c, estado: c.estado, pendiente: false })),
    ...this.cola.operaciones().filter((o) => o.tipo === 'COMPRA' && ['REGISTRADA_LOCAL', 'ENVIADA'].includes(o.estado)).map((o) => {
      const items = (o.payload['items'] as { variante_id: number; cantidad: number }[] | undefined) ?? [];
      const total = items.reduce((s, i) => { const v = this.catalogoLocal.productos().flatMap((p) => p.variantes).find((x) => x.id === i.variante_id); return s + Number(v?.precio_final ?? 0) * i.cantidad; }, 0);
      const sucursal = this.catalogoLocal.meta()?.sucursales.find((s) => s.id === o.sucursal_id)?.nombre ?? 'Sucursal';
      return { id: o.id, codigo: o.referencia ?? `Compra local ${o.id.slice(0, 8)}`, fecha: o.creada_en, sucursal, total: total.toFixed(2), total_unidades: items.reduce((s, i) => s + i.cantidad, 0), comprobante_numero: null, estado: o.estado, pendiente: true };
    }),
  ]);
  readonly mensaje = signal<string | null>(null);
  readonly cargando = signal(true);
  readonly texto = (e: string) => TEXTO_ESTADO_PEDIDO[e as EstadoPedido] ?? e;
  readonly clase = (e: string) => CLASE_ESTADO_PEDIDO[e as EstadoPedido] ?? '';

  async ngOnInit() {
    await this.cola.cargar();
    const s = this.auth.sesion();
    const cache = s ? await this.db.leerComprasClienteLocal<CompraResumen[]>(`${s.empresa?.id ?? 0}:${s.usuario.id}`) : undefined;
    if (!this.red.online()) { this.servidor.set(cache ?? []); const pendientes = this.cola.operaciones().some((o) => o.tipo === 'COMPRA' && ['REGISTRADA_LOCAL', 'ENVIADA'].includes(o.estado)); this.mensaje.set(cache?.length || pendientes ? null : 'Sin conexión: todavía no se descargó su historial de compras.'); this.cargando.set(false); return; }
    this.api.compras().subscribe({
      next: (r) => { this.servidor.set(r.compras); if (s) void this.db.guardarComprasClienteLocal(`${s.empresa?.id ?? 0}:${s.usuario.id}`, r.compras); const pendientes = this.cola.operaciones().some((o) => o.tipo === 'COMPRA' && ['REGISTRADA_LOCAL', 'ENVIADA'].includes(o.estado)); this.mensaje.set(pendientes ? null : r.mensaje); this.cargando.set(false); },
      error: (e) => { this.servidor.set(cache ?? []); this.mensaje.set(cache?.length ? null : mensajeError(e)); this.cargando.set(false); if (!cache?.length) this.toast.error(mensajeError(e)); },
    });
  }
}
