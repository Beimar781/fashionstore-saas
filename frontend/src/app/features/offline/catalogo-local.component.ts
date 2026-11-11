import { DatePipe } from '@angular/common';
import { ErrorComponent } from '../../core/ui/vacio.component';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/auth/auth.service';
import { CatalogoLocalService } from '../../core/offline/catalogo-local.service';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { ToastService, mensajeError } from '../../core/ui/toast.service';
import { BsPipe } from '../../core/formato-bs';

/** CU-37 · Catálogo para uso offline: se descarga una vez con conexión y se consulta y busca sin ella. Siempre dice de cuándo es (RN16). */
@Component({
  selector: 'app-catalogo-local',
  imports: [ErrorComponent, BsPipe, FormsModule, DatePipe],
  template: `
    <section class="card pad stack">
      <div class="row between">
        <div>
          <h2>Catálogo en este dispositivo</h2>
          @if (meta(); as m) {
            <p class="small muted">Descargado el {{ m.generado_en | date: 'dd/MM/yyyy HH:mm' }} · {{ productos().length }} producto(s) · {{ m.sucursales.length }} sucursal(es)@if (esPersonal) { · {{ m.clientes.length }} cliente(s) }</p>
            @if (motivoDesactualizado() === 'viejo') { <div class="alert warn small" role="status">Esta información puede estar desactualizada: se descargó hace más de un día.</div> }
            @else if (motivoDesactualizado() === 'sin-conexion') { <div class="alert small" role="status">Sin conexión para renovarla: se muestra la última descarga.</div> }
          } @else { <p class="small muted">Todavía no descargó el catálogo. Descárguelo con conexión para poder consultar y vender sin Internet.</p> }
        </div>
        <button class="btn primary" (click)="descargar()" [disabled]="local.descargando() || !red.online()">{{ local.descargando() ? 'Descargando…' : meta() ? 'Actualizar catálogo' : 'Descargar catálogo' }}</button>
      </div>
      @if (!red.online()) { <p class="small muted">Sin conexión: se muestra lo que ya está guardado.</p> }
      @if (error()) { <app-error [texto]="error()" /> }

      @if (local.hayCatalogo()) {
        <label>Buscar en el catálogo guardado<input name="q" [ngModel]="texto()" (ngModelChange)="texto.set($event)" placeholder="Nombre, categoría, SKU o código de barras" autocomplete="off" /></label>
        <div class="table-wrap"><table>
          <thead><tr><th>Prenda</th><th>Talla</th><th>Color</th><th>SKU</th><th class="right">Precio</th><th class="right">Stock</th></tr></thead>
          <tbody>
            @for (r of resultados(); track r.variante.id) {
              <tr><td>{{ r.producto.nombre }}<div class="small muted">{{ r.producto.categoria }}</div></td><td>{{ r.variante.talla }}</td><td>{{ r.variante.color }}</td><td class="small">{{ r.variante.sku }}</td>
                <td class="right nowrap">@if (r.variante.promocion) { <s class="muted small">{{ r.variante.precio | bs }}</s> } {{ r.variante.precio_final | bs }}</td>
                <td class="right">{{ detalleStock(r.variante) }}</td></tr>
            } @empty { <tr><td colspan="6" class="empty">No hay prendas con ese texto.</td></tr> }
          </tbody></table></div>
      }
    </section>`,
})
export class CatalogoLocalComponent {
  readonly local = inject(CatalogoLocalService);
  readonly red = inject(ConnectivityService);
  private auth = inject(AuthService);
  private toast = inject(ToastService);

  readonly productos = this.local.productos;
  readonly meta = this.local.meta;
  readonly texto = signal('');
  readonly error = signal('');
  readonly esPersonal = this.auth.rol() !== 'Cliente';
  readonly resultados = computed(() => this.local.buscar(this.texto()));
  /** Distingue «tiene más de un día» de «no hay conexión para renovarla» (antes un aviso mezclaba ambos aunque la descarga fuera de hoy). */
  readonly motivoDesactualizado = computed<'viejo' | 'sin-conexion' | null>(() => {
    const m = this.meta();
    if (!m) return null;
    if (Date.now() - new Date(m.generado_en).getTime() > 24 * 3600 * 1000) return 'viejo';
    return this.red.online() ? null : 'sin-conexion';
  });

  detalleStock(v: { stock: Record<string, number> }) {
    const m = this.meta();
    const partes = Object.entries(v.stock).map(([id, n]) => (m && m.sucursales.length > 1 ? `${m.sucursales.find((s) => s.id === Number(id))?.nombre ?? id}: ${n}` : String(n)));
    return partes.length ? partes.join(' · ') : '0';
  }

  async descargar() {
    this.error.set('');
    try { await this.local.descargar(); this.toast.ok('Catálogo descargado: ya puede consultarlo sin conexión.'); } catch (e) { this.error.set(mensajeError(e)); }
  }
}
