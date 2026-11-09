import { Component, inject, signal } from '@angular/core';
import { AuthService } from '../../core/auth/auth.service';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { CatalogoLocalComponent } from './catalogo-local.component';
import { OperacionesLocalesComponent } from './operaciones.component';
import { RegistrarOfflineComponent } from './registrar-offline.component';
import { RegistroSyncComponent } from './registro-sync.component';
import { ResumenTurnoComponent } from './resumen-turno.component';

type Pestana = 'catalogo' | 'registrar' | 'operaciones' | 'registro' | 'turno';

/** Operación sin conexión (RF18 a RF21): catálogo descargado, registro de ventas de contado o reservas y cola de operaciones con su sincronización. */
@Component({
  selector: 'app-modo-offline',
  imports: [CatalogoLocalComponent, RegistrarOfflineComponent, OperacionesLocalesComponent, RegistroSyncComponent, ResumenTurnoComponent],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Modo sin conexión</h1><p>Descargue el catálogo, registre ventas de contado o reservas aunque no haya Internet y sincronícelas cuando vuelva.</p></div>
        <span class="badge" [class.ok]="red.online()" [class.warn]="!red.online()">{{ red.online() ? 'Con conexión' : 'Sin conexión' }}</span></div>
      <div class="tabs" role="tablist">
        <button role="tab" [class.activa]="pestana() === 'catalogo'" (click)="pestana.set('catalogo')">Catálogo</button>
        <button role="tab" [class.activa]="pestana() === 'registrar'" (click)="pestana.set('registrar')">Registrar</button>
        <button role="tab" [class.activa]="pestana() === 'operaciones'" (click)="pestana.set('operaciones')">Operaciones @if (cola.pendientes().length) { <span class="badge warn">{{ cola.pendientes().length }}</span> }</button>
        @if (!esCliente) { <button role="tab" [class.activa]="pestana() === 'turno'" (click)="pestana.set('turno')">Mi turno</button> }
        <button role="tab" [class.activa]="pestana() === 'registro'" (click)="pestana.set('registro')">Registro</button>
      </div>
      @switch (pestana()) {
        @case ('catalogo') { <app-catalogo-local /> }
        @case ('registrar') { <app-registrar-offline /> }
        @case ('operaciones') { <app-operaciones-locales /> }
        @case ('registro') { <app-registro-sync /> }
        @case ('turno') { <app-resumen-turno /> }
      }
    </div>`,
})
export class ModoOfflinePage {
  readonly red = inject(ConnectivityService);
  readonly cola = inject(ColaOperacionesService);
  readonly pestana = signal<Pestana>('catalogo');
  readonly esCliente = inject(AuthService).rol() === 'Cliente';
}
