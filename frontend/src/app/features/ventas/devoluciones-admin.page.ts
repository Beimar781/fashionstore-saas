import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DevolucionesApi } from '../../core/api/devoluciones.api';
import { Devolucion } from '../../core/devoluciones.models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** CU-41 · Administrador: plazo de devolución de la empresa y consulta de todas las notas de devolución y cambio. */
@Component({
  selector: 'app-devoluciones-admin',
  imports: [FormsModule, DatePipe],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Devoluciones y cambios</h1><p>Plazo de devolución de la empresa y notas registradas en todas las sucursales.</p></div></div>

      <form class="card pad row" style="margin-bottom:1rem" (ngSubmit)="guardarPlazo()">
        <label style="max-width:240px">Plazo de devolución (días desde el pago)<input name="p" type="number" min="0" max="365" [(ngModel)]="plazo" /></label>
        <button class="btn primary" style="align-self:end">Guardar plazo</button>
      </form>

      <form class="card pad row" style="margin-bottom:1rem" (ngSubmit)="cargar()">
        <label style="max-width:170px">Desde<input name="d" type="date" [(ngModel)]="desde" /></label>
        <label style="max-width:170px">Hasta<input name="h" type="date" [(ngModel)]="hasta" /></label>
        <button class="btn" style="align-self:end">Consultar</button>
      </form>
      @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }

      <div class="card table-wrap">
        @if (!notas().length) { <div class="empty">No hay devoluciones ni cambios en ese periodo.</div> } @else {
          <table>
            <thead><tr><th>Nota</th><th>Fecha</th><th>Sucursal</th><th>Tipo</th><th>Comprobante</th><th>Motivo</th><th class="right">Devuelto</th><th class="right">Reembolso</th><th class="right">Cobrado</th><th></th></tr></thead>
            <tbody>
              @for (d of notas(); track d.id) {
                <tr><td><strong>{{ d.numero }}</strong></td><td class="nowrap">{{ d.fecha | date: 'dd/MM HH:mm' }}</td><td>{{ d.sucursal }}</td><td>{{ d.tipo === 'CAMBIO' ? 'Cambio' : 'Devolución' }}</td><td>{{ d.comprobante }}</td><td>{{ d.motivo }}</td>
                  <td class="right nowrap">Bs {{ d.monto_devuelto }}</td><td class="right nowrap">Bs {{ d.reembolso }}</td><td class="right nowrap">Bs {{ d.cobro_adicional }}</td><td class="actions"><button class="btn sm" (click)="imprimir(d)">Nota</button></td></tr>
              }
            </tbody>
          </table>
        }
      </div>
    </div>`,
})
export class DevolucionesAdminPage implements OnInit {
  private api = inject(DevolucionesApi);
  private toast = inject(ToastService);

  readonly notas = signal<Devolucion[]>([]);
  readonly error = signal('');
  plazo = 15; desde = ''; hasta = '';

  ngOnInit() {
    this.api.plazo().subscribe({ next: (c) => (this.plazo = c.plazo_dias), error: (e) => this.error.set(mensajeError(e)) });
    this.cargar();
  }

  cargar() {
    this.error.set('');
    this.api.listar({ desde: this.desde, hasta: this.hasta }).subscribe({ next: (l) => this.notas.set(l), error: (e) => this.error.set(mensajeError(e)) });
  }

  guardarPlazo() {
    this.api.fijarPlazo(Number(this.plazo)).subscribe({
      next: (c) => { this.plazo = c.plazo_dias; this.toast.ok(`Plazo de devolución: ${c.plazo_dias} días.`); },
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }

  imprimir(d: Devolucion) { this.api.nota(d.id).subscribe({ next: (blob) => window.open(URL.createObjectURL(blob), '_blank'), error: (e) => this.toast.error(mensajeError(e)) }); }
}
