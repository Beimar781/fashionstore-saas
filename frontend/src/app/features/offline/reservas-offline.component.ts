import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CatalogoLocalService } from '../../core/offline/catalogo-local.service';
import { OperacionesSucursalService } from '../../core/offline/operaciones-sucursal.service';

/** B4 · Atención de reservas sin conexión (Encargado): validar el código, «Preparar», marcar «No encontrada» y «Atender». Todo sale de la copia descargada y se envía solo al volver la red. */
@Component({
  selector: 'app-reservas-offline',
  imports: [FormsModule, DatePipe],
  template: `
    @if (!local.meta()) { <div class="alert warn" role="status">Todavía no hay una copia de las reservas en este dispositivo: se descarga sola cuando hay conexión.</div> }
    @else {
      <section class="card pad stack">
        <label>Validar el código de la reserva<input name="cr" [ngModel]="filtro()" (ngModelChange)="filtro.set($event)" placeholder="RSV-XXXXXXXX" autocomplete="off" style="text-transform:uppercase" /></label>
        @for (r of visibles(); track r.id) {
          <div class="card pad stack">
            <strong>{{ r.codigo }} · {{ r.estado }}</strong><span class="small muted">{{ r.cliente || 'Cliente' }} · visita {{ r.programada_para | date: 'dd/MM HH:mm' }}</span>
            @for (i of r.items; track i.id) {
              <div class="row between small"><span>{{ i.cantidad }}× {{ i.producto }} ({{ i.talla }}, {{ i.color }}) · {{ i.estado }}</span>
                @if (i.estado === 'RESERVADO' && r.estado !== 'EN_PROBADOR') { <button class="btn sm" (click)="tareas.noEncontrada(r, i.id)">No encontrada</button> }</div>
            }
            <div class="row">
              @if (r.estado === 'PENDIENTE') { <button class="btn sm" (click)="tareas.preparar(r)">Preparar</button> }
              @if (r.estado === 'PENDIENTE' || r.estado === 'PREPARADA') { <button class="btn sm primary" (click)="tareas.atender(r, true)">Atender · lleva las prendas</button><button class="btn sm" (click)="tareas.atender(r, false)">Atender · no las lleva</button> }
              @if (r.estado === 'EN_PROBADOR') { <span class="small muted">Atendida: cobre las prendas en Caja con este código.</span> }
            </div>
          </div>
        } @empty { <p class="muted small">No hay reservas descargadas{{ filtro().trim() ? ' con ese código' : '' }}.</p> }
      </section>
    }`,
})
export class ReservasOfflineComponent {
  readonly local = inject(CatalogoLocalService);
  readonly tareas = inject(OperacionesSucursalService);

  readonly filtro = signal('');
  readonly visibles = computed(() => (this.local.meta()?.reservas_sucursal ?? []).filter((r) => !this.filtro().trim() || r.codigo.toLowerCase().includes(this.filtro().trim().toLowerCase())));
}
