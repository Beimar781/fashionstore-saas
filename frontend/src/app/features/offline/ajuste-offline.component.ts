import { Component, inject, signal, viewChild } from '@angular/core';
import { ErrorComponent } from '../../core/ui/vacio.component';
import { FormsModule } from '@angular/forms';
import { CatalogoLocalService, PrendaLocal } from '../../core/offline/catalogo-local.service';
import { MOTIVOS_AJUSTE, MotivoAjuste, OperacionesSucursalService } from '../../core/offline/operaciones-sucursal.service';
import { BuscadorPrendaComponent } from './buscador-prenda.component';

/** B6 · Ajuste de inventario sin conexión (Encargado): conteo, merma o daño. Viaja como diferencia; si dejaría el stock negativo, el servidor lo deja en conflicto. */
@Component({
  selector: 'app-ajuste-offline',
  imports: [ErrorComponent, FormsModule, BuscadorPrendaComponent],
  template: `
    @if (!local.meta()) { <div class="alert warn" role="status">Todavía no hay una copia del catálogo en este dispositivo: se descarga sola cuando hay conexión.</div> }
    @else {
      <section class="card pad stack">
        <p class="small muted">El ajuste se envía como diferencia (no como valor absoluto) para no pisar las ventas hechas mientras tanto. Si dejaría el stock negativo, queda en conflicto.</p>
        <app-buscador-prenda (prenda)="prenda.set($event)" />
        <label>Diferencia (por ejemplo +3 o -2)<input type="number" name="df" [(ngModel)]="diferencia" /></label>
        <label>Motivo (obligatorio)<select name="mt" [(ngModel)]="motivo">@for (m of motivos; track m.valor) { <option [value]="m.valor">{{ m.texto }}</option> }</select></label>
        <label>Nota (opcional)<input name="nt" [(ngModel)]="nota" maxlength="150" /></label>
        @if (error()) { <app-error [texto]="error()" /> }
        <button class="btn primary" (click)="registrar()">Registrar ajuste</button>
      </section>
    }`,
})
export class AjusteOfflineComponent {
  readonly local = inject(CatalogoLocalService);
  private tareas = inject(OperacionesSucursalService);
  private buscador = viewChild(BuscadorPrendaComponent);

  readonly motivos = MOTIVOS_AJUSTE;
  readonly prenda = signal<PrendaLocal | null>(null);
  readonly error = signal('');
  diferencia: number | null = null; motivo: MotivoAjuste = 'CONTEO'; nota = '';

  async registrar() {
    const p = this.prenda();
    if (!p || !this.diferencia) { this.error.set('Elija la prenda e indique la diferencia (positiva o negativa, distinta de cero).'); return; }
    await this.tareas.ajustar(p.variante.id, this.diferencia, this.motivo, this.nota, `${p.producto.nombre} (${p.variante.talla}, ${p.variante.color})`);
    this.buscador()?.limpiar();
    this.diferencia = null; this.nota = ''; this.error.set('');
  }
}
