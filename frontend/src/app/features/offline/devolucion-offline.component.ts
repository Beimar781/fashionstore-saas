import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/auth/auth.service';
import { CatalogoLocalService } from '../../core/offline/catalogo-local.service';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { VentaReciente } from '../../core/offline.models';
import { ToastService } from '../../core/ui/toast.service';
import { BsPipe } from '../../core/formato-bs';

export const MSG_PLAZO_VENCIDO = 'El plazo de devolución de esta venta venció.';

/** B3 · Devolución sin conexión (Cajero y Encargado). Se usa en la pantalla normal de Devoluciones cuando no hay red y en «Tareas de la sucursal».
 *  Las ventas salen de la copia descargada, con su plazo y lo ya devuelto; el servidor vuelve a validar todo al sincronizar. */
@Component({
  selector: 'app-devolucion-offline',
  imports: [BsPipe, FormsModule, DatePipe],
  template: `
    @if (!local.meta()) { <div class="alert warn" role="status">Todavía no hay una copia de las ventas en este dispositivo: se descarga sola cuando hay conexión.</div> }
    @else if (!venta()) {
      <section class="card pad stack">
        <p class="small muted">Ventas recientes de la sucursal, dentro del plazo de devolución, descargadas con el catálogo.</p>
        <label>Buscar por número de comprobante<input name="cb" [ngModel]="filtro()" (ngModelChange)="filtro.set($event)" autocomplete="off" /></label>
        @for (v of ventasVisibles(); track v.comprobante) { <button type="button" class="btn" (click)="elegirVenta(v)">{{ v.comprobante }} · {{ v.total | bs }} · {{ v.pagado_en | date: 'dd/MM HH:mm' }}</button> }
        @empty { <p class="muted small">No hay ventas descargadas con ese comprobante.</p> }
      </section>
    } @else {
      <section class="card pad stack">
        <h3>Venta {{ venta()!.comprobante }}</h3>
        <p class="small muted">Plazo hasta {{ venta()!.vence_el | date: 'dd/MM/yyyy HH:mm' }}</p>
        @for (i of venta()!.items; track i.pedido_item_id) {
          <div class="row between small"><span>{{ i.producto }} ({{ i.talla }}, {{ i.color }}) · vendidas {{ i.vendida }} · se pueden devolver {{ i.devolvible }}</span>
            <input type="number" min="0" [max]="i.devolvible" [ngModel]="cantidades()[i.pedido_item_id] || 0" (ngModelChange)="poner(i.pedido_item_id, $event, i.devolvible)" [name]="'c' + i.pedido_item_id" style="width:5rem" /></div>
        }
        <label>Motivo<input name="mo" [(ngModel)]="motivo" maxlength="200" /></label>
        <label class="check"><input type="checkbox" name="sd" [(ngModel)]="condicion.sin_danos" /> Sin daños</label>
        <label class="check"><input type="checkbox" name="sg" [(ngModel)]="condicion.sin_desgaste" /> Sin desgaste</label>
        <label class="check"><input type="checkbox" name="ce" [(ngModel)]="condicion.con_etiquetas" /> Con sus etiquetas</label>
        @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
        <div class="row"><button class="btn" (click)="venta.set(null)">Volver</button><button class="btn primary" (click)="registrarDevolucion()">Registrar devolución</button></div>
      </section>
    }`,
})
export class DevolucionOfflineComponent {
  readonly local = inject(CatalogoLocalService);
  private cola = inject(ColaOperacionesService);
  private toast = inject(ToastService);
  private auth = inject(AuthService);

  readonly filtro = signal('');
  readonly venta = signal<VentaReciente | null>(null);
  readonly cantidades = signal<Record<number, number>>({});
  readonly error = signal('');
  readonly ventasVisibles = computed(() => (this.local.meta()?.ventas_recientes ?? []).filter((v) => !this.filtro().trim() || v.comprobante.toLowerCase().includes(this.filtro().trim().toLowerCase())));
  motivo = '';
  condicion = { sin_danos: true, sin_desgaste: true, con_etiquetas: true };

  private get sucursalId() { return this.auth.sesion()?.usuario.sucursal_id ?? null; }

  elegirVenta(v: VentaReciente) { this.venta.set(v); this.cantidades.set({}); this.error.set(''); }
  poner(id: number, valor: number, maximo: number) { this.cantidades.update((c) => ({ ...c, [id]: Math.max(0, Math.min(Number(valor) || 0, maximo)) })); }

  /** B3: se valida el plazo guardado en la descarga y lo ya devuelto; el servidor lo vuelve a validar al sincronizar. */
  async registrarDevolucion() {
    const venta = this.venta()!;
    const elegidas = Object.entries(this.cantidades()).filter(([, c]) => c > 0).map(([id, c]) => ({ pedido_item_id: Number(id), cantidad: c }));
    if (new Date() > new Date(venta.vence_el)) { this.error.set(MSG_PLAZO_VENCIDO); return; }
    if (!elegidas.length) { this.error.set('Elija al menos una prenda y su cantidad.'); return; }
    await this.cola.registrar('DEVOLUCION', { comprobante: venta.comprobante, motivo: this.motivo.trim(), items: elegidas, condicion: { ...this.condicion } }, this.sucursalId, `Devolución de ${venta.comprobante}`, { devuelto: { comprobante: venta.comprobante, items: elegidas } });
    await this.local.actualizarExtras((m) => { for (const v of m.ventas_recientes ?? []) if (v.comprobante === venta.comprobante) for (const i of v.items) { const c = elegidas.find((e) => e.pedido_item_id === i.pedido_item_id); if (c) i.devolvible = Math.max(i.devolvible - c.cantidad, 0); } });
    this.toast.ok('Devolución guardada. Se enviará sola al recuperar la conexión.');
    this.venta.set(null); this.motivo = ''; this.error.set('');
  }
}
