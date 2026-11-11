import { Component, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CatalogoLocalService, PrendaLocal } from '../../core/offline/catalogo-local.service';
import { OperacionesSucursalService } from '../../core/offline/operaciones-sucursal.service';
import { BuscadorPrendaComponent } from './buscador-prenda.component';

/** B5 · Recepción de mercadería sin conexión (Encargado): sube el inventario local de forma provisional y se envía sola al volver la red. */
@Component({
  selector: 'app-recepcion-offline',
  imports: [FormsModule, BuscadorPrendaComponent],
  template: `
    @if (!local.meta()) { <div class="alert warn" role="status">Todavía no hay una copia del catálogo en este dispositivo: se descarga sola cuando hay conexión.</div> }
    @else {
      <section class="card pad stack">
        <p class="small muted">La mercadería recibida sube el inventario de forma provisional hasta sincronizar.</p>
        <app-buscador-prenda (prenda)="prenda.set($event)" />
        <label>Cantidad recibida<input type="number" min="1" name="qr" [(ngModel)]="cantidad" /></label>
        <label>Referencia del envío o proveedor<input name="rf" [(ngModel)]="referencia" maxlength="100" /></label>
        @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
        <button class="btn primary" (click)="registrar()">Registrar recepción</button>
      </section>
    }`,
})
export class RecepcionOfflineComponent {
  readonly local = inject(CatalogoLocalService);
  private tareas = inject(OperacionesSucursalService);
  private buscador = viewChild(BuscadorPrendaComponent);

  readonly prenda = signal<PrendaLocal | null>(null);
  readonly error = signal('');
  cantidad = 1; referencia = '';

  async registrar() {
    const p = this.prenda();
    if (!p || !(this.cantidad >= 1)) { this.error.set('Elija la prenda e indique una cantidad de 1 o más.'); return; }
    if (!this.referencia.trim()) { this.error.set('Indique la referencia del envío o del proveedor.'); return; }
    await this.tareas.recibir(p.variante.id, this.cantidad, this.referencia, `${p.producto.nombre} (${p.variante.talla}, ${p.variante.color})`);
    this.buscador()?.limpiar();
    this.referencia = ''; this.cantidad = 1; this.error.set('');
  }
}
