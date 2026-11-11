import { Component, OnInit, inject, signal } from '@angular/core';
import { AuthService } from '../../core/auth/auth.service';
import { CatalogoLocalService } from '../../core/offline/catalogo-local.service';
import { AjusteOfflineComponent } from './ajuste-offline.component';
import { DevolucionOfflineComponent } from './devolucion-offline.component';
import { RecepcionOfflineComponent } from './recepcion-offline.component';
import { ReservasOfflineComponent } from './reservas-offline.component';

type Tarea = 'devolucion' | 'recepcion' | 'ajuste' | 'reservas';

/** B3 a B6 · Tareas de la sucursal sin conexión, reunidas en el panel de diagnóstico. El Cajero devuelve prendas; el Encargado, además, recibe mercadería, ajusta el inventario y atiende reservas.
 *  Son los mismos componentes que usan las pantallas normales (Devoluciones, Recepción, Inventario y Reservas) cuando no hay conexión. */
@Component({
  selector: 'app-tareas-sucursal',
  imports: [DevolucionOfflineComponent, RecepcionOfflineComponent, AjusteOfflineComponent, ReservasOfflineComponent],
  template: `
    <section class="stack">
      <div class="tabs" role="tablist">
        <button role="tab" [class.activa]="tarea() === 'devolucion'" (click)="tarea.set('devolucion')">Devolución</button>
        @if (encargado) {
          <button role="tab" [class.activa]="tarea() === 'recepcion'" (click)="tarea.set('recepcion')">Recepción</button>
          <button role="tab" [class.activa]="tarea() === 'ajuste'" (click)="tarea.set('ajuste')">Ajuste de inventario</button>
          <button role="tab" [class.activa]="tarea() === 'reservas'" (click)="tarea.set('reservas')">Reservas</button>
        }
      </div>
      @switch (tarea()) {
        @case ('devolucion') { <app-devolucion-offline /> }
        @case ('recepcion') { <app-recepcion-offline /> }
        @case ('ajuste') { <app-ajuste-offline /> }
        @case ('reservas') { <app-reservas-offline /> }
      }
    </section>`,
})
export class TareasSucursalComponent implements OnInit {
  private local = inject(CatalogoLocalService);

  readonly encargado = inject(AuthService).rol() === 'Encargado';
  readonly tarea = signal<Tarea>('devolucion');

  ngOnInit() { void this.local.cargar(); }
}
